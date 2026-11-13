import type { Response } from "express";
import type { ApiErrorDetail } from "./errors.js";

export function requestIdOf(res: Response): string {
  const value = res.locals.requestId;
  return typeof value === "string" ? value : "";
}

export function meta(res: Response) {
  return {
    requestId: requestIdOf(res),
    timestamp: new Date().toISOString(),
  };
}

export function ok<T>(res: Response, data: T) {
  return {
    success: true as const,
    data,
    meta: meta(res),
  };
}

export function fail(
  res: Response,
  code: string,
  message: string,
  details: ApiErrorDetail[] | null = null
) {
  return {
    success: false as const,
    data: null,
    error: {
      code,
      message,
      details,
    },
    meta: meta(res),
  };
}
