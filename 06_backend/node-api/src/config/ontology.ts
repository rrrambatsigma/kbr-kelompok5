/**
 * Satu sumber kebenaran untuk kosakata ontology PTP yang dipakai backend.
 *
 * Ontology saat ini masih sementara. Saat TTL final masuk, file ini dan
 * fixture kasus uji yang perlu ditinjau - bukan seluruh service.
 */
export const PTP_NAMESPACE =
  "http://kbr.kelompok5.org/penyakit-tanaman-pangan#";

export const ONTOLOGY_VOCABULARY = {
  classes: {
    plant: "TanamanPangan",
    disease: "Penyakit",
    symptom: "Gejala",
    canonicalSymptom: "GejalaKanonik",
    control: "Pengendalian",
    riskFactor: "FaktorRisiko",
  },
  properties: {
    attacksPlant: "menyerangTanaman",
    hasSymptom: "memilikiGejala",
    hasCanonicalSymptom: "memilikiGejalaKanonik",
    controlledBy: "dikendalikanDengan",
    causedBy: "disebabkanOleh",
    influencedBy: "dipengaruhiOleh",
    diseaseDescription: "deskripsiPenyakit",
    severity: "tingkatKeparahan",
    attacksPart: "menyerangBagian",
    attacksPhase: "menyerangFase",
  },
} as const;

const VOCAB = ONTOLOGY_VOCABULARY;

/** Wajib ada; tanpa ini diagnosis tidak bisa berjalan. */
export const REQUIRED_ONTOLOGY_VOCABULARY = {
  classes: [VOCAB.classes.plant, VOCAB.classes.disease, VOCAB.classes.symptom],
  properties: [VOCAB.properties.attacksPlant, VOCAB.properties.hasSymptom],
} as const;

/** Boleh hilang; fitur terkait otomatis nonaktif, sistem tetap jalan. */
export const OPTIONAL_ONTOLOGY_VOCABULARY = {
  classes: [
    VOCAB.classes.canonicalSymptom,
    VOCAB.classes.control,
    VOCAB.classes.riskFactor,
  ],
  properties: [
    VOCAB.properties.hasCanonicalSymptom,
    VOCAB.properties.controlledBy,
    VOCAB.properties.causedBy,
    VOCAB.properties.influencedBy,
    VOCAB.properties.diseaseDescription,
    VOCAB.properties.severity,
  ],
} as const;

/** Urutan tampilan fase pertumbuhan (kelas ontology, bukan individu). */
export const PHASE_ORDER = [
  "FasePembibitan",
  "FaseVegetatif",
  "FaseAnakan",
  "FaseGeneratif",
  "FasePemasakan",
  "FasePanen",
] as const;

/** Prioritas saat satu penyakit punya lebih dari satu kategori inferred. */
export const DISEASE_CATEGORY_PRIORITY = [
  "PenyakitJamur",
  "PenyakitBakteri",
  "PenyakitVirus",
  "PenyakitOomycete",
  "PenyakitFitoplasma",
  "PenyakitLainnya",
] as const;

export function ptpIri(localName: string): string {
  return `${PTP_NAMESPACE}${localName}`;
}
