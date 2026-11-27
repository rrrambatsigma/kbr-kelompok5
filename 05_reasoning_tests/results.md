# Hasil Validasi Reasoning Diagnosis

- Waktu: 2026-11-27T12:59:56.361Z
- Base URL: http://127.0.0.1:3000
- Model: forward-chaining-cf-v1
- Ontology: e42991cedc4f / e42991cedc4f9f714f59004de1b47b604b355152f6beffb14bc4c389d90509cc

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
- Performa: tidak dijalankan (pakai `--perf`)

## Catatan

- Kasus `gold` saat ini di-seed dari ontology dan bertanda `source: ontology-temporary`; verifikasi halaman buku sebelum mengklaim akurasi independen.
- Kasus `sanity` dibuat otomatis dari gejala penyakit itu sendiri; hanya untuk regression, bukan akurasi.
- Baseline memakai exact match + rumus lama 0,7/0,3 pada kasus yang sama.
