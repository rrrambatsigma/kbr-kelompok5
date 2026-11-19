# Backend KBR — Spring Boot + Apache Jena

Backend ini adalah lapisan API tipis untuk memuat dan memeriksa ontologi
`04_ontology/ontology_md.ttl`. Fokusnya saat ini adalah validasi koneksi
ontology ke Java, bukan diagnosis penuh.

## Stack

| Komponen | Versi |
|---|---|
| Java | 21 |
| Spring Boot | 4.1.2 |
| Apache Jena | 6.2.0 |
| Port default | 8081 |

## Menjalankan

```powershell
cd 06_backend
.\mvnw.cmd spring-boot:run
```

Konfigurasi ada di `src/main/resources/application.properties`:

```properties
server.port=8081
ontology.file=../04_ontology/ontology_md.ttl
```

Path `../04_ontology/...` relatif terhadap direktori kerja `06_backend`.
Jika aplikasi dijalankan dari root proyek, override path-nya:

```powershell
.\mvnw.cmd spring-boot:run -Dspring-boot.run.arguments=--ontology.file=04_ontology/ontology_md.ttl
```

## Endpoint yang tersedia

### `GET /api/health`

```json
{
  "status": "UP",
  "message": "KBR Backend is running"
}
```

### `GET /api/ontology/status`

```json
{
  "loaded": true,
  "tripleCount": 18973,
  "message": "Ontology berhasil dimuat menggunakan Apache Jena"
}
```

`tripleCount` mengikuti isi file yang dimuat. Jika artefak dibangun ulang,
angka ini otomatis berubah.

## Struktur kode

- `config/OntologyConfig.java` — memuat Turtle ke bean Jena `Model`; gagal cepat
  bila file ontology tidak ditemukan.
- `service/OntologyService.java` — status model dan jumlah triple.
- `controller/OntologyController.java` — endpoint status ontology.
- `controller/HealthController.java` — health check.

## Batas integrasi yang perlu diketahui

1. **SWRL tidak dieksekusi Jena.** `ontology_md.ttl` memuat 4 aturan SWRL, tetapi
   Jena ARQ hanya membaca triple. Inferensi `menghasilkanPenyakit` dan
   `merekomendasikanPengendalian` harus dijalankan offline dengan Pellet/
   owlready2, atau diturunkan ulang lewat SPARQL `CONSTRUCT`.
2. **Belum ada endpoint diagnosis.** API belum menerima gejala, memetakan ke
   `GejalaKanonik`, atau mengembalikan ranking penyakit.
3. **Belum ada query SPARQL di backend.** Jena sudah tersedia, tetapi controller
   masih terbatas pada status model.
4. **Tidak ada database.** Sumber kebenaran tetap file ontology; backend tidak
   menyimpan data pasien atau riwayat diagnosis.
5. **Tidak ada frontend.** Kontrak API masih minimal dan belum dipakai UI.

## Pola query yang disarankan untuk endpoint diagnosis

Query kandidat penyakit berdasarkan tanaman dan gejala kanonik:

```sparql
PREFIX ptp: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?penyakit ?nama (COUNT(DISTINCT ?gejala) AS ?kecocokan)
WHERE {
  ?penyakit a ptp:Penyakit ;
            rdfs:label ?nama ;
            ptp:menyerangTanaman ptp:Padi ;
            ptp:memilikiGejala ?pengamatan .
  ?pengamatan ptp:memilikiGejalaKanonik ?gejala .
}
GROUP BY ?penyakit ?nama
ORDER BY DESC(?kecocokan)
```

Query pengendalian penyakit kandidat:

```sparql
PREFIX ptp: <http://kbr.kelompok5.org/penyakit-tanaman-pangan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?aksi ?nama
WHERE {
  ptp:PenyakitBlasPadi ptp:dikendalikanDengan ?aksi .
  ?aksi rdfs:label ?nama .
}
```

Alur integrasi yang disarankan:

1. Validasi request: tanaman harus salah satu dari 7 tanaman in-scope.
2. Petakan input gejala ke IRI `GejalaKanonik`; tolak istilah yang tidak dikenal.
3. Jalankan query kandidat, hitung irisan gejala, lalu ranking berdasarkan jumlah
   kecocokan dan faktor lingkungan bila ada.
4. Ambil pengendalian spesifik lewat `dikendalikanDengan`; bila kosong, pakai
   `pengendalianUmum` milik tanaman.
5. Kembalikan penyakit, skor, pengendalian, dan kutipan `BuktiSumber`.
6. Tandai hasil sebagai diagnosis awal, bukan kepastian laboratorium.

## Verifikasi

```powershell
cd 06_backend
.\mvnw.cmd test
```

Test saat ini hanya memastikan konteks Spring Boot dapat dimuat. Test ontologi
dan SWRL ada di `04_ontology/tests/`.
