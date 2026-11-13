import type { ErrorRequestHandler, RequestHandler } from "express";
import { AppError } from "../lib/errors.js";
import { fail } from "../lib/response.js";

export const notFoundHandler: RequestHandler = (req, res) => {
  res
    .status(404)
    .json(fail(res, "NOT_FOUND", `Endpoint tidak ditemukan: ${req.method} ${req.path}`));
};

export const errorHandler: ErrorRequestHandler = (error, _req, res, next) => {
  if (res.headersSent) {
    next(error);
    return;
  }

  if (error instanceof AppError) {
    if (error.status >= 500) {
      console.error(`[${String(res.locals.requestId)}] ${error.code}:`, error.message);
    }
    res
      .status(error.status)
      .json(fail(res, error.code, error.message, error.details ?? null));
    return;
  }

  if (isJsonParseError(error)) {
    res
      .status(400)
      .json(fail(res, "INVALID_REQUEST", "Body request bukan JSON yang valid"));
    return;
  }

  console.error(`[${String(res.locals.requestId)}] Unhandled error:`, error);
  res
    .status(500)
    .json(fail(res, "INTERNAL_ERROR", "Terjadi kesalahan internal pada API"));
};

function isJsonParseError(error: unknown): boolean {
  if (!(error instanceof SyntaxError)) {
    return false;
  }
  const candidate = error as SyntaxError & {
    status?: number;
    type?: string;
  };
  return candidate.status === 400 || candidate.type === "entity.parse.failed";
}
