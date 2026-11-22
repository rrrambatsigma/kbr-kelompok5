# Triage Mapping Gejala dan Pengendalian

Laporan ini memisahkan gap nyata dari noise. Sumber baris adalah `SOURCE_GAP_AUDIT.json`; klasifikasi di sini adalah keputusan awal sebelum perubahan aturan mapping.

## Ringkasan

| Item | Jumlah |
|---|---:|
| Total record belum dipetakan | 95 |
| Gejala | 58 |
| Pengendalian | 37 |

| Jenis | Kategori | Jumlah |
|---|---|---:|
| Gejala | Ambigu | 15 |
| Gejala | Bukan gejala | 38 |
| Gejala | Butuh konsep baru | 5 |
| Pengendalian | Ambigu | 10 |
| Pengendalian | Bukan tindakan | 9 |
| Pengendalian | Duplikat/parafrase | 6 |
| Pengendalian | Tindakan nyata | 12 |

## Gejala

| # | Tanaman | Penyakit | Kategori | Usulan | Alasan | Kutipan |
|---:|---|---|---|---|---|---|
| 1 | Padi | Penyakit Hawar Daun Bakteri | Butuh konsep baru | Tambah konsep/rule kanonik | Gejala nyata belum masuk kosakata kanonik. | Sementara itu, fase kresek ditandai terutama oleh infeksi sistemis karena pada fase ini gejala penyakit biasanya muncul 1-2 minggu setelah transplantasi persemaian ke lapangan. |
| 2 | Padi | Penyakit Hawar Daun Bakteri | Butuh konsep baru | Tambah konsep/rule kanonik | Gejala nyata belum masuk kosakata kanonik. | Istilah kresek sendiri diambil dari bahasa Jawa yang berarti suara daun-daun yang mati yang bergesekan satu sama lain menyerupai suara kresek (Goto, 1992). |
| 3 | Padi | Penyakit Blas | Butuh konsep baru | Tambah konsep/rule kanonik | Malai patah/empty perlu konsep terpisah dari malai kosong. | Gejala khas dari penyakit ini, yaitu blas daun dan blas malai. |
| 4 | Padi | Penyakit Hawar Pelepah Daun | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Gejala penyakit HDP dapat dilihat pada selubung daun. |
| 5 | Padi | Penyakit Hawar Pelepah Daun | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Gejala tersebut dapat ditemukan pada padi fase anakan sampai fase matang susu. |
| 6 | Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Infeksi pada daun bendera dapat menyebabkan daun menjadi abnormal di mana daun akan terpelintir dan memendek seperti pada Gambar 1.8. |
| 7 | Kedelai | Penyakit Rebah Semai | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Gejala yang muncul pada tanaman yang terserang S. |
| 8 | Kedelai | Penyakit Rebah Kecambah | Butuh konsep baru | Tambah konsep/rule kanonik | Gejala nyata belum masuk kosakata kanonik. | solani akan menunjukkan gejala adanya lekukan coklat dan berkembang menjadi warna hitam pada pangkal akar muda yang terinfeksi (Muslim et al., 2019). |
| 9 | Kedelai | Penyakit Layu Fusarium | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gejala penyakit yang disebabkan oleh patogen Fusarium spp. |
| 10 | Kedelai | Penyakit Karat Daun | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Akibat serangan oleh patogen ini menyebabkan penurunan produksi polong kedelai mencapai 30-60%. |
| 11 | Kedelai | Penyakit Karat Daun | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Intensitas serangan berat pada saat pengisian polong. |
| 12 | Kedelai | Penyakit Embun Palsu (Downy mildew) | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Gejala yang muncul pada tanaman yang terinfeksi P. |
| 13 | Kedelai | Penyakit Embun Palsu (Downy mildew) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Daun menjadi kaku seperti gejala tanaman yang terinfeksi virus. |
| 14 | Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Pengaturan jarak tanam pada beberapa varietas kedelai tidak memengaruhi terhadap intensitas serangan C. |
| 15 | Kedelai | Penyakit Bercak Target | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gejala juga dapat muncul pada bagian tanaman seperti batang dan polong yang terinfeksi patogen C. |
| 16 | Kedelai | Penyakit Bercak Biji Ungu | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gejala pada tanaman kedelai yang terinfeksi patogen C. |
| 17 | Kedelai | Penyakit Bercak Biji Ungu | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gejala ini biasanya dianggap sebagai gejala karena pengaruh cahaya matahari. |
| 18 | Kedelai | Penyakit Bercak Biji Ungu | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Pada gejala awal tanaman tidak terlihat sakit karena gejala yang disebabkan oleh C. |
| 19 | Kedelai | Penyakit Bercak Biji Ungu | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Budidaya tanaman kedelai juga dihadapkan dengan adanya serangan dari bakteri penyebab penyakit. |
| 20 | Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gejala tanaman yang disebabkan oleh patogen P. |
| 21 | Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | akibat serangan patogen ini maka benih yang dihasilkan menjadi berukuran kecil dan warnanya akan berubah. |
| 22 | Kedelai | Penyakit Bakteri Pustul | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gejala yang muncul akibat serangan patogen X. |
| 23 | Kedelai | Penyakit Mosaik Kedelai (Soybean Mosaic Virus) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Tanaman dapat menunjukkan gejala yang sama atau berbeda akibat patogen SMV. |
| 24 | Kedelai | Penyakit Mosaik Kedelai (Soybean Mosaic Virus) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Hal ini dipengaruhi oleh beberapa faktor seperti umur tanaman saat terinfeksi patogen SMV, kondisi lingkungan pada saat adanya infeksi, virus yang menginfeksi benih dan sumber inokulum di lapangan menunjukkan gejala yang beragam. |
| 25 | Kedelai | Penyakit Samar Kacang Tunggak (Cowpea Mild Mottle Virus) | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Gejala akan semakin berkembang seiring dengan meningkatnya umur tanaman. |
| 26 | Kedelai | Penyakit Kerdil Kedelai (Soybean Stunt Virus) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | yang menusukkan alat mulut stylet pada tanaman sehat sehingga virus akan memperbanyak diri dan membentuk partikel virus yang baru pada tanaman yang sehat sehingga tanaman yang sehat akan terinfeksi dan menunjukkan gejala sesuai dengan virus |
| 27 | KacangTanah | Penyakit Bercak Daun | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Gejala berbeda-beda tergantung dari spesies patogennya (Cercospora arachidicola dan C. |
| 28 | KacangTanah | Penyakit Bercak Daun | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Serangan penyakit berdampak pada pengurangan jumlah polong dan berat biji per tanaman sehingga dapat mengakibatkan penurunan hasil dan produksi sebesar 50%. |
| 29 | KacangTanah | Penyakit Belang (Mottle) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Tetapi umumnya gejala kedua virus ini sukar dibedakan. |
| 30 | KacangTanah | Penyakit Belang (Mottle) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gejala serangan dan makroskopis ditunjukkan Gambar 4. |
| 31 | UbiJalar | layu fusarium | Butuh konsep baru | Tambah konsep/rule kanonik | Gejala nyata belum masuk kosakata kanonik. | Tanaman merambat berwarna kecokelatan (1B dan E), tanaman yang mati sering terdapat miselium berwarna merah muda dengan makrokonidia dan mikrokonidia patogen (1C dan F). |
| 32 | UbiJalar | layu fusarium | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gejala serangan Fusarium pada umbi ubi jalar berupa kanker melingkar permukaan yang minimal memengaruhi jaringan di bawahnya, berwarna coklat pucat sampai kehitaman kering, rerata diameter awalnya 2-4 mm, luka dapat tumbuh dan berkembang me |
| 33 | UbiJalar | Penyakit kudis | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Daun menjadi tidak produktif dalam fotosintesis jika pada tingkat serangan berat, sehingga hasil ubi rendah dan bahkan tidak menghasilkan sama sekali (Rukmana, 1997). |
| 34 | UbiJalar | Penyakit kudis | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Sumber inokulum penyakit kudis biasanya berasal dari bahan tanam (setek) yang terinfeksi jamur, penyakit ini menyebar lebih cepat ke tanaman yang sehat percikan air hujan yang disertai angin, lebih banyak terjadi serangan pada musim hujan ( |
| 35 | UbiJalar | Penyakit kudis | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Selain itu, faktor lingkungan juga memengaruhi perubahan ketahanan ubi jalar terhadap penyakit kudis (Roosda et al., 20013), sehingga kultivar yang tahan dapat berubah menjadi tidak tahan dan periode inkubasi juga memengaruhi munculnya geja |
| 36 | UbiJalar | Penyakit kudis | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Hasil penelitian Martanto (2010) menjelaskan bahwa tanaman ubi jalar membentuk lapisan gabus untuk mempertahankan diri dari serangan penyakit kudis (Gambar 3A dan B). |
| 37 | UbiJalar | Penyakit bercak kuning | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Informasi penelitian di Indonesia terkait virus pada ubi jalar masih sedikit, namun yang paling dominan adalah serangan SPFMV. |
| 38 | UbiJalar | Penyakit bercak kuning | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Menurut Cooper and Jones (2006) bahwa variabilitas dalam ekspresi gejala disebabkan karena beberapa faktor seperti kondisi lingkungan, strain virus, spesies atau genotipe tanaman inang, umur dan fisiologi inang. |
| 39 | UbiJalar | Penyakit busuk hitam (black rot) | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | (2018) menjelaskan bahwa gejala serangan C. |
| 40 | UbiJalar | Penyakit busuk hitam (black rot) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Gambar 4.6: Gejala dan bentuk mikroskopis C. |
| 41 | UbiJalar | Penyakit busuk hitam (black rot) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | fimbriata, (a&b) gejala pascapanen pada ubi jalar (c&d) Anterior dan posterior koloni SPL17100 pada media PDA yang diinkubasi selama 7 hari pada 25 °C, e,g,h) aleurokonidiophore dengan aleurokonidia, f) perithecium dengan leher panjang (i&j |
| 42 | Jagung | Penyakit Karat Daun | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Gejala karat biasanya diawali dari daun bagian bawah dan berkembang ke daun bagian atas, umumnya muncul pada masa generatif (Puspawati and Sudarma, 2016). |
| 43 | Jagung | Penyakit Karat Daun | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Keparahan penyakit yang disebabkan karat daun dapat berkisar antara 26.67% hingga 90.91%. |
| 44 | Jagung | Penyakit Karat Daun | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Perkembangan penyakit dipengaruhi oleh kondisi lingkungan seperti suhu dan kelembaban. |
| 45 | Jagung | Penyakit Karat Daun | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Suhu 25.2°C – 28.8°C merupakan suhu optimum perkembangan penyakit karat. |
| 46 | Jagung | Penyakit Karat Daun | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Semakin tinggi kelembaban maka laju infeksi akan meningkat pada batas tertentu. |
| 47 | Jagung | Penyakit Karat Daun | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Laju infeksi ditentukan oleh kenaikan suhu dan kelembaban, meningkatnya suhu dapat menurunkan laju infeksi dan sebaliknya meningkatnya kelembaban dapat meningkatkan laju infeksi (Puspawati and Sudarma, 2016). |
| 48 | Jagung | Penyakit Karat Daun | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Menurut Hamidson et al., (2019) keparahan penyakit karat jagung dapat mencapai 79.9% hingga 83.15%. |
| 49 | Jagung | Penyakit Karat Daun | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Penyakit karat akan berkembang lebih baik pada suhu yang rendah dan kelembaban tinggi. |
| 50 | Jagung | Penyakit Bulai | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Penyakit jagung mulai muncul antara 15 hingga 17 hari setelah infeksi (Habibi et al., 2017). |
| 51 | Jagung | Penyakit Bulai | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Kecepatan angin, kelembaban yang tinggi lebih dari 90% dan suhu di bawah 24°C dapat meningkatkan laju infeksi penyakit bulai. |
| 52 | Jagung | Penyakit Bulai | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Penyakit bulai menyerang tanaman pada fase vegetatif dan infeksi akan berkurang saat tanaman semakin tua karena semakin dewasa tanaman akan lebih tahan terhadap penyakit bulai (Purwanto et al., 2016). |
| 53 | Jagung | Penyakit Bulai | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Kejadian penyakit yang disebabkan penyakit bulai bervariasi antara 19.33% sampai 28.37% dan bergantung pada kondisi lingkungan tiap wilayah (Kurniawan et al., 2017). |
| 54 | Kedelai | Penyakit Embun Palsu (Downy mildew) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Pada permukaan bawah daun warna coklat tersebut terdapat tubuh buah miselium dan sporangium berupa benang-benang halus yang berwarna putih kecoklatan menyerupai bulu, oleh karena itu disebut embun bulu. |
| 55 | Kedelai | Penyakit Antraknosa | Ambigu | Review manual | Tidak ada pola gejala yang cukup jelas. | Gejala penyakit antraknosa pada kedelai dapat ditemukan pada bagian batang, tangkai daun, daun, dan polong. |
| 56 | KacangHijau | Penyakit Bercak Daun | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Pada varietas rentan menyebabkan gejala defoliasi prematur pengurangan ukuran polong dan biji (Grewal et al. 1980). |
| 57 | KacangHijau | Penyakit Layu | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Miselia berwarna putih akan ditemukan di sekitar gejala, dan pada gejala tingkat lanjut akan ditemukan sejumlah sclerosia pada akar (Jin Hyeuk 2017) dan daun dekat permukaan tanah (Gambar 25). |
| 58 | UbiKayu | Tanaman kerdil (stunt) | Bukan gejala | Exception: bukan gejala | Konteks patogen/lingkungan/pengendalian/metadata, bukan deskripsi gejala. | Tanaman tidak tumbuh secara normal, gejala ini umumnya terjadi pada tanaman yang mengalami infeksi awal oleh virus ini. Tanaman yang terinfeksi virus ini umumnya akan memiliki batang yang berukuran kecil |

## Pengendalian

| # | Tanaman | Penyakit | Kategori | Usulan | Alasan | Kutipan |
|---:|---|---|---|---|---|---|
| 1 | Padi | Penyakit Blas | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Beberapa strategi pengendalian telah disarikan Miah et al. |
| 2 | Padi | Penyakit Kerdil Rumput dan Kerdil Hampa | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Strategi pengendalian penyakit kerdil rumput dan kerdil hampa hampir sama dengan pengendalian penyakit tungro. |
| 3 | Kedelai | Penyakit Rebah Semai | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | rolfsii memiliki kisaran inang yang luas seperti famili leguminoceae, Cruciferaceae, Cucurbitaceae, tanaman pisang, jeruk, gandum, padi, tebu, bit, keladi, bahkan tanaman rempah (Sumartini, 2012). |
| 4 | Kedelai | Penyakit Rebah Semai | Duplikat/parafrase | Perluas keyword/rule lalu petakan | Tindakan sudah dikenal; tinggal perluas keyword/rule. | Hasil penelitian yang dilakukan oleh Fitria and Masnilah, (2020) pada beberapa varietas kedelai terhadap patogen S. |
| 5 | Kedelai | Penyakit Rebah Semai | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | rolfsii sebesar 20-85% (Marwan et al., 2017). |
| 6 | Kedelai | Penyakit Rebah Semai | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | rolfsii dengan melilitkan hifanya dengan membentuk haustorium pada hifa patogen kemudian menghasilkan enzim kitinase yang menyebabkan dinding sel patogen lisis dan rusak (Chamzurni et al., 2011). |
| 7 | Kedelai | Penyakit Rebah Kecambah | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Menurut Inayati and Yusnawan, (2017) pengendalian penyakit yang disebabkan oleh R. |
| 8 | Kedelai | Penyakit Layu Fusarium | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | oxysporum mengurangi intensitas patogen (Kaya et al., 2020). |
| 9 | Kedelai | Penyakit Karat Daun | Duplikat/parafrase | Perluas keyword/rule lalu petakan | Sebutan tindakan ada, tetapi kalimatnya fragmen/parafrase. | Hampir beberapa varietas unggul kedelai dapat dipatahkan ketahanannya oleh ras patogen yang baru. |
| 10 | Kedelai | Penyakit Embun Tepung (Powdery Mildew) | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | mampu menekan penyakit embun tepung pada tanaman pepaya (Firnando et al., 2020). |
| 11 | Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | Duplikat/parafrase | Perluas keyword/rule lalu petakan | Sebutan tindakan ada, tetapi kalimatnya fragmen/parafrase. | Siklus penyakit terjadi melalui penggunaan benih yang terinfeksi patogen C. |
| 12 | Kedelai | Penyakit Bercak Daun Mata Katak (Frogeye Leaf Spot) | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Menurut Inayati and Yusnawan, (2017) pengendalian C. |
| 13 | Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | syringae pada tanaman kedelai (Majid, 2016). |
| 14 | Kedelai | Penyakit Hawar Bakteri (Bacterial Blight) | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | syringae menjadi awal pengelolaan perkembangan penyakit. |
| 15 | KacangTanah | Penyakit Bercak Daun | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Berbagai upaya pengendalian telah banyak dilakukan untuk dapat mengurangi kerusakan akibat penyakit bercak daun. |
| 16 | KacangTanah | Penyakit Bercak Daun | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | Mikroorganisme ini biasanya berasal dari daerah perakaran atau endofit dan juga dari jaringan endofit daun. |
| 17 | KacangTanah | Penyakit Bercak Daun | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | Menurut Istifadah dan Sari (2017), Jamur T. |
| 18 | KacangTanah | Penyakit Bercak Daun | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | arachidicola mengalami resistensi dan lingkungan mendukung dalam perkembangan patogen |
| 19 | KacangTanah | Penyakit Bercak Daun | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | Karat daun merupakan penyakit tular udara yang penyebarannya melalui angin dan percikan air hujan. |
| 20 | KacangTanah | Penyakit Belang (Mottle) | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Pengujian ketahanan tanaman terhadap PStV pernah dilakukan terhadap 11.000 genotipe menunjukkan semua genotipe rentan terhadap PStV. |
| 21 | KacangTanah | Penyakit Belang (Mottle) | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | Pendekatan bioteknologi melalui rekayasa genetik untuk menghasilkan tanaman transgenik diharapkan mampu membantu upaya memperoleh tanaman kacang tanah yang terinfeksi PStV. |
| 22 | KacangTanah | Penyakit Belang (Mottle) | Duplikat/parafrase | Perluas keyword/rule lalu petakan | Sebutan tindakan ada, tetapi kalimatnya fragmen/parafrase. | Penggunaan tanaman dari benih yang sebelumnya terinfeksi PStV akan menyebabkan ledakan penyakit terutama saat populasi vektor tinggi. |
| 23 | KacangTanah | Penyakit Belang (Mottle) | Duplikat/parafrase | Perluas keyword/rule lalu petakan | Tindakan sudah dikenal; tinggal perluas keyword/rule. | Infeksi benih 2-5% dapat menyebabkan endemis penyakit saat panen. |
| 24 | KacangTanah | Penyakit Belang (Mottle) | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | Karena penularan dapat terjadi dengan sangat cepat sebelum serangga mati. |
| 25 | KacangTanah | Penyakit Belang (Mottle) | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Pertumbuhan tanaman yang tegar akan mampu mengurangi kehilangan hasil akibat infeksi PStV. |
| 26 | KacangTanah | Penyakit Belang (Mottle) | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | Infeksi PStV pada kacang tanah pada musim hujan dapat lebih ringan dibanding musim kemarau |
| 27 | KacangTanah | Penyakit Layu Bakteri | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | Beberapa mikroba telah diteliti dan dilaporkan mampu berperan sebagai agens pengendali hayati penyakit layu bakteri R. |
| 28 | KacangTanah | Penyakit Layu Bakteri | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | solanacearum pada tanaman aromatik nilam. |
| 29 | UbiJalar | layu fusarium | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | oxysporum (Scattolini, Hernandez and Gonzales, 2020). |
| 30 | Jagung | Penyakit Hawar Daun | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Aplikasi dilakukan sebanyak enam kali (pada umur 28, 35, 42, 49, 56, 63 hari setelah tanam) dengan cara penyemprotan ke bagian daun. |
| 31 | Jagung | Penyakit Bulai | Tindakan nyata | Tambah aksi kanonik | Tindakan nyata yang belum punya aksi kanonik. | Oleh karena itu, diperlukan pengendalian yang lebih ramah lingkungan. |
| 32 | Jagung | Penyakit Bulai | Duplikat/parafrase | Perluas keyword/rule lalu petakan | Tindakan sudah dikenal; tinggal perluas keyword/rule. | Tanaman yang diberikan perlakuan V1P2 yaitu kombinasi varietas Pioneer 27 dan isolat P. |
| 33 | Jagung | Penyakit Layu Stewart | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | Hasilnya menunjukkan bahwa perkembangan penyakit dapat terhambat dengan kemampuan penekanan penyakit sebesar 76.92% hingga 92.30%. |
| 34 | KacangTanah | Pengendalian umum KacangTanah | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | Menurut Istifadah dan Sari (2017), Jamur T. |
| 35 | KacangTanah | Pengendalian umum KacangTanah | Ambigu | Review manual | Tidak ada verba tindakan yang jelas. | arachidicola mengalami resistensi dan lingkungan mendukung dalam perkembangan patogen |
| 36 | KacangTanah | Pengendalian umum KacangTanah | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | Beberapa mikroba telah diteliti dan dilaporkan mampu berperan sebagai agens pengendali hayati penyakit layu bakteri R. |
| 37 | KacangTanah | Pengendalian umum KacangTanah | Bukan tindakan | Exception: bukan tindakan | Fragmen/konteks penelitian, bukan instruksi tindakan. | solanacearum pada tanaman aromatik nilam. |

## Keputusan

- `Duplikat/parafrase` diselesaikan dengan memperluas aturan yang sudah ada, bukan menambah kelas baru.
- `Butuh konsep baru` hanya untuk pola yang berulang dan benar-benar gejala.
- `Bukan gejala`/`Bukan tindakan` masuk exception list, bukan dipaksa menjadi 0.
- `Ambigu` perlu review manual sebelum dipetakan.
