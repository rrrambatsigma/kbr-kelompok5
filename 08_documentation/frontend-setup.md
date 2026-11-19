# TaniCare Frontend Setup

## Prasyarat

- Node.js 20+ (diuji pada Node 24)
- Backend TaniCare berjalan:
  - Fuseki `:3030`
  - Java reasoning API `:8082`
  - Node API `:3000`

## Instalasi

```powershell
cd E:\kbr-kelompok5\07_frontend
npm install
```

## Environment

Salin `.env.example` menjadi `.env`:

```ini
VITE_API_BASE_URL=http://localhost:3000
```

Jangan memakai `127.0.0.1` untuk frontend jika backend CORS masih default
`http://localhost:5173`. Buka aplikasi melalui `http://localhost:5173`.

## Menjalankan

Pastikan backend hidup:

```powershell
# Fuseki (jika belum)
.\06_backend\scripts\start-fuseki.ps1

# Java
cd .\06_backend\reasoning-api
.\mvnw.cmd spring-boot:run

# Node API
cd ..\node-api
npm run dev
```

Lalu frontend:

```powershell
cd E:\kbr-kelompok5\07_frontend
npm run dev
```

Buka `http://localhost:5173`.

## Perintah lain

```powershell
npm run build    # production build + TypeScript check
npm run preview  # preview build
npm test         # Vitest
```

## Struktur singkat

- `src/pages` — halaman utama.
- `src/components` — komponen reusable.
- `src/services/api` — semua komunikasi HTTP.
- `src/context` — state diagnosis.
- `src/styles/index.css` — Tailwind + design tokens.
- `DESIGN.md` — acuan visual.

## Batasan saat ini

Wizard diagnosis memakai tanaman + gejala + jumlah kandidat, sesuai kontrak
`POST /api/diagnosis`. Varietas, fase pertumbuhan, bagian tanaman, dan kondisi
lingkungan belum didukung sebagai input backend.

## Troubleshooting

| Gejala | Tindakan |
|---|---|
| Data tidak muncul | Pastikan Node API `:3000` hidup dan `VITE_API_BASE_URL` benar |
| CORS error | Buka lewat `http://localhost:5173`, samakan `FRONTEND_URL` backend |
| Hasil diagnosis kosong | Lakukan diagnosis dari wizard; direct URL tanpa state memang kosong |
| Build gagal | Jalankan `npm install` lalu `npm run build` |
| Backend `DEGRADED` | Java `:8082` mati; kandidat tetap tampil tanpa kategori |
