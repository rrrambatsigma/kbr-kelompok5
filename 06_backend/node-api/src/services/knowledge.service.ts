import { ptpNamespace } from "../config/fuseki.js";
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

export interface DiagnosisDisease {
  id: string;
  iri: string;
  label: string;
  symptoms: Array<{ id: string; iri: string; label: string }>;
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
        WHERE {
          VALUES ?disease { <${iri}> }
          ?disease ptp:memilikiGejala ?symptom .
          OPTIONAL { ?symptom rdfs:label ?label }
          OPTIONAL {
            ?symptom ptp:terdapatPada ?part .
            OPTIONAL { ?part rdfs:label ?partLabel }
          }
        }
        GROUP BY ?symptom ?label
        ORDER BY ?label
      `),
      rows(`
        ${PREFIXES}
        SELECT DISTINCT ?control ?label ?description
        WHERE {
          VALUES ?disease { <${iri}> }
          ?disease ptp:dikendalikanDengan ?control .
          OPTIONAL { ?control rdfs:label ?label }
          OPTIONAL { ?control ptp:deskripsiPengendalian ?description }
        }
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
      };
    }),
    controls: controlRows.map((binding) => {
      const controlIri = requireTerm(binding, "control", "pengendalian");
      return {
        id: localName(controlIri),
        iri: controlIri,
        label: labelOrFallback(binding, controlIri),
        description: termValue(binding, "description") ?? null,
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
        WHERE {
          ?symptom a/rdfs:subClassOf* ptp:Gejala .
          FILTER EXISTS { ?disease ptp:memilikiGejala ?symptom }
          OPTIONAL { ?symptom rdfs:label ?label }
          OPTIONAL {
            ?symptom ptp:terdapatPada ?part .
            OPTIONAL { ?part rdfs:label ?partLabel }
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
        WHERE {
          ?disease ptp:menyerangTanaman <${plantIri}> ;
                   ptp:memilikiGejala ?symptom .
          OPTIONAL { ?symptom rdfs:label ?label }
          OPTIONAL {
            ?symptom ptp:terdapatPada ?part .
            OPTIONAL { ?part rdfs:label ?partLabel }
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
    };
  });
}

export async function getDiagnosisDataset(
  plantId: string
): Promise<DiagnosisDisease[]> {
  const plantIri = toIri(plantId);

  const bindings = await rows(`
    ${PREFIXES}
    SELECT ?disease ?diseaseLabel ?symptom ?symptomLabel
    WHERE {
      ?disease ptp:menyerangTanaman <${plantIri}> ;
               ptp:memilikiGejala ?symptom .
      OPTIONAL { ?disease rdfs:label ?diseaseLabel }
      OPTIONAL { ?symptom rdfs:label ?symptomLabel }
    }
  `);

  const byDisease = new Map<string, DiagnosisDisease>();

  for (const binding of bindings) {
    const diseaseIri = requireTerm(binding, "disease", "penyakit");
    const symptomIri = requireTerm(binding, "symptom", "gejala");

    let disease = byDisease.get(diseaseIri);
    if (disease === undefined) {
      disease = {
        id: localName(diseaseIri),
        iri: diseaseIri,
        label: termValue(binding, "diseaseLabel") ?? localName(diseaseIri),
        symptoms: [],
      };
      byDisease.set(diseaseIri, disease);
    }

    if (!disease.symptoms.some((item) => item.iri === symptomIri)) {
      disease.symptoms.push({
        id: localName(symptomIri),
        iri: symptomIri,
        label: termValue(binding, "symptomLabel") ?? localName(symptomIri),
      });
    }
  }
  return [...byDisease.values()];
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
