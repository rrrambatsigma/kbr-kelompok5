import {
  ReasoningError,
  ReasoningUnavailableError,
} from "../lib/errors.js";

export interface ReasoningClientOptions {
  baseUrl: string;
  timeoutMs: number;
  /** Retry hanya untuk network error/502/503, bukan timeout. */
  retryCount?: number;
  retryDelayMs?: number;
}

export interface ReasoningClient {
  getStatus(requestId?: string): Promise<unknown>;
  getDiseaseCategories(
    diseaseIris: readonly string[],
    requestId?: string
  ): Promise<unknown>;
}

interface RequestOptions {
  method: "GET" | "POST";
  body?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isTimeoutError(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    (error.name === "TimeoutError" || error.name === "AbortError")
  );
}

function describeError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

/**
 * Client HTTP untuk Java reasoning-api.
 *
 * Dipisahkan dari reasoning.service agar bisa diuji dengan mock server tanpa
 * memuat env atau menyentuh service Java yang sebenarnya.
 */
export function createReasoningClient(
  options: ReasoningClientOptions
): ReasoningClient {
  const baseUrl = options.baseUrl.replace(/\/$/, "");
  const retryCount = options.retryCount ?? 1;
  const retryDelayMs = options.retryDelayMs ?? 200;

  async function request(
    path: string,
    requestOptions: RequestOptions,
    requestId?: string
  ): Promise<unknown> {
    for (let attempt = 0; attempt <= retryCount; attempt += 1) {
      const headers: Record<string, string> = {
        Accept: "application/json",
      };

      if (requestOptions.body !== undefined) {
        headers["Content-Type"] = "application/json";
      }
      if (requestId !== undefined && requestId.trim() !== "") {
        headers["X-Request-Id"] = requestId.trim();
      }

      let response: Response;

      try {
        response = await fetch(`${baseUrl}${path}`, {
          method: requestOptions.method,
          headers,
          ...(requestOptions.body === undefined
            ? {}
            : { body: requestOptions.body }),
          signal: AbortSignal.timeout(options.timeoutMs),
        });
      } catch (error) {
        if (isTimeoutError(error)) {
          throw new ReasoningUnavailableError(
            `Reasoning API tidak merespons dalam ${options.timeoutMs} ms`
          );
        }

        if (attempt < retryCount) {
          await sleep(retryDelayMs);
          continue;
        }

        throw new ReasoningUnavailableError(
          `Reasoning API tidak dapat dihubungi: ${describeError(error)}`
        );
      }

      let text: string;
      try {
        text = await response.text();
      } catch (error) {
        throw new ReasoningError(
          "REASONING_INVALID_RESPONSE",
          502,
          `Gagal membaca response Reasoning API: ${describeError(error)}`
        );
      }

      let parsed: unknown;
      try {
        parsed = text === "" ? {} : JSON.parse(text);
      } catch {
        throw new ReasoningError(
          "REASONING_INVALID_RESPONSE",
          502,
          "Reasoning API mengembalikan body yang bukan JSON valid"
        );
      }

      const envelope: Record<string, unknown> = isRecord(parsed) ? parsed : {};

      if (!response.ok || envelope["success"] === false) {
        const errorValue = envelope["error"];
        const errorRecord = isRecord(errorValue) ? errorValue : {};
        const code =
          typeof errorRecord["code"] === "string"
            ? errorRecord["code"]
            : "REASONING_ERROR";
        const message =
          typeof errorRecord["message"] === "string"
            ? errorRecord["message"]
            : `Reasoning API mengembalikan HTTP ${response.status}`;

        if (
          (response.status === 502 || response.status === 503) &&
          attempt < retryCount
        ) {
          await sleep(retryDelayMs);
          continue;
        }

        throw new ReasoningError(code, response.status, message);
      }

      return envelope["data"];
    }

    throw new ReasoningUnavailableError(
      "Reasoning API tidak dapat dihubungi setelah retry"
    );
  }

  return {
    getStatus(requestId?: string): Promise<unknown> {
      return request("/api/reasoning/status", { method: "GET" }, requestId);
    },

    getDiseaseCategories(
      diseaseIris: readonly string[],
      requestId?: string
    ): Promise<unknown> {
      return request(
        "/api/reasoning/disease-categories",
        {
          method: "POST",
          body: JSON.stringify({ diseaseIris: [...diseaseIris] }),
        },
        requestId
      );
    },
  };
}
