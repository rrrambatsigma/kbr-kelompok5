package id.ac.uns.kbr.reasoning_api.service;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.Function;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.annotation.Nullable;

import openllet.owlapi.OpenlletReasoner;
import openllet.owlapi.OpenlletReasonerFactory;

import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.IRI;
import org.semanticweb.owlapi.model.OWLAnnotation;
import org.semanticweb.owlapi.model.OWLClass;
import org.semanticweb.owlapi.model.OWLDataFactory;
import org.semanticweb.owlapi.model.OWLLiteral;
import org.semanticweb.owlapi.model.OWLNamedIndividual;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyManager;
import org.semanticweb.owlapi.reasoner.InferenceType;
import org.semanticweb.owlapi.reasoner.InconsistentOntologyException;
import org.semanticweb.owlapi.reasoner.NodeSet;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import id.ac.uns.kbr.reasoning_api.exception.OntologyLoadException;
import id.ac.uns.kbr.reasoning_api.exception.OntologyNotLoadedException;
import id.ac.uns.kbr.reasoning_api.exception.ReasoningTimeoutException;
import id.ac.uns.kbr.reasoning_api.model.OntologySnapshot;

/**
 * Owns the ontology/reasoner lifecycle.
 *
 * <ul>
 *   <li>Loads the ontology at application startup.</li>
 *   <li>Reloads atomically: a failed load never replaces the previous state.</li>
 *   <li>Guards every reasoner read with a read/write lock.</li>
 *   <li>Precomputes classification and caches disease categories so request
 *       handlers never query a mutable reasoner concurrently.</li>
 * </ul>
 */
@Service
public class OntologyProvider {

    private static final Logger log = LoggerFactory.getLogger(OntologyProvider.class);

    public static final String PTP_NAMESPACE =
            "http://kbr.kelompok5.org/penyakit-tanaman-pangan#";

    private static final List<String> DISEASE_CATEGORIES = List.of(
            "PenyakitJamur",
            "PenyakitBakteri",
            "PenyakitVirus",
            "PenyakitLainnya"
    );

    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

    private final Path ontologyPath;
    private final long reasoningTimeoutMs;
    private final boolean failFast;

    private volatile OntologySnapshot snapshot;
    private volatile String lastError;

    public OntologyProvider(
            @Value("${ontology.file-path}") String ontologyFilePath,
            @Value("${ontology.reasoning-timeout-ms:120000}") long reasoningTimeoutMs,
            @Value("${ontology.fail-fast:false}") boolean failFast
    ) {
        this.ontologyPath = Path.of(ontologyFilePath).toAbsolutePath().normalize();
        this.reasoningTimeoutMs = reasoningTimeoutMs;
        this.failFast = failFast;
    }

    @PostConstruct
    public void init() {
        try {
            reload();
            log.info(
                    "Ontology loaded at startup: file={}, checksum={}, consistent={}",
                    snapshot.sourceFile(),
                    snapshot.checksum(),
                    snapshot.consistent()
            );
        } catch (RuntimeException e) {
            lastError = safeMessage(e);
            log.error("Ontology gagal dimuat saat startup: {}", safeMessage(e), e);
            if (failFast) {
                throw new IllegalStateException(
                        "Ontology gagal dimuat saat startup: " + safeMessage(e),
                        e
                );
            }
            log.warn("Aplikasi tetap berjalan tanpa ontology. Status readiness akan DOWN.");
        }
    }

    /**
     * Builds a complete new snapshot and swaps it in. The old snapshot is only
     * disposed after the new one is valid, so a failed reload keeps the old
     * state intact.
     */
    public OntologySnapshot reload() {
        lock.writeLock().lock();
        try {
            OntologySnapshot next = buildSnapshot();
            OntologySnapshot previous = snapshot;
            snapshot = next;
            lastError = null;
            disposeSnapshot(previous);
            return next;
        } catch (RuntimeException e) {
            lastError = safeMessage(e);
            throw e;
        } finally {
            lock.writeLock().unlock();
        }
    }

    @PreDestroy
    public void shutdown() {
        lock.writeLock().lock();
        try {
            OntologySnapshot current = snapshot;
            snapshot = null;
            disposeSnapshot(current);
        } finally {
            lock.writeLock().unlock();
        }
    }

    public boolean isLoaded() {
        return snapshot != null;
    }

    public boolean isReady() {
        OntologySnapshot current = snapshot;
        return current != null && current.consistent();
    }

    public Optional<OntologySnapshot> current() {
        return Optional.ofNullable(snapshot);
    }

    @Nullable
    public String lastError() {
        return lastError;
    }

    public Path ontologyPath() {
        return ontologyPath;
    }

