# KBR Backend API

Backend REST untuk sistem pakar penyakit tanaman pangan. Semua data dibaca
langsung dari `04_ontology/ontology.ttl` menggunakan Apache Jena. Backend tidak
menyimpan data penyakit di database dan tidak mengubah ontology.

## Menjalankan

```powershell
cd 06_backend
.\mvnw.cmd spring-boot:run
```

Default port `8081`. Untuk memakai port lain:

```powershell
java -jar target\kbr-backend-0.0.1-SNAPSHOT.jar --server.port=8082
```

Konfigurasi ada di `06_backend/src/main/resources/application.properties`:

| Property | Arti |
| --- | --- |
| `ontology.file` | Lokasi ontology. Dicoba juga `04_ontology/ontology.ttl` dan `../04_ontology/ontology.ttl`. |
| `server.port` | Port HTTP. |
| `app.cors.allowed-origins` | Origin frontend yang diizinkan, dipisah koma. |
| `reasoning.engine` | `noop` selama reasoning belum diintegrasikan. |
| `reasoning.timeout-ms` | Disiapkan untuk adapter reasoning; belum dipaksakan backend. |

## Konvensi

- `id` setiap entitas adalah local name ontology, misalnya `Padi`,
  `PenyakitBlasPadi`, atau `MagnaportheGrisea`.
- Endpoint daftar selalu mengembalikan `{ "count": <jumlah>, "items": [ ... ] }`.
- Error memakai `ProblemDetail` dengan field `code`, `timestamp`, dan `errors`
  (untuk error validasi).
- Field yang tidak tersedia di ontology dikembalikan `null` dan disertai
  `warnings`. Backend tidak mengarang deskripsi, kategori, tingkat keparahan,
  atau URL.
- `category` penyakit masih `null` sampai reasoning engine terintegrasi.

## Endpoint

### `GET /api/health`

```json
{ "status": "UP", "message": "KBR Backend is running" }
```

### `GET /api/ontology/status`

```json
{
  "loaded": true,
  "tripleCount": 5436,
  "file": "../04_ontology/ontology.ttl",
  "counts": {
    "plants": 7,
    "diseases": 57,
    "symptoms": 240,
    "pathogens": 59,
    "controls": 261,
    "varieties": 34,
    "plantParts": 6,
    "growthPhases": 3,
    "environmentalFactors": 5,
    "references": 2
  },
  "reasoning": { "engine": "noop", "available": false },
  "message": "Ontology berhasil dimuat menggunakan Apache Jena"
}
```

### `GET /api/plants`

Mengembalikan 7 tanaman. Item berisi `id`, `label`, `scientificName`,
`diseaseCount`, `varietyCount`, dan `generalControlCount`.

### `GET /api/plants/{id}`

Berisi detail tanaman, daftar penyakit, varietas, pengendalian umum, dan
`warnings`.

```json
{
  "id": "Padi",
  "label": "Padi",
  "scientificName": null,
  "description": null,
  "diseases": [
    {
      "id": "PenyakitBlasPadi",
      "label": "Penyakit Blas",
      "plantId": "Padi",
      "plantLabel": "Padi",
      "pathogenNames": [
        "Magnaporthe grisea",
        "Pyricularia grisea",
        "Pyricularia oryzae"
      ],
      "symptomCount": 7,
      "controlCount": 8,
      "category": null
    }
  ],
  "varieties": [],
  "generalControls": [],
  "warnings": ["SCIENTIFIC_NAME_NOT_AVAILABLE", "DESCRIPTION_NOT_AVAILABLE"]
}
```

### `GET /api/plants/{id}/symptoms?diseaseId={diseaseId}`

Daftar gejala milik tanaman, opsional difilter ke satu penyakit. Jika
`diseaseId` bukan milik tanaman tersebut, request ditolak dengan `400`.

### `GET /api/diseases?plantId={plantId}`

Daftar seluruh penyakit (57) atau penyakit milik satu tanaman. Setiap penyakit
muncul tepat satu kali, meskipun ontology menetapkan lebih dari satu patogen.
`pathogenNames` berisi semua patogen yang tercatat.

### `GET /api/diseases/{id}`

Detail penyakit beserta seluruh patogen, gejala, bagian tanaman, fase, faktor
lingkungan, pengendalian, pengendalian umum, referensi, dan `warnings`.

`pathogens` dapat berisi lebih dari satu item (12 penyakit memiliki 2–5
patogen). Penyakit tanpa patogen mengembalikan `pathogens: []` dan warning
`PATHOGEN_NOT_AVAILABLE`.

### `GET /api/symptoms?plantId=&diseaseId=&partId=`

Daftar gejala. Filter dapat dikombinasikan. `partId` memfilter berdasarkan
bagian tanaman tempat gejala muncul. Kombinasi `plantId` + `diseaseId` harus
konsisten.

Item gejala:

```json
{
  "id": "GejalaBlasDaunMenunjukkanBercakBerwarna_2a00d88b",
  "label": "Daun menunjukkan bercak berbentuk belah ketupat",
  "partIds": ["Daun"],
  "partLabels": ["Daun"],
  "diseaseId": "PenyakitBlasPadi",
  "diseaseLabel": "Penyakit Blas"
}
```

### `POST /api/diagnosis`

Request:

