# Hasil Validasi Reasoning Diagnosis

- Waktu: 2026-11-24T06:14:27.148Z
- Base URL: http://127.0.0.1:3000
- Model: forward-chaining-cf-v1
- Ontology: 63caa37dd6a3 / 63caa37dd6a3d67026d1c64b96a1d5e99e698afb6976e5167532ad7751ca2b6b

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
| TINGGI | 7 | 100.0% | 100.0% |
| SEDANG | 13 | 92.3% | 100.0% |
| RENDAH | 2 | 50.0% | 100.0% |

## Kasus gagal

Tidak ada kasus yang gagal.

## Top-1 meleset (masih dalam top-3)

- **PADI-PURE-HDB-01** expected `PenyakitHawarDaunBakteriPadi`, rank 2
  - top-3: PenyakitKerdilRumputDanKerdilHampaPadi (0.556, SEDANG); PenyakitHawarDaunBakteriPadi (0.360, RENDAH); PenyakitHawarPelepahDaunPadi (0.281, RENDAH)
- **KACANGTANAH-PURE-KARAT-01** expected `PenyakitKaratDaunKacangTanah`, rank 2
  - top-3: PenyakitBercakDaunKacangTanah (0.521, SEDANG); PenyakitKaratDaunKacangTanah (0.421, SEDANG); PenyakitBelangMottleKacangTanah (0.169, RENDAH)

## Determinism & performa

- Determinism: stabil (PADI-BLAS-01)
- Performa: p50 32.7797 ms; p95 51.6967 ms (20 sampel)

## Catatan

- Kasus `gold` saat ini di-seed dari ontology dan bertanda `source: ontology-temporary`; verifikasi halaman buku sebelum mengklaim akurasi independen.
- Kasus `sanity` dibuat otomatis dari gejala penyakit itu sendiri; hanya untuk regression, bukan akurasi.
- Baseline memakai exact match + rumus lama 0,7/0,3 pada kasus yang sama.
