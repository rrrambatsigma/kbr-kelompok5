export interface ApiErrorDetail {
  field?: string;
  message: string;
}

/**
 * Error with a stable machine-readable code and HTTP status.
 * Anything that is not an AppError is treated as an internal error.
 */
export class AppError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: ApiErrorDetail[] | undefined;

  constructor(
    code: string,
    status: number,
    message: string,
    details?: ApiErrorDetail[]
  ) {
    super(message);
    this.name = "AppError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export class InvalidRequestError extends AppError {
  constructor(message: string, details?: ApiErrorDetail[]) {
    super("INVALID_REQUEST", 400, message, details);
  }
}

export class NotFoundError extends AppError {
  constructor(message: string) {
    super("NOT_FOUND", 404, message);
  }
}

export class FusekiUnavailableError extends AppError {
  constructor(message: string) {
    super("FUSEKI_UNAVAILABLE", 503, message);
  }
}

export class FusekiQueryError extends AppError {
  constructor(message: string, upstreamStatus: number) {
    super("FUSEKI_QUERY_ERROR", 500, message, [
      { message: `Fuseki menolak query (HTTP ${upstreamStatus})` },
    ]);
  }
}

export class FusekiInvalidResponseError extends AppError {
  constructor(message: string) {
    super("FUSEKI_INVALID_RESPONSE", 502, message);
  }
}

export class ReasoningUnavailableError extends AppError {
  constructor(message: string) {
    super("REASONING_UNAVAILABLE", 503, message);
  }
}

export class ReasoningError extends AppError {
  constructor(code: string, status: number, message: string) {
    super(code, status, message);
  }
}
