# Log Kasus & Case-Based Reasoning (CBR)

Dokumen ini menjelaskan **ABox runtime**: tempat menyimpan kasus diagnosis
pengguna, terpisah dari ontology kurasi. Tujuannya agar sistem punya memori
kasus yang bisa dipakai sebagai bukti tambahan, tanpa mencemari pengetahuan
pakar dan tanpa membuat ontology inkonsisten.

## 1. Konsep: dua ABox

| Bagian | Isi | Sifat |
|---|---|---|
| `plant-kb` (dataset `plant-kb`) | TBox + ABox pakar dari kurasi dokumen | Read-only, statis |
| `plant-kb-kasus` (dataset `plant-kb-kasus`) | Kasus diagnosis pengguna | Writable, tumbuh |

Alasannya:

- `load-ontology.ps1 -Reset` menghapus seluruh dataset ontology. Kalau kasus
  disimpan di sana, log ikut hilang.
- Kasus pengguna **bukan fakta pakar**. Kalau dimasukkan ke graf kurasi, kasus
  bisa memicu kontradiksi (misalnya tanaman diberi gejala tanaman lain) dan
  mengacaukan inferensi Openllet.
- Dataset terpisah membuat hak akses jelas: kurasi read-only, kasus writable.

Kasus **tidak pernah** dibaca oleh reasoner. Ia hanya dibaca oleh Node API
untuk CBR dan halaman riwayat.

## 2. Model data

Kasus ditulis ke graf `urn:kbr:kasus` di dataset `plant-kb-kasus`, memakai
kelas yang sudah ada di ontology:

- `ptp:Diagnosis` — satu kasus.
- `ptp:KandidatDiagnosis` — kandidat hasil reasoning (subclass `Diagnosis`).
- `ptp:memilikiTanaman`, `ptp:memilikiObservasi`,
  `ptp:menghasilkanPenyakit`, `ptp:merekomendasikanPengendalian`.
- `ptp:peringkat`, `ptp:skorKecocokan`, `ptp:tingkatKeyakinan`,
  `ptp:alasanKecocokan`.

Properti tambahan (dideklarasikan di
`06_backend/fuseki-config/case-vocab.ttl`):

| Properti | Isi |
|---|---|
| `ptp:idKasus` | UUID kasus |
| `ptp:waktuKasus` | waktu simpan (`xsd:dateTime`) |
| `ptp:sumberKasus` | `pengguna` atau `uji` |
| `ptp:statusVerifikasi` | `belum_diverifikasi` atau `terverifikasi` |
| `ptp:catatanPengguna` | catatan bebas, ≤ 500 karakter |
| `ptp:teksGejalaBebas` | teks gejala mentah, ≤ 500 karakter |
| `ptp:namaTanaman`, `ptp:namaPenyakit`, `ptp:ringkasanGejala` | label untuk tampilan |
| `ptp:faseKasus`, `ptp:kandidat` | relasi |

Contoh:

```turtle
<urn:kbr:kasus/6f1c...> a ptp:Diagnosis ;
  ptp:idKasus "6f1c..." ;
  ptp:waktuKasus "2026-11-22T10:00:00.000Z"^^xsd:dateTime ;
  ptp:sumberKasus "pengguna" ;
  ptp:statusVerifikasi "terverifikasi" ;
  ptp:memilikiTanaman ptp:Padi ;
  ptp:namaTanaman "Padi" ;
  ptp:ringkasanGejala "Bercak daun | Khas malai" ;
  ptp:memilikiObservasi ptp:PengamatanPenyakitBlasPadiBercakDaun, ... ;
  ptp:menghasilkanPenyakit ptp:PenyakitBlasPadi ;
  ptp:namaPenyakit "Penyakit Blas" ;
  ptp:teksGejalaBebas "daun menguning dan ada bercak" ;
  ptp:catatanPengguna "lahan tergenang" ;
  ptp:kandidat <urn:kbr:kasus/6f1c.../kandidat-1> .

<urn:kbr:kasus/6f1c.../kandidat-1> a ptp:KandidatDiagnosis ;
  ptp:peringkat 1 ;
  ptp:skorKecocokan "0.871"^^xsd:decimal ;
  ptp:tingkatKeyakinan "TINGGI" ;
  ptp:alasanKecocokan "..." ;
  ptp:menghasilkanPenyakit ptp:PenyakitBlasPadi .
```

## 3. API

| Method | Path | Keterangan |
|---|---|---|
| `POST` | `/api/cases` | Simpan kasus. Server menjalankan ulang diagnosis (deterministik), jadi skor tidak dikirim client. |
| `GET` | `/api/cases?plantId=&status=&limit=&offset=` | Daftar kasus. |
| `GET` | `/api/cases/stats` | Total, terverifikasi, per tanaman, per penyakit. |
| `GET` | `/api/cases/:id` | Detail + kandidat. |
| `POST` | `/api/cases/:id/verify` | `{ "diseaseId": "..." }` opsional; default top-1. |
| `DELETE` | `/api/cases/:id` | Hapus kasus + kandidat. |
| `GET` | `/api/health/cases` | Status case store (tidak memengaruhi readiness diagnosis). |

