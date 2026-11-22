# Hasil Validasi Reasoning Diagnosis

- Waktu: 2026-11-22T07:58:52.326Z
- Base URL: http://127.0.0.1:3000
- Model: forward-chaining-cf-v1
- Ontology: 65f92b9452f9 / 65f92b9452f9a63f71ebd24b52ae237cfb303c12230054bf785a441ebbe168a5

## Ringkasan (fokus: gold + ambiguous)

| Metrik | Baseline (0.7/0.3) | Model baru | Delta |
|---|---:|---:|---:|
| Top-1 | 0.636 | 0.909 | +0.273 |
| Top-3 | 0.909 | 1.000 | +0.091 |
| MRR | 0.742 | 0.955 | +0.212 |

Kasus fokus: **22**; semua kasus normal: **75**; error request: **0**; negative: **5/5** lulus.
Sanity (53 kasus) tidak masuk fokus karena dibuat dari gejala penyakit itu sendiri.

## Per tipe kasus

| Tipe | Kasus | Top-1 baru | Top-3 baru | MRR baru | Top-1 baseline | Top-3 baseline |
|---|---:|---:|---:|---:|---:|---:|
| gold | 14 | 100.0% | 100.0% | 1.000 | 100.0% | 100.0% |
| sanity | 53 | 100.0% | 100.0% | 1.000 | 100.0% | 100.0% |
| ambiguous | 8 | 75.0% | 100.0% | 0.875 | 0.0% | 75.0% |

## Per tanaman (semua kasus normal)

| Tanaman | Kasus | Top-1 | Top-3 | MRR |
|---|---:|---:|---:|---:|
| Padi | 9 | 88.9% | 100.0% | 0.944 |
| Kedelai | 18 | 100.0% | 100.0% | 1.000 |
| Jagung | 8 | 100.0% | 100.0% | 1.000 |
| UbiJalar | 7 | 100.0% | 100.0% | 1.000 |
| UbiKayu | 20 | 100.0% | 100.0% | 1.000 |
| KacangTanah | 8 | 87.5% | 100.0% | 0.938 |
| KacangHijau | 5 | 100.0% | 100.0% | 1.000 |

## Negative tests

| Kasus | Expected | Actual | Status |
|---|---:|---:|---|
| NEG-PLANT-01 | 404 | 404 | lulus |
| NEG-SYMPTOM-01 | 400 | 400 | lulus |
| NEG-EMPTY-01 | 400 | 400 | lulus |
| NEG-TOPN-01 | 400 | 400 | lulus |
| NEG-DUP-01 | 200 | 200 | lulus |

## Ambang

| Cek | Target | Aktual | Status |
|---|---:|---:|---|
| Top-1 fokus (gold+ambiguous) | 0.700 | 0.909 | lulus |
| Top-3 fokus (gold+ambiguous) | 0.900 | 1.000 | lulus |
| MRR fokus (gold+ambiguous) | 0.800 | 0.955 | lulus |
| Top-1 ambiguous | 0.500 | 0.750 | lulus |

## Kalibrasi confidence (fokus)

| Confidence | Kasus | Top-1 | Top-3 |
|---|---:|---:|---:|
| TINGGI | 8 | 100.0% | 100.0% |
| SEDANG | 12 | 91.7% | 100.0% |
| RENDAH | 2 | 50.0% | 100.0% |

## Peringatan validasi

- KEDELAI-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKedelaiBercakTanaman (case: "Bercak tanaman pada Penyakit Karat Daun", ontology: "Bercak pada tanaman pada Penyakit Karat Daun")
- UBIJALAR-KUDIS-01: label berbeda untuk PengamatanPenyakitKudisUbiJalarKlorosisTanaman (case: "Klorosis tanaman pada Penyakit kudis", ontology: "Klorosis pada tanaman pada Penyakit kudis")
- UBIJALAR-BUSUKHITAM-01: label berbeda untuk PengamatanPenyakitBusukHitamBlackRotUbiJalarBusukTanaman (case: "Busuk tanaman pada Penyakit busuk hitam (black rot)", ontology: "Busuk pada tanaman pada Penyakit busuk hitam (black rot)")
- KACANGTANAH-BERCAK-01: label berbeda untuk PengamatanPenyakitBercakDaunKacangTanahBercakTanaman (case: "Bercak tanaman pada Penyakit Bercak Daun", ontology: "Bercak pada tanaman pada Penyakit Bercak Daun")
- KACANGTANAH-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKacangTanahBercakTanaman (case: "Bercak tanaman pada KARAT", ontology: "Bercak pada tanaman pada KARAT")
- KACANGHIJAU-LAYU-01: label berbeda untuk PengamatanPenyakitLayuKacangHijauBusukTanaman (case: "Busuk tanaman pada LAYU", ontology: "Busuk pada tanaman pada LAYU")
- KACANGHIJAU-EMBUN-01: label berbeda untuk PengamatanPenyakitEmbunTepungKacangHijauTepungDaun (case: "Tepung daun pada EMBUN TEPUNG", ontology: "Tepung pada daun pada EMBUN TEPUNG")
- KEDELAI-AMBIG-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKedelaiBercakTanaman (case: "Bercak tanaman pada Penyakit Karat Daun", ontology: "Bercak pada tanaman pada Penyakit Karat Daun")
- KACANGTANAH-AMBIG-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKacangTanahBercakTanaman (case: "Bercak tanaman pada KARAT", ontology: "Bercak pada tanaman pada KARAT")

## Kasus gagal

Tidak ada kasus yang gagal.

## Top-1 meleset (masih dalam top-3)

- **PADI-PURE-HDB-01** expected `PenyakitHawarDaunBakteriPadi`, rank 2
  - top-3: PenyakitKerdilRumputDanKerdilHampaPadi (0.556, SEDANG); PenyakitHawarDaunBakteriPadi (0.352, RENDAH); PenyakitHawarPelepahDaunPadi (0.281, RENDAH)
- **KACANGTANAH-PURE-KARAT-01** expected `PenyakitKaratDaunKacangTanah`, rank 2
  - top-3: PenyakitBercakDaunKacangTanah (0.521, SEDANG); PenyakitKaratDaunKacangTanah (0.421, SEDANG); PenyakitBelangMottleKacangTanah (0.169, RENDAH)

## Determinism & performa

- Determinism: stabil (PADI-BLAS-01)
- Performa: p50 36.5967 ms; p95 69.7361 ms (20 sampel)

## Catatan

- Kasus `gold` saat ini di-seed dari ontology dan bertanda `source: ontology-temporary`; verifikasi halaman buku sebelum mengklaim akurasi independen.
- Kasus `sanity` dibuat otomatis dari gejala penyakit itu sendiri; hanya untuk regression, bukan akurasi.
- Baseline memakai exact match + rumus lama 0,7/0,3 pada kasus yang sama.
