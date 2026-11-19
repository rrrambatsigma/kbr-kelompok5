---
name: TaniCare Expert Agronomy System
colors:
  canvas: "#F6F5ED"
  surface: "#FFFFFF"
  surface-low: "#ECF6ED"
  border: "#E5E9E5"
  foreground: "#202923"
  muted: "#68736C"
  primary: "#003421"
  primary-container: "#174B35"
  secondary: "#156C43"
  accent: "#A8C9A5"
  warning: "#C2410C"
typography:
  heading: Plus Jakarta Sans
  body: Inter
rounded:
  card: 1rem
  container: 1.5rem
  control: 0.75rem
spacing:
  touch-target: 48px
---

# TaniCare Design System

## Karakter

Contemporary Field-Utility: bersih, natural, akademik, dan siap dipakai di
lapangan. Hindari gaya neon/futuristik dan dashboard admin generik.

## Warna

- **Primary `#003421`** untuk teks utama, navigasi, dan aksi utama.
- **Primary container `#174B35`** untuk tombol utama dan permukaan tegas.
- **Secondary `#156C43`** untuk state aktif, tautan, dan aksen.
- **Accent `#A8C9A5`** untuk track progress, chip, dan highlight lembut.
- **Canvas `#F6F5ED`**, surface `#FFFFFF`, border `#E5E9E5`.
- **Warning `#C2410C`** untuk risiko/kegagalan yang perlu perhatian.

Jangan membuat warna baru di luar token ini.

## Tipografi

- Heading: **Plus Jakarta Sans**.
- Body: **Inter**.
- Nama ilmiah patogen/tanaman wajib italic.
- Angka skor memakai tampilan mono/telemetry yang jelas.

## Bentuk dan Elevasi

- Card: radius 1rem, border 1px, shadow tipis.
- Container besar: radius 1.5rem.
- Tombol/input: radius 0.75rem, tinggi minimum 48px.
- Elevasi minimal; utamakan border dan kontras permukaan.

## Komponen

- Tombol utama: filled `#174B35`, teks putih, 48px.
- Tombol sekunder: outline `#156C43`, surface putih.
- Input: 48px, border `#E5E9E5`, focus ring `#156C43`.
- Chip gejala: putih saat belum dipilih, `#174B35` saat dipilih.
- Confidence meter: track `#A8C9A5`/`#DBE5DC`, fill primary/secondary.
- Badge: pill, kontras cukup.

## Aksesibilitas

- Target sentuh minimum 48px.
- Label form eksplisit, bukan hanya placeholder.
- Fokus keyboard terlihat.
- Kontras teks memadai.
- Tidak ada horizontal overflow di mobile.
