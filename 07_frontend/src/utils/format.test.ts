import { describe, expect, it } from "vitest";

import {
  categoryLabel,
  confidenceLabel,
  scorePercent,
} from "./format";

describe("format helpers", () => {
  it("mengubah skor 0..1 menjadi persentase", () => {
    expect(scorePercent(0)).toBe(0);
    expect(scorePercent(0.745)).toBe(75);
    expect(scorePercent(1)).toBe(100);
  });

  it("memetakan kategori backend ke label manusiawi", () => {
    expect(categoryLabel("PenyakitJamur")).toBe("Jamur");
    expect(categoryLabel("PenyakitBakteri")).toBe("Bakteri");
    expect(categoryLabel(null)).toBe("Belum terklasifikasi");
    expect(categoryLabel("KategoriBaru")).toBe("KategoriBaru");
  });

  it("memberi label keyakinan dalam bahasa Indonesia", () => {
    expect(confidenceLabel("TINGGI")).toContain("tinggi");
    expect(confidenceLabel("SEDANG")).toContain("sedang");
    expect(confidenceLabel("RENDAH")).toContain("rendah");
  });
});
