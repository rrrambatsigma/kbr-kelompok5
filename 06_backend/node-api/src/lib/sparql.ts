import { InvalidRequestError } from "./errors.js";

/**
 * Helper kecil untuk membangun SPARQL dengan aman.
 *
 * Semua nilai yang berasal dari user (catatan, teks bebas, ID) wajib lewat
 * fungsi di file ini sebelum masuk INSERT DATA / DELETE.
 */

const FORBIDDEN_IRI = /[<>"{}|^`\\\s\u0000-\u001F]/;

export function escapeIri(value: string): string {
  const trimmed = value.trim();

  if (trimmed === "") {
    throw new InvalidRequestError("IRI tidak boleh kosong");
  }

  if (FORBIDDEN_IRI.test(trimmed)) {
    throw new InvalidRequestError(`IRI mengandung karakter tidak aman: "${value}"`);
  }

  return `<${trimmed}>`;
}

export function escapeLiteral(value: string): string {
  const escaped = value
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\r/g, "\\r")
    .replace(/\n/g, "\\n")
    .replace(/\t/g, "\\t");

  return `"${escaped}"`;
}

const XSD = "http://www.w3.org/2001/XMLSchema#";

export function literalString(value: string): string {
  return `${escapeLiteral(value)}^^<${XSD}string>`;
}

export function literalDateTime(iso: string): string {
  if (Number.isNaN(Date.parse(iso))) {
    throw new InvalidRequestError(`Nilai waktu tidak valid: "${iso}"`);
  }
  return `${escapeLiteral(iso)}^^<${XSD}dateTime>`;
}

export function literalDecimal(value: number): string {
  if (!Number.isFinite(value)) {
    throw new InvalidRequestError(`Nilai decimal tidak valid: ${value}`);
  }
  return `${escapeLiteral(String(value))}^^<${XSD}decimal>`;
}

export function literalInteger(value: number): string {
  if (!Number.isInteger(value)) {
    throw new InvalidRequestError(`Nilai integer tidak valid: ${value}`);
  }
  return `${escapeLiteral(String(value))}^^<${XSD}integer>`;
}
