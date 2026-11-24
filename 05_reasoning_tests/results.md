# Hasil Validasi Reasoning Diagnosis

- Waktu: 2026-11-24T04:27:02.075Z
- Base URL: http://127.0.0.1:3000
- Model: forward-chaining-cf-v1
- Ontology: 2085d0a7f368 / 2085d0a7f36841e6d2b5ce04a2d79b48028f02e1d8a504037be8b8866bf5cbc4

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

- PADI-BLAS-01: label berbeda untuk PengamatanPenyakitBlasPadiBercakDaun (case: "Bercak daun pada Penyakit Blas", ontology: "Bercak daun — Penyakit Blas")
- PADI-BLAS-01: label berbeda untuk PengamatanPenyakitBlasPadiKhasMalai (case: "Pengamatan gejala Penyakit Blas", ontology: "Gejala khas dari penyakit ini, yaitu blas daun dan blas malai.")
- PADI-BLAS-01: label berbeda untuk PengamatanPenyakitBlasPadiMalaiPatah (case: "Malai patah pada Penyakit Blas", ontology: "Malai patah — Penyakit Blas")
- PADI-HDB-01: label berbeda untuk PengamatanPenyakitHawarDaunBakteriPadiHawarDaun (case: "Hawar daun pada Penyakit Hawar Daun Bakteri", ontology: "Hawar daun — Penyakit Hawar Daun Bakteri")
- PADI-HDB-01: label berbeda untuk PengamatanPenyakitHawarDaunBakteriPadiKlorosisDaun (case: "Klorosis daun pada Penyakit Hawar Daun Bakteri", ontology: "Klorosis daun — Penyakit Hawar Daun Bakteri")
- PADI-HDB-01: label berbeda untuk PengamatanPenyakitHawarDaunBakteriPadiLayuDaun (case: "Layu daun pada Penyakit Hawar Daun Bakteri", ontology: "Layu daun — Penyakit Hawar Daun Bakteri")
- KEDELAI-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKedelaiBercakDaun (case: "Bercak daun pada KARAT", ontology: "Bercak daun — Penyakit Karat Daun")
- KEDELAI-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKedelaiKlorosisDaun (case: "Klorosis daun pada KARAT", ontology: "Klorosis daun — Penyakit Karat Daun")
- KEDELAI-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKedelaiBercakTanaman (case: "Bercak tanaman pada Penyakit Karat Daun", ontology: "Bercak pada tanaman — Penyakit Karat Daun")
- KEDELAI-BIJIUNGU-01: label berbeda untuk PengamatanPenyakitBercakBijiUnguKedelaiBercakDaun (case: "Bercak daun pada Penyakit Bercak Biji Ungu", ontology: "Bercak daun — Penyakit Bercak Biji Ungu")
- KEDELAI-BIJIUNGU-01: label berbeda untuk PengamatanPenyakitBercakBijiUnguKedelaiHawarDaun (case: "Hawar daun pada Penyakit Bercak Biji Ungu", ontology: "Hawar daun — Penyakit Bercak Biji Ungu")
- KEDELAI-BIJIUNGU-01: label berbeda untuk PengamatanPenyakitBercakBijiUnguKedelaiNekrosisDaun (case: "Nekrosis daun pada Penyakit Bercak Biji Ungu", ontology: "Nekrosis daun — Penyakit Bercak Biji Ungu")
- JAGUNG-BULAI-01: label berbeda untuk PengamatanPenyakitBulaiJagungKlorosisDaun (case: "Klorosis daun pada Penyakit Bulai", ontology: "Klorosis daun — Penyakit Bulai")
- JAGUNG-BULAI-01: label berbeda untuk PengamatanPenyakitBulaiJagungKerdilTanaman (case: "Kerdil tanaman pada Penyakit Bulai", ontology: "Kerdil tanaman — Penyakit Bulai")
- JAGUNG-BULAI-01: label berbeda untuk PengamatanPenyakitBulaiJagungPertumbuhanTerhambat (case: "Pertumbuhan terhambat pada Penyakit Bulai", ontology: "Pertumbuhan terhambat — Penyakit Bulai")
- JAGUNG-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunJagungKlorosisDaun (case: "Klorosis daun pada Penyakit Karat Daun", ontology: "Klorosis daun — Penyakit Karat Daun")
- JAGUNG-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunJagungBercakTanaman (case: "Bercak pada tanaman pada Penyakit Karat Daun", ontology: "Bercak pada tanaman — Penyakit Karat Daun")
- JAGUNG-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunJagungBiasanyaDiawaliBagianBawahBerkembang (case: "Pengamatan gejala Penyakit Karat Daun", ontology: "Gejala karat biasanya diawali dari daun bagian bawah dan berkembang ke daun bagian atas…")
- UBIJALAR-KUDIS-01: label berbeda untuk PengamatanPenyakitKudisUbiJalarBercakDaun (case: "Bercak daun pada Penyakit kudis", ontology: "Bercak daun — Penyakit kudis")
- UBIJALAR-KUDIS-01: label berbeda untuk PengamatanPenyakitKudisUbiJalarKlorosisTanaman (case: "Klorosis tanaman pada Penyakit kudis", ontology: "Klorosis pada tanaman — Penyakit kudis")
- UBIJALAR-KUDIS-01: label berbeda untuk PengamatanPenyakitKudisUbiJalarMenjadiTidakProduktifFotosintesisTingkat (case: "Pengamatan gejala Penyakit kudis", ontology: "Daun menjadi tidak produktif dalam fotosintesis jika pada tingkat serangan berat…")
- UBIJALAR-BUSUKHITAM-01: label berbeda untuk PengamatanPenyakitBusukHitamBlackRotUbiJalarBusukAkar (case: "Busuk akar pada Penyakit busuk hitam (black rot)", ontology: "Busuk akar — Penyakit busuk hitam (black rot)")
- UBIJALAR-BUSUKHITAM-01: label berbeda untuk PengamatanPenyakitBusukHitamBlackRotUbiJalarBusukTanaman (case: "Busuk tanaman pada Penyakit busuk hitam (black rot)", ontology: "Busuk pada tanaman — Penyakit busuk hitam (black rot)")
- UBIJALAR-BUSUKHITAM-01: label berbeda untuk PengamatanPenyakitBusukHitamBlackRotUbiJalarFimbriataABPascapanenC (case: "Pengamatan gejala Penyakit busuk hitam (black rot)", ontology: "Fimbriata, (a&b) gejala pascapanen pada ubi jalar (c&d) Anterior dan posterior koloni…")
- UBIKAYU-BUSUKAKAR-01: label berbeda untuk PengamatanBusukAkarUbiKayuBusukAkar (case: "Busuk akar pada Busuk akar", ontology: "Busuk akar")
- UBIKAYU-BUSUKAKAR-01: label berbeda untuk PengamatanBusukAkarUbiKayuBusukBatang (case: "Busuk batang pada Busuk akar", ontology: "Busuk batang — Busuk akar")
- UBIKAYU-HDB-01: label berbeda untuk PengamatanHawarDaunBakteriUbiKayuHawarDaun (case: "Hawar daun pada Hawar daun bakteri", ontology: "Hawar daun — Hawar daun bakteri")
- UBIKAYU-HDB-01: label berbeda untuk PengamatanHawarDaunBakteriUbiKayuLayuDaun (case: "Layu daun pada Hawar daun bakteri", ontology: "Layu daun — Hawar daun bakteri")
- KACANGTANAH-BERCAK-01: label berbeda untuk PengamatanPenyakitBercakDaunKacangTanahBercakDaun (case: "Bercak daun pada Penyakit Bercak Daun", ontology: "Bercak daun")
- KACANGTANAH-BERCAK-01: label berbeda untuk PengamatanPenyakitBercakDaunKacangTanahKlorosisDaun (case: "Klorosis daun pada Penyakit Bercak Daun", ontology: "Klorosis daun — Penyakit Bercak Daun")
- KACANGTANAH-BERCAK-01: label berbeda untuk PengamatanPenyakitBercakDaunKacangTanahBercakTanaman (case: "Bercak tanaman pada Penyakit Bercak Daun", ontology: "Bercak pada tanaman — Penyakit Bercak Daun")
- KACANGTANAH-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKacangTanahBercakDaun (case: "Bercak daun pada KARAT", ontology: "Bercak daun — Penyakit Karat Daun")
- KACANGTANAH-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKacangTanahKlorosisDaun (case: "Klorosis daun pada KARAT", ontology: "Klorosis daun — Penyakit Karat Daun")
- KACANGTANAH-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKacangTanahBercakTanaman (case: "Bercak tanaman pada KARAT", ontology: "Bercak pada tanaman — Penyakit Karat Daun")
- KACANGHIJAU-LAYU-01: label berbeda untuk PengamatanPenyakitLayuKacangHijauLayuDaun (case: "Layu daun pada LAYU", ontology: "Layu daun")
- KACANGHIJAU-LAYU-01: label berbeda untuk PengamatanPenyakitLayuKacangHijauBusukTanaman (case: "Busuk tanaman pada LAYU", ontology: "Busuk pada tanaman — Penyakit Layu")
- KACANGHIJAU-EMBUN-01: label berbeda untuk PengamatanPenyakitEmbunTepungKacangHijauTepungDaun (case: "Tepung daun pada EMBUN TEPUNG", ontology: "Tepung pada daun — Penyakit Embun Tepung")
- PADI-AMBIG-HDB-01: label berbeda untuk PengamatanPenyakitHawarDaunBakteriPadiIstilahKresekSendiriDiambilBahasa (case: "Pengamatan gejala Penyakit Hawar Daun Bakteri", ontology: "Istilah kresek sendiri diambil dari bahasa Jawa yang berarti suara daun-daun yang mati…")
- PADI-AMBIG-HDB-01: label berbeda untuk PengamatanPenyakitHawarPelepahDaunPadiBercakDaun (case: "Bercak daun pada Penyakit Hawar Pelepah Daun", ontology: "Bercak daun — Penyakit Hawar Pelepah Daun")
- PADI-AMBIG-HDB-01: label berbeda untuk PengamatanPenyakitKerdilRumputDanKerdilHampaPadiKlorosisDaun (case: "Klorosis daun pada Penyakit Kerdil Rumput dan Kerdil Hampa", ontology: "Klorosis daun — Penyakit Kerdil Rumput dan Kerdil Hampa")
- KEDELAI-AMBIG-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKedelaiBercakTanaman (case: "Bercak tanaman pada Penyakit Karat Daun", ontology: "Bercak pada tanaman — Penyakit Karat Daun")
- KEDELAI-AMBIG-KARAT-01: label berbeda untuk PengamatanPenyakitBercakBijiUnguKedelaiBercakDaun (case: "Bercak daun pada Penyakit Bercak Biji Ungu", ontology: "Bercak daun — Penyakit Bercak Biji Ungu")
- KEDELAI-AMBIG-KARAT-01: label berbeda untuk PengamatanPenyakitMosaikKedelaiSoybeanMosaicVirusKedelaiKlorosisDaun (case: "Klorosis daun pada Penyakit Mosaik Kedelai (Soybean Mosaic Virus)", ontology: "Klorosis daun — Penyakit Mosaik Kedelai (Soybean Mosaic Virus)")
- JAGUNG-AMBIG-BULAI-01: label berbeda untuk PengamatanPenyakitBulaiJagungMulaiMuncul15Hingga17 (case: "Pengamatan gejala Penyakit Bulai", ontology: "Penyakit jagung mulai muncul antara 15 hingga 17 hari setelah infeksi (Habibi et al.…")
- JAGUNG-AMBIG-BULAI-01: label berbeda untuk PengamatanPenyakitKaratDaunJagungKlorosisDaun (case: "Klorosis daun pada Penyakit Karat Daun", ontology: "Klorosis daun — Penyakit Karat Daun")
- JAGUNG-AMBIG-BULAI-01: label berbeda untuk PengamatanPenyakitLayuStewartJagungKerdilTanaman (case: "Kerdil tanaman pada Penyakit Layu Stewart", ontology: "Kerdil tanaman — Penyakit Layu Stewart")
- UBIKAYU-AMBIG-HDB-01: label berbeda untuk PengamatanHawarDaunBakteriUbiKayuHawarDaun (case: "Hawar daun pada Hawar daun bakteri", ontology: "Hawar daun — Hawar daun bakteri")
- UBIKAYU-AMBIG-HDB-01: label berbeda untuk PengamatanBercakDaunCoklatUbiKayuBercakDaun (case: "Bercak daun pada Bercak daun Coklat", ontology: "Bercak daun — Bercak daun Coklat")
- UBIKAYU-AMBIG-HDB-01: label berbeda untuk PengamatanBusukPangkalBatangUbiKayuLayuDaun (case: "Layu daun pada Busuk pangkal batang", ontology: "Layu daun — Busuk pangkal batang")
- KACANGTANAH-AMBIG-KARAT-01: label berbeda untuk PengamatanPenyakitKaratDaunKacangTanahBercakTanaman (case: "Bercak tanaman pada KARAT", ontology: "Bercak pada tanaman — Penyakit Karat Daun")
- KACANGTANAH-AMBIG-KARAT-01: label berbeda untuk PengamatanPenyakitBercakDaunKacangTanahBercakDaun (case: "Bercak daun pada Penyakit Bercak Daun", ontology: "Bercak daun")
- KACANGTANAH-AMBIG-KARAT-01: label berbeda untuk PengamatanPenyakitBercakDaunKacangTanahKlorosisDaun (case: "Klorosis daun pada Penyakit Bercak Daun", ontology: "Klorosis daun — Penyakit Bercak Daun")
- UBIJALAR-AMBIG-BERCAKKUNING-01: label berbeda untuk PengamatanPenyakitBercakKuningUbiJalarPucukMati (case: "Pucuk mati pada Penyakit bercak kuning", ontology: "Pucuk mati — Penyakit bercak kuning")
- UBIJALAR-AMBIG-BERCAKKUNING-01: label berbeda untuk PengamatanPenyakitKudisUbiJalarBercakDaun (case: "Bercak daun pada Penyakit kudis", ontology: "Bercak daun — Penyakit kudis")
- UBIJALAR-AMBIG-BERCAKKUNING-01: label berbeda untuk PengamatanLayuFusariumUbiJalarKlorosisDaun (case: "Klorosis daun pada layu fusarium", ontology: "Klorosis daun — layu fusarium")
- PADI-PURE-HDB-01: label berbeda untuk PengamatanPenyakitHawarPelepahDaunPadiBercakDaun (case: "Bercak daun pada Penyakit Hawar Pelepah Daun", ontology: "Bercak daun — Penyakit Hawar Pelepah Daun")
- PADI-PURE-HDB-01: label berbeda untuk PengamatanPenyakitKerdilRumputDanKerdilHampaPadiKlorosisDaun (case: "Klorosis daun pada Penyakit Kerdil Rumput dan Kerdil Hampa", ontology: "Klorosis daun — Penyakit Kerdil Rumput dan Kerdil Hampa")
- KACANGTANAH-PURE-KARAT-01: label berbeda untuk PengamatanPenyakitBercakDaunKacangTanahBercakDaun (case: "Bercak daun pada Penyakit Bercak Daun", ontology: "Bercak daun")
- KACANGTANAH-PURE-KARAT-01: label berbeda untuk PengamatanPenyakitBercakDaunKacangTanahKlorosisDaun (case: "Klorosis daun pada Penyakit Bercak Daun", ontology: "Klorosis daun — Penyakit Bercak Daun")

