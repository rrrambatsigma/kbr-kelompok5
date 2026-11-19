# Audit Ketersediaan Sumber per Gap

Sumber yang diaudit: `00_sumber_data/05_PenyakitUtamaKedelai.md`, `00_sumber_data/07_PenyakitKacangHijau.md`, baseline lengkap `02_extraction/llamaparse/baseline/DOC002.blocks.jsonl`, dan chunks DOC002/DOC005. Tidak ada sumber eksternal.

> Catatan: `00_sumber_data/02_PenyakitTanamanPangan.md` hanya preview/truncated. Teks lengkap DOC002 ada di baseline blocks.

## Ringkasan

| Item | Jumlah |
|---|---:|
| Penyakit | 53 |
| Gejala belum dipetakan | 64 |
| Pengendalian belum dipetakan | 38 |
| Baris audit metadata | 169 |
| Unit sumber menyebut drainase | 3 |
| Unit sumber menyebut rotasi/pergiliran | 26 |

## Status metadata

| Gap | available | partial | absent |
|---|---:|---:|---:|
| Severity | 24 | 5 | 10 |
| Fase | 0 | 2 | 40 |
| Varietas tahan | 4 | 31 | 10 |
| Nama Inggris | 0 | 21 | 22 |

## Detail gap metadata