    /**
     * Runs a read-only operation against a stable snapshot while holding the
     * read lock. Reload cannot swap the reasoner during the operation.
     */
    public <T> T withSnapshot(Function<OntologySnapshot, T> operation) {
        lock.readLock().lock();
        try {
            OntologySnapshot current = snapshot;
            if (current == null) {
                throw new OntologyNotLoadedException(
                        "Ontology belum dimuat. Periksa log startup atau panggil reload."
                );
            }
            return operation.apply(current);
        } finally {
            lock.readLock().unlock();
        }
    }

    private OntologySnapshot buildSnapshot() {
        validateOntologyFile();

        OWLOntologyManager manager = null;
        OpenlletReasoner reasoner = null;

        try {
            String checksum = sha256(ontologyPath);

            manager = OWLManager.createOWLOntologyManager();
            OWLOntology ontology =
                    manager.loadOntologyFromOntologyDocument(ontologyPath.toFile());

            reasoner = OpenlletReasonerFactory.getInstance().createReasoner(ontology);

            InferenceResult inference = computeInferences(manager, reasoner);

            String ontologyIri = ontology.getOntologyID()
                    .getOntologyIRI()
                    .map(IRI::toString)
                    .orElse(null);

            String version = extractVersion(ontology)
                    .orElseGet(() -> checksum.substring(0, Math.min(12, checksum.length())));

            log.info(
                    "Inference selesai: consistent={}, diseaseCategories={}, unclassified={}",
                    inference.consistent(),
                    inference.categoryCounts(),
                    inference.unclassifiedDiseaseCount()
            );

            return new OntologySnapshot(
                    manager,
                    ontology,
                    reasoner,
                    ontologyIri,
                    version,
                    ontologyPath.getFileName().toString(),
                    checksum,
                    inference.consistent(),
                    Instant.now(),
                    ontology.getClassesInSignature().size(),
                    ontology.getIndividualsInSignature().size(),
                    ontology.getObjectPropertiesInSignature().size(),
                    ontology.getDataPropertiesInSignature().size(),
                    Map.copyOf(inference.categoryByIri()),
                    Map.copyOf(inference.categoryCounts()),
                    inference.unclassifiedDiseaseCount()
            );
        } catch (RuntimeException e) {
            disposeReasoner(reasoner);
            clearManager(manager);
            if (e instanceof OntologyLoadException
                    || e instanceof ReasoningTimeoutException) {
                throw e;
            }
            throw new OntologyLoadException(
                    "Gagal memuat ontology: " + safeMessage(e),
                    e
            );
        } catch (Exception e) {
            disposeReasoner(reasoner);
            clearManager(manager);
            throw new OntologyLoadException(
                    "Gagal memuat ontology: " + safeMessage(e),
                    e
            );
        }
    }

    private void validateOntologyFile() {
        if (!Files.exists(ontologyPath)) {
            throw new OntologyLoadException(
                    "File ontology tidak ditemukan: " + ontologyPath.getFileName()
            );
        }
        if (!Files.isRegularFile(ontologyPath)) {
            throw new OntologyLoadException(
                    "Path ontology bukan file biasa: " + ontologyPath.getFileName()
            );
        }
        if (!Files.isReadable(ontologyPath)) {
            throw new OntologyLoadException(
                    "File ontology tidak dapat dibaca: " + ontologyPath.getFileName()
            );
        }
    }

    private InferenceResult computeInferences(
            OWLOntologyManager manager,
            OpenlletReasoner reasoner
    ) {
        return runTimed("classify-and-cache", () -> {
            boolean consistent = isConsistent(reasoner);

            Map<String, String> categoryByIri = new LinkedHashMap<>();
            Map<String, Long> categoryCounts = new LinkedHashMap<>();
            long unclassified = 0L;

            if (consistent) {
                reasoner.precomputeInferences(
                        InferenceType.CLASS_HIERARCHY,
                        InferenceType.CLASS_ASSERTIONS
                );

                OWLDataFactory dataFactory = manager.getOWLDataFactory();
                OWLClass penyakit = dataFactory.getOWLClass(
                        IRI.create(PTP_NAMESPACE + "Penyakit")
                );

                NodeSet<OWLNamedIndividual> diseases =
                        reasoner.getInstances(penyakit, false);

                for (OWLNamedIndividual disease : diseases.getFlattened()) {
                    String category = resolveCategory(reasoner, disease);
                    if (category == null) {
                        unclassified++;
                    } else {
                        categoryByIri.put(disease.getIRI().toString(), category);
                        categoryCounts.merge(category, 1L, Long::sum);
                    }
                }
            }

            for (String category : DISEASE_CATEGORIES) {
                categoryCounts.putIfAbsent(category, 0L);
            }

            return new InferenceResult(
                    consistent,
                    categoryByIri,
                    categoryCounts,
                    unclassified
            );
        });
    }

