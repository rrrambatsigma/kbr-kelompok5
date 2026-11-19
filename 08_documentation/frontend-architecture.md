# TaniCare Frontend Architecture

## Stack

- React 19
- Vite 6
- TypeScript
- React Router 6
- Tailwind CSS 3 + CSS design tokens
- Lucide React untuk ikon
- Vitest + React Testing Library

Frontend hanya berkomunikasi dengan Node/Express `:3000`. Java `:8082` dan
Fuseki `:3030` adalah internal backend.

## Struktur folder

```text
07_frontend/
  src/
    components/
      common/        Button, Badge, Spinner, EmptyState, ErrorState,
                     PageHeader, SectionHeading, Breadcrumb, SearchInput,
                     Pagination, Stepper, ConfidenceMeter, Logo
      layout/        Navbar, Footer
      knowledge-base/DiseaseCard
    context/         DiagnosisContext
    layouts/         PublicLayout, AppShell
    pages/           HomePage, DiagnosisPage, DiagnosisResultPage,
                     KnowledgeBasePage, DiseaseDetailPage, NotFoundPage
    services/api/    client, plants, symptoms, diagnosis, diseases, health
    styles/          index.css (Tailwind + design tokens)
    test/            setup
    types/           api.ts
    utils/           apiError.ts, format.ts
  DESIGN.md
  .env.example
```

## Routing

| Path | Layout | Halaman |
|---|---|---|
| `/` | PublicLayout | Home |
| `/diagnosis` | AppShell | Wizard diagnosis |
| `/diagnosis/result` | AppShell | Hasil diagnosis |
| `/knowledge-base` | PublicLayout | Katalog penyakit |
| `/knowledge-base/:id` | PublicLayout | Detail penyakit |
| `*` | PublicLayout | NotFound |

`ScrollToTop` menangani scroll dan hash (`/#tentang`).

## Alur data

```text
Page
  → service (plants/symptoms/diagnosis/diseases)
  → apiRequest (fetch, timeout, envelope parsing, error mapping)
  → Node API :3000
  → Fuseki/Java (internal)
```

Tidak ada fetch langsung ke Fuseki, tidak ada mock data untuk fitur utama.
Jika backend gagal, UI menampilkan `ErrorState` dengan tombol coba lagi.

## State diagnosis

`DiagnosisContext` menyimpan:

- tanaman terpilih
- gejala terpilih
- `topN`
- hasil diagnosis terakhir

State dipersist ke `sessionStorage` dengan key `tanicare.diagnosis.v1`.
Halaman hasil membaca state ini; direct URL tanpa state menampilkan empty state.
Tombol “Ubah data” kembali ke wizard dengan state utuh; “Diagnosis tanaman lain”
mereset state.

## Service layer

- `client.ts`: base URL dari `VITE_API_BASE_URL`, timeout 15 detik,
  `AbortController`, validasi envelope, `ApiError`.
- `plants.ts`: `listPlants`, `getPlant`.
- `symptoms.ts`: `listSymptoms(plantId)`.
- `diagnosis.ts`: `submitDiagnosis`.
- `diseases.ts`: `listDiseases`, `getDisease`.
- `health.ts`: readiness check (tersedia untuk pengembangan).

## Error handling

`friendlyApiError` memetakan kode backend:

- `NETWORK_ERROR`, `REQUEST_TIMEOUT`
- `FUSEKI_UNAVAILABLE`, `REASONING_UNAVAILABLE`, `DEPENDENCY_UNAVAILABLE`
- `ONTOLOGY_MISMATCH`
- `INVALID_REQUEST`, `NOT_FOUND`, `INVALID_RESPONSE`

Pesan pengguna tidak menampilkan stack trace atau detail internal.

## Design system

Token utama mengikuti DESIGN.md:

- Canvas `#F6F5ED`, surface `#FFFFFF`, border `#E5E9E5`
- Primary `#003421`, primary container `#174B35`
- Secondary `#156C43`, accent `#A8C9A5`
- Warning `#C2410C`
- Heading Plus Jakarta Sans; body Inter
- Target sentuh minimum 48px

Komponen memakai radius 1rem/1.5rem, border tipis, dan shadow minimal.
Confidence ditampilkan sebagai “skor kecocokan” (persentase) + label
`TINGGI/SEDANG/RENDAH`, bukan certainty factor statistik.

## Batasan yang disengaja

- Wizard 3 tahap karena API diagnosis hanya menerima tanaman + gejala + topN.
- Tidak ada varietas/fase/lingkungan sebagai input.
- Tidak ada filter tipe patogen di katalog karena list endpoint tidak membawa
  field tersebut.
- Tidak ada foto penyakit; UI memakai ilustrasi/gradient dan data tekstual.
