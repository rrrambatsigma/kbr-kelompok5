
import { fusekiConfig } from "../config/fuseki.js";

export interface SparqlSelectResponse {
  head: {
    vars: string[];
  };
  results: {
    bindings: Array<Record<string, {
      type: string;
      value: string;
    }>>;
  };
}

export async function queryFuseki<T>(
  query: string
): Promise<T> {
  const response = await fetch(fusekiConfig.queryUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/sparql-results+json",
    },
    body: new URLSearchParams({ query }),
    signal: AbortSignal.timeout(5000),
  });

  if (!response.ok) {
    throw new Error(
      `Fuseki request failed: HTTP ${response.status}`
    );
  }

  return (await response.json()) as T;
}