| Tanaman | Penyakit | Gap | Status | Alasan | Bukti/kutipan | Sumber |
|---|---|---|---|---|---|---|
| Jagung | Penyakit Bulai | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Jagung | Penyakit Busuk Pelepah | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| Jagung | Penyakit Busuk Pelepah | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Jagung | Penyakit Busuk Pelepah | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Jagung | Penyakit Busuk Pelepah | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Jagung | Penyakit Hawar Daun | Varietas tahan | available | Ada nama varietas/kultivar dengan status tahan/toleran/rentan. | selain itu juga dapat dilakukan dengan menggunakan varietas tahan terhadap hawar daun. | DOC002 DOC002_P102_B005 hal. 102 |
| Jagung | Penyakit Hawar Daun | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Jagung | Penyakit Karat Daun | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | selain itu, penggunaan varietas tahan juga dapat dilakukan untuk menekan perkembangan penyakit karat daun jagung. | DOC002 DOC002_P104_B005 hal. 104 |
| Jagung | Penyakit Karat Daun | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Jagung | Penyakit Layu Stewart | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | varietas jagung bersari bebas (lamuru, srikandi dan arjuna) dan hibrida (pioneer 21, bima 5, bisi 16, dekal b) menunjukkan respons yang beragam yaitu dari agak rentan hingga tahan, sedangkan varietas jagung manis (virginia, hawaii, s. huat, | DOC002 DOC002_P108_B003 hal. 108 |
| Jagung | Penyakit Layu Stewart | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| KacangHijau | Penyakit Bercak Daun | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | pada varietas rentan menyebabkan gejala defoliasi prematur pengurangan ukuran polong dan biji (grewal et al. 1980). | DOC005 DOC005_C059_01 hal. 59 |
| KacangHijau | Penyakit Bercak Daun | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| KacangHijau | Penyakit Embun Tepung | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| KacangHijau | Penyakit Embun Tepung | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | faktor-faktor yang mempengaruhi ### a) faktor lingkungan adanya tanaman inang rentan, inokulum yang agresif, dan kondisi cuaca yang sesuai sangat mendukung perkembangan penyakit. | DOC005 DOC005_C052_01 hal. 52 |
| KacangHijau | Penyakit Embun Tepung | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| KacangHijau | Penyakit Layu | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | kelembapan tanah juga mempengaruhi kejadian penyakit di lapang. | DOC005 DOC005_C064_01 hal. 64 |
| KacangHijau | Penyakit Layu | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | patogen colletotrichum truncatum dan soybean mosaic virus terbawa benih kedelai dan pengendaliannya. | DOC005 DOC005_C064_01 hal. 64 |
| KacangTanah | Penyakit Belang (Mottle) | Severity | partial | Ada pernyataan kualitatif (berat/ringan/merugikan), tanpa angka. | selain itu, upaya untuk mengurangi intensitas serangan pstv yaitu dengan menggunakan mulsa mengkilap. | DOC002 DOC002_P074_B002 hal. 74 |
| KacangTanah | Penyakit Belang (Mottle) | Fase | partial | Ada istilah masa/saat/periode, tetapi bukan label fase eksplisit. | infeksi benih 2-5% dapat menyebabkan endemis penyakit saat panen. | DOC002 DOC002_P073_B008 hal. 73 |
| KacangTanah | Penyakit Belang (Mottle) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | penanaman varietas kacang tanah tahan pstv merupakan cara pengendalian yang efektif, murah, dan dapat dikombinasikan dengan cara pengendalian yang lain. | DOC002 DOC002_P073_B006 hal. 73 |
| KacangTanah | Penyakit Bercak Daun | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| KacangTanah | Penyakit Karat Daun | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| KacangTanah | Penyakit Karat Daun | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| KacangTanah | Penyakit Layu Bakteri | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| KacangTanah | Penyakit Layu Bakteri | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| KacangTanah | Penyakit Layu Bakteri | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | kacang tanah umumnya kurang rentan dibandingkan tomat, kentang, tembakau dan terung. | DOC002 DOC002_P074_B008 hal. 74 |
| KacangTanah | Penyakit Layu Bakteri | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Kedelai | Penyakit Antraknosa | Severity | partial | Ada pernyataan kualitatif (berat/ringan/merugikan), tanpa angka. | benih terinfeksi berakibat kehilangan hasil lebih tinggi, dibandingkan infeksi pada batang. | DOC005 DOC005_C031_01 hal. 31 |
| Kedelai | Penyakit Antraknosa | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | penentuan varietas yang digunakan sebaiknya merujuk pada sejarah lahan, jika lahan tersebut merupakan lahan endemik c. truncatum, maka pemilihan benih sehat dari varietas yang tahan merupakan pilihan yang tepat. | DOC005 DOC005_C031_01 hal. 31 |
| Kedelai | Penyakit Antraknosa | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Kedelai | Penyakit Bakteri Pustul | Severity | partial | Ada pernyataan kualitatif (berat/ringan/merugikan), tanpa angka. | gejala selanjutnya adalah daun yang terinfeksi akan rontok akibat intensitas serangan yang tinggi sehingga akan mengganggu proses fotosintesis dan berpengaruh terhadap pengisian polong. | DOC002 DOC002_P056_B007 hal. 56 |
| Kedelai | Penyakit Bakteri Pustul | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Bakteri Pustul | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Kedelai | Penyakit Bakteri Pustul | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Kedelai | Penyakit Bercak Biji Ungu | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | penyakit bercak biji ungu atau hawar daun cercospora merupakan penyakit yang penting juga pada tanaman kedelai karena dapat menyebabkan kehilangan hasil. | DOC002 DOC002_P053_B004 hal. 53 |
| Kedelai | Penyakit Bercak Biji Ungu | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Bercak Biji Ungu | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Kedelai | Penyakit Bercak Biji Ungu | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | pada intensitas serangan yang bintik menjadi berkembang pada bagian daun hingga menutupi 30% bagian | DOC002 DOC002_P047_B009 hal. 47 |
| Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | pengendalian penyakit ini dapat dilakukan dengan menanam varietas yang tahan terhadap patogen c. sojina (giesler, 2013). | DOC002 DOC002_P048_B005 hal. 48 |
| Kedelai | Penyakit Bercak Target | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| Kedelai | Penyakit Bercak Target | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Bercak Target | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Kedelai | Penyakit Bercak Target | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Kedelai | Penyakit Embun Palsu (Downy mildew) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Embun Palsu (Downy mildew) | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Kedelai | Penyakit Embun Tepung (Powdery Mildew) | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| Kedelai | Penyakit Embun Tepung (Powdery Mildew) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Embun Tepung (Powdery Mildew) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | varietas anjasmoro dan mahameru merupakan varietas yang rentan terhadap patogen | DOC002 DOC002_P045_B007 hal. 45 |
| Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Kedelai | Penyakit Karat Daun | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Karat Daun | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Kedelai | Penyakit Kerdil Kedelai (Soybean Stunt Virus) | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| Kedelai | Penyakit Kerdil Kedelai (Soybean Stunt Virus) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Kerdil Kedelai (Soybean Stunt Virus) | Varietas tahan | partial | Ada penyebutan varietas, tetapi status ketahanan tidak eksplisit. | pada penularan virus dipengaruhi oleh beberapa faktor seperti strain virus yang menginfeksi tanaman, varietas dan jenis tanaman akan memengaruhi | DOC002 DOC002_P061_B006 hal. 61 |
| Kedelai | Penyakit Layu Fusarium | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| Kedelai | Penyakit Layu Fusarium | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Layu Fusarium | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Kedelai | Penyakit Layu Fusarium | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Kedelai | Penyakit Mosaik Kedelai (Soybean Mosaic Virus) | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| Kedelai | Penyakit Mosaik Kedelai (Soybean Mosaic Virus) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Mosaik Kedelai (Soybean Mosaic Virus) | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Kedelai | Penyakit Rebah Kecambah | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | hasil penelitian yang dilakukan oleh fitria and masnilah, (2020) pada beberapa varietas kedelai terhadap patogen s. rolfsii diketahui bahwa varietas dena 1 tingkat keparahan penyakitnya lebih rendah dibandingkan dengan varietas anjasmoro, d | DOC002 DOC002_P040_B002 hal. 40 |
| Kedelai | Penyakit Rebah Kecambah | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Rebah Kecambah | Varietas tahan | available | Ada nama varietas/kultivar dengan status tahan/toleran/rentan. | pengendalian dengan varietas tahan menjadi salah satu pengendalian yang efektif. | DOC002 DOC002_P040_B002 hal. 40 |
| Kedelai | Penyakit Rebah Kecambah | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| category \| item \| \| ---------------- \| ---------------------------------------------------------- \| \| disease symptoms \| hypocotyl rot \| \| \| post-emergence damping off \| \| \| root rot \| \| \| pre-emergence damping off \| \| inoculum source \| d | DOC002 DOC002_MD_C011_01 |
| Kedelai | Penyakit Rebah Semai | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | hasil penelitian yang dilakukan oleh fitria and masnilah, (2020) pada beberapa varietas kedelai terhadap patogen s. rolfsii diketahui bahwa varietas dena 1 tingkat keparahan penyakitnya lebih rendah dibandingkan dengan varietas anjasmoro, d | DOC002 DOC002_P040_B002 hal. 40 |
| Kedelai | Penyakit Rebah Semai | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Kedelai | Penyakit Samar Kacang Tunggak (Cowpea Mild Mottle Virus) | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | virus) pada tanaman kedelai dengan skor keparahan penyakit 0: tidak ada | DOC002 DOC002_P059_B008 hal. 59 |
| Kedelai | Penyakit Samar Kacang Tunggak (Cowpea Mild Mottle Virus) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Kedelai | Penyakit Samar Kacang Tunggak (Cowpea Mild Mottle Virus) | Varietas tahan | available | Ada nama varietas/kultivar dengan status tahan/toleran/rentan. | hal ini dipengaruhi oleh faktor varietas tanaman yang ditanam, umur tanaman yang terinfeksi dan | DOC002 DOC002_P059_B011 hal. 59 |
| Padi | Penyakit Blas | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Padi | Penyakit Blas | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | adapun bentuk, warna dan ukuran dari bercak dapat bervariasi tergantung dari umur dan ketahanan varietas tanaman serta umur dari bercak (ou 1985). | DOC002 DOC002_P030_B002 hal. 30 |
| Padi | Penyakit Blas | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Padi | Penyakit Hawar Daun Bakteri | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Padi | Penyakit Hawar Daun Bakteri | Varietas tahan | available | Ada nama varietas/kultivar dengan status tahan/toleran/rentan. | selain itu penanaman varietas tahan yang sesuai dengan patotipe patogen (sudir et al. (2012). | DOC002 DOC002_P028_B004 hal. 28 |
| Padi | Penyakit Hawar Daun Bakteri | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Padi | Penyakit Hawar Pelepah Daun | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Padi | Penyakit Hawar Pelepah Daun | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | Varietas tahan | absent | Tidak ada varietas/kultivar yang disebut. |  |  |
| Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | kedua virus tersebut dapat ditularkan oleh wereng coklat (nilaparvata lugens) (senewe et al. 2020). | DOC002 DOC002_P034_B010 hal. 34 |
| Padi | Penyakit Tungro | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| Padi | Penyakit Tungro | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| Padi | Penyakit Tungro | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | kedua virus tersebut memiliki ciri yang berbeda, di mana rtbv memiliki bentuk berupa batang dengan panjang 150 nm dan lebar 35 nm. | DOC002 DOC002_P033_B007 hal. 33 |
| UbiJalar | layu fusarium | Severity | absent | Tidak ada kalimat severity di unit penyakit/tanaman. |  |  |
| UbiJalar | layu fusarium | Fase | partial | Ada istilah masa/saat/periode, tetapi bukan label fase eksplisit. | saat panen, produsen sering memanen ubi jalar di bawah suhu dan kelembaban relatif dan pengeringan dilakukan di lapangan dengan kisaran suhu optimum 29 – 32° c dengan kelembaban 85%, di mana kondisi tersebut memungkinkan penyembuhan perider | DOC002 DOC002_P082_B007 hal. 82 |
| UbiJalar | layu fusarium | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | ubi jalar yang terserang f. oxysporum f.sp. batatas terjadi degradasi atau pengurangan klorofil pada genotipe yang rentan dan sangat rentan (mousa et al., 2018) tetapi penurunan klorofil paling rendah pada genotipe yang resistan (dinu et al | DOC002 DOC002_P081_B009 hal. 81 |
| UbiJalar | layu fusarium | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| UbiJalar | Penyakit bercak kuning | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | kejadian penyakit akibat spfmv pun dapat berbeda tergantung daerah agrioekologinya (tugume, mukasa and valkonen, 2008). | DOC002 DOC002_P086_B003 hal. 86 |
| UbiJalar | Penyakit bercak kuning | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiJalar | Penyakit bercak kuning | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | pengendalian yang dapat dilakukan dengan cara menggunakan varietas tahan, menggunakan bibit, setek atau bahan tanam yang bebas virus, rotasi tanaman, sanitasi dan eradikasi tanaman, serta mengendalikan serangga vektor (saleh et al., 2015). | DOC002 DOC002_P086_B006 hal. 86 |
| UbiJalar | Penyakit bercak kuning | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | beberapa virus sudah dilaporkan dapat menginfeksi ubi jalar di antaranya sweet potato feathery mottle virus (spfmv), sweet potato mild mottle virus (spmmv), sweet potato chlorotic fleck virus (spcfv), sweet potato latent potyvirus (splv), s | DOC002 DOC002_P085_B006 hal. 85 |
| UbiJalar | Penyakit busuk hitam (black rot) | Severity | partial | Ada pernyataan kualitatif (berat/ringan/merugikan), tanpa angka. | penyakit busuk hitam (black rot) disebabkan oleh jamur ceratocystis fimbriata menjadi salah satu ancaman produksi pada ubi jalar di dunia (muramoto et al., 2012) dan menyebabkan kerusakan parah selama penyimpanan pascapanen (baker et al., 2 | DOC002 DOC002_P087_B004 hal. 87 |
| UbiJalar | Penyakit busuk hitam (black rot) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiJalar | Penyakit busuk hitam (black rot) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | sterilisasi akar atau bahan sebelum ditanam di persemaian, sterilisasi tanah dan rotasi tanaman efektif untuk pencegahan menggunakan kultivar yang tahan (okada et al., 2017). | DOC002 DOC002_P087_B008 hal. 87 |
| UbiJalar | Penyakit kudis | Severity | partial | Ada pernyataan kualitatif (berat/ringan/merugikan), tanpa angka. | daun menjadi tidak produktif dalam fotosintesis jika pada tingkat serangan berat, sehingga hasil ubi rendah dan bahkan tidak menghasilkan sama sekali (rukmana, 1997). | DOC002 DOC002_P083_B005 hal. 83 |
| UbiJalar | Penyakit kudis | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiJalar | Penyakit kudis | Nama Inggris | absent | Tidak ada nama Inggris eksplisit di sumber dalam scope. |  |  |
| UbiKayu | Antraknosa | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Antraknosa | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Antraknosa | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Antraknosa | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Antraknosa | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Antraknosa | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Antraknosa | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Antraknosa | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Bercak daun baur | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Bercak daun baur | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Bercak daun baur | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Bercak daun baur | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Bercak daun Coklat | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Bercak daun Coklat | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Bercak daun Coklat | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Bercak daun Coklat | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Bercak daun putih | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Bercak daun putih | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Bercak daun putih | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Bercak daun putih | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Busuk akar dan umbi | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Busuk akar dan umbi | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Busuk akar dan umbi | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Busuk akar dan umbi | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Busuk akar | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Busuk akar | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Busuk akar | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Busuk akar | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Busuk pangkal batang | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Busuk pangkal batang | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Busuk pangkal batang | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Busuk pangkal batang | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Busuk Umbi | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Busuk Umbi | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Busuk Umbi | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Busuk Umbi | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Cassava Brown Streak Disease (CBSD) | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Cassava Brown Streak Disease (CBSD) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Cassava Brown Streak Disease (CBSD) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Cassava Brown Streak Disease (CBSD) | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Cassava Mosaic Begomovirus (CMBs) | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Cassava Mosaic Begomovirus (CMBs) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Cassava Mosaic Begomovirus (CMBs) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Cassava Mosaic Begomovirus (CMBs) | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Hawar bakteri | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Hawar bakteri | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Hawar bakteri | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Hawar bakteri | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Hawar daun bakteri | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Hawar daun bakteri | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Hawar daun bakteri | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Hawar daun bakteri | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Nekrosis pada titik tunas (Cassava bud necrosis) | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Nekrosis pada titik tunas (Cassava bud necrosis) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Nekrosis pada titik tunas (Cassava bud necrosis) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Nekrosis pada titik tunas (Cassava bud necrosis) | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Sapu setan (Witches broom) | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Sapu setan (Witches broom) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Sapu setan (Witches broom) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Superelongasi | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Superelongasi | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Superelongasi | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Superelongasi | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |
| UbiKayu | Tanaman kerdil (stunt) | Severity | available | Ada angka kehilangan hasil/keparahan/intensitas. | salah satunya yaitu dengan tujuan mengurangi kehilangan hasil, khususnya kehilangan hasil yang disebabkan oleh serangan penyakit tanaman. | DOC002 DOC002_P090_B003 hal. 90 |
| UbiKayu | Tanaman kerdil (stunt) | Fase | absent | Tidak ada penyebutan fase tanaman. |  |  |
| UbiKayu | Tanaman kerdil (stunt) | Varietas tahan | partial | Ada pernyataan tahan/toleran/rentan, tetapi nama varietas tidak jelas. | upaya untuk mengurangi kehilangan hasil panen atau penurunan produktivitas akibat serangan penyakit pada tanaman ubi kayu yaitu di antaranya dapat dilakukan melalui penggunaan tanaman tahan penyakit dan seleksi ketat terhadap bahan perbanya | DOC002 DOC002_P096_B008 hal. 96 |
| UbiKayu | Tanaman kerdil (stunt) | Nama Inggris | partial | Ada frasa Inggris di sumber; perlu verifikasi sebagai nama penyakit. | \| \| 8 \| sapu setan (witches broom) \| fitoplasma \| tanaman tumbuh kerdil (dwarf), ruas batang memendek, pada ujung tanaman tumbuh tunas yang banyak menyerupai sapu \| \| 9 \| cassava mosaic begomovirus (cmbs) \| begomovirus \| tampak motif mosaik | DOC002 DOC002_MD_C014_01 |

## Gejala belum dipetakan

Semua baris di bawah berasal dari sumber. Status `available` berarti teks bukti ada; kolom `triase awal` memisahkan kandidat gejala nyata dari noise.

| # | Tanaman | Penyakit | Triase awal | Kutipan | Sumber | Chunk |
|---:|---|---|---|---|---|---|
| 1 | Padi | Penyakit Hawar Daun Bakteri | butuh_konsep_baru | gejala khas dari penyakit ini adalah tepi bergelombang atau penggulungan yang terlihat jelas pada helaian daun. | DOC002 | DOC002_C027_01 |
| 2 | Padi | Penyakit Hawar Daun Bakteri | ambigu | sementara itu, fase kresek ditandai terutama oleh infeksi sistemis karena pada fase ini gejala penyakit biasanya muncul 1-2 minggu setelah transplantasi persemaian ke lapangan. | DOC002 | DOC002_C027_03 |
| 3 | Padi | Penyakit Hawar Daun Bakteri | butuh_konsep_baru | istilah kresek sendiri diambil dari bahasa jawa yang berarti suara daun-daun yang mati yang bergesekan satu sama lain menyerupai suara kresek (goto, 1992). | DOC002 | DOC002_C027_03 |
| 4 | Padi | Penyakit Blas | butuh_konsep_baru | gejala khas dari penyakit ini, yaitu blas daun dan blas malai. | DOC002 | DOC002_C029_04 |
| 5 | Padi | Penyakit Hawar Pelepah Daun | butuh_konsep_baru | gejala penyakit hdp dapat dilihat pada selubung daun. | DOC002 | DOC002_C032_02 |
| 6 | Padi | Penyakit Hawar Pelepah Daun | ambigu | gejala tersebut dapat ditemukan pada padi fase anakan sampai fase matang susu. | DOC002 | DOC002_C032_02 |
| 7 | Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | bukan_gejala | infeksi pada daun bendera dapat menyebabkan daun menjadi abnormal di mana daun akan terpelintir dan memendek seperti pada gambar 1.8. | DOC002 | DOC002_C035_01 |
| 8 | Kedelai | Penyakit Rebah Semai | ambigu | gejala yang muncul pada tanaman yang terserang s. | DOC002 | DOC002_C038_03 |
| 9 | Kedelai | Penyakit Rebah Kecambah | butuh_konsep_baru | solani maka benih tidak akan berkecambah atau mati. | DOC002 | DOC002_C040_02 |
| 10 | Kedelai | Penyakit Rebah Kecambah | butuh_konsep_baru | solani akan menunjukkan gejala adanya lekukan coklat dan berkembang menjadi warna hitam pada pangkal akar muda yang terinfeksi (muslim et al., 2019). | DOC002 | DOC002_C040_02 |
| 11 | Kedelai | Penyakit Layu Fusarium | bukan_gejala | gejala penyakit yang disebabkan oleh patogen fusarium spp. | DOC002 | DOC002_C042_01 |
| 12 | Kedelai | Penyakit Karat Daun | bukan_gejala | akibat serangan oleh patogen ini menyebabkan penurunan produksi polong kedelai mencapai 30-60%. | DOC002 | DOC002_C043_03 |
| 13 | Kedelai | Penyakit Karat Daun | butuh_konsep_baru | intensitas serangan berat pada saat pengisian polong. | DOC002 | DOC002_C043_03 |
| 14 | Kedelai | Penyakit Embun Palsu (Downy mildew) | ambigu | gejala yang muncul pada tanaman yang terinfeksi p. | DOC002 | DOC002_C046_02 |
| 15 | Kedelai | Penyakit Embun Palsu (Downy mildew) | bukan_gejala | daun menjadi kaku seperti gejala tanaman yang terinfeksi virus. | DOC002 | DOC002_C046_02 |
| 16 | Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | bukan_gejala | pengaturan jarak tanam pada beberapa varietas kedelai tidak memengaruhi terhadap intensitas serangan c. | DOC002 | DOC002_C048_02 |
| 17 | Kedelai | Penyakit Bercak Target | bukan_gejala | gejala juga dapat muncul pada bagian tanaman seperti batang dan polong yang terinfeksi patogen c. | DOC002 | DOC002_C051_02 |
| 18 | Kedelai | Penyakit Bercak Biji Ungu | bukan_gejala | gejala pada tanaman kedelai yang terinfeksi patogen c. | DOC002 | DOC002_C053_01 |
| 19 | Kedelai | Penyakit Bercak Biji Ungu | ambigu | gejala ini biasanya dianggap sebagai gejala karena pengaruh cahaya matahari. | DOC002 | DOC002_C053_01 |
| 20 | Kedelai | Penyakit Bercak Biji Ungu | ambigu | pada gejala awal tanaman tidak terlihat sakit karena gejala yang disebabkan oleh c. | DOC002 | DOC002_C054_01 |
| 21 | Kedelai | Penyakit Bercak Biji Ungu | bukan_gejala | budidaya tanaman kedelai juga dihadapkan dengan adanya serangan dari bakteri penyebab penyakit. | DOC002 | DOC002_C054_02 |
| 22 | Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | bukan_gejala | gejala tanaman yang disebabkan oleh patogen p. | DOC002 | DOC002_C054_03 |
| 23 | Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | bukan_gejala | akibat serangan patogen ini maka benih yang dihasilkan menjadi berukuran kecil dan warnanya akan berubah. | DOC002 | DOC002_C054_03 |
| 24 | Kedelai | Penyakit Bakteri Pustul | bukan_gejala | gejala yang muncul akibat serangan patogen x. | DOC002 | DOC002_C056_02 |
| 25 | Kedelai | Penyakit Mosaik Kedelai (Soybean Mosaic Virus) | bukan_gejala | tanaman dapat menunjukkan gejala yang sama atau berbeda akibat patogen smv. | DOC002 | DOC002_C057_03 |
| 26 | Kedelai | Penyakit Mosaik Kedelai (Soybean Mosaic Virus) | bukan_gejala | hal ini dipengaruhi oleh beberapa faktor seperti umur tanaman saat terinfeksi patogen smv, kondisi lingkungan pada saat adanya infeksi, virus yang menginfeksi benih dan sumber inokulum di lapangan menunjukkan gejala yang | DOC002 | DOC002_C057_03 |
| 27 | Kedelai | Penyakit Samar Kacang Tunggak (Cowpea Mild Mottle Virus) | ambigu | gejala akan semakin berkembang seiring dengan meningkatnya umur tanaman. | DOC002 | DOC002_C059_01 |
| 28 | Kedelai | Penyakit Samar Kacang Tunggak (Cowpea Mild Mottle Virus) | butuh_konsep_baru | pada gejala yang parah maka tanaman kedelai akan menunjukkan gejala yang semakin beragam dan kompleks serta diikuti dengan gejala mal formasi pada daun tanaman kedelai (sulandari et al., 2014). | DOC002 | DOC002_C059_01 |
| 29 | Kedelai | Penyakit Kerdil Kedelai (Soybean Stunt Virus) | bukan_gejala | yang menusukkan alat mulut stylet pada tanaman sehat sehingga virus akan memperbanyak diri dan membentuk partikel virus yang baru pada tanaman yang sehat sehingga tanaman yang sehat akan terinfeksi dan menunjukkan gejala | DOC002 | DOC002_C061_02 |
| 30 | KacangTanah | Penyakit Bercak Daun | bukan_gejala | gejala berbeda-beda tergantung dari spesies patogennya (cercospora arachidicola dan c. | DOC002 | DOC002_C065_01 |
| 31 | KacangTanah | Penyakit Bercak Daun | butuh_konsep_baru | serangan penyakit berdampak pada pengurangan jumlah polong dan berat biji per tanaman sehingga dapat mengakibatkan penurunan hasil dan produksi sebesar 50%. | DOC002 | DOC002_C065_01 |
| 32 | KacangTanah | Penyakit Belang (Mottle) | ambigu | kadang-kadang gejala oleh pstv berupa garis putus-putus berwarna hijau gelap (stripe). | DOC002 | DOC002_C072_01 |
| 33 | KacangTanah | Penyakit Belang (Mottle) | bukan_gejala | tetapi umumnya gejala kedua virus ini sukar dibedakan. | DOC002 | DOC002_C072_01 |
| 34 | KacangTanah | Penyakit Belang (Mottle) | bukan_gejala | gejala serangan dan makroskopis ditunjukkan gambar 4. | DOC002 | DOC002_C072_01 |
| 35 | UbiJalar | layu fusarium | bukan_gejala | tanaman merambat berwarna kecokelatan (1b dan e), tanaman yang mati sering terdapat miselium berwarna merah muda dengan makrokonidia dan mikrokonidia patogen (1c dan f). | DOC002 | DOC002_C080_01 |
| 36 | UbiJalar | layu fusarium | bukan_gejala | gejala serangan fusarium pada umbi ubi jalar berupa kanker melingkar permukaan yang minimal memengaruhi jaringan di bawahnya, berwarna coklat pucat sampai kehitaman kering, rerata diameter awalnya 2-4 mm, luka dapat tumb | DOC002 | DOC002_C080_01 |
| 37 | UbiJalar | Penyakit kudis | bukan_gejala | daun menjadi tidak produktif dalam fotosintesis jika pada tingkat serangan berat, sehingga hasil ubi rendah dan bahkan tidak menghasilkan sama sekali (rukmana, 1997). | DOC002 | DOC002_C083_01 |
| 38 | UbiJalar | Penyakit kudis | bukan_gejala | sumber inokulum penyakit kudis biasanya berasal dari bahan tanam (setek) yang terinfeksi jamur, penyakit ini menyebar lebih cepat ke tanaman yang sehat percikan air hujan yang disertai angin, lebih banyak terjadi seranga | DOC002 | DOC002_C083_01 |
| 39 | UbiJalar | Penyakit kudis | ambigu | selain itu, faktor lingkungan juga memengaruhi perubahan ketahanan ubi jalar terhadap penyakit kudis (roosda et al., 20013), sehingga kultivar yang tahan dapat berubah menjadi tidak tahan dan periode inkubasi juga memeng | DOC002 | DOC002_C083_01 |
| 40 | UbiJalar | Penyakit kudis | bukan_gejala | hasil penelitian martanto (2010) menjelaskan bahwa tanaman ubi jalar membentuk lapisan gabus untuk mempertahankan diri dari serangan penyakit kudis (gambar 3a dan b). | DOC002 | DOC002_C083_02 |
| 41 | UbiJalar | Penyakit bercak kuning | bukan_gejala | informasi penelitian di indonesia terkait virus pada ubi jalar masih sedikit, namun yang paling dominan adalah serangan spfmv. | DOC002 | DOC002_C085_01 |
| 42 | UbiJalar | Penyakit bercak kuning | bukan_gejala | menurut cooper and jones (2006) bahwa variabilitas dalam ekspresi gejala disebabkan karena beberapa faktor seperti kondisi lingkungan, strain virus, spesies atau genotipe tanaman inang, umur dan fisiologi inang. | DOC002 | DOC002_C086_01 |
| 43 | UbiJalar | Penyakit busuk hitam (black rot) | ambigu | (2018) menjelaskan bahwa gejala serangan c. | DOC002 | DOC002_C087_01 |
| 44 | UbiJalar | Penyakit busuk hitam (black rot) | bukan_gejala | gambar 4.6: gejala dan bentuk mikroskopis c. | DOC002 | DOC002_C088_02 |
| 45 | UbiJalar | Penyakit busuk hitam (black rot) | bukan_gejala | fimbriata, (a&b) gejala pascapanen pada ubi jalar (c&d) anterior dan posterior koloni spl17100 pada media pda yang diinkubasi selama 7 hari pada 25 °c, e,g,h) aleurokonidiophore dengan aleurokonidia, f) perithecium denga | DOC002 | DOC002_C088_02 |
| 46 | Jagung | Penyakit Karat Daun | ambigu | bintil berbentuk bulat atau oval dan dapat saling bergabung. | DOC002 | DOC002_C103_03 |
| 47 | Jagung | Penyakit Karat Daun | bukan_gejala | jika bintil pecah, spora akan keluar dan terbawa angin maupun percikan air hujan sehingga menjadi sumber inokulum baru dan dapat menginfeksi tanaman lain. | DOC002 | DOC002_C103_03 |
| 48 | Jagung | Penyakit Karat Daun | butuh_konsep_baru | gejala karat biasanya diawali dari daun bagian bawah dan berkembang ke daun bagian atas, umumnya muncul pada masa generatif (puspawati and sudarma, 2016). | DOC002 | DOC002_C103_03 |
| 49 | Jagung | Penyakit Karat Daun | butuh_konsep_baru | keparahan penyakit yang disebabkan karat daun dapat berkisar antara 26.67% hingga 90.91%. | DOC002 | DOC002_C103_03 |
| 50 | Jagung | Penyakit Karat Daun | bukan_gejala | perkembangan penyakit dipengaruhi oleh kondisi lingkungan seperti suhu dan kelembaban. | DOC002 | DOC002_C103_03 |
| 51 | Jagung | Penyakit Karat Daun | bukan_gejala | suhu 25.2°c – 28.8°c merupakan suhu optimum perkembangan penyakit karat. | DOC002 | DOC002_C103_03 |
| 52 | Jagung | Penyakit Karat Daun | bukan_gejala | semakin tinggi kelembaban maka laju infeksi akan meningkat pada batas tertentu. | DOC002 | DOC002_C103_03 |
| 53 | Jagung | Penyakit Karat Daun | bukan_gejala | laju infeksi ditentukan oleh kenaikan suhu dan kelembaban, meningkatnya suhu dapat menurunkan laju infeksi dan sebaliknya meningkatnya kelembaban dapat meningkatkan laju infeksi (puspawati and sudarma, 2016). | DOC002 | DOC002_C103_03 |
| 54 | Jagung | Penyakit Karat Daun | ambigu | menurut hamidson et al., (2019) keparahan penyakit karat jagung dapat mencapai 79.9% hingga 83.15%. | DOC002 | DOC002_C103_03 |
| 55 | Jagung | Penyakit Karat Daun | bukan_gejala | penyakit karat akan berkembang lebih baik pada suhu yang rendah dan kelembaban tinggi. | DOC002 | DOC002_C103_03 |
| 56 | Jagung | Penyakit Bulai | ambigu | penyakit jagung mulai muncul antara 15 hingga 17 hari setelah infeksi (habibi et al., 2017). | DOC002 | DOC002_C105_02 |
| 57 | Jagung | Penyakit Bulai | bukan_gejala | kecepatan angin, kelembaban yang tinggi lebih dari 90% dan suhu di bawah 24°c dapat meningkatkan laju infeksi penyakit bulai. | DOC002 | DOC002_C105_02 |
| 58 | Jagung | Penyakit Bulai | ambigu | penyakit bulai menyerang tanaman pada fase vegetatif dan infeksi akan berkurang saat tanaman semakin tua karena semakin dewasa tanaman akan lebih tahan terhadap penyakit bulai (purwanto et al., 2016). | DOC002 | DOC002_C105_02 |
| 59 | Jagung | Penyakit Bulai | ambigu | kejadian penyakit yang disebabkan penyakit bulai bervariasi antara 19.33% sampai 28.37% dan bergantung pada kondisi lingkungan tiap wilayah (kurniawan et al., 2017). | DOC002 | DOC002_C105_02 |
| 60 | Kedelai | Penyakit Embun Palsu (Downy mildew) | butuh_konsep_baru | pada permukaan bawah daun warna coklat tersebut terdapat tubuh buah miselium dan sporangium berupa benang-benang halus yang berwarna putih kecoklatan menyerupai bulu, oleh karena itu disebut embun bulu. | DOC005 | DOC005_C026_02 |
| 61 | Kedelai | Penyakit Antraknosa | butuh_konsep_baru | gejala penyakit antraknosa pada kedelai dapat ditemukan pada bagian batang, tangkai daun, daun, dan polong. | DOC005 | DOC005_C031_02 |
| 62 | KacangHijau | Penyakit Bercak Daun | bukan_gejala | pada varietas rentan menyebabkan gejala defoliasi prematur pengurangan ukuran polong dan biji (grewal et al. 1980). | DOC005 | DOC005_C059_02 |
| 63 | KacangHijau | Penyakit Layu | bukan_gejala | miselia berwarna putih akan ditemukan di sekitar gejala, dan pada gejala tingkat lanjut akan ditemukan sejumlah sclerosia pada akar (jin hyeuk 2017) dan daun dekat permukaan tanah (gambar 25). | DOC005 | DOC005_C064_03 |
| 64 | UbiKayu | Tanaman kerdil (stunt) | bukan_gejala | tanaman tidak tumbuh secara normal, gejala ini umumnya terjadi pada tanaman yang mengalami infeksi awal oleh virus ini. tanaman yang terinfeksi virus ini umumnya akan memiliki batang yang berukuran kecil | DOC002 | T5.2_BATANG#4 |

## Pengendalian belum dipetakan

| # | Tanaman | Penyakit | Triase awal | Kutipan | Sumber | Chunk |
|---:|---|---|---|---|---|---|
| 1 | Padi | Penyakit Blas | butuh_konsep_baru | beberapa strategi pengendalian telah disarikan miah et al. | DOC002 | DOC002_C030_02 |
| 2 | Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | butuh_konsep_baru | strategi pengendalian penyakit kerdil rumput dan kerdil hampa hampir sama dengan pengendalian penyakit tungro. | DOC002 | DOC002_C035_03 |
| 3 | Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | butuh_konsep_baru | selain mengendalikan patogennya, vektornya pun harus dikendalikan. | DOC002 | DOC002_C035_03 |
| 4 | Kedelai | Penyakit Rebah Semai | ambigu | rolfsii memiliki kisaran inang yang luas seperti famili leguminoceae, cruciferaceae, cucurbitaceae, tanaman pisang, jeruk, gandum, padi, tebu, bit, keladi, bahkan tanaman rempah (sumartini, 2012). | DOC002 | DOC002_C040_01 |
| 5 | Kedelai | Penyakit Rebah Semai | butuh_konsep_baru | hasil penelitian yang dilakukan oleh fitria and masnilah, (2020) pada beberapa varietas kedelai terhadap patogen s. | DOC002 | DOC002_C040_01 |
| 6 | Kedelai | Penyakit Rebah Semai | bukan_tindakan | rolfsii sebesar 20-85% (marwan et al., 2017). | DOC002 | DOC002_C040_01 |
| 7 | Kedelai | Penyakit Rebah Semai | bukan_tindakan | rolfsii dengan melilitkan hifanya dengan membentuk haustorium pada hifa patogen kemudian menghasilkan enzim kitinase yang menyebabkan dinding sel patogen lisis dan rusak (chamzurni et al., 2011). | DOC002 | DOC002_C040_01 |
| 8 | Kedelai | Penyakit Rebah Kecambah | butuh_konsep_baru | menurut inayati and yusnawan, (2017) pengendalian penyakit yang disebabkan oleh r. | DOC002 | DOC002_C041_02 |
| 9 | Kedelai | Penyakit Layu Fusarium | butuh_konsep_baru | oxysporum mengurangi intensitas patogen (kaya et al., 2020). | DOC002 | DOC002_C043_02 |
| 10 | Kedelai | Penyakit Karat Daun | butuh_konsep_baru | hampir beberapa varietas unggul kedelai dapat dipatahkan ketahanannya oleh ras patogen yang baru. | DOC002 | DOC002_C044_02 |
| 11 | Kedelai | Penyakit Embun Tepung (Powdery Mildew) | butuh_konsep_baru | mampu menekan penyakit embun tepung pada tanaman pepaya (firnando et al., 2020). | DOC002 | DOC002_C046_01 |
| 12 | Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | butuh_konsep_baru | siklus penyakit terjadi melalui penggunaan benih yang terinfeksi patogen c. | DOC002 | DOC002_C048_02 |
| 13 | Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | butuh_konsep_baru | menurut inayati and yusnawan, (2017) pengendalian c. | DOC002 | DOC002_C048_02 |
| 14 | Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | bukan_tindakan | syringae pada tanaman kedelai (majid, 2016). | DOC002 | DOC002_C055_02 |
| 15 | Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | ambigu | syringae menjadi awal pengelolaan perkembangan penyakit. | DOC002 | DOC002_C055_02 |
| 16 | KacangTanah | Penyakit Bercak Daun | butuh_konsep_baru | berbagai upaya pengendalian telah banyak dilakukan untuk dapat mengurangi kerusakan akibat penyakit bercak daun. | DOC002 | DOC002_C066_04 |
| 17 | KacangTanah | Penyakit Bercak Daun | ambigu | mikroorganisme ini biasanya berasal dari daerah perakaran atau endofit dan juga dari jaringan endofit daun. | DOC002 | DOC002_C066_04 |
| 18 | KacangTanah | Penyakit Bercak Daun | bukan_tindakan | menurut istifadah dan sari (2017), jamur t. | DOC002 | DOC002_C067_01 |
| 19 | KacangTanah | Penyakit Bercak Daun | ambigu | arachidicola mengalami resistensi dan lingkungan mendukung dalam perkembangan patogen | DOC002 | DOC002_C068_02 |
| 20 | KacangTanah | Penyakit Bercak Daun | ambigu | karat daun merupakan penyakit tular udara yang penyebarannya melalui angin dan percikan air hujan. | DOC002 | DOC002_C070_01 |
| 21 | KacangTanah | Penyakit Belang (Mottle) | bukan_tindakan | pengujian ketahanan tanaman terhadap pstv pernah dilakukan terhadap 11.000 genotipe menunjukkan semua genotipe rentan terhadap pstv. | DOC002 | DOC002_C073_03 |
| 22 | KacangTanah | Penyakit Belang (Mottle) | bukan_tindakan | pendekatan bioteknologi melalui rekayasa genetik untuk menghasilkan tanaman transgenik diharapkan mampu membantu upaya memperoleh tanaman kacang tanah yang terinfeksi pstv. | DOC002 | DOC002_C073_03 |
| 23 | KacangTanah | Penyakit Belang (Mottle) | butuh_konsep_baru | penggunaan tanaman dari benih yang sebelumnya terinfeksi pstv akan menyebabkan ledakan penyakit terutama saat populasi vektor tinggi. | DOC002 | DOC002_C073_04 |
| 24 | KacangTanah | Penyakit Belang (Mottle) | butuh_konsep_baru | infeksi benih 2-5% dapat menyebabkan endemis penyakit saat panen. | DOC002 | DOC002_C073_04 |
| 25 | KacangTanah | Penyakit Belang (Mottle) | ambigu | karena penularan dapat terjadi dengan sangat cepat sebelum serangga mati. | DOC002 | DOC002_C073_05 |
| 26 | KacangTanah | Penyakit Belang (Mottle) | butuh_konsep_baru | pertumbuhan tanaman yang tegar akan mampu mengurangi kehilangan hasil akibat infeksi pstv. | DOC002 | DOC002_C073_05 |
| 27 | KacangTanah | Penyakit Belang (Mottle) | ambigu | infeksi pstv pada kacang tanah pada musim hujan dapat lebih ringan dibanding musim kemarau | DOC002 | DOC002_C073_05 |
| 28 | KacangTanah | Penyakit Layu Bakteri | duplikat_parafrase | beberapa mikroba telah diteliti dan dilaporkan mampu berperan sebagai agens pengendali hayati penyakit layu bakteri r. | DOC002 | DOC002_C077_02 |
| 29 | KacangTanah | Penyakit Layu Bakteri | bukan_tindakan | solanacearum pada tanaman aromatik nilam. | DOC002 | DOC002_C077_02 |
| 30 | UbiJalar | layu fusarium | ambigu | oxysporum (scattolini, hernandez and gonzales, 2020). | DOC002 | DOC002_C082_02 |
| 31 | Jagung | Penyakit Hawar Daun | butuh_konsep_baru | aplikasi dilakukan sebanyak enam kali (pada umur 28, 35, 42, 49, 56, 63 hari setelah tanam) dengan cara penyemprotan ke bagian daun. | DOC002 | DOC002_C102_02 |
| 32 | Jagung | Penyakit Bulai | butuh_konsep_baru | oleh karena itu, diperlukan pengendalian yang lebih ramah lingkungan. | DOC002 | DOC002_C106_02 |
| 33 | Jagung | Penyakit Bulai | butuh_konsep_baru | tanaman yang diberikan perlakuan v1p2 yaitu kombinasi varietas pioneer 27 dan isolat p. | DOC002 | DOC002_C106_02 |
| 34 | Jagung | Penyakit Layu Stewart | bukan_tindakan | hasilnya menunjukkan bahwa perkembangan penyakit dapat terhambat dengan kemampuan penekanan penyakit sebesar 76.92% hingga 92.30%. | DOC002 | DOC002_C108_02 |
| 35 | KacangTanah | Pengendalian umum KacangTanah | bukan_tindakan | menurut istifadah dan sari (2017), jamur t. | DOC002 | DOC002_C067_01 |
| 36 | KacangTanah | Pengendalian umum KacangTanah | ambigu | arachidicola mengalami resistensi dan lingkungan mendukung dalam perkembangan patogen | DOC002 | DOC002_C068_02 |
| 37 | KacangTanah | Pengendalian umum KacangTanah | duplikat_parafrase | beberapa mikroba telah diteliti dan dilaporkan mampu berperan sebagai agens pengendali hayati penyakit layu bakteri r. | DOC002 | DOC002_C077_02 |
| 38 | KacangTanah | Pengendalian umum KacangTanah | bukan_tindakan | solanacearum pada tanaman aromatik nilam. | DOC002 | DOC002_C077_02 |

## Drainase dan rotasi

- Unit sumber yang menyebut drainase: **3**.
- Unit sumber yang menyebut rotasi/pergiliran: **26**.
- Informasi ini sudah ada di sumber, tetapi saat ini lebih banyak direpresentasikan sebagai aksi pengendalian daripada kondisi lingkungan.

Contoh bukti drainase:

- DOC002 `DOC002_P041_B007`: menurut inayati and yusnawan, (2017) pengendalian penyakit yang disebabkan oleh r. solani dapat dilakukan dengan beberapa cara yaitu teknik pengendalian secara kultur teknis seperti rotasi tanam, melakukan perbaikan drainase, penanaman kedelai tidak pada musim hujan yang tinggi, melakukan eradikasi 
- DOC002 `DOC002_P097_B003`: secara umum pengendalian penyakit pada tanaman ubi kayu yaitu pada perbaikan cara atau teknik budidaya yang tepat sebagai upaya preventif, yang meliputi pengaturan jarak tanam, memperbaiki drainase pertanaman, rotasi tanaman, dan tumpang sari, penggunaan varietas tahan penyakit, serta bahan perbanya
- DOC002 `DOC002_MD_C012_01`: **gambar 2.3: siklus penyakit *r. solani* penyebab penyakit rebah kecambah pada tanaman kedelai (ajayi-oyetunde and bradley, 2018)** menurut inayati and yusnawan, (2017) pengendalian penyakit yang disebabkan oleh *r. solani* dapat dilakukan dengan beberapa cara yaitu teknik pengendalian secara kultu

Contoh bukti rotasi:

- DOC002 `DOC002_P040_B002`: pengendalian patogen s. rolfsii dengan rotasi atau pergiliran tanaman di lahan kurang efektif. hal ini karena patogen s. rolfsii memiliki kisaran inang yang luas seperti famili leguminoceae, cruciferaceae, cucurbitaceae, tanaman pisang, jeruk, gandum, padi, tebu, bit, keladi, bahkan tanaman rempah (
- DOC002 `DOC002_P041_B007`: menurut inayati and yusnawan, (2017) pengendalian penyakit yang disebabkan oleh r. solani dapat dilakukan dengan beberapa cara yaitu teknik pengendalian secara kultur teknis seperti rotasi tanam, melakukan perbaikan drainase, penanaman kedelai tidak pada musim hujan yang tinggi, melakukan eradikasi 
- DOC002 `DOC002_P046_B002`: pengendalian penyakit dapat dilakukan dengan melakukan rotasi tanaman dengan mengganti tanaman dengan tanaman yang bukan inang patogen e. diffusa. melakukan eradikasi tanaman yang menjadi sumber inokulum. pengendalian dengan agens hayati seperti cendawan lecanicillium lecanii mampu menekan perkemban
- DOC002 `DOC002_P048_B005`: pengendalian penyakit ini dapat dilakukan dengan menanam varietas yang tahan terhadap patogen c. sojina (giesler, 2013). selain menanam varietas tahan pengelolaan tanaman seperti melakukan rotasi tanam selama 2 tahun dan pengolahan lahan dengan membajak lahan dan membersihkan sumber inokulum dapat m
- DOC002 `DOC002_P052_B005`: pengendalian yang dapat dilakukan adalah penggunaan benih kedelai yang bebas dari patogen c. cassicola, eradikasi lahan dari sisa-sisa tanaman yang terinfeksi patogen dan melakukan sanitasi lahan, melakukan pergiliran tanaman dengan tanaman yang bukan inang patogen c. cassiicola seperti jagung dan s

## Kesimpulan

- Gap gejala/pengendalian bukan berarti sumber kosong; teks bukti tersedia dan menunggu triase/mapping.
- Severity, fase, varietas, dan nama Inggris bersifat best-effort: sebagian tersedia, sebagian hanya parsial, dan sisanya tidak tersedia.
- Drainase dan rotasi tetap tersedia di sumber, tetapi tidak dimodelkan sebagai kelas faktor lingkungan; drainase/rotasi dipakai sebagai aksi pengendalian, sedangkan kondisi drainase diwakili `KondisiDrainaseBaik`/`KondisiDrainaseBuruk`.