## Kasus gagal

Tidak ada kasus yang gagal.

## Top-1 meleset (masih dalam top-3)

- **PADI-PURE-HDB-01** expected `PenyakitHawarDaunBakteriPadi`, rank 2
  - top-3: PenyakitKerdilRumputDanKerdilHampaPadi (0.556, SEDANG); PenyakitHawarDaunBakteriPadi (0.352, RENDAH); PenyakitHawarPelepahDaunPadi (0.281, RENDAH)
- **KACANGTANAH-PURE-KARAT-01** expected `PenyakitKaratDaunKacangTanah`, rank 2
  - top-3: PenyakitBercakDaunKacangTanah (0.521, SEDANG); PenyakitKaratDaunKacangTanah (0.421, SEDANG); PenyakitBelangMottleKacangTanah (0.169, RENDAH)

## Determinism & performa

- Determinism: stabil (PADI-BLAS-01)
- Performa: p50 48.4767 ms; p95 82.7558 ms (20 sampel)

## Catatan

- Kasus `gold` saat ini di-seed dari ontology dan bertanda `source: ontology-temporary`; verifikasi halaman buku sebelum mengklaim akurasi independen.
- Kasus `sanity` dibuat otomatis dari gejala penyakit itu sendiri; hanya untuk regression, bukan akurasi.
- Baseline memakai exact match + rumus lama 0,7/0,3 pada kasus yang sama.