    private boolean isConsistent(OpenlletReasoner reasoner) {
        try {
            return reasoner.isConsistent();
        } catch (InconsistentOntologyException exception) {
            return false;
        }
    }

    @Nullable
    private String resolveCategory(
            OpenlletReasoner reasoner,
            OWLNamedIndividual individual
    ) {
        Set<String> typeLocalNames = new LinkedHashSet<>();

        collectTypeLocalNames(reasoner, individual, false, typeLocalNames);
        if (typeLocalNames.isEmpty()) {
            collectTypeLocalNames(reasoner, individual, true, typeLocalNames);
        }

        for (String category : DISEASE_CATEGORIES) {
            if (typeLocalNames.contains(category)) {
                return category;
            }
        }
        return null;
    }

    private void collectTypeLocalNames(
            OpenlletReasoner reasoner,
            OWLNamedIndividual individual,
            boolean direct,
            Set<String> target
    ) {
        NodeSet<OWLClass> types = reasoner.getTypes(individual, direct);
        for (OWLClass type : types.getFlattened()) {
            IRI iri = type.getIRI();
            if (iri.getNamespace().equals(PTP_NAMESPACE)) {
                target.add(iri.getFragment());
            }
        }
    }

    private <T> T runTimed(String operation, Callable<T> task) {
        ExecutorService executor = Executors.newSingleThreadExecutor(runnable -> {
            Thread thread = new Thread(runnable, "kbr-reasoner-" + operation);
            thread.setDaemon(true);
            return thread;
        });

        try {
            Future<T> future = executor.submit(task);
            return future.get(reasoningTimeoutMs, TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            log.error(
                    "Reasoning '{}' melebihi batas {} ms; thread akan dihentikan",
                    operation,
                    reasoningTimeoutMs
            );
            throw new ReasoningTimeoutException(
                    "Reasoning '" + operation + "' melebihi batas "
                            + reasoningTimeoutMs + " ms"
            );
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new OntologyLoadException("Proses reasoning diinterupsi", e);
        } catch (ExecutionException e) {
            Throwable cause = e.getCause() == null ? e : e.getCause();
            if (cause instanceof RuntimeException runtime) {
                throw runtime;
            }
            throw new OntologyLoadException(
                    "Reasoning gagal pada tahap " + operation + ": " + safeMessage(cause),
                    cause
            );
        } finally {
            executor.shutdownNow();
        }
    }

    private Optional<String> extractVersion(OWLOntology ontology) {
        OWLDataFactory dataFactory = OWLManager.getOWLDataFactory();
        var versionInfo = dataFactory.getOWLVersionInfo();

        Optional<String> fromAnnotation = ontology.annotations()
                .filter(annotation -> annotation.getProperty().equals(versionInfo))
                .map(OWLAnnotation::getValue)
                .map(value -> value.asLiteral())
                .flatMap(Optional::stream)
                .map(OWLLiteral::getLiteral)
                .findFirst();

        if (fromAnnotation.isPresent()) {
            return fromAnnotation;
        }

        return ontology.getOntologyID()
                .getVersionIRI()
                .map(IRI::toString);
    }

    private String sha256(Path file) {
        try (InputStream input = Files.newInputStream(file)) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) != -1) {
                digest.update(buffer, 0, read);
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (IOException | NoSuchAlgorithmException e) {
            throw new OntologyLoadException(
                    "Gagal menghitung checksum ontology: " + safeMessage(e),
                    e
            );
        }
    }

    private void disposeSnapshot(@Nullable OntologySnapshot old) {
        if (old == null) {
            return;
        }
        disposeReasoner(old.reasoner());
        clearManager(old.manager());
    }

    private void disposeReasoner(@Nullable OpenlletReasoner oldReasoner) {
        if (oldReasoner == null) {
            return;
        }
        try {
            oldReasoner.dispose();
        } catch (RuntimeException e) {
            log.warn("Gagal dispose reasoner lama: {}", safeMessage(e));
        }
    }

    private void clearManager(@Nullable OWLOntologyManager oldManager) {
        if (oldManager == null) {
            return;
        }
        try {
            oldManager.clearOntologies();
        } catch (RuntimeException e) {
            log.warn("Gagal membersihkan ontology manager lama: {}", safeMessage(e));
        }
    }

    private static String safeMessage(Throwable throwable) {
        String message = throwable.getMessage();
        if (message == null || message.isBlank()) {
            return throwable.getClass().getSimpleName();
        }
        return message;
    }

    private record InferenceResult(
            boolean consistent,
            Map<String, String> categoryByIri,
            Map<String, Long> categoryCounts,
            long unclassifiedDiseaseCount
    ) {
    }
}
