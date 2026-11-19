export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Array<{ field?: string; message: string }> | null;

  constructor(
    code: string,
    message: string,
    status = 0,
    details: Array<{ field?: string; message: string }> | null = null
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export const apiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000"
).replace(/\/$/, "");

const DEFAULT_TIMEOUT_MS = 15_000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body === undefined ? {} : { "Content-Type": "application/json" }),
        ...init.headers,
      },
      signal: controller.signal,
    });

    const text = await response.text();
    let body: unknown;

    try {
      body = text === "" ? {} : JSON.parse(text);
    } catch {
      throw new ApiError(
        "INVALID_RESPONSE",
        "Server mengembalikan response yang tidak dapat dibaca.",
        response.status
      );
    }

    if (!isRecord(body)) {
      throw new ApiError(
        "INVALID_RESPONSE",
        "Struktur response server tidak valid.",
        response.status
      );
    }

    if (!response.ok || body["success"] === false) {
      const errorValue = isRecord(body["error"]) ? body["error"] : {};
      const code =
        typeof errorValue["code"] === "string"
          ? errorValue["code"]
          : "REQUEST_FAILED";
      const message =
        typeof errorValue["message"] === "string"
          ? errorValue["message"]
          : `Permintaan gagal (HTTP ${response.status}).`;
      const details = Array.isArray(errorValue["details"])
        ? (errorValue["details"] as Array<{ field?: string; message: string }>)
        : null;

      throw new ApiError(code, message, response.status, details);
    }

    return body["data"] as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        "REQUEST_TIMEOUT",
        "Permintaan melebihi batas waktu. Periksa koneksi ke backend.",
        0
      );
    }

    throw new ApiError(
      "NETWORK_ERROR",
      "Tidak dapat terhubung ke server TaniCare. Pastikan backend berjalan.",
      0
    );
  } finally {
    window.clearTimeout(timer);
  }
}
