import { describe, expect, it } from "vitest";

import { ApiError } from "../services/api/client";
import { friendlyApiError } from "./apiError";

describe("friendlyApiError", () => {
  it("memberi pesan untuk backend yang tidak dapat dihubungi", () => {
    expect(
      friendlyApiError(new ApiError("NETWORK_ERROR", "fetch failed"))
    ).toMatch(/tidak dapat terhubung/i);
  });

  it("memberi pesan untuk Fuseki yang tidak tersedia", () => {
    expect(
      friendlyApiError(new ApiError("FUSEKI_UNAVAILABLE", "down"))
    ).toMatch(/basis pengetahuan/i);
  });

  it("meneruskan pesan validasi backend", () => {
    expect(
      friendlyApiError(
        new ApiError("INVALID_REQUEST", "symptomIds minimal berisi satu ID")
      )
    ).toContain("symptomIds");
  });
});
