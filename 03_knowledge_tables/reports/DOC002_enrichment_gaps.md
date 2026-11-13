# Gap dan cakupan enrichment DOC002/DOC005

Scope: 7 tanaman utama. Fakta: **84**.

## Ringkasan predikat

| Predikat | Jumlah |
|---|---:|
| `deskripsiPenyakit` | 53 |
| `deskripsiTanaman` | 7 |
| `dipengaruhiOleh` | 11 |
| `memilikiKondisiTumbuh` | 4 |
| `tingkatKeparahan` | 9 |

## Kondisi tumbuh per tanaman

| Tanaman | Kondisi |
|---|---|
| Padi | — |
| Kedelai | Cahaya sedang, Suhu dingin, Suhu sedang |
| Jagung | — |
| Ubi jalar | — |
| Ubi kayu | Tanah subur |
| Kacang tanah | — |
| Kacang hijau | — |

## Deskripsi

| Tipe | Terisi |
|---|---:|
| Tanaman | 7/7 |
| Penyakit | 53/53 |

## Tanaman tanpa kondisi tumbuh

Jumlah: **5**

- Padi
- Jagung
- Ubi jalar
- Kacang tanah
- Kacang hijau
- Tidak ada kalimat syarat tumbuh eksplisit untuk tanaman ini pada sumber dalam scope (baseline/MD DOC002 dan DOC005).

## Tanaman tanpa deskripsi

Jumlah: **0**

Tidak ada — terisi penuh.

## Penyakit tanpa deskripsi

Jumlah: **0**

Tidak ada — terisi penuh.

## Penyakit tanpa tautan patogen di curated

Jumlah: **3**

Tautan belum ada di curated; kutipan di bawah adalah kandidat bukti, bukan tautan final.

- `DIS_005` Penyakit Kerdil Rumput dan Kerdil Hampa (Padi)
  - bukti: Penyakit kerdil rumput disebabkan oleh virus kerdil rumput tipe 1 dan virus kerdil rumput tipe 2, sedangkan penyakit kerdil hampa disebabkan oleh virus kerdil hampa.
  - bukti: Kedua virus tersebut dapat ditularkan oleh wereng coklat (Nilaparvata lugens) (Senewe et al. 2020).
- `DIS_022` Penyakit Belang (Mottle) (Kacang tanah)
  - bukti: Penyakit belang merupakan penyakit yang disebabkan oleh virus.
  - bukti: Virus yang menyerang yaitu Peanut mottle virus (PeMoV) maupun Peanut stripe virus (PStV).
  - bukti: Serangga vektor yang membawa virus menginfeksi tanaman kacang tanah adalah Aphids sp. Aphis dengan tipe mulut mencucuk menghisap merupakan vektor PStV yang efisien.
- `DIS_039` Nekrosis pada titik tunas (Cassava bud necrosis) (Ubi kayu)

## Penyakit tanpa pengendalian tingkat penyakit

Jumlah: **17**

- `DIS_028` Bercak daun Coklat (Ubi kayu) (ada kendali tingkat bab)
- `DIS_029` Bercak daun baur (Ubi kayu) (ada kendali tingkat bab)
- `DIS_030` Bercak daun putih (Ubi kayu) (ada kendali tingkat bab)
- `DIS_031` Antraknosa (Ubi kayu) (ada kendali tingkat bab)
- `DIS_032` Hawar daun bakteri (Ubi kayu) (ada kendali tingkat bab)
- `DIS_033` Sapu setan (Witches broom) (Ubi kayu) (ada kendali tingkat bab)
- `DIS_034` Cassava Mosaic Begomovirus (CMBs) (Ubi kayu) (ada kendali tingkat bab)
- `DIS_035` Cassava Brown Streak Disease (CBSD) (Ubi kayu) (ada kendali tingkat bab)
- `DIS_036` Hawar bakteri (Ubi kayu) (ada kendali tingkat bab)
- `DIS_037` Superelongasi (Ubi kayu) (ada kendali tingkat bab)
- `DIS_038` Tanaman kerdil (stunt) (Ubi kayu) (ada kendali tingkat bab)
- `DIS_039` Nekrosis pada titik tunas (Cassava bud necrosis) (Ubi kayu) (ada kendali tingkat bab)
- `DIS_040` Busuk pangkal batang (Ubi kayu) (ada kendali tingkat bab)
- `DIS_041` Busuk akar dan umbi (Ubi kayu) (ada kendali tingkat bab)
- `DIS_042` Busuk Umbi (Ubi kayu) (ada kendali tingkat bab)
- `DIS_043` Busuk akar (Ubi kayu) (ada kendali tingkat bab)
- `DIS_110` Antraknosa (Ubi kayu) (ada kendali tingkat bab)

## Catatan cakupan

- Baseline DOC002 mencakup 6 tanaman DOC002 (Padi, Kedelai, Jagung, Ubi jalar, Ubi kayu, Kacang tanah).
- DOC005 mencakup Kedelai, Kacang tanah, Kacang hijau.
- MD DOC002 hanya mencakup Padi, Kedelai, dan Ubi kayu.
- Penyakit Ubi kayu di DOC002 berupa baris tabel; deskripsi per penyakit diambil dari baris tabel gejala.
- Dari baris tabel Ubi kayu: 15 verbatim di chunk MD, 2 sel tabel terkurasi (`needs_review`).
- Total fakta berstatus `needs_review`: 11.
- Fakta tanaman di luar 7 tanaman utama dibuang.

