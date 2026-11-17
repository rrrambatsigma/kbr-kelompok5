function readInt(
  name: string,
  fallback: number,
  min: number,
  max: number
): number {
  const raw = process.env[name];

  if (raw === undefined || raw.trim() === "") {
    return fallback;
  }

  const value = Number(raw);

  if (!Number.isInteger(value) || value < min || value > max) {
    throw new Error(
      `Konfigurasi ${name} tidak valid: "${raw}". Nilai harus integer ${min}-${max}.`
    );
  }

  return value;
}

function readUrl(name: string, fallback: string): string {
  const raw = process.env[name];

  if (raw === undefined || raw.trim() === "") {
    return fallback;
  }

  try {
    const url = new URL(raw.trim());
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      throw new Error("protokol harus http atau https");
    }
    return url.toString().replace(/\/$/, "");
  } catch {
    throw new Error(
      `Konfigurasi ${name} tidak valid: "${raw}". Nilai harus URL http(s).`
    );
  }
}

export const env = {
  nodeEnv: process.env.NODE_ENV?.trim() || "development",
  host: process.env.HOST?.trim() || "127.0.0.1",
  port: readInt("PORT", 3000, 1, 65535),

  fusekiBaseUrl: readUrl("FUSEKI_BASE_URL", "http://localhost:3030"),
  fusekiDataset: process.env.FUSEKI_DATASET?.trim() || "plant-kb",
  fusekiTimeoutMs: readInt("FUSEKI_TIMEOUT_MS", 5000, 100, 120000),

  reasoningApiUrl: readUrl("REASONING_API_URL", "http://localhost:8082"),
  reasoningTimeoutMs: readInt("REASONING_TIMEOUT_MS", 15000, 100, 300000),

  /**
   * Opsional. Dipakai health check untuk membandingkan SHA-256 file ontology
   * dengan checksum yang dilaporkan Java. Kosong = status UNKNOWN.
   */
  ontologyFilePath: process.env.ONTOLOGY_FILE_PATH?.trim() || "",

  frontendUrl: readUrl("FRONTEND_URL", "http://localhost:5173"),
} as const;
