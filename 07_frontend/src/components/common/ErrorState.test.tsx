import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  it("menampilkan pesan dan memanggil retry", () => {
    const onRetry = vi.fn();
    render(
      <ErrorState
        title="Gagal memuat"
        message="Backend tidak tersedia"
        onRetry={onRetry}
      />
    );

    expect(screen.getByText("Gagal memuat")).toBeInTheDocument();
    expect(screen.getByText("Backend tidak tersedia")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /coba lagi/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
