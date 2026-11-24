import { ptpNamespace } from "../config/fuseki.js";
import { PHASE_ORDER } from "../config/ontology.js";
import { InvalidRequestError, NotFoundError } from "../lib/errors.js";
import {
  ask,
  localName,
  requireIntegerTerm,
  select,
  termValue,
  type SparqlBinding,
} from "./fuseki.service.js";

const PREFIXES = `
PREFIX ptp: <${ptpNamespace}>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
`;

const SAFE_IRI = /^https?:\/\/[^\s<>"{}|\\^`]+$/;
const SAFE_LOCAL_NAME = /^[A-Za-z_][A-Za-z0-9_.-]*$/;

export function toIri(raw: string): string {
  const trimmed = raw.trim();

  if (SAFE_IRI.test(trimmed)) {
    return trimmed;
  }

  if (!SAFE_LOCAL_NAME.test(trimmed)) {
    throw new InvalidRequestError(
      `ID tidak valid: "${raw}". Gunakan local name atau IRI penuh.`
    );
  }

  return `${ptpNamespace}${trimmed}`;
}

export interface NamedEntity {
  id: string;
  iri: string;
  label: string;
}

export interface PlantSummary extends NamedEntity {
  scientificName: string | null;
  diseaseCount: number;
}

export interface DiseaseSummary extends NamedEntity {
  plantId: string | null;
  plantLabel: string | null;
  symptomCount: number;
}

export interface SymptomSummary extends NamedEntity {
  partId: string | null;
  partLabel: string | null;
  canonicalId: string | null;
  canonicalLabel: string | null;
}

export interface PhaseSummary extends NamedEntity {
  diseaseCount: number;
}

export interface ControlSummary extends NamedEntity {
  description: string | null;
}

export interface PathogenSummary extends NamedEntity {
  scientificName: string | null;
}

export interface DiseaseDetail extends DiseaseSummary {
  symptoms: SymptomSummary[];
  controls: ControlSummary[];
  pathogens: PathogenSummary[];
  parts: NamedEntity[];
  phases: NamedEntity[];
  riskFactors: NamedEntity[];
}

export interface CanonicalSymptom {
  id: string;
  iri: string;
  label: string;
}

export interface DiagnosisSymptom {
  id: string;
  iri: string;
  label: string;
  canonical: CanonicalSymptom | null;
}

export interface DiagnosisDisease {
  id: string;
  iri: string;
  label: string;
  symptoms: DiagnosisSymptom[];
  riskFactors: NamedEntity[];
  phases: NamedEntity[];
  description: string | null;
  severity: string | null;
}

export interface DiagnosisDatasetStats {
  diseaseCount: number;
  diseaseWithSymptomsCount: number;
  symptomObservationCount: number;
  canonicalObservationCount: number;
  canonicalConceptCount: number;
}

/**
 * Bentuk data ternormalisasi yang menjadi input mesin reasoning.
 *
 * Layer ini sengaja tidak mengetahui SPARQL/ontology mentah; engine hanya
 * menerima struktur ini. Dengan begitu ontology sementara bisa diganti tanpa
 * mengubah engine.
 */
export interface DiagnosisDataset {
  plant: PlantSummary;
  diseases: DiagnosisDisease[];
  /** Semua kelas fase yang bisa dipilih, termasuk yang belum punya tautan. */
  phaseOptions: PhaseSummary[];
  stats: DiagnosisDatasetStats;
}

function labelOrFallback(binding: SparqlBinding, iri: string): string {
  return termValue(binding, "label") ?? localName(iri);
}

export async function plantExists(id: string): Promise<boolean> {
  const iri = toIri(id);
  return ask(`
    ${PREFIXES}
    ASK { <${iri}> a ptp:TanamanPangan }
  `);
}

export async function listPlants(): Promise<PlantSummary[]> {
  const result = await select(`
    ${PREFIXES}
    SELECT ?plant ?label ?scientificName
           (COUNT(DISTINCT ?disease) AS ?diseaseCount)
    WHERE {
      ?plant a ptp:TanamanPangan .
      OPTIONAL { ?plant rdfs:label ?label }
      OPTIONAL { ?plant ptp:namaIlmiah ?scientificName }
      OPTIONAL { ?disease ptp:menyerangTanaman ?plant }
    }
    GROUP BY ?plant ?label ?scientificName
    ORDER BY ?label
  `);

  return result.results.bindings.map((binding) => {
    const iri = termValue(binding, "plant");
    if (iri === undefined) {
      throw new InvalidRequestError("Fuseki mengembalikan tanaman tanpa IRI");
    }
    return {
      id: localName(iri),
      iri,
      label: labelOrFallback(binding, iri),
      scientificName: termValue(binding, "scientificName") ?? null,
      diseaseCount: requireIntegerTerm(binding, "diseaseCount"),
    };
  });
}

export async function listPhases(plantId?: string): Promise<PhaseSummary[]> {
  const plantIri = plantId === undefined ? null : toIri(plantId);

  if (plantId !== undefined && !(await plantExists(plantId))) {
    throw new NotFoundError(`Tanaman tidak ditemukan: ${plantId}`);
  }

  const plantFilter =
    plantIri === null ? "" : `FILTER(?plant = <${plantIri}>)`;

  const result = await select(`
    ${PREFIXES}
    SELECT ?phase ?label (COUNT(DISTINCT ?disease) AS ?diseaseCount)
    WHERE {
      ?phase a owl:Class ;
             rdfs:subClassOf+ ptp:FasePertumbuhan .
      OPTIONAL { ?phase rdfs:label ?label }
      OPTIONAL {
        ?disease ptp:menyerangTanaman ?plant ;
                 ptp:menyerangFase ?phaseIndividual .
        ?phaseIndividual a ?phaseType .
        ?phaseType rdfs:subClassOf* ?phase .
        ${plantFilter}
      }
    }
    GROUP BY ?phase ?label
  `);

  const phases = result.results.bindings.map((binding) => {
    const iri = termValue(binding, "phase");
    if (iri === undefined) {
      throw new InvalidRequestError("Fuseki mengembalikan fase tanpa IRI");
    }
    return {
      id: localName(iri),
      iri,
      label: labelOrFallback(binding, iri),
      diseaseCount: requireIntegerTerm(binding, "diseaseCount"),
    };
  });

  return phases.sort((left, right) => {
    const leftOrder = PHASE_ORDER.indexOf(
      left.id as (typeof PHASE_ORDER)[number]
    );
    const rightOrder = PHASE_ORDER.indexOf(
      right.id as (typeof PHASE_ORDER)[number]
    );
    return (
      (leftOrder === -1 ? PHASE_ORDER.length : leftOrder) -
        (rightOrder === -1 ? PHASE_ORDER.length : rightOrder) ||
      left.label.localeCompare(right.label, "id")
    );
  });
}

export interface PlantDetail extends PlantSummary {
  diseases: DiseaseSummary[];
}

export async function getPlant(id: string): Promise<PlantDetail> {
  const iri = toIri(id);
  const plants = await listPlants();
  const plant = plants.find((item) => item.iri === iri);

  if (plant === undefined) {
    throw new NotFoundError(`Tanaman tidak ditemukan: ${id}`);
  }

  const diseases = await listDiseases(id);
  return { ...plant, diseases };
}

export async function listDiseases(plantId?: string): Promise<DiseaseSummary[]> {
  const plantIri = plantId === undefined ? null : toIri(plantId);

  if (plantId !== undefined && !(await plantExists(plantId))) {
    throw new NotFoundError(`Tanaman tidak ditemukan: ${plantId}`);
  }

  const plantFilter =
    plantIri === null ? "" : `FILTER(?plant = <${plantIri}>)`;

  const result = await select(`
    ${PREFIXES}
    SELECT ?disease ?label ?plant ?plantLabel
           (COUNT(DISTINCT ?symptom) AS ?symptomCount)
    WHERE {
      ?disease a ptp:Penyakit .
      OPTIONAL { ?disease rdfs:label ?label }
      OPTIONAL {
        ?disease ptp:menyerangTanaman ?plant .
        OPTIONAL { ?plant rdfs:label ?plantLabel }
      }
      OPTIONAL { ?disease ptp:memilikiGejala ?symptom }
      ${plantFilter}
    }
    GROUP BY ?disease ?label ?plant ?plantLabel
    ORDER BY ?label
  `);

  return result.results.bindings.map((binding) => {
    const iri = termValue(binding, "disease");
    if (iri === undefined) {
      throw new InvalidRequestError("Fuseki mengembalikan penyakit tanpa IRI");
    }
    const plantValue = termValue(binding, "plant");

    return {
      id: localName(iri),
      iri,
      label: labelOrFallback(binding, iri),
      plantId: plantValue === undefined ? null : localName(plantValue),
      plantLabel: termValue(binding, "plantLabel") ?? null,
      symptomCount: requireIntegerTerm(binding, "symptomCount"),
    };
  });
}

async function rows(query: string): Promise<SparqlBinding[]> {
  const result = await select(query);
  return result.results.bindings;
}

export async function getDisease(id: string): Promise<DiseaseDetail> {
  const iri = toIri(id);

  const infoRows = await rows(`
    ${PREFIXES}
    SELECT ?disease ?label ?plant ?plantLabel
    WHERE {
      VALUES ?disease { <${iri}> }
      ?disease a ptp:Penyakit .
      OPTIONAL { ?disease rdfs:label ?label }
      OPTIONAL {
        ?disease ptp:menyerangTanaman ?plant .
        OPTIONAL { ?plant rdfs:label ?plantLabel }
      }
    }
  `);

  const info = infoRows[0];

  if (info === undefined) {
    throw new NotFoundError(`Penyakit tidak ditemukan: ${id}`);
  }

  const [symptomRows, controlRows, pathogenRows, partRows, phaseRows, riskRows] =
    await Promise.all([
      rows(`
        ${PREFIXES}
        SELECT ?symptom ?label
               (SAMPLE(?part) AS ?part)
               (SAMPLE(?partLabel) AS ?partLabel)
               (SAMPLE(?canonical) AS ?canonical)
               (SAMPLE(?canonicalLabel) AS ?canonicalLabel)
        WHERE {
          VALUES ?disease { <${iri}> }
          ?disease ptp:memilikiGejala ?symptom .
          OPTIONAL { ?symptom rdfs:label ?label }
          OPTIONAL {
            ?symptom ptp:terdapatPada ?part .
            OPTIONAL { ?part rdfs:label ?partLabel }
          }
          OPTIONAL {
            ?symptom ptp:memilikiGejalaKanonik ?canonical .
            OPTIONAL { ?canonical rdfs:label ?canonicalLabel }
          }
        }
        GROUP BY ?symptom ?label
        ORDER BY ?label
      `),
      rows(`
        ${PREFIXES}
        SELECT ?control ?label
               (SAMPLE(?globalDescription) AS ?globalDescription)
               (GROUP_CONCAT(DISTINCT ?quote; separator=" ") AS ?quotes)
        WHERE {
          VALUES ?disease { <${iri}> }
          ?disease ptp:dikendalikanDengan ?control .
          OPTIONAL { ?control rdfs:label ?label }
          OPTIONAL { ?control ptp:deskripsiPengendalian ?globalDescription }
          OPTIONAL {
            ?disease ptp:didukungOleh ?evidence .
            ?evidence a ptp:BuktiPengendalian ;
                      ptp:kutipanSumber ?quote .
            ?control ptp:didukungOleh ?evidence .
          }
        }
        GROUP BY ?control ?label
        ORDER BY ?label
      `),
      rows(`
        ${PREFIXES}
        SELECT DISTINCT ?pathogen ?label ?scientificName
        WHERE {
          VALUES ?disease { <${iri}> }
          ?disease ptp:disebabkanOleh ?pathogen .
          OPTIONAL { ?pathogen rdfs:label ?label }
          OPTIONAL { ?pathogen ptp:namaIlmiahPatogen ?scientificName }
        }
        ORDER BY ?label
      `),
      rows(`
        ${PREFIXES}
        SELECT DISTINCT ?part ?label
        WHERE {
          VALUES ?disease { <${iri}> }
          ?disease ptp:menyerangBagian ?part .
          OPTIONAL { ?part rdfs:label ?label }
        }
        ORDER BY ?label
      `),
      rows(`
        ${PREFIXES}
        SELECT DISTINCT ?phase ?label
        WHERE {
          VALUES ?disease { <${iri}> }
          ?disease ptp:menyerangFase ?phase .
          OPTIONAL { ?phase rdfs:label ?label }
        }
        ORDER BY ?label
      `),
      rows(`
        ${PREFIXES}
        SELECT DISTINCT ?factor ?label
        WHERE {
          VALUES ?disease { <${iri}> }
          ?disease ptp:dipengaruhiOleh ?factor .
          OPTIONAL { ?factor rdfs:label ?label }
        }
        ORDER BY ?label
      `),
    ]);

  const plantIri = termValue(info, "plant");

  return {
    id: localName(iri),
    iri,
    label: labelOrFallback(info, iri),
    plantId: plantIri === undefined ? null : localName(plantIri),
    plantLabel: termValue(info, "plantLabel") ?? null,
    symptomCount: symptomRows.length,
    symptoms: symptomRows.map((binding) => {
      const symptomIri = requireTerm(binding, "symptom", "gejala");
      return {
        id: localName(symptomIri),
        iri: symptomIri,
        label: labelOrFallback(binding, symptomIri),
        partId: optionalLocalName(termValue(binding, "part")),
        partLabel: termValue(binding, "partLabel") ?? null,
        canonicalId: optionalLocalName(termValue(binding, "canonical")),
        canonicalLabel: termValue(binding, "canonicalLabel") ?? null,
      };
    }),
    controls: controlRows.map((binding) => {
      const controlIri = requireTerm(binding, "control", "pengendalian");
      const quotes = termValue(binding, "quotes");
      return {
        id: localName(controlIri),
        iri: controlIri,
        label: labelOrFallback(binding, controlIri),
        description:
          (quotes !== undefined && quotes.trim() !== "" ? quotes : null) ??
          termValue(binding, "globalDescription") ??
          null,
      };
    }),
    pathogens: pathogenRows.map((binding) => {
      const pathogenIri = requireTerm(binding, "pathogen", "patogen");
      return {
        id: localName(pathogenIri),
        iri: pathogenIri,
        label: labelOrFallback(binding, pathogenIri),
        scientificName: termValue(binding, "scientificName") ?? null,
      };
    }),
    parts: namedEntities(partRows, "part"),
    phases: namedEntities(phaseRows, "phase"),
    riskFactors: namedEntities(riskRows, "factor"),
  };
}

function requireTerm(
  binding: SparqlBinding,
  key: string,
  description: string
): string {
  const value = termValue(binding, key);
  if (value === undefined) {
    throw new InvalidRequestError(`Fuseki mengembalikan ${description} tanpa IRI`);
  }
  return value;
}

function optionalLocalName(value: string | undefined): string | null {
  return value === undefined ? null : localName(value);
}

function namedEntities(
  bindings: SparqlBinding[],
  key: string
): NamedEntity[] {
  return bindings.map((binding) => {
    const iri = requireTerm(binding, key, key);
    return {
      id: localName(iri),
      iri,
      label: labelOrFallback(binding, iri),
    };
  });
}

export async function listSymptoms(plantId?: string): Promise<SymptomSummary[]> {
  const plantIri = plantId === undefined ? null : toIri(plantId);

  if (plantId !== undefined && !(await plantExists(plantId))) {
    throw new NotFoundError(`Tanaman tidak ditemukan: ${plantId}`);
  }

  const query =
    plantIri === null
      ? `
        ${PREFIXES}
        SELECT ?symptom ?label
               (SAMPLE(?part) AS ?part)
               (SAMPLE(?partLabel) AS ?partLabel)
               (SAMPLE(?canonical) AS ?canonical)
               (SAMPLE(?canonicalLabel) AS ?canonicalLabel)
        WHERE {
          ?symptom a/rdfs:subClassOf* ptp:Gejala .
          FILTER EXISTS { ?disease ptp:memilikiGejala ?symptom }
          OPTIONAL { ?symptom rdfs:label ?label }
          OPTIONAL {
            ?symptom ptp:terdapatPada ?part .
            OPTIONAL { ?part rdfs:label ?partLabel }
          }
          OPTIONAL {
            ?symptom ptp:memilikiGejalaKanonik ?canonical .
            OPTIONAL { ?canonical rdfs:label ?canonicalLabel }
          }
        }
        GROUP BY ?symptom ?label
        ORDER BY ?label
      `
      : `
        ${PREFIXES}
        SELECT ?symptom ?label
               (SAMPLE(?part) AS ?part)
               (SAMPLE(?partLabel) AS ?partLabel)
               (SAMPLE(?canonical) AS ?canonical)
               (SAMPLE(?canonicalLabel) AS ?canonicalLabel)
        WHERE {
          ?disease ptp:menyerangTanaman <${plantIri}> ;
                   ptp:memilikiGejala ?symptom .
          OPTIONAL { ?symptom rdfs:label ?label }
          OPTIONAL {
            ?symptom ptp:terdapatPada ?part .
            OPTIONAL { ?part rdfs:label ?partLabel }
          }
          OPTIONAL {
            ?symptom ptp:memilikiGejalaKanonik ?canonical .
            OPTIONAL { ?canonical rdfs:label ?canonicalLabel }
          }
        }
        GROUP BY ?symptom ?label
        ORDER BY ?label
      `;

  const bindings = await rows(query);

  return bindings.map((binding) => {
    const iri = requireTerm(binding, "symptom", "gejala");
    return {
      id: localName(iri),
      iri,
      label: labelOrFallback(binding, iri),
      partId: optionalLocalName(termValue(binding, "part")),
      partLabel: termValue(binding, "partLabel") ?? null,
      canonicalId: optionalLocalName(termValue(binding, "canonical")),
      canonicalLabel: termValue(binding, "canonicalLabel") ?? null,
    };
  });
}

export async function getDiagnosisDataset(
  plantId: string
): Promise<DiagnosisDataset> {
  const plantIri = toIri(plantId);

  const [plants, diseaseRows, symptomRows, riskRows, phaseRows, phaseOptions] =
    await Promise.all([
      listPlants(),
      rows(`
        ${PREFIXES}
        SELECT ?disease ?label ?description ?severity
        WHERE {
          ?disease a ptp:Penyakit ;
                   ptp:menyerangTanaman <${plantIri}> .
          OPTIONAL { ?disease rdfs:label ?label }
          OPTIONAL { ?disease ptp:deskripsiPenyakit ?description }
          OPTIONAL { ?disease ptp:tingkatKeparahan ?severity }
        }
        ORDER BY ?label
      `),
      rows(`
        ${PREFIXES}
        SELECT ?disease ?symptom ?symptomLabel ?canonical ?canonicalLabel
        WHERE {
          ?disease ptp:menyerangTanaman <${plantIri}> ;
                   ptp:memilikiGejala ?symptom .
          OPTIONAL { ?symptom rdfs:label ?symptomLabel }
          OPTIONAL {
            ?symptom ptp:memilikiGejalaKanonik ?canonical .
            OPTIONAL { ?canonical rdfs:label ?canonicalLabel }
          }
        }
      `),
      rows(`
        ${PREFIXES}
        SELECT DISTINCT ?disease ?factor ?factorLabel
        WHERE {
          ?disease ptp:menyerangTanaman <${plantIri}> ;
                   ptp:dipengaruhiOleh ?factor .
          OPTIONAL { ?factor rdfs:label ?factorLabel }
        }
        ORDER BY ?factorLabel
      `),
      rows(`
        ${PREFIXES}
        SELECT DISTINCT ?disease ?phase ?label
        WHERE {
          ?disease ptp:menyerangTanaman <${plantIri}> ;
                   ptp:menyerangFase ?phaseIndividual .
          ?phaseIndividual a ?phase .
          ?phase rdfs:subClassOf+ ptp:FasePertumbuhan .
          OPTIONAL { ?phase rdfs:label ?label }
        }
        ORDER BY ?label
      `),
      listPhases(plantId),
    ]);

  const plant = plants.find((item) => item.iri === plantIri);

  if (plant === undefined) {
    throw new NotFoundError(`Tanaman tidak ditemukan: ${plantId}`);
  }

  const byDisease = new Map<string, DiagnosisDisease>();

  const ensureDisease = (
    iri: string,
    binding: SparqlBinding
  ): DiagnosisDisease => {
    let disease = byDisease.get(iri);

    if (disease === undefined) {
      disease = {
        id: localName(iri),
        iri,
        label: labelOrFallback(binding, iri),
        symptoms: [],
        riskFactors: [],
        phases: [],
        description: termValue(binding, "description") ?? null,
        severity: termValue(binding, "severity") ?? null,
      };
      byDisease.set(iri, disease);
    }

    return disease;
  };

  // Penyakit tetap dimasukkan walau belum punya gejala, supaya layer data
  // jujur tentang isi ontology dan engine bisa memberi warning yang tepat.
  for (const row of diseaseRows) {
    ensureDisease(requireTerm(row, "disease", "penyakit"), row);
  }

  for (const row of symptomRows) {
    const disease = ensureDisease(
      requireTerm(row, "disease", "penyakit"),
      row
    );
    const symptomIri = requireTerm(row, "symptom", "gejala");

    if (disease.symptoms.some((item) => item.iri === symptomIri)) {
      continue;
    }

    const canonicalIri = termValue(row, "canonical");

    disease.symptoms.push({
      id: localName(symptomIri),
      iri: symptomIri,
      label: termValue(row, "symptomLabel") ?? localName(symptomIri),
      canonical:
        canonicalIri === undefined
          ? null
          : {
              id: localName(canonicalIri),
              iri: canonicalIri,
              label:
                termValue(row, "canonicalLabel") ?? localName(canonicalIri),
            },
    });
  }

  for (const row of riskRows) {
    const disease = byDisease.get(
      requireTerm(row, "disease", "penyakit")
    );

    if (disease === undefined) {
      continue;
    }

    const factorIri = requireTerm(row, "factor", "faktor risiko");

    if (!disease.riskFactors.some((item) => item.iri === factorIri)) {
      disease.riskFactors.push({
        id: localName(factorIri),
        iri: factorIri,
        label:
          termValue(row, "factorLabel") ?? localName(factorIri),
      });
    }
  }

  for (const row of phaseRows) {
    const disease = byDisease.get(
      requireTerm(row, "disease", "penyakit")
    );

    if (disease === undefined) {
      continue;
    }

    const phaseIri = requireTerm(row, "phase", "fase pertumbuhan");

    if (!disease.phases.some((item) => item.iri === phaseIri)) {
      disease.phases.push({
        id: localName(phaseIri),
        iri: phaseIri,
        label: labelOrFallback(row, phaseIri),
      });
    }
  }

  const diseases = [...byDisease.values()];

  // Urutan stabil: penting untuk hasil diagnosis yang deterministik.
  diseases.sort(
    (left, right) =>
      left.label.localeCompare(right.label, "id") ||
      left.iri.localeCompare(right.iri)
  );

  for (const disease of diseases) {
    disease.symptoms.sort(
      (left, right) =>
        left.label.localeCompare(right.label, "id") ||
        left.iri.localeCompare(right.iri)
    );
    disease.riskFactors.sort(
      (left, right) =>
        left.label.localeCompare(right.label, "id") ||
        left.iri.localeCompare(right.iri)
    );
    disease.phases.sort(
      (left, right) =>
        left.label.localeCompare(right.label, "id") ||
        left.iri.localeCompare(right.iri)
    );
  }

  const observedSymptoms = new Set<string>();
  const canonicalObservations = new Set<string>();
  const canonicalConcepts = new Set<string>();

  for (const disease of diseases) {
    for (const symptom of disease.symptoms) {
      observedSymptoms.add(symptom.iri);

      if (symptom.canonical !== null) {
        canonicalObservations.add(symptom.iri);
        canonicalConcepts.add(symptom.canonical.iri);
      }
    }
  }

  return {
    plant,
    diseases,
    phaseOptions,
    stats: {
      diseaseCount: diseases.length,
      diseaseWithSymptomsCount: diseases.filter(
        (disease) => disease.symptoms.length > 0
      ).length,
      symptomObservationCount: observedSymptoms.size,
      canonicalObservationCount: canonicalObservations.size,
      canonicalConceptCount: canonicalConcepts.size,
    },
  };
}

export async function getControlsForDiseases(
  diseaseIris: string[]
): Promise<Record<string, NamedEntity[]>> {
  if (diseaseIris.length === 0) {
    return {};
  }

  const values = diseaseIris.map((iri) => `<${iri}>`).join(" ");

  const bindings = await rows(`
    ${PREFIXES}
    SELECT DISTINCT ?disease ?control ?label
    WHERE {
      VALUES ?disease { ${values} }
      ?disease ptp:dikendalikanDengan ?control .
      OPTIONAL { ?control rdfs:label ?label }
    }
    ORDER BY ?label
  `);

  const result: Record<string, NamedEntity[]> = {};

  for (const binding of bindings) {
    const diseaseIri = requireTerm(binding, "disease", "penyakit");
    const controlIri = requireTerm(binding, "control", "pengendalian");
    const list = result[diseaseIri] ?? [];
    if (!list.some((item) => item.iri === controlIri)) {
      list.push({
        id: localName(controlIri),
        iri: controlIri,
        label: labelOrFallback(binding, controlIri),
      });
    }
    result[diseaseIri] = list;
  }

  return result;
}