```json
{
  "plantId": "Padi",
  "symptomIds": [
    "GejalaBlasDaunMenunjukkanBercakBerwarna_2a00d88b",
    "GejalaGejalaPenyakitBlasDapatDitandai_c0feda66"
  ],
  "partIds": ["Daun"],
  "phaseId": null,
  "environmentalFactorIds": ["KondisiMusimHujan"],
  "topN": 5
}
```

Aturan:

- `plantId` wajib dan harus ada di ontology.
- `symptomIds` wajib, minimal satu, maksimal 100.
- Semua gejala harus ada dan harus terkait dengan `plantId`.
- `topN` opsional, 1–10, default 5.
- `partIds`, `phaseId`, dan `environmentalFactorIds` saat ini diteruskan
  sebagai konteks dan belum mengubah skor.

Skor kandidat adalah heuristik, bukan probabilitas:

```text
score = 0.7 * (matched / selectedSymptoms)
      + 0.3 * (matched / totalSymptomsOfDisease)
```

`matchRatio = matched / selectedSymptoms`, `coverage = matched /
totalSymptomsOfDisease`. Nilai dibulatkan ke 3 desimal.

Response berisi `input`, `candidates`, `reasoning`, `warnings`, dan `message`.
Setiap kandidat menyertakan gejala yang cocok/tidak cocok serta `evidence`
(bagian tanaman, fase, faktor lingkungan, pengendalian, pengendalian umum,
referensi).

## Daftar warning

Tanaman:

- `SCIENTIFIC_NAME_NOT_AVAILABLE`
- `DESCRIPTION_NOT_AVAILABLE`

Penyakit:

- `DESCRIPTION_NOT_AVAILABLE`
- `PATHOGEN_NOT_AVAILABLE`
- `DISEASE_CONTROL_NOT_AVAILABLE`
- `GENERAL_CONTROL_FALLBACK_USED`

Diagnosis:

- `DUPLICATE_SYMPTOM_IDS_IGNORED`
- `MIXED_DISEASE_SYMPTOMS`
- `NO_MATCHING_DISEASE`
- `REASONING_NOT_CONFIGURED`
- `REASONING_UNAVAILABLE`
- `REASONING_TIMEOUT`
- `REASONING_INCONSISTENT`
- `REASONING_ERROR`

## Error

| HTTP | `code` | Penyebab |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | Bean validation gagal. |
| 400 | `INVALID_REQUEST` | ID tidak konsisten atau gejala bukan milik tanaman. |
| 400 | `MALFORMED_JSON` | Body bukan JSON valid. |
| 400 | `TYPE_MISMATCH` | Tipe parameter query salah. |
| 404 | `RESOURCE_NOT_FOUND` | Tanaman/penyakit/bagian tidak ditemukan. |
| 404 | `ENDPOINT_NOT_FOUND` | Path tidak dikenal. |
| 405 | `METHOD_NOT_ALLOWED` | Method HTTP tidak didukung. |
| 500 | `INTERNAL_SERVER_ERROR` | Kesalahan tak terduga. |

## Kontrak reasoning

Reasoning belum diimplementasikan. Backend hanya menyediakan seam berikut:

```java
public interface ReasoningEngine {
    ReasoningResult analyze(ReasoningInput input);
    boolean isAvailable();
    String name();
}
```

Input:

```java
record ReasoningInput(
    String plantId,
    List<String> symptomIds,
    List<String> candidateDiseaseIds) {}
```

Output:

```java
record ReasoningResult(
    String engine,
    ReasoningStatus status,
    boolean used,
    Map<String, List<String>> inferredTypes,
    String consistency,
    long durationMs,
    String message) {}
```

`ReasoningStatus`: `OK`, `NOT_CONFIGURED`, `UNAVAILABLE`, `TIMEOUT`,
`INCONSISTENT`, `ERROR`.

Integrasi yang diharapkan:

1. Implementasikan `ReasoningEngine` dan daftarkan sebagai Spring bean.
2. Set `reasoning.engine` ke nama selain `noop` agar `NoOpReasoningEngine`
   tidak aktif.
3. Kembalikan tipe hasil inferensi pada `inferredTypes`, dipetakan per ID
   penyakit. Backend memakai `PenyakitJamur`, `PenyakitBakteri`,
   `PenyakitVirus`, atau `PenyakitLainnya` untuk mengisi `category`.
4. Tangani timeout di adapter (misalnya memakai `reasoning.timeout-ms`).
5. Jika adapter gagal, backend tetap mengembalikan HTTP 200 dengan diagnosis
   berbasis gejala dan warning reasoning yang sesuai.

## Keterbatasan data saat ini

- 57 penyakit, 240 gejala, 59 patogen, 261 pengendalian.
- `deskripsiPenyakit`, `deskripsiTanaman`, `tingkatKeparahan`, `namaPengendalian`,
  dan `urlReferensi` tidak memiliki nilai di ontology.
- `namaIlmiah` hanya tersedia untuk 3 tanaman.
- Subclass penyakit (`PenyakitJamur`, dan seterusnya) dan subclass tanaman
  (`Serealia`, `Legum`) belum memiliki individual asserted; kategori hanya bisa
  diisi lewat reasoning.
- Tiga penyakit tidak memiliki patogen.
- 17 penyakit UbiKayu tidak memiliki pengendalian spesifik; pengendalian umum
  tanaman dipakai sebagai fallback dengan warning.
- Gejala saat ini unik untuk satu penyakit, sehingga diagnosis berbasis
  pencocokan gejala langsung cukup deterministik.
