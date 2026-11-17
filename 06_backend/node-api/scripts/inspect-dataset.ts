/**
 * Utilitas dev: menampilkan dataset diagnosis ternormalisasi untuk satu tanaman.
 *
 *   npm run dataset:inspect -- Padi
 *
 * Dipakai untuk memeriksa layer data sebelum/sesudah ontology diganti.
 */
import { getDiagnosisDataset } from "../src/services/knowledge.service.js";

const plantId = process.argv[2] ?? "Padi";
const dataset = await getDiagnosisDataset(plantId);

console.log(
  JSON.stringify(
    {
      plant: {
        id: dataset.plant.id,
        label: dataset.plant.label,
        iri: dataset.plant.iri,
      },
      stats: dataset.stats,
      diseases: dataset.diseases.map((disease) => ({
        id: disease.id,
        label: disease.label,
        symptomCount: disease.symptoms.length,
        canonicalSymptomCount: disease.symptoms.filter(
          (symptom) => symptom.canonical !== null
        ).length,
        riskFactors: disease.riskFactors.map((factor) => factor.label),
        hasDescription: disease.description !== null,
        severity: disease.severity,
      })),
    },
    null,
    2
  )
);
