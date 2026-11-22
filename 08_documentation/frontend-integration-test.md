# Frontend Integration Test — TaniCare

Tanggal: 19 November 2026

Lingkungan:

- Frontend Vite `http://localhost:5173`
- Node API `http://localhost:3000`
- Java reasoning API `http://127.0.0.1:8082`
- Fuseki `http://127.0.0.1:3030`
- Browser Chromium melalui browser panel

## Hasil build dan unit test

| Pemeriksaan | Hasil |
|---|---|
| `npm run build` | PASS |
| `npm test` | PASS - 11 test |
| TypeScript `tsc --noEmit` | PASS |
| Console error kritis | Tidak ada |

## Pengujian endpoint dari frontend

| Fitur | Endpoint | Hasil |
|---|---|---|
| Daftar tanaman | `GET /api/plants` | 7 tanaman tampil |
| Preview penyakit | `GET /api/diseases` | 53 penyakit; Padi/Jagung tampil |
| Gejala Padi | `GET /api/symptoms?plantId=Padi` | 26 gejala tampil, dikelompokkan per bagian |
| Fase Padi | `GET /api/phases?plantId=Padi` | 7 opsi fase tampil (2 punya tautan penyakit) |
| Fase Ubi Kayu | `GET /api/phases?plantId=UbiKayu` | 7 opsi fase tampil, semua tanpa tautan; diagnosis tetap bisa lanjut |
| Diagnosis | `POST /api/diagnosis` | 200; Blas top-1 |
| Detail penyakit | `GET /api/diseases/PenyakitBulaiJagung` | Detail patogen/gejala/pengendalian tampil |
| Empty result | direct `/diagnosis/result` | Empty state tampil |
| 404 | `/halaman-tidak-ada` | Halaman NotFound tampil |

## Pengujian end-to-end diagnosis

Langkah yang dilakukan:

1. Buka `/`.
2. Klik “Mulai Diagnosis”.
3. Pilih Padi.
4. Pada langkah "Fase Tumbuh", pilih "Fase Anakan" (opsional).
5. Pilih 3 gejala:
   - Bercak daun pada Penyakit Blas
   - Pengamatan gejala Penyakit Blas (gejala umum)
   - Pengamatan gejala Penyakit Blas (malai)
6. Lanjutkan → Konfirmasi.
7. Klik “Proses Diagnosis”.

Hasil:

```text
URL: /diagnosis/result
Fase: Fase Anakan
Top candidate: Penyakit Blas
Status fase kandidat: Fase belum tercatat (Blas belum punya tautan fase)
Skor: 75% (0.7466)
Confidence: TINGGI
Penjelasan: 3 gejala cocok persis. Kandidat ini menjelaskan seluruh gejala yang dipilih.
Patogen: Magnaporthe grisea
Kandidat lain: 3 (Kerdil, Hawar Pelepah, HDB)
```

Skenario fase cocok: pilih Padi → Fase Anakan → gejala Hawar Pelepah
Padi. Kandidat Hawar Pelepah harus menampilkan “Sesuai fase”.

Payload yang dikirim benar-benar berasal dari form dan response berasal dari
backend. Tidak ada hasil statis.

## Pengujian fase pertumbuhan

Halaman fase menampilkan **7 kelas fase**:

1. Fase Pembibitan
2. Fase Vegetatif
3. Fase Anakan
4. Fase Pembungaan
5. Fase Generatif
6. Fase Pemasakan
7. Fase Panen

Untuk Padi, Fase Anakan dan Fase Pemasakan menampilkan `1 penyakit`; lima
lainnya menampilkan “Belum ada penyakit tertaut”. Semua tetap bisa dipilih.
Fase yang tidak punya tautan tidak menghasilkan error; `phaseMatch` mengikuti
data penyakit.

## Pengujian faktor risiko

- Diagnosis Blas: card “Faktor risiko & pemicu” menampilkan **Musim hujan**.
- Diagnosis HDB: card menampilkan beberapa faktor (suhu, kelembapan, hujan
  lebat) sesuai relasi `dipengaruhiOleh`.
- Faktor risiko tidak mengubah skor atau ranking; nilainya hanya informasi.
- Jika kandidat tidak punya faktor, UI menampilkan empty state.

## Pengujian Knowledge Base

1. Buka `/knowledge-base`.
2. Statistik: 53 entri penyakit, 7 komoditas.
3. Cari “Blas” → 1 hasil: Penyakit Blas.
4. Buka detail `PenyakitBulaiJagung` → patogen, gejala, pengendalian, fase,
   faktor risiko tampil.
5. Pagination: 9 kartu per halaman, 6 halaman untuk 53 entri.

## Error handling yang diuji

- Direct result tanpa state → empty state, bukan data contoh.
- Search tanpa hasil → empty state + reset filter.
- **Backend Node dimatikan**, lalu Knowledge Base dibuka:
  - halaman menampilkan “Tidak dapat terhubung ke server TaniCare”;
  - statistik menampilkan `—`, bukan angka palsu;
  - tombol “Coba lagi” tersedia.
- Node dinyalakan lagi, “Coba lagi” ditekan → 53 entri dan 7 komoditas
  kembali tampil.
- API client memiliki pemetaan error untuk backend mati, timeout,
  `FUSEKI_UNAVAILABLE`, `REASONING_UNAVAILABLE`, `INVALID_REQUEST`,
  `NOT_FOUND`, dan `INVALID_RESPONSE`.

## Responsive

- Desktop 1440×900: navbar horizontal, hero dua kolom, grid tanaman 4 kolom.
- Lebar ~510px: sidebar menjadi nav horizontal, form satu kolom, kartu
  bertumpuk.
- Tidak ditemukan horizontal overflow pada halaman yang diuji.
- Tombol utama dan input memiliki tinggi minimum 48px.

## Gap yang belum diuji karena backend belum mendukung

- Varietas, bagian tanaman, dan kondisi lingkungan sebagai input diagnosis.
- Filter tipe patogen pada katalog.
- Foto penyakit.
- Statistik “entri tervalidasi”/“gejala klinis” yang berbeda dari count API.

Gap ini tidak diisi dengan data palsu.

## Cara mengulang

```powershell
# Service backend harus hidup
cd .\06_backend\reasoning-api
.\mvnw.cmd spring-boot:run

cd ..\node-api
npm run dev

# Frontend
cd ..\..\07_frontend
npm install
npm run dev
```

Buka `http://localhost:5173`, lalu ulangi skenario di atas.
