
const FUSEKI_BASE_URL =
  process.env.FUSEKI_BASE_URL || "http://localhost:3030";

const FUSEKI_DATASET =
  process.env.FUSEKI_DATASET || "plant-kb";

export const fusekiConfig = {
  baseUrl: FUSEKI_BASE_URL.replace(/\/$/, ""),
  dataset: FUSEKI_DATASET,
  queryUrl: `${FUSEKI_BASE_URL.replace(/\/$/, "")}/${FUSEKI_DATASET}/query`,
};
