package org.kbr.kelompok5;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.kbr.kelompok5.repository.OntologyRepository;
import org.kbr.kelompok5.repository.OntologyRows.DiseaseRow;
import org.kbr.kelompok5.repository.OntologyRows.PathogenRow;
import org.kbr.kelompok5.repository.OntologyRows.PlantRow;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class OntologyRepositoryTest {

    @Autowired
    private OntologyRepository repository;

    @Test
    void ontologyCountsMatchCurrentData() {
        assertThat(repository.countByType("TanamanPangan")).isEqualTo(7);
        assertThat(repository.countByType("Penyakit")).isEqualTo(57);
        assertThat(repository.countByType("Gejala")).isEqualTo(240);
        assertThat(repository.countByType("Patogen")).isEqualTo(59);
        assertThat(repository.countByType("Pengendalian")).isEqualTo(261);
        assertThat(repository.countByType("Varietas")).isEqualTo(34);
        assertThat(repository.countByType("BagianTanaman")).isEqualTo(6);
        assertThat(repository.countByType("FasePertumbuhan")).isEqualTo(3);
        assertThat(repository.countByType("FaktorLingkungan")).isEqualTo(5);
        assertThat(repository.countByType("Referensi")).isEqualTo(2);
    }

    @Test
    void plantLookupContainsCountsAndScientificName() {
        PlantRow padi = repository.findPlant("Padi").orElseThrow();
        assertThat(padi.label()).isEqualTo("Padi");
        assertThat(padi.scientificName()).isNull();
        assertThat(padi.diseaseCount()).isEqualTo(5);
        assertThat(padi.varietyCount()).isEqualTo(4);
        assertThat(padi.generalControlCount()).isZero();

        PlantRow kedelai = repository.findPlant("Kedelai").orElseThrow();
        assertThat(kedelai.scientificName()).isEqualTo("Glycine max L. Merril");
        assertThat(kedelai.diseaseCount()).isEqualTo(18);
        assertThat(kedelai.varietyCount()).isEqualTo(11);
    }

    @Test
    void diseaseLookupContainsSymptomsAndControls() {
        DiseaseRow blas = repository.findDisease("PenyakitBlasPadi").orElseThrow();
        assertThat(blas.label()).isEqualTo("Penyakit Blas");
        assertThat(blas.plant().id()).isEqualTo("Padi");
        assertThat(blas.pathogenNames()).containsExactly(
                "Magnaporthe grisea",
                "Pyricularia grisea",
                "Pyricularia oryzae");
        assertThat(blas.symptomCount()).isEqualTo(7);
        assertThat(blas.controlCount()).isEqualTo(8);

        DiseaseRow antraknosa = repository.findDisease("ANTRAKNOSAKedelai").orElseThrow();
        assertThat(antraknosa.symptomCount()).isEqualTo(2);
        assertThat(antraknosa.controlCount()).isEqualTo(4);
    }

    @Test
    void pathogenTypeIsAvailableWhenAsserted() {
        assertThat(repository.findPathogensOfDisease("PenyakitBlasPadi"))
                .extracting(PathogenRow::id)
                .containsExactly(
                        "MagnaportheGrisea",
                        "PyriculariaGrisea",
                        "PyriculariaOryzae");

        PathogenRow pathogen = repository.findPathogensOfDisease("PenyakitBlasPadi").get(0);
        assertThat(pathogen.scientificName()).isEqualTo("Magnaporthe grisea");
        assertThat(pathogen.type()).isEqualTo("Jamur");
    }

    @Test
    void diseaseWithoutPathogenReturnsEmpty() {
        assertThat(repository.findPathogensOfDisease(
                "NekrosisPadaTitikTunasCassavaBudNecrosisUbiKayu")).isEmpty();
    }

    @Test
    void diseaseListsContainEachDiseaseOnce() {
        assertThat(repository.findAllDiseases())
                .hasSize(57)
                .extracting(DiseaseRow::id)
                .doesNotHaveDuplicates();

        assertThat(repository.findDiseasesByPlant("Kedelai"))
                .extracting(DiseaseRow::id)
                .doesNotHaveDuplicates();

        assertThat(repository.findDisease("KARATKedelai").orElseThrow().pathogenNames())
                .hasSize(2);
    }

    @Test
    void symptomQueriesRespectPlantAndDiseaseFilters() {
        assertThat(repository.findSymptomsByPlant("Padi")).hasSize(32);
        assertThat(repository.findSymptomsByPlant("Kedelai")).hasSize(94);
        assertThat(repository.findSymptomsByDisease("PenyakitBlasPadi")).hasSize(7);
        assertThat(repository.findAllSymptoms()).hasSize(240);
    }

    @Test
    void controlsAndReferencesAreMapped() {
        assertThat(repository.findControlsOfDisease("ANTRAKNOSAKedelai")).hasSize(4);
        assertThat(repository.findGeneralControlsOfPlant("KacangTanah")).hasSize(40);
        assertThat(repository.findGeneralControlsOfPlant("UbiKayu")).hasSize(5);

        assertThat(repository.findReferencesOfDisease("PenyakitBlasPadi"))
                .singleElement()
                .satisfies(reference -> {
                    assertThat(reference.id()).isEqualTo("BukuDOC002");
                    assertThat(reference.title()).isNotBlank();
                    assertThat(reference.year()).isEqualTo(2021);
                });
    }

    @Test
    void varietiesAndDiseaseRelationsAreMapped() {
        assertThat(repository.findVarietiesOfPlant("Padi")).hasSize(4);
        assertThat(repository.findPartsOfDisease("PenyakitBlasPadi"))
                .extracting(ref -> ref.id())
                .containsExactly("Daun");
        assertThat(repository.findEnvironmentalFactorsOfDisease("PenyakitBlasPadi"))
                .extracting(ref -> ref.id())
                .containsExactly("KondisiMusimHujan");
        assertThat(repository.findPhasesOfDisease("PenyakitBlasPadi")).isEmpty();
    }
}
