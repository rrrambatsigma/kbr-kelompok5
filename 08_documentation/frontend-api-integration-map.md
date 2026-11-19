# TaniCare Frontend - Backend Integration Map

Dokumen ini mencatat endpoint aktual yang dipakai frontend. Sumber kebenaran
adalah route/service Node/Express di `06_backend/node-api`; frontend **tidak**
memanggil Java atau Fuseki secara langsung.

Base URL frontend:

```text
VITE_API_BASE_URL=http://localhost:3000
```

## Ringkasan endpoint

| Fitur UI | Endpoint | Method | Status | Dipakai di |
|---|---|---|---|---|
| Daftar tanaman | `/api/plants` | GET | Available | Home, Diagnosis |
| Detail tanaman | `/api/plants/:id` | GET | Available | Belum dipakai UI |
| Daftar gejala per tanaman | `/api/symptoms?plantId=` | GET | Available | Diagnosis |
| Diagnosis | `/api/diagnosis` | POST | Available | Diagnosis |
| Daftar penyakit | `/api/diseases` | GET | Available | Home, Knowledge Base |
| Detail penyakit | `/api/diseases/:id` | GET | Available | Disease Detail, Result |
| Health readiness | `/api/health/ready` | GET | Available | Tidak dipakai rutin |
| Health ontology | `/api/health/ontology` | GET | Available | Tidak dipakai rutin |
| Reasoning status (Java) | `/api/reasoning/status` | GET | Available | Internal Node |

## Kontrak yang dipakai

### `GET /api/plants`

Response item:

```json
{
  "id": "Padi",
  "iri": "http://kbr.kelompok5.org/penyakit-tanaman-pangan#Padi",
  "label": "Padi",
  "scientificName": null,
  "diseaseCount": 5
}
```

Catatan: `scientificName` bisa `null`; UI menampilkan “Nama ilmiah belum
tersedia”, bukan mengarang.

### `GET /api/symptoms?plantId=Padi`

Response item:

```json
{
  "id": "PengamatanPenyakitBlasPadiBercakDaun",
  "iri": "http://.../PengamatanPenyakitBlasPadiBercakDaun",
  "label": "Bercak daun pada Penyakit Blas",
  "partId": "Daun",
  "partLabel": "Daun"
}
```

`partId`/`partLabel` bisa `null`; UI memakai kelompok “Gejala umum”.

### `POST /api/diagnosis`

Request:

```json
{
  "plantId": "Padi",
  "symptomIds": ["PengamatanPenyakitBlasPadiBercakDaun"],
  "topN": 5
}
```

Response `data` (disederhanakan):

```json
{
  "input": {
    "plantId": "Padi",
    "plantLabel": "Padi",
    "symptomIds": ["..."],
    "symptoms": [{ "id": "...", "label": "..." }],
    "topN": 5
  },
  "candidates": [
    {
      "diseaseId": "PenyakitBlasPadi",
      "label": "Penyakit Blas",
      "score": 0.7466,
      "confidence": "TINGGI",
      "category": "PenyakitJamur",
      "matchedCount": 3,
      "selectedCount": 3,
      "totalSymptoms": 6,
      "matchedSymptoms": [],
      "unmatchedSelectedSymptoms": [],
      "evidence": [],
      "explanation": "3 gejala cocok persis...",
      "scoreComponents": {
        "evidence": 0.9955,
        "completeness": 1,
        "coverage": 0.5
      },
      "controls": []
    }
  ],
  "reasoning": {
    "status": "UP",
    "modelVersion": "forward-chaining-cf-v1",
    "ontologyVersion": "17cabff2112e",
    "checksum": "..."
  },
  "warnings": [],
  "message": "..."
}
```

### `GET /api/diseases`

Item:

```json
{
  "id": "PenyakitBlasPadi",
  "label": "Penyakit Blas",
  "plantId": "Padi",
  "plantLabel": "Padi",
  "symptomCount": 6
}
```

### `GET /api/diseases/:id`

Field yang tersedia:

- `symptoms[]` + `partId`/`partLabel`
- `controls[]` + `description`
- `pathogens[]` + `scientificName`
- `parts[]`, `phases[]`, `riskFactors[]`

Field yang **tidak** tersedia di endpoint ini:

- deskripsi bebas penyakit
- tingkat keparahan terstruktur
- gambar penyakit
- kategori patogen di list

UI hanya menampilkan field yang ada.

## Gap backend

| Kebutuhan UI | Status | Catatan |
|---|---|---|
| Varietas | Missing | Tidak ada endpoint varietas |
| Fase pertumbuhan sebagai pilihan | Missing | Hanya muncul di detail penyakit, bukan input diagnosis |
| Daftar bagian tanaman global | Missing | Bagian hanya tersedia per penyakit/gejala |
| Kondisi lingkungan sebagai input | Missing | `dipengaruhiOleh` ada di ontology, tetapi tidak dipakai diagnosis |
| Filter tipe patogen di katalog | Missing | List penyakit tidak membawa tipe patogen |
| Foto penyakit | Missing | Tidak ada field gambar |
| Tingkat risiko/severity | Partial | `tingkatKeparahan` ada di ontology, belum diekspos list/detail |
| Certainty factor statistik | Tidak dipakai | Backend mengirim `score` + `confidence`; UI tidak menghitung CF |

Frontend tidak membuat endpoint atau data pengganti untuk gap di atas.
Jika fitur ini dibutuhkan, backend harus ditambah terlebih dahulu.

## CORS dan port

- Frontend dev: `http://localhost:5173`
- Backend Node: `http://localhost:3000`
- Java internal: `http://127.0.0.1:8082`
- Node `FRONTEND_URL` default `http://localhost:5173`

Gunakan `localhost` untuk frontend, bukan `127.0.0.1`, agar origin CORS cocok
dengan default backend.
