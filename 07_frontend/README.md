# TaniCare Frontend

Frontend TaniCare — sistem pakar identifikasi penyakit tanaman pangan tropis.

Stack: React 19, Vite 6, TypeScript, React Router, Tailwind CSS.

## Menjalankan

```powershell
npm install
copy .env.example .env
npm run dev
```

Buka `http://localhost:5173`. Backend Node harus berjalan di
`http://localhost:3000` (lihat `06_backend/README.md`).

## Halaman

- `/` — homepage
- `/diagnosis` — wizard diagnosis
- `/diagnosis/result` — hasil reasoning
- `/knowledge-base` — katalog penyakit
- `/knowledge-base/:id` — detail penyakit

## Dokumentasi

- `DESIGN.md` — token dan aturan visual
- `../08_documentation/frontend-architecture.md`
- `../08_documentation/frontend-api-integration-map.md`
- `../08_documentation/frontend-integration-test.md`
- `../08_documentation/frontend-setup.md`

## Perintah

```powershell
npm run build
npm test
npm run preview
```