Contoh simpan:

```json
{
  "plantId": "Padi",
  "symptomIds": ["PengamatanPenyakitBlasPadiBercakDaun"],
  "topN": 5,
  "note": "lahan tergenang",
  "freeTextSymptoms": "daun menguning dan ada bercak",
  "confirmedDiseaseId": "PenyakitBlasPadi"
}
```

`source` default `pengguna`. `source: "uji"` dipakai integration test dan
tidak dihitung di CBR/statistik.

## 4. CBR (kasus serupa)

Saat `POST /api/diagnosis`, setelah kandidat dihitung:

1. Query kasus dengan tanaman yang sama dan gejala beririsan.
2. Filter: `statusVerifikasi = terverifikasi`, `sumberKasus = pengguna`,
   overlap ≥ `CBR_MIN_OVERLAP`.
3. Agregasi per penyakit → `similarCases: { count, maxOverlap, lastSeen }`.
4. Ditempel ke setiap kandidat.

Aturan penting:

- **CBR tidak mengubah skor.** Ia hanya bukti tambahan di UI.
- Kasus `belum_diverifikasi` tidak dihitung (bisa diubah lewat
  `CBR_INCLUDE_UNVERIFIED=true` untuk eksperimen).
- Kalau case store mati/timeout, diagnosis tetap 200 dan menambahkan warning
  `CASE_STORE_UNAVAILABLE`.

Yang dimaksud "belajar" di sini: **akumulasi kasus + retrieval + verifikasi
manusia**, bukan training model.

## 5. Input gejala dengan kata sendiri

Pengguna bisa menulis, misalnya, `daun menguning dan ada bercak`.

1. `POST /api/symptoms/match` mencocokkan teks ke label + `deskripsiGejala`
   dengan pencarian kata kunci dan kamus sinonim
   (`06_backend/node-api/src/data/symptom-synonyms.ts`).
2. Hasilnya saran ID gejala. Pengguna klik saran → ID gejala yang masuk ke
   diagnosis.
3. Teks mentah disimpan sebagai `ptp:teksGejalaBebas` saat kasus disimpan.

Batasannya: ini **pencarian kata kunci**, bukan pemahaman bahasa. Tidak semua
keluhan akan terpetakan, dan ID yang dipilih tetap harus dikonfirmasi pengguna.
Teks bebas tidak pernah menjadi fakta ontology.

## 6. Verifikasi dan batasan

- Verifikasi dilakukan di halaman `/riwayat` (pilih kandidat, atau default
  top-1). Status berubah menjadi `terverifikasi`.
- Belum ada autentikasi. Endpoint tulis hanya aman karena Fuseki dijalankan
  dengan `--localhost` dan `shiro.ini` membatasi ke localhost.
- Kasus tidak menyimpan identitas pengguna.
- Teks bebas dibatasi 500 karakter dan sebaiknya tidak memuat data pribadi.

## 7. Menjalankan

```powershell
# 1. Sekali saja, saat Fuseki mati
.\06_backend\scripts\init-case-store.ps1

# 2. Jalankan Fuseki (dua dataset)
.\06_backend\scripts\start-fuseki.ps1

# 3. Java, Node, frontend
cd 06_backend\reasoning-api; .\mvnw.cmd spring-boot:run
cd 06_backend\node-api; npm run dev
cd 07_frontend; npm run dev
```

Cek:

```powershell
Invoke-RestMethod http://127.0.0.1:3000/api/health/cases
Invoke-RestMethod http://127.0.0.1:3000/api/cases/stats
```

Reset ontology **tidak** menghapus kasus:

```powershell
.\06_backend\scripts\load-ontology.ps1 -Reset   # hanya plant-kb
```

## 8. Demo singkat

1. Diagnosis Padi, ketik "daun menguning dan ada bercak", pilih 3 saran.
2. Di halaman hasil, klik **Simpan kasus**.
3. Buka `/riwayat`, klik **Verifikasi**.
4. Ulangi sampai ada 2 kasus Blas terverifikasi.
5. Diagnosis Padi dengan gejala Blas → kandidat Blas menampilkan badge
   **2 kasus serupa**; skor tidak berubah.
6. Hapus kasus dari `/riwayat` untuk membersihkan demo.

## 9. Konfigurasi

| Env | Default | Arti |
|---|---|---|
| `FUSEKI_CASE_DATASET` | `plant-kb-kasus` | Nama dataset kasus |
| `CASE_LOG_ENABLED` | `true` | Matikan untuk menonaktifkan log |
| `CBR_INCLUDE_UNVERIFIED` | `false` | Ikutkan kasus belum diverifikasi |
| `CBR_MIN_OVERLAP` | `1` | Minimal gejala beririsan |
| `CBR_TIMEOUT_MS` | `2000` | Batas waktu query CBR |
| `SYMPTOM_MATCH_LIMIT` | `5` | Maksimal saran gejala |
| `SYMPTOM_MATCH_MIN_SCORE` | `0.35` | Ambang skor saran |
