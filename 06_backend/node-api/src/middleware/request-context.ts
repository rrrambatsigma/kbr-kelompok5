import { randomUUID } from "node:crypto";
import type { NextFunction, Request, Response } from "express";

/**
 * Adds a request id and emits one line per request after the response
 * finishes. Request ids are echoed in the JSON envelope and error logs.
 */
export function requestContext(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const incoming = req.header("x-request-id");
  const requestId = incoming && incoming.trim() !== "" ? incoming.trim() : randomUUID();
  res.locals.requestId = requestId;
  res.setHeader("x-request-id", requestId);

  const startedAt = Date.now();

  res.on("finish", () => {
    const durationMs = Date.now() - startedAt;
    console.log(
      `${req.method} ${req.originalUrl} -> ${res.statusCode} (${durationMs}ms) [${requestId}]`
    );
  });

  next();
}
