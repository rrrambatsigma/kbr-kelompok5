import { ApiError } from "../services/api/client";

export function friendlyApiError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Terjadi kesalahan yang tidak terduga. Silakan coba lagi.";
  }

  switch (error.code) {
    case "NETWORK_ERROR":
      return "Tidak dapat terhubung ke server TaniCare. Pastikan backend berjalan.";
    case "REQUEST_TIMEOUT":
      return "Permintaan terlalu lama. Periksa koneksi lalu coba lagi.";
    case "FUSEKI_UNAVAILABLE":
      return "Basis pengetahuan tanaman sedang tidak tersedia. Coba beberapa saat lagi.";
    case "REASONING_UNAVAILABLE":
      return "Layanan penalaran sedang tidak tersedia. Hasil mungkin belum lengkap.";
    case "DEPENDENCY_UNAVAILABLE":
      return "Sebagian layanan TaniCare belum siap. Coba lagi setelah beberapa saat.";
    case "ONTOLOGY_MISMATCH":
      return "Versi basis pengetahuan tidak konsisten. Hubungi administrator sistem.";
    case "INVALID_REQUEST":
      return error.message || "Data yang dikirim belum lengkap atau tidak valid.";
    case "NOT_FOUND":
      return "Data yang diminta tidak ditemukan.";
    case "INVALID_RESPONSE":
      return "Server mengembalikan data yang tidak dapat dibaca.";
    default:
      return error.message || "Permintaan gagal. Silakan coba lagi.";
  }
}
