# Derivasi Certainty Factor (CF) Diagnosis

Dokumen ini menjawab pertanyaan: **angka skor diagnosis berasal dari mana?**
Semua parameter yang memengaruhi skor dikumpulkan di
`06_backend/node-api/src/lib/reasoning/config.ts` dan dapat diuji ulang.

## 1. Alur perhitungan

```text
gejala terpilih
  → bobot bukti (w)        = bobot dasar × specificitas × bobot bagian
  → CF gabungan            = 1 - Π(1 - w)              (noisy-OR / MYCIN)
  → skor kandidat          = CF × faktor kelengkapan × faktor cakupan × faktor fase
```

### 1.1 Specificitas gejala

Specificitas menurunkan bobot gejala yang dipakai banyak penyakit.

```text
spec(df, N) = 0.5 + 0.5 × log((N + 1) / (df + 1)) / log(N + 1)
```

- `df` = jumlah penyakit (pada tanaman yang sama) yang memiliki konsep gejala itu.
- `N` = jumlah penyakit bergejala pada tanaman itu.
- `df = 1` → `spec = 1.0` (gejala khas).
- `df = N` → `spec = 0.5` (gejala umum).
- Rumus ini adalah varian IDF: semakin langka sebuah gejala, semakin tinggi
  daya bedanya. Batas bawah 0.5 mencegah gejala umum bernilai nol.

### 1.2 Bobot bukti

```text
w = min(0.9, bobot_dasar × spec × bobot_bagian)
```

| Komponen | Nilai | Sumber |
|---|---:|---|
| `bobot_dasar` exact match | 1.0 | observasi sama persis |
| `bobot_dasar` pilihan konsep kanonik | 1.0 | user memilih konsep langsung |
| `bobot_dasar` kanonik dari observasi penyakit lain | 0.6 | pencocokan lebih lemah |
| `maxEvidenceWeight` | 0.9 | mencegah satu bukti langsung mentok |
| `bobot_bagian` | 1.0 | **provisional**, menunggu expert |

### 1.3 CF gabungan

```text
CF = 1 - Π(1 - wᵢ)
```

Ini adalah noisy-OR, ekuivalen dengan kombinasi Certainty Factor MYCIN
`CF = CF + w × (1 − CF)`. Urutan bukti tidak mengubah hasil. Contoh:

| Bukti | CF |
|---|---:|
| 1 × 0.9 | 0.900 |
| 2 × 0.9 | 0.990 |
| 1 × 0.7 + 1 × 0.5 | 0.850 |
| 3 × 0.5 | 0.875 |

### 1.4 Skor akhir

```text
completeness = jumlah gejala cocok / jumlah gejala dipilih
coverage     = jumlah gejala cocok / max(jumlah gejala penyakit, 4)
faktor_fase  = 1.05 jika fase cocok, selain itu 1.0
skor         = CF × (0.7 + 0.3 × completeness) × (0.5 + 0.5 × coverage) × faktor_fase
```

- `completeness` menghukum kandidat yang hanya menjelaskan sebagian gejala user.
- `coverage` menghukum kandidat yang penuh gejala tetapi hanya sebagian kecil
  gejalanya yang cocok. Penyebut minimum 4 mencegah penyakit dengan 1–2 gejala
  mendapat coverage 1.0 karena datanya miskin.
- `faktor_fase` hanya ranking lembut; tidak pernah menghukum kandidat tanpa
  data fase.

### 1.5 Ambang keyakinan

| Label | Syarat |
|---|---|
| `TINGGI` | skor ≥ 0.7 dan bukti ≥ 2 |
| `SEDANG` | skor ≥ 0.4 dan bukti ≥ 2 |
| `RENDAH` | selain itu, termasuk semua kasus 1 bukti |

## 2. Bobot per bagian tanaman

Bobot bagian **belum diisi expert**; saat ini semua 1.0 (netral) agar ranking
tidak berubah sebelum validasi. Nilai usulan untuk diisi setelah diskusi dengan
mahasiswa proteksi tanaman:

| Bagian | Bobot usulan | Alasan |
|---|---:|---|
| Daun | 1.00 | gejala paling banyak dan paling mudah diamati |
| Malai | 0.95 | gejala reproduktif, kuat untuk padi |
| Batang | 0.90 | perlu pengamatan fisik |
| Akar | 0.90 | sering baru terlihat saat tanaman mati |
| Umbi | 0.90 | spesifik untuk ubi-umbian |
| Buah | 0.85 | bergantung fase |
| Biji | 0.80 | perlu pengamatan pascapanen |
| Polong | 0.80 | spesifik legum |
| Pucuk | 0.85 | gejala awal |
| Bunga | 0.75 | jarang tercatat |

Cara mengisi: ubah `PART_WEIGHTS` di `config.ts`, jalankan
`node run.mjs --perf`, lalu bandingkan top-1/top-3/MRR. Jangan mengubah bobot
tanpa mencatat hasilnya di dokumen ini.

## 3. Kalibrasi

Parameter ambang (0.7 / 0.4) dan faktor 0.7/0.5 dipilih dari evaluasi 75 kasus
(`05_reasoning_tests/`), bukan angka bulat sembarang:

| Metrik | Baseline 0.7/0.3 | Model sekarang |
|---|---:|---:|
| Top-1 fokus | 0.636 | **0.909** |
| Top-3 fokus | 0.909 | **1.000** |
| MRR fokus | 0.742 | **0.955** |
| Top-1 ambiguous | 0.000 | **0.750** |
| Negative | — | **5/5** |

Setelah bobot bagian diisi expert, kalibrasi ulang dan simpan hasil baru di
`05_reasoning_tests/results.md`.

## 4. Batas yang harus disebut di laporan

- Skor adalah **ranking berbasis aturan**, bukan probabilitas statistik.
- Bobot dasar dan bobot bagian adalah **penilaian pakar**, bukan hasil regresi.
- Specificitas dihitung dari distribusi gejala di KB, bukan dari prevalensi
  lapangan.
- Validasi expert minimal 20 kasus diperlukan sebelum mengklaim akurasi.

## 5. Lokasi kode

| Komponen | File |
|---|---|
| Parameter | `06_backend/node-api/src/lib/reasoning/config.ts` |
| Specificitas & bobot bukti | `06_backend/node-api/src/lib/reasoning/specificity.ts` |
| Kombinasi CF & skor | `06_backend/node-api/src/lib/reasoning/certainty.ts` |
| Pencocokan gejala | `06_backend/node-api/src/lib/reasoning/engine.ts` |
| Evaluasi | `05_reasoning_tests/run.mjs` |
