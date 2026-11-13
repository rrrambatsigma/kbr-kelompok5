"""Generator ABox ontologi "Penyakit Tanaman Pangan Indonesia".

Membaca knowledge tables terkurasi DOC002 dan DOC005 untuk tujuh tanaman
pangan, lalu membangun ABox di atas TBox ``tbox.py``. Prinsip utama:

- hanya fakta yang punya dukungan sumber yang di-assert;
- teks sumber disimpan verbatim pada node BuktiSumber;
- gejala dan pengendalian dinormalisasi ke konsep kanonik;
- observasi lingkungan kuantitatif dipisahkan dari kondisi kualitatif;
- class dan individual tidak dicampur;
- tidak ada hash, UUID, atau ID database di local name.

Pemakaian dari root repo::

    python 04_ontology/build_ontology.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ONTO_DIR.parent
TABLE_DIR = PROJECT_ROOT / "03_knowledge_tables"
CURATED2 = TABLE_DIR / "curated" / "DOC002"
CURATED5 = TABLE_DIR / "curated" / "DOC005"
AUTO_DIR = TABLE_DIR / "auto"
META_PATH = PROJECT_ROOT / "01_knowledge_sources" / "source_metadata" / "manual_metadata.json"
DEFAULT_TTL = ONTO_DIR / "ontology.ttl"
DEFAULT_OWL = ONTO_DIR / "ontology.owl"
REPORT_PATH = ONTO_DIR / "extraction_report.json"

sys.path.insert(0, str(ONTO_DIR))

import tbox  # noqa: E402
from tbox import KBR, PROV, SKOS  # noqa: E402

PLANT_LOCAL: dict[str, str] = {
    "PLANT_001": "Padi",
    "PLANT_002": "Kedelai",
    "PLANT_018": "Kedelai",
    "PLANT_006": "Jagung",
    "PLANT_004": "UbiJalar",
    "PLANT_005": "UbiKayu",
    "PLANT_003": "KacangTanah",
    "PLANT_019": "KacangTanah",
    "PLANT_020": "KacangHijau",
}
PLANT_CLASS = {
    "Padi": "Serealia",
    "Jagung": "Serealia",
    "Kedelai": "Legum",
    "KacangTanah": "Legum",
    "KacangHijau": "Legum",
    "UbiKayu": "UmbiUmbian",
    "UbiJalar": "UmbiUmbian",
}
PLANT_LABELS = {
    "Padi": "Padi",
    "Kedelai": "Kedelai",
    "Jagung": "Jagung",
    "UbiJalar": "Ubi jalar",
    "UbiKayu": "Ubi kayu",
    "KacangTanah": "Kacang tanah",
    "KacangHijau": "Kacang hijau",
}
PLANT_ORDER = ["Padi", "Kedelai", "Jagung", "UbiJalar", "UbiKayu", "KacangTanah", "KacangHijau"]

TAXON_CLASS = {
    "jamur": "Jamur",
    "bakteri": "Bakteri",
    "virus": "Virus",
    "nematoda": "Nematoda",
    "oomycete": "Oomycete",
    "fitoplasma": "Fitoplasma",
}
TAXON_PRIORITY = {
    "oomycete": 6,
    "fitoplasma": 5,
    "virus": 4,
    "bakteri": 3,
    "nematoda": 2,
    "jamur": 1,
    "": 0,
}

PART_WORDS = {
    "daun": "Daun",
    "batang": "Batang",
    "akar": "Akar",
    "umbi": "Umbi",
    "buah": "Buah",
    "biji": "Biji",
    "malai": "Malai",
    "polong": "Polong",
    "pucuk": "Pucuk",
    "tunas": "Pucuk",
    "bunga": "Bunga",
}
PART_LABELS = {
    "Daun": "Daun",
    "Batang": "Batang",
    "Akar": "Akar",
    "Umbi": "Umbi",
    "Buah": "Buah",
    "Biji": "Biji",
    "Malai": "Malai",
    "Polong": "Polong",
    "Pucuk": "Pucuk",
    "Bunga": "Bunga",
}
PART_SUBCLASS = {
    "Daun": "GejalaDaun",
    "Batang": "GejalaBatang",
    "Akar": "GejalaAkar",
    "Umbi": "GejalaUmbi",
    "Buah": "GejalaBuah",
    "Biji": "GejalaBiji",
    "Malai": "GejalaMalai",
    "Polong": "GejalaPolong",
    "Pucuk": "GejalaPucuk",
    "Bunga": "GejalaBunga",
}
TABLE_PART = {"T5.1_DAUN": "daun", "T5.2_BATANG": "batang", "T5.3_AKAR": "akar"}

CANONICAL_SYMPTOMS: dict[str, dict[str, str]] = {
    "BercakDaun": {
        "label": "Bercak daun",
        "part": "Daun",
        "comment": "Konsep kanonik untuk gejala bercak atau noda pada daun.",
    },
    "HawarDaun": {
        "label": "Hawar daun",
        "part": "Daun",
        "comment": "Konsep kanonik untuk gejala hawar pada daun atau pelepah.",
    },
    "KlorosisDaun": {
        "label": "Klorosis daun",
        "part": "Daun",
        "comment": "Konsep kanonik untuk daun menguning atau klorotik.",
    },
    "MosaikDaun": {
        "label": "Mosaik daun",
        "part": "Daun",
        "comment": "Konsep kanonik untuk pola mosaik atau belang pada daun.",
    },
    "KerdilTanaman": {
        "label": "Kerdil tanaman",
        "part": "Batang",
        "comment": "Konsep kanonik untuk pertumbuhan tanaman yang kerdil.",
    },
    "LayuDaun": {
        "label": "Layu daun",
        "part": "Daun",
        "comment": "Konsep kanonik untuk gejala layu pada daun atau tanaman.",
    },
    "BusukBatang": {
        "label": "Busuk batang",
        "part": "Batang",
        "comment": "Konsep kanonik untuk pembusukan pada batang atau pelepah.",
    },
    "BusukAkar": {
        "label": "Busuk akar",
        "part": "Akar",
        "comment": "Konsep kanonik untuk pembusukan pada akar.",
    },
    "BusukBuah": {
        "label": "Busuk buah",
        "part": "Buah",
        "comment": "Konsep kanonik untuk pembusukan pada buah.",
    },
    "MalaiKosong": {
        "label": "Malai kosong",
        "part": "Malai",
        "comment": "Konsep kanonik untuk malai kosong atau hampa.",
    },
    "PucukMati": {
        "label": "Pucuk mati",
        "part": "Pucuk",
        "comment": "Konsep kanonik untuk pucuk atau tunas yang mati.",
    },
    "PertumbuhanTerhambat": {
        "label": "Pertumbuhan terhambat",
        "part": "Batang",
        "comment": "Konsep kanonik untuk pertumbuhan tanaman yang terhambat.",
    },
}

CANONICAL_SYMPTOM_RULES: list[tuple[str, tuple[tuple[str, ...], ...]]] = [
    ("BercakDaun", (("bercak", "noda"), ("daun",))),
    ("HawarDaun", (("hawar",), ("daun", "pelepah"))),
    ("KlorosisDaun", (("klorosis", "klorotik", "menguning", "kekuningan", "kuning"), ("daun",))),
    ("MosaikDaun", (("mosaik", "belang", "mottle"), ("daun",))),
    ("KerdilTanaman", (("kerdil", "dwarf"),)),
    ("LayuDaun", (("layu",),)),
    ("BusukBatang", (("busuk",), ("batang", "pelepah"))),
    ("BusukAkar", (("busuk",), ("akar",))),
    ("BusukBuah", (("busuk",), ("buah",))),
    ("MalaiKosong", (("malai",), ("kosong", "hampa"))),
    ("PucukMati", (("pucuk", "tunas"), ("mati", "nekrosis", "membusuk"))),
    ("PertumbuhanTerhambat", (("terhambat", "pertumbuhan tidak normal", "tidak tumbuh normal"),)),
]

CONTROL_ACTIONS: dict[str, dict] = {
    "PenggunaanVarietasTahan": {
        "label": "Penggunaan varietas tahan",
        "category": "PengendalianKulturTeknis",
        "keywords": ("varietas tahan", "varietas resisten", "varietas toleran", "ketahanan varietas", "menanam varietas"),
        "comment": "Tindakan kanonik penggunaan varietas yang dinyatakan tahan atau toleran.",
    },
    "PenggunaanBenihSehat": {
        "label": "Penggunaan benih sehat",
        "category": "PengendalianKulturTeknis",
        "keywords": ("benih sehat", "benih bebas", "benih bersertifikat", "benih unggul"),
        "comment": "Tindakan kanonik penggunaan benih sehat atau bersertifikat.",
    },
    "PerlakuanBenih": {
        "label": "Perlakuan benih",
        "category": "PengendalianKulturTeknis",
        "keywords": ("perlakuan benih", "seed treatment", "perendaman benih", "perlakuan air panas"),
        "comment": "Tindakan kanonik perlakuan benih sebelum tanam.",
    },
    "SanitasiLahan": {
        "label": "Sanitasi lahan",
        "category": "PengendalianKulturTeknis",
        "keywords": ("sanitasi", "membersihkan sisa", "pembersihan sisa", "eradikasi", "pemusnahan sisa", "membakar sisa"),
        "comment": "Tindakan kanonik sanitasi lahan dan sisa tanaman.",
    },
    "RotasiTanaman": {
        "label": "Rotasi tanaman",
        "category": "PengendalianKulturTeknis",
        "keywords": ("rotasi tanaman", "pergiliran tanaman", "rotasi"),
        "comment": "Tindakan kanonik pergiliran atau rotasi tanaman.",
    },
    "PengaturanJarakTanam": {
        "label": "Pengaturan jarak tanam",
        "category": "PengendalianKulturTeknis",
        "keywords": ("jarak tanam", "populasi tanaman", "kerapatan tanam"),
        "comment": "Tindakan kanonik pengaturan jarak atau kerapatan tanam.",
    },
    "PemupukanBerimbang": {
        "label": "Pemupukan berimbang",
        "category": "PengendalianKulturTeknis",
        "keywords": ("pemupukan", "pupuk", "unsur hara", "nutrisi tanaman"),
        "comment": "Tindakan kanonik pemupukan dan pengelolaan unsur hara.",
    },
    "PengaturanWaktuTanam": {
        "label": "Pengaturan waktu tanam",
        "category": "PengendalianKulturTeknis",
        "keywords": ("waktu tanam", "penanaman serempak", "menanam serempak", "serempak"),
        "comment": "Tindakan kanonik pengaturan waktu atau keserempakan tanam.",
    },
    "PengairanDanDrainase": {
        "label": "Pengairan dan drainase",
        "category": "PengendalianKulturTeknis",
        "keywords": ("pengairan", "irigasi", "drainase", "pengaturan air", "penyiraman"),
        "comment": "Tindakan kanonik pengaturan air, irigasi, dan drainase.",
    },
    "PengelolaanGulma": {
        "label": "Pengelolaan gulma",
        "category": "PengendalianKulturTeknis",
        "keywords": ("gulma", "penyiangan", "pengendalian gulma"),
        "comment": "Tindakan kanonik pengelolaan gulma.",
    },
    "PenggunaanMulsa": {
        "label": "Penggunaan mulsa",
        "category": "PengendalianKulturTeknis",
        "keywords": ("mulsa", "penutup tanah"),
        "comment": "Tindakan kanonik penggunaan mulsa atau penutup tanah.",
    },
    "PemangkasanTanaman": {
        "label": "Pemangkasan tanaman",
        "category": "PengendalianKulturTeknis",
        "keywords": ("pemangkasan", "pruning", "memangkas"),
        "comment": "Tindakan kanonik pemangkasan bagian tanaman.",
    },
    "PanenTepatWaktu": {
        "label": "Panen tepat waktu",
        "category": "PengendalianKulturTeknis",
        "keywords": ("panen tepat waktu", "waktu panen", "segera dipanen"),
        "comment": "Tindakan kanonik panen pada waktu yang dianjurkan.",
    },
    "PembersihanAlat": {
        "label": "Pembersihan alat",
        "category": "PengendalianKulturTeknis",
        "keywords": ("sterilisasi alat", "desinfeksi alat", "pembersihan alat"),
        "comment": "Tindakan kanonik pembersihan dan sterilisasi alat.",
    },
    "KarantinaTanaman": {
        "label": "Karantina tanaman",
        "category": "PengendalianKulturTeknis",
        "keywords": ("karantina", "isolasi tanaman"),
        "comment": "Tindakan kanonik karantina atau isolasi tanaman.",
    },
    "PengaturanKelembapan": {
        "label": "Pengaturan kelembapan",
        "category": "PengendalianKulturTeknis",
        "keywords": ("ventilasi", "sirkulasi udara", "kelembapan ruang", "pengaturan kelembapan"),
        "comment": "Tindakan kanonik pengaturan kelembapan dan sirkulasi udara.",
    },
    "PenerapanKulturTeknis": {
        "label": "Penerapan kultur teknis",
        "category": "PengendalianKulturTeknis",
        "keywords": ("kultur teknis", "teknik budidaya", "cara budidaya", "praktik budidaya"),
        "comment": "Tindakan kanonik penerapan kultur teknis secara umum.",
    },
    "PencabutanTanaman": {
        "label": "Pencabutan tanaman",
        "category": "PengendalianMekanis",
        "keywords": ("pencabutan", "mencabut", "dicabut"),
        "comment": "Tindakan kanonik pencabutan tanaman terserang.",
    },
    "PengumpulanDanPemusnahan": {
        "label": "Pengumpulan dan pemusnahan",
        "category": "PengendalianMekanis",
        "keywords": ("pengumpulan", "pemusnahan", "dikumpulkan", "dibakar", "dibenamkan"),
        "comment": "Tindakan kanonik pengumpulan dan pemusnahan bagian tanaman terserang.",
    },
    "PenggunaanPerangkap": {
        "label": "Penggunaan perangkap",
        "category": "PengendalianMekanis",
        "keywords": ("perangkap", "trap", "feromon"),
        "comment": "Tindakan kanonik penggunaan perangkap.",
    },
    "PenerapanPengendalianMekanis": {
        "label": "Penerapan pengendalian mekanis",
        "category": "PengendalianMekanis",
        "keywords": ("pengendalian mekanis", "mekanis"),
        "comment": "Tindakan kanonik penerapan pengendalian mekanis secara umum.",
    },
    "PenggunaanAgensHayati": {
        "label": "Penggunaan agens hayati",
        "category": "PengendalianBiologis",
        "keywords": ("agens hayati", "musuh alami", "predator", "parasitoid", "mikroorganisme antagonis", "pengendalian hayati", "pengendalian biologis"),
        "comment": "Tindakan kanonik penggunaan agens hayati.",
    },
    "PenggunaanTrichoderma": {
        "label": "Penggunaan Trichoderma",
        "category": "PengendalianBiologis",
        "keywords": ("trichoderma",),
        "comment": "Tindakan kanonik penggunaan Trichoderma.",
    },
    "PenggunaanBacillus": {
        "label": "Penggunaan Bacillus",
        "category": "PengendalianBiologis",
        "keywords": ("bacillus",),
        "comment": "Tindakan kanonik penggunaan Bacillus.",
    },
    "PenggunaanPseudomonas": {
        "label": "Penggunaan Pseudomonas",
        "category": "PengendalianBiologis",
        "keywords": ("pseudomonas",),
        "comment": "Tindakan kanonik penggunaan Pseudomonas.",
    },
    "PenggunaanBeauveria": {
        "label": "Penggunaan Beauveria",
        "category": "PengendalianBiologis",
        "keywords": ("beauveria",),
        "comment": "Tindakan kanonik penggunaan Beauveria.",
    },
    "PenggunaanMetarhizium": {
        "label": "Penggunaan Metarhizium",
        "category": "PengendalianBiologis",
        "keywords": ("metarhizium",),
        "comment": "Tindakan kanonik penggunaan Metarhizium.",
    },
    "PenggunaanBiopestisida": {
        "label": "Penggunaan biopestisida",
        "category": "PengendalianBiologis",
        "keywords": ("biopestisida", "pestisida hayati", "biofungisida"),
        "comment": "Tindakan kanonik penggunaan biopestisida.",
    },
    "PenggunaanEkstrakTanaman": {
        "label": "Penggunaan ekstrak tanaman",
        "category": "PengendalianBiologis",
        "keywords": ("ekstrak",),
        "comment": "Tindakan kanonik penggunaan ekstrak tanaman.",
    },
    "PenerapanPengendalianBiologis": {
        "label": "Penerapan pengendalian biologis",
        "category": "PengendalianBiologis",
        "keywords": ("pengendalian biologis", "pengendalian hayati"),
        "comment": "Tindakan kanonik penerapan pengendalian biologis secara umum.",
    },
    "PenggunaanFungisida": {
        "label": "Penggunaan fungisida",
        "category": "PengendalianKimiawi",
        "keywords": ("fungisida", "mankozeb", "benomyl", "heksakonazol", "klorotalonil", "difenokonazol", "propikonazol", "tebuconazol"),
        "comment": "Tindakan kanonik penggunaan fungisida.",
    },
    "PenggunaanBakterisida": {
        "label": "Penggunaan bakterisida",
        "category": "PengendalianKimiawi",
        "keywords": ("bakterisida", "streptomisin", "antibiotik", "tembaga", "kupri"),
        "comment": "Tindakan kanonik penggunaan bakterisida.",
    },
    "PenggunaanInsektisida": {
        "label": "Penggunaan insektisida",
        "category": "PengendalianKimiawi",
        "keywords": ("insektisida", "deltametrin", "imidakloprid", "abamektin"),
        "comment": "Tindakan kanonik penggunaan insektisida.",
    },
    "PenggunaanHerbisida": {
        "label": "Penggunaan herbisida",
        "category": "PengendalianKimiawi",
        "keywords": ("herbisida", "glifosat", "paraquat"),
        "comment": "Tindakan kanonik penggunaan herbisida.",
    },
    "PenggunaanPestisidaNabati": {
        "label": "Penggunaan pestisida nabati",
        "category": "PengendalianKimiawi",
        "keywords": ("pestisida nabati", "fungisida nabati", "insektisida nabati", "pestisida botanis"),
        "comment": "Tindakan kanonik penggunaan pestisida nabati.",
    },
    "PerlakuanKimiaTanah": {
        "label": "Perlakuan kimia tanah",
        "category": "PengendalianKimiawi",
        "keywords": ("fumigasi", "metam sodium", "kloropikrin"),
        "comment": "Tindakan kanonik perlakuan kimia tanah.",
    },
    "PenerapanPengendalianKimiawi": {
        "label": "Penerapan pengendalian kimiawi",
        "category": "PengendalianKimiawi",
        "keywords": ("pengendalian kimiawi", "aplikasi kimia", "bahan aktif"),
        "comment": "Tindakan kanonik penerapan pengendalian kimiawi secara umum.",
    },
    "PerlakuanAirPanas": {
        "label": "Perlakuan air panas",
        "category": "PengendalianFisik",
        "keywords": ("air panas", "hot water", "perlakuan panas"),
        "comment": "Tindakan kanonik perlakuan air panas.",
    },
    "SolarisasiTanah": {
        "label": "Solarisasi tanah",
        "category": "PengendalianFisik",
        "keywords": ("solarisasi", "solarization", "mulsa plastik transparan"),
        "comment": "Tindakan kanonik solarisasi tanah.",
    },
    "PengaturanSuhuPenyimpanan": {
        "label": "Pengaturan suhu penyimpanan",
        "category": "PengendalianFisik",
        "keywords": ("penyimpanan dingin", "suhu rendah", "pendinginan", "cold storage"),
        "comment": "Tindakan kanonik pengaturan suhu penyimpanan.",
    },
    "PerlakuanRadiasi": {
        "label": "Perlakuan radiasi",
        "category": "PengendalianFisik",
        "keywords": ("radiasi", "ultraviolet", "sinar gamma", "iradiasi"),
        "comment": "Tindakan kanonik perlakuan radiasi.",
    },
    "PenerapanPengendalianFisik": {
        "label": "Penerapan pengendalian fisik",
        "category": "PengendalianFisik",
        "keywords": ("pengendalian fisik", "perlakuan fisik"),
        "comment": "Tindakan kanonik penerapan pengendalian fisik secara umum.",
    },
    "PengendalianHamaTerpadu": {
        "label": "Pengendalian hama terpadu",
        "category": "PengendalianTerpadu",
        "keywords": ("pengendalian hama terpadu", "pht", "integrated pest management", "ipm"),
        "comment": "Tindakan kanonik pengendalian hama terpadu.",
    },
    "PengelolaanTerpadu": {
        "label": "Pengelolaan terpadu",
        "category": "PengendalianTerpadu",
        "keywords": ("pengelolaan terpadu", "pengendalian terpadu", "integrated management"),
        "comment": "Tindakan kanonik pengelolaan terpadu.",
    },
}

CATEGORY_ACTION_MAP: dict[str, list[str]] = {
    "varietas tahan": ["PenggunaanVarietasTahan"],
    "benih sehat": ["PenggunaanBenihSehat"],
    "perlakuan benih": ["PerlakuanBenih"],
    "sanitasi": ["SanitasiLahan"],
    "rotasi tanaman": ["RotasiTanaman"],
    "sanitasi dan rotasi": ["SanitasiLahan", "RotasiTanaman"],
    "kultur teknis": ["PenerapanKulturTeknis"],
    "fungisida nabati": ["PenggunaanPestisidaNabati"],
    "fungisida sintetik": ["PenggunaanFungisida"],
    "pestisida nabati": ["PenggunaanPestisidaNabati"],
    "agens hayati": ["PenggunaanAgensHayati"],
}

PHASE_DEFS: dict[str, dict[str, str]] = {
    "FaseMatangSusu": {"label": "Fase matang susu", "class": "FasePemasakan"},
    "FaseVegetatifUmum": {"label": "Fase vegetatif", "class": "FaseVegetatif"},
    "FaseGeneratifUmum": {"label": "Fase generatif", "class": "FaseGeneratif"},
    "FasePembibitanTanaman": {"label": "Fase pembibitan", "class": "FasePembibitan"},
    "FaseAnakanTanaman": {"label": "Fase anakan", "class": "FaseAnakan"},
    "FaseMatang": {"label": "Fase matang", "class": "FasePemasakan"},
}
PHASE_RE = re.compile(
    r"\bfase\s+(matang\s+susu|vegetatif|generatif|pembibitan|anakan|matang)\b",
    re.I,
)
PHASE_KEY = {
    "matang susu": "FaseMatangSusu",
    "vegetatif": "FaseVegetatifUmum",
    "generatif": "FaseGeneratifUmum",
    "pembibitan": "FasePembibitanTanaman",
    "anakan": "FaseAnakanTanaman",
    "matang": "FaseMatang",
}

ENV_FACTORS: dict[str, dict] = {
    "Suhu": {"terms": ("suhu",), "class": "Suhu", "unit": "°C"},
    "Kelembapan": {"terms": ("kelembapan", "kelembaban"), "class": "KelembapanUdara", "unit": "%"},
    "CurahHujan": {"terms": ("curah hujan",), "class": "CurahHujan", "unit": "mm"},
}
QUALITATIVE_RULES: list[tuple[str, str, str, re.Pattern[str]]] = [
    ("KondisiKelembapanTinggi", "KelembapanUdara", "Kelembapan tinggi", re.compile(r"kelembap(?:a|e)n\s+(?:yang\s+)?tinggi", re.I)),
    ("KondisiKelembapanRendah", "KelembapanUdara", "Kelembapan rendah", re.compile(r"kelembap(?:a|e)n\s+(?:yang\s+)?rendah", re.I)),
    ("KondisiMusimHujan", "Musim", "Musim hujan", re.compile(r"musim\s+hujan", re.I)),
    ("KondisiMusimKemarau", "Musim", "Musim kemarau", re.compile(r"musim\s+kemarau", re.I)),
    ("KondisiCurahHujanTinggi", "CurahHujan", "Curah hujan tinggi", re.compile(r"curah\s+hujan\s+(?:yang\s+)?tinggi", re.I)),
    ("KondisiCurahHujanRendah", "CurahHujan", "Curah hujan rendah", re.compile(r"curah\s+hujan\s+(?:yang\s+)?rendah", re.I)),
    ("KondisiSuhuTinggi", "Suhu", "Suhu tinggi", re.compile(r"suhu\s+(?:yang\s+)?tinggi", re.I)),
    ("KondisiSuhuRendah", "Suhu", "Suhu rendah", re.compile(r"suhu\s+(?:yang\s+)?rendah", re.I)),
]

# Kompatibilitas pipeline enrichment lama: pola kondisi kualitatif tanpa label.
ENV_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (local, cls, pattern) for local, cls, _label, pattern in QUALITATIVE_RULES
]

VARIETY_STOPWORDS = {
    "yang", "dan", "atau", "pada", "untuk", "dengan", "adalah", "dapat", "akan",
    "lebih", "dari", "ini", "itu", "dalam", "sebagai", "tanaman", "kedelai",
    "padi", "jagung", "ubi", "kacang", "hijau", "tanah", "kayu", "jalar",
    "unggul", "lokal", "hanya", "setiap", "beberapa", "lainnya", "lain",
    "baru", "tersebut", "terkait", "mampu", "memiliki", "terhadap", "penyakit",
    "tahan", "rentan", "peka", "genjah", "serta", "yaitu", "yakni", "antara",
    "hasil", "penelitian", "jenis", "secara", "umum", "disebut", "termasuk",
    "dikenal", "bernama", "misalnya", "contoh", "seperti", "menggunakan",
    "dipakai", "menanam", "penanaman", "agak", "sangat", "cukup", "paling",
    "karat", "daun", "bulai", "hawar", "layu", "bakteri", "virus", "jamur",
    "busuk", "kerdil", "mosaik", "embun", "bercak", "antraknosa",
    "superelongasi", "sapu", "setan", "titik", "tunas", "pangkal", "pelepah",
    "blas", "tungro", "kudis", "patogen", "ras", "galur", "isolat", "vektor",
    "hama", "inang", "balitkabi", "puslitbangtan", "menurut", "juga", "bisa",
    "harus", "perlu", "banyak", "murah", "mudah", "aman", "cepat", "baik",
    "tinggi", "rendah", "sedang", "normal", "optimum", "ideal", "varietas",
    "variety", "toleran", "resistan", "resisten", "ketahanan", "keparahan",
    "infeksi", "serangan", "kejadian", "gejala", "sumber", "cara", "salah",
    "satu", "dua", "tiga", "diketahui", "dilaporkan", "dianjurkan",
    "diperoleh", "ditemukan", "diberikan", "diberi", "boleh", "sekitar",
    "sebelum", "sesudah", "saat", "ketika", "apabila", "bila", "jika",
    "karena", "sehingga", "namun", "tetapi", "sedangkan", "telah", "sudah",
    "masih", "belum", "tanpa", "oleh", "ke", "di", "kepada", "bagi", "buat",
}
RESIST_MARKERS = re.compile(r"\b(tahan|resistan|resisten|toleran)\b", re.I)
VULN_MARKERS = re.compile(r"\b(rentan|peka)\b", re.I)
VARIETY_PRIMARY_RE = re.compile(r"\bvarietas\b", re.I)
VARIETY_FALLBACK_RE = re.compile(r"\badalah\s+([A-Z][A-Za-z0-9\-']*(?:\s+[A-Z0-9][A-Za-z0-9\-']*){0,5})", re.UNICODE)


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def pascal(text: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in re.split(r"[^0-9A-Za-z]+", text or "") if w)


def significant_words(text: str, limit: int = 5) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", text or "") if w.lower() not in VARIETY_STOPWORDS]
    return " ".join(words[:limit])


def unique_local(prefix: str, text: str, builder: "Builder") -> str:
    base = prefix + (pascal(significant_words(text)) or "TanpaTeks")
    local = base
    counter = 2
    while local in builder.used_locals:
        local = f"{base}{counter}"
        counter += 1
    return local


def text_parts(text: str) -> list[str]:
    low = (text or "").lower()
    found: list[str] = []
    for word, part in PART_WORDS.items():
        if re.search(r"\b" + re.escape(word), low) and part not in found:
            found.append(part)
    return found


def subsection_parts(subsection: str) -> list[str]:
    low = norm(subsection)
    found: list[str] = []
    for word, part in PART_WORDS.items():
        if word in low and part not in found:
            found.append(part)
    if "umbi" in low and "Akar" not in found:
        found.insert(0, "Akar")
    return found


def disease_qualifier(entry: dict[str, str]) -> str:
    parts = subsection_parts(entry.get("subsection") or "")
    if parts:
        return "".join(parts)
    en = pascal(entry.get("name_en") or "")
    if en:
        return en
    sec = pascal(entry.get("section") or "")
    return sec or "Umum"


DISEASE_LOCAL_ALIASES = {
    "ANTRAKNOSAKedelai": "PenyakitAntraknosaKedelai",
    "BERCAKDAUNKacangTanah": "PenyakitBercakDaunKacangTanah",
    "KARATKedelai": "PenyakitKaratDaunKedelai",
    "EMBUNBULUKedelai": "PenyakitEmbunPalsuDownyMildewKedelai",
    "BERCAKDAUNKacangHijau": "PenyakitBercakDaunKacangHijau",
    "EMBUNTEPUNGKacangHijau": "PenyakitEmbunTepungKacangHijau",
    "KARATKacangTanah": "PenyakitKaratDaunKacangTanah",
    "LAYUKacangHijau": "PenyakitLayuKacangHijau",
}

DISEASE_LABEL_ALIASES = {
    "ANTRAKNOSAKedelai": "Penyakit Antraknosa",
    "BERCAKDAUNKacangTanah": "Penyakit Bercak Daun",
    "KARATKedelai": "Penyakit Karat Daun",
    "EMBUNBULUKedelai": "Penyakit Embun Palsu (Downy mildew)",
    "BERCAKDAUNKacangHijau": "Penyakit Bercak Daun",
    "EMBUNTEPUNGKacangHijau": "Penyakit Embun Tepung",
    "KARATKacangTanah": "Penyakit Karat Daun",
    "LAYUKacangHijau": "Penyakit Layu",
}


def match_canonical_symptoms(text: str) -> list[str]:
    low = norm(text)
    found: list[str] = []
    for local, groups in CANONICAL_SYMPTOM_RULES:
        if all(any(term in low for term in group) for group in groups):
            found.append(local)
    return found


def match_control_actions(text: str, category: str, source: str) -> list[str]:
    low = norm(text)
    found: list[str] = []
    for local, spec in CONTROL_ACTIONS.items():
        if any(keyword in low for keyword in spec["keywords"]):
            found.append(local)
    if source == "DOC005" and category:
        fallback = CATEGORY_ACTION_MAP.get(category.strip().lower(), [])
        if not any(local in found for local in fallback):
            for local in fallback:
                if local not in found:
                    found.append(local)
    general = {name for name in found if name.startswith("Penerapan")}
    if general:
        specific = [name for name in found if not name.startswith("Penerapan")]
        if specific:
            found = specific
    return found


def normalize_quote(text: str | None) -> str:
    value = (text or "").replace("\r", " ").replace("\n", " ")
    value = value.replace("\ufffdC", "°C").replace("\ufffd C", "°C")
    value = value.replace("\u2013", "-").replace("\u2014", "-").replace("\u00ad", "")
    return re.sub(r"\s+", " ", value).strip()


def is_complete_sentence(text: str) -> bool:
    value = normalize_quote(text)
    if len(re.sub(r"[^0-9A-Za-z]", "", value)) < 35:
        return False
    if not re.match(r"^[\"“(]?[A-Z0-9]", value):
        return False
    if not re.search(r"[.!?]$", value):
        return False
    if re.search(r"\b(et al\.|dkk\.)\s*$", value, re.I):
        return False
    if value.count("(") != value.count(")"):
        return False
    if re.search(r"[,;:\-–—/]\s*$", value):
        return False
    return True


def decimal_value(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def fmt_number(value: Decimal | None) -> str:
    if value is None:
        return ""
    value = value.normalize()
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def value_slug(obs: dict) -> str:
    unit = obs["unit"].replace("°C", "Celsius").replace("%", "Persen").replace("mm", "Milimeter")
    if obs.get("min") is not None and obs.get("max") is not None:
        low = fmt_number(obs["min"]).replace(".", "Koma")
        high = fmt_number(obs["max"]).replace(".", "Koma")
        return f"{low}Sampai{high}{unit}"
    op = pascal(obs.get("operator") or "")
    return f"{op}{fmt_number(obs.get('single')).replace('.', 'Koma')}{unit}"


def _env_unit_compatible(factor: str, unit: str) -> bool:
    if not unit:
        return factor == "Suhu"
    if factor == "Suhu":
        return unit in ("°C", "C")
    if factor == "Kelembapan":
        return unit == "%"
    if factor == "CurahHujan":
        return unit == "mm"
    return False


def _env_window(source: str, start: int, factor: str) -> str:
    window = source[start : start + 110]
    lower = window.lower()
    for other, cfg in ENV_FACTORS.items():
        if other == factor:
            continue
        indexes = [lower.find(term) for term in cfg["terms"]]
        indexes = [index for index in indexes if index > 0]
        if indexes:
            window = window[: min(indexes)]
    return re.split(r";|\.\s+(?=[A-Z])", window)[0]


def parse_env_observations(text: str) -> list[dict]:
    source = normalize_quote(text)
    lower = source.lower()
    results: list[dict] = []
    seen: set[tuple] = set()
    for factor, cfg in ENV_FACTORS.items():
        for term in cfg["terms"]:
            for match in re.finditer(r"\b" + re.escape(term) + r"\b", lower):
                window = _env_window(source, match.end(), factor)
                low_window = window.lower()
                actual_class = cfg["class"]
                if factor == "Kelembapan" and ("tanah" in low_window or "lahan" in low_window):
                    actual_class = "KelembapanTanah"
                range_match = re.search(
                    r"(\d+(?:[.,]\d+)?)\s*(°\s*C|%|mm)?\s*(?:-|sampai|hingga|s/d)\s*(\d+(?:[.,]\d+)?)\s*(°\s*C|%|mm)?",
                    window,
                    re.I,
                )
                if range_match:
                    min_value = decimal_value(range_match.group(1))
                    max_value = decimal_value(range_match.group(3))
                    unit = (range_match.group(4) or range_match.group(2) or cfg["unit"]).replace(" ", "")
                    if unit.upper() in ("°C", "C"):
                        unit = "°C"
                    if not _env_unit_compatible(factor, unit):
                        continue
                    if min_value is not None and max_value is not None and min_value <= max_value:
                        key = (factor, actual_class, min_value, max_value, unit)
                        if key not in seen:
                            seen.add(key)
                            results.append(
                                {
                                    "factor": factor,
                                    "class": actual_class,
                                    "min": min_value,
                                    "max": max_value,
                                    "single": None,
                                    "operator": "range",
                                    "unit": unit,
                                    "condition": "Optimum" if re.search(r"optimum|optimal", low_window) else "",
                                    "window": window,
                                }
                            )
                    continue
                single_match = re.search(
                    r"(di\s*bawah|kurang\s*dari|<|lebih\s*dari|di\s*atas|>|sekitar|optimum|optimal|mencapai)?\s*(\d+(?:[.,]\d+)?)\s*(°\s*C|%|mm)?",
                    window,
                    re.I,
                )
                if not single_match:
                    continue
                comparator = (single_match.group(1) or "").strip().lower()
                value = decimal_value(single_match.group(2))
                unit = (single_match.group(3) or cfg["unit"]).replace(" ", "")
                if unit.upper() in ("°C", "C"):
                    unit = "°C"
                if value is None or not _env_unit_compatible(factor, unit):
                    continue
                if factor != "Suhu" and not single_match.group(3) and not comparator:
                    continue
                operator = "sama dengan"
                if comparator in ("di bawah", "kurang dari", "<"):
                    operator = "<"
                elif comparator in ("lebih dari", "di atas", ">"):
                    operator = ">"
                elif comparator == "sekitar":
                    operator = "sekitar"
                elif comparator in ("optimum", "optimal"):
                    operator = "optimum"
                key = (factor, actual_class, None, None, value, operator, unit)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "factor": factor,
                        "class": actual_class,
                        "min": None,
                        "max": None,
                        "single": value,
                        "operator": operator,
                        "unit": unit,
                        "condition": "Optimum" if operator == "optimum" else "",
                        "window": window,
                    }
                )
    return results


def qualitative_matches(text: str) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for local, cls, label, pattern in QUALITATIVE_RULES:
        if pattern.search(text or "") and local not in [item[0] for item in found]:
            found.append((local, cls, label))
    return found


def extract_phases(text: str) -> list[str]:
    found: list[str] = []
    for match in PHASE_RE.finditer(text or ""):
        key = re.sub(r"\s+", " ", match.group(1).lower())
        local = PHASE_KEY.get(key)
        if local and local not in found:
            found.append(local)
    return found


def _strip_variety_tail(part: str) -> str:
    part = re.split(r"\s*\(", part)[0]
    part = re.sub(r"\s+\d+(?:\.\d+)?\s*%.*$", "", part)
    return part.strip().strip(",;:()\"'")


def _valid_variety(name: str) -> bool:
    if not name or len(name) < 2:
        return False
    for tok in name.split():
        if tok.isdigit():
            continue
        if len(tok) < 2:
            return False
        if tok.isupper():
            return False
        if re.search(r"[A-Z].*[A-Z]", tok):
            return False
    return True


def _strip_plant_prefix(name: str) -> str:
    tokens = name.split()
    plant_words = {"jagung", "kedelai", "padi", "kacang", "hijau", "tanah", "ubi", "kayu", "jalar"}
    while tokens and tokens[0].lower() in plant_words and len(tokens) > 1:
        tokens = tokens[1:]
    return " ".join(tokens)


def _proper_run(part: str) -> str:
    part = _strip_variety_tail(part)
    tokens: list[str] = []
    started = False
    for raw in part.split():
        tok = raw.strip(",;:()\"'")
        if not tok:
            continue
        if not started:
            if not re.match(r"^[A-Z]", tok):
                continue
            low = tok.lower()
            if low in VARIETY_STOPWORDS and low not in {"padi", "kedelai", "jagung", "ubi", "kacang", "hijau", "tanah", "kayu", "jalar"}:
                continue
            started = True
            tokens.append(tok)
            continue
        if re.match(r"^\d+$", tok):
            tokens.append(tok)
        elif re.match(r"^[A-Z][A-Za-z0-9\-']*$", tok):
            if tok.lower() in {"yang", "dan", "atau", "adalah", "dengan", "untuk", "pada"}:
                break
            tokens.append(tok)
        else:
            break
        if len(tokens) >= 6:
            break
    return " ".join(tokens)


def extract_varieties(text: str) -> list[str]:
    found: list[str] = []

    def push(name: str) -> None:
        name = _strip_plant_prefix(name)
        if not _valid_variety(name) or name in found or len(found) >= 6:
            return
        found.append(name)

    for match in VARIETY_PRIMARY_RE.finditer(text):
        rest = text[match.end():]
        window = re.split(r"[.\n]", rest)[0][:200]
        for part in re.split(r",\s*|\s+dan\s+|\s+atau\s+|\s+sedangkan\s+", window):
            push(_proper_run(part))
    if not found:
        for match in VARIETY_FALLBACK_RE.finditer(text):
            push(_proper_run(match.group(1)))
    return found


class Builder:
    def __init__(self) -> None:
        self.graph = Graph()
        self.errors: list[str] = []
        self.used_locals: set[str] = set()

    def individual(self, local: str, *classes: str) -> URIRef:
        if local in self.used_locals:
            self.errors.append(f"local name individu duplikat: {local}")
        self.used_locals.add(local)
        uri = KBR[local]
        self.graph.add((uri, RDF.type, OWL.NamedIndividual))
        for cls in classes:
            self.graph.add((uri, RDF.type, KBR[cls]))
        return uri

    def ensure_individual(self, local: str, *classes: str) -> URIRef:
        uri = KBR[local]
        if local not in self.used_locals:
            self.used_locals.add(local)
            self.graph.add((uri, RDF.type, OWL.NamedIndividual))
        for cls in classes:
            self.graph.add((uri, RDF.type, KBR[cls]))
        return uri

    def label(self, uri: URIRef, text: str | None) -> None:
        if text and text.strip():
            self.graph.add((uri, RDFS.label, Literal(text.strip(), lang="id")))
            self.graph.add((uri, SKOS.prefLabel, Literal(text.strip(), lang="id")))

    def alt(self, uri: URIRef, text: str | None) -> None:
        if text and text.strip():
            self.graph.add((uri, SKOS.altLabel, Literal(text.strip(), lang="id")))

    def comment(self, uri: URIRef, text: str | None) -> None:
        if text and text.strip():
            self.graph.add((uri, RDFS.comment, Literal(text.strip(), lang="id")))

    def lang(self, uri: URIRef, prop: str, value: str | None) -> None:
        if value and value.strip():
            self.graph.add((uri, KBR[prop], Literal(value.strip(), lang="id")))

    def plain(self, uri: URIRef, prop: str, value: str | None) -> None:
        if value and str(value).strip():
            self.graph.add((uri, KBR[prop], Literal(str(value).strip())))

    def decimal(self, uri: URIRef, prop: str, value: Decimal | None) -> None:
        if value is not None:
            self.graph.add((uri, KBR[prop], Literal(value, datatype=XSD.decimal)))

    def integer(self, uri: URIRef, prop: str, value: int | str | None) -> None:
        if value is None or str(value).strip() == "":
            return
        try:
            self.graph.add((uri, KBR[prop], Literal(int(value), datatype=XSD.integer)))
        except (TypeError, ValueError):
            self.errors.append(f"nilai bukan integer untuk {prop}: {value!r}")

    def link(self, uri: URIRef, prop: str, target: URIRef) -> None:
        self.graph.add((uri, KBR[prop], target))
        spec = tbox.OBJECT_PROPERTIES.get(prop, {})
        inverse = spec.get("inverse")
        if inverse:
            self.graph.add((target, KBR[inverse], uri))
        if prop in ("dikendalikanDengan", "pengendalianUmum", "merekomendasikanPengendalian"):
            self.graph.add((uri, KBR["berkaitanPengendalian"], target))

    def ext_link(self, uri: URIRef, prop: URIRef, target: URIRef) -> None:
        self.graph.add((uri, prop, target))


def plant_rows_merged() -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for rows in (read_csv(AUTO_DIR / "plants.csv"), read_csv(CURATED5 / "plants.csv")):
        for row in rows:
            pid = row["plant_id"].strip()
            if pid not in PLANT_LOCAL:
                continue
            local = PLANT_LOCAL[pid]
            if local not in merged:
                merged[local] = {
                    "local": local,
                    "label": (row.get("plant_name_id") or PLANT_LABELS[local]).strip(),
                    "scientific_name": (row.get("scientific_name") or "").strip(),
                    "plant_ids": [pid],
                }
            else:
                if not merged[local]["scientific_name"] and (row.get("scientific_name") or "").strip():
                    merged[local]["scientific_name"] = row["scientific_name"].strip()
                merged[local]["plant_ids"].append(pid)
    return [merged[k] for k in PLANT_ORDER if k in merged]


def penyakit_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []

    def add(row: dict[str, str], source: str) -> None:
        pid = row["plant_id"].strip()
        if pid not in PLANT_LOCAL:
            return
        nama = (row.get("disease_name_verbatim") or "").strip()
        if not nama:
            return
        plant_local = PLANT_LOCAL[pid]
        entries.append(
            {
                "disease_id": row["disease_id"].strip(),
                "plant_local": plant_local,
                "plant_id": pid,
                "nama": nama,
                "name_en": (row.get("disease_name_en_verbatim") or row.get("name_en_verbatim") or "").strip(),
                "base": pascal(nama + plant_local),
                "section": (row.get("section") or row.get("chapter_title") or "").strip(),
                "subsection": (row.get("subsection") or "").strip(),
                "page_start": (row.get("page_start") or "").strip(),
                "page_end": (row.get("page_end") or "").strip(),
                "chunk_id": (row.get("chunk_id") or "").strip(),
                "evidence_chunk_ids": (row.get("evidence_chunk_ids") or "").strip(),
                "source_block_id": (row.get("source_block_id") or "").strip(),
                "source_block_ids": (row.get("source_block_ids") or "").strip(),
                "reference_verbatim": (row.get("reference_verbatim") or "").strip(),
                "source": source,
            }
        )

    for row in read_csv(CURATED2 / "diseases.csv"):
        add(row, "DOC002")
    for row in read_csv(CURATED5 / "diseases.csv"):
        add(row, "DOC005")

    counts = Counter(entry["base"] for entry in entries)
    for entry in entries:
        if counts[entry["base"]] == 1:
            entry["local"] = entry["base"]
        else:
            entry["local"] = entry["base"] + disease_qualifier(entry)

    for entry in entries:
        canonical = DISEASE_LOCAL_ALIASES.get(entry["local"])
        if canonical:
            entry["legacy_local"] = entry["local"]
            entry["local"] = canonical
            entry["label"] = DISEASE_LABEL_ALIASES.get(
                entry["legacy_local"], entry["nama"]
            )
        else:
            entry["label"] = entry["nama"]
    return entries


def unique_diseases(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for entry in entries:
        current = unique.get(entry["local"])
        if current is None or (
            current.get("legacy_local") and not entry.get("legacy_local")
        ):
            unique[entry["local"]] = entry
    return list(unique.values())


def symptom_records(entries: list[dict[str, str]]) -> tuple[list[dict], list[str]]:
    by_norm: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        by_norm.setdefault(norm(entry["nama"]), []).append(entry)
    ids = {e["disease_id"] for e in entries}
    records: list[dict] = []
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    def add(record: dict) -> None:
        key = (record["disease_id"], record["text"], record.get("chunk_id", ""))
        if key not in seen:
            seen.add(key)
            record["kind"] = "gejala"
            records.append(record)

    for row in read_csv(CURATED2 / "symptoms.csv"):
        did = row["disease_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if did in ids and text:
            add(
                {
                    "disease_id": did,
                    "text": text,
                    "source": "DOC002",
                    "source_id": (row.get("symptom_id") or "").strip(),
                    "chunk_id": (row.get("chunk_id") or "").strip(),
                    "page": (row.get("page_start") or "").strip(),
                    "char_start": (row.get("char_start") or "").strip(),
                    "char_end": (row.get("char_end") or "").strip(),
                }
            )
    for row in read_csv(CURATED5 / "symptoms.csv"):
        did = row["disease_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if did in ids and text:
            add(
                {
                    "disease_id": did,
                    "text": text,
                    "source": "DOC005",
                    "source_id": (row.get("symptom_id") or "").strip(),
                    "chunk_id": (row.get("chunk_id") or "").strip(),
                    "page": (row.get("page_start") or "").strip(),
                    "char_start": (row.get("char_start") or "").strip(),
                    "char_end": (row.get("char_end") or "").strip(),
                }
            )
    for row in read_csv(CURATED2 / "ubi_kayu_tabel_5.csv"):
        nama = (row.get("disease_name") or "").strip()
        text = (row.get("symptom_text") or "").strip()
        if not nama or not text:
            continue
        candidates = by_norm.get(norm(nama), [])
        disease_id = ""
        if len(candidates) == 1:
            disease_id = candidates[0]["disease_id"]
        elif len(candidates) > 1:
            want = TABLE_PART.get(row["table_id"].strip(), "")
            hits = [c for c in candidates if want in norm(c["subsection"])]
            if len(hits) == 1:
                disease_id = hits[0]["disease_id"]
            else:
                errors.append(f"nama penyakit tabel ambigu: {nama!r}")
                continue
        else:
            errors.append(f"nama penyakit tabel tidak dikenal: {nama!r}")
            continue
        add(
            {
                "disease_id": disease_id,
                "text": text,
                "source": "DOC002",
                "source_id": f"{row.get('table_id', '').strip()}#{row.get('row_no', '').strip()}",
                "chunk_id": "",
                "source_block_id": (row.get("source_block_id") or "").strip(),
                "page": (row.get("page") or "").strip(),
            }
        )
    return records, errors


def pathogen_records(entries: list[dict[str, str]]) -> list[dict]:
    scope = {e["disease_id"] for e in entries}
    rows2 = {r["pathogen_id"].strip(): r for r in read_csv(CURATED2 / "pathogens.csv")}
    rows5 = {r["pathogen_id"].strip(): r for r in read_csv(CURATED5 / "pathogens.csv")}
    records: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path, table, source in (
        (CURATED2 / "disease_pathogen.csv", rows2, "DOC002"),
        (CURATED5 / "disease_pathogen.csv", rows5, "DOC005"),
    ):
        for row in read_csv(path):
            did = row["disease_id"].strip()
            pid = row["pathogen_id"].strip()
            if did not in scope or (did, pid) in seen:
                continue
            seen.add((did, pid))
            records.append(
                {
                    "disease_id": did,
                    "pathogen_id": pid,
                    "row": table[pid],
                    "source": source,
                    "relation_note": (row.get("relation_note") or "").strip(),
                    "evidence_chunk_id": (row.get("evidence_chunk_id") or "").strip(),
                    "kind": "patogen",
                }
            )
    return records


def control_records(entries: list[dict[str, str]]) -> list[dict]:
    scope = {e["disease_id"] for e in entries}
    records: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path, source in ((CURATED2 / "controls.csv", "DOC002"), (CURATED5 / "controls.csv", "DOC005")):
        for row in read_csv(path):
            did = row["disease_id"].strip()
            text = (row.get("verbatim_text") or "").strip()
            if did not in scope or row.get("scope", "").strip() != "disease" or not text:
                continue
            if (did, text) in seen:
                continue
            seen.add((did, text))
            records.append(
                {
                    "disease_id": did,
                    "text": text,
                    "source": source,
                    "source_id": (row.get("control_id") or "").strip(),
                    "chunk_id": (row.get("chunk_id") or "").strip(),
                    "page": (row.get("page_start") or "").strip(),
                    "char_start": (row.get("char_start") or "").strip(),
                    "char_end": (row.get("char_end") or "").strip(),
                    "category": (row.get("control_category") or "").strip(),
                    "kind": "pengendalian",
                }
            )
    return records


def chapter_control_records() -> list[dict]:
    records: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in read_csv(CURATED2 / "controls.csv"):
        pid = row["plant_id"].strip()
        text = (row.get("verbatim_text") or "").strip()
        if pid not in PLANT_LOCAL or row.get("scope", "").strip() != "chapter" or not text:
            continue
        plant_local = PLANT_LOCAL[pid]
        if (plant_local, text) in seen:
            continue
        seen.add((plant_local, text))
        records.append(
            {
                "plant_local": plant_local,
                "text": text,
                "source": "DOC002",
                "source_id": (row.get("control_id") or "").strip(),
                "chunk_id": (row.get("chunk_id") or "").strip(),
                "page": (row.get("page_start") or "").strip(),
                "char_start": (row.get("char_start") or "").strip(),
                "char_end": (row.get("char_end") or "").strip(),
                "category": (row.get("control_category") or "").strip(),
                "kind": "pengendalian",
            }
        )
    return records


def all_context_records(symptom_rows: list[dict], control_rows: list[dict]) -> list[dict]:
    return symptom_rows + control_rows


def make_evidence(
    builder: Builder,
    prefix: str,
    record: dict,
    evidence_class: str,
    reference_local: str,
    label: str,
    cache: dict[tuple, URIRef],
    report: dict,
) -> URIRef:
    key = (
        prefix,
        record.get("source"),
        record.get("source_id"),
        record.get("chunk_id"),
        record.get("text"),
        evidence_class,
    )
    if key in cache:
        return cache[key]
    local = unique_local(prefix, record.get("text", ""), builder)
    uri = builder.individual(local, evidence_class)
    builder.label(uri, label)
    builder.comment(uri, "Node bukti yang menyimpan kutipan dan lokasi sumber.")
    original = (record.get("text") or "").strip()
    normalized = normalize_quote(original)
    builder.lang(uri, "kutipanSumber", original)
    builder.lang(uri, "kutipanNormalisasi", normalized)
    builder.plain(uri, "dokumenSumber", record.get("source"))
    builder.plain(uri, "identifierSumber", record.get("source_id"))
    builder.plain(uri, "idChunkSumber", record.get("chunk_id") or record.get("evidence_chunk_id"))
    builder.plain(uri, "idBlokSumber", record.get("source_block_id"))
    builder.plain(uri, "halamanSumber", record.get("page"))
    if not is_complete_sentence(original):
        builder.lang(uri, "catatanKualitas", "Kutipan sumber berupa fragmen atau kalimat terpotong.")
        report["data_quality"]["fragment_quotes"] += 1
    builder.ext_link(uri, PROV.wasDerivedFrom, KBR[reference_local])
    cache[key] = uri
    return uri


def build_referensi(builder: Builder) -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    for doc_id in ("DOC002", "DOC005"):
        info = meta["documents"][doc_id]
        local = f"Buku{doc_id}"
        uri = builder.individual(local, "Buku")
        builder.label(uri, info.get("title"))
        builder.comment(uri, "Referensi buku yang menjadi sumber data.")
        builder.lang(uri, "judulReferensi", info.get("title"))
        builder.integer(uri, "tahunTerbit", info.get("publication_year"))
        builder.plain(uri, "namaPenulis", ", ".join(info.get("authors") or []))
        builder.plain(uri, "identifierSumber", doc_id)


def build_tanaman(builder: Builder) -> None:
    for row in plant_rows_merged():
        uri = builder.individual(row["local"], PLANT_CLASS[row["local"]])
        builder.label(uri, row["label"])
        builder.comment(uri, "Tanaman pangan dalam ruang lingkup knowledge base.")
        builder.plain(uri, "namaIlmiah", row["scientific_name"] or None)
        builder.plain(uri, "identifierSumber", ";".join(row["plant_ids"]))


def build_bagi_tanaman(builder: Builder) -> None:
    for part, label in PART_LABELS.items():
        uri = builder.individual(part, "BagianTanaman")
        builder.label(uri, label)
        builder.comment(uri, "Bagian tanaman yang dapat menjadi lokasi gejala.")


def build_canonical_symptoms(builder: Builder) -> None:
    for local, spec in CANONICAL_SYMPTOMS.items():
        uri = builder.individual(local, "GejalaKanonik")
        builder.label(uri, spec["label"])
        builder.comment(uri, spec["comment"])
        builder.alt(uri, spec["label"].lower())


def build_canonical_controls(builder: Builder) -> None:
    for local, spec in CONTROL_ACTIONS.items():
        uri = builder.individual(local, spec["category"])
        builder.label(uri, spec["label"])
        builder.comment(uri, spec["comment"])
        builder.lang(uri, "namaPengendalian", spec["label"])


def build_kondisi_katalog(builder: Builder) -> None:
    for local, cls, label, _pattern in QUALITATIVE_RULES:
        uri = builder.individual(local, cls)
        builder.label(uri, label)
        builder.comment(uri, "Kondisi lingkungan kualitatif terkait penyakit tanaman.")


def build_penyakit(builder: Builder, entries: list[dict[str, str]], report: dict) -> None:
    cache: dict[tuple, URIRef] = {}
    groups: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        groups.setdefault(entry["local"], []).append(entry)

    for local, group in groups.items():
        canonical = next(
            (entry for entry in group if not entry.get("legacy_local")),
            group[0],
        )
        uri = builder.individual(local, "Penyakit")
        builder.label(uri, canonical.get("label") or canonical["nama"])
        builder.comment(uri, "Data penyakit dari sumber; rincian bukti tersedia pada node BuktiSumber.")
        builder.alt(uri, canonical["name_en"] or None)
        builder.plain(uri, "namaInggrisPenyakit", canonical["name_en"] or None)

        for entry in group:
            if entry is not canonical or entry.get("legacy_local") or entry["nama"] != canonical.get("label"):
                builder.alt(uri, entry["nama"])
            builder.plain(uri, "identifierSumber", entry["disease_id"])
            builder.link(uri, "menyerangTanaman", KBR[entry["plant_local"]])
            reference = "BukuDOC005" if entry["source"] == "DOC005" else "BukuDOC002"
            builder.link(uri, "memilikiReferensi", KBR[reference])
            record = {
                "text": entry["nama"] + (f". {entry['reference_verbatim']}" if entry["reference_verbatim"] else ""),
                "source": entry["source"],
                "source_id": entry["disease_id"],
                "chunk_id": entry["chunk_id"] or entry["evidence_chunk_ids"].split(";")[0] if entry["evidence_chunk_ids"] else entry["chunk_id"],
                "source_block_id": entry["source_block_id"] or entry["source_block_ids"].split(";")[0] if entry["source_block_ids"] else entry["source_block_id"],
                "page": entry["page_start"],
                "kind": "penyakit",
            }
            evidence = make_evidence(
                builder,
                "BuktiPenyakit" + local,
                record,
                "BuktiPenyakit",
                reference,
                f"Bukti penyakit {entry['nama']}",
                cache,
                report,
            )
            builder.link(uri, "didukungOleh", evidence)


def build_patogen(builder: Builder, entries: list[dict[str, str]], records: list[dict], report: dict) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    groups: dict[str, list[dict]] = {}
    for record in records:
        row = record["row"]
        key = norm(row.get("scientific_name")) or "unknown"
        groups.setdefault(key, []).append(record)
    local_by_key: dict[str, str] = {}
    used_bases: dict[str, list[str]] = {}
    representative: dict[str, dict] = {}
    taxon_by_key: dict[str, str] = {}
    for key, group in groups.items():
        representative[key] = max(group, key=lambda r: TAXON_PRIORITY.get((r["row"].get("taxon_group") or "").strip().lower(), 0))
        taxon_by_key[key] = (representative[key]["row"].get("taxon_group") or "").strip().lower()
        base = pascal(representative[key]["row"].get("scientific_name") or "") or "PatogenTidakDiketahui"
        used_bases.setdefault(base, []).append(key)
    for key, group in groups.items():
        row = representative[key]["row"]
        base = pascal(row.get("scientific_name") or "") or "PatogenTidakDiketahui"
        local = base if len(used_bases[base]) == 1 else base + str(used_bases[base].index(key) + 1)
        if local in tbox.CLASSES:
            local = "Patogen" + local
        local_by_key[key] = local
        taxon = taxon_by_key[key]
        classes = ["Patogen"]
        if taxon in TAXON_CLASS:
            classes = [TAXON_CLASS[taxon]]
        uri = builder.individual(local, *classes)
        builder.label(uri, row.get("scientific_name") or row.get("verbatim_text") or "Patogen tidak diketahui")
        builder.comment(uri, "Patogen yang tercatat pada sumber.")
        builder.plain(uri, "namaIlmiahPatogen", row.get("scientific_name") or None)
        builder.plain(uri, "identifierSumber", row.get("pathogen_id") or None)
        if taxon not in TAXON_CLASS:
            report["data_quality"]["unknown_pathogens"] += 1
    cache: dict[tuple, URIRef] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        row = record["row"]
        key = norm(row.get("scientific_name")) or "unknown"
        disease_uri = KBR[entry["local"]]
        pathogen_uri = KBR[local_by_key[key]]
        builder.link(disease_uri, "disebabkanOleh", pathogen_uri)
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        text = record["relation_note"] or row.get("verbatim_text") or row.get("scientific_name") or ""
        evidence_record = {
            "text": text,
            "source": record["source"],
            "source_id": row.get("pathogen_id"),
            "chunk_id": record["evidence_chunk_id"] or row.get("chunk_id"),
            "page": row.get("page"),
            "kind": "patogen",
        }
        evidence = make_evidence(
            builder,
            "BuktiPatogen" + entry["local"],
            evidence_record,
            "BuktiPatogen",
            reference,
            f"Bukti patogen {entry['nama']}",
            cache,
            report,
        )
        builder.link(disease_uri, "didukungOleh", evidence)
        builder.link(pathogen_uri, "didukungOleh", evidence)
        report["pathogen_links"].append(
            {"disease": entry["local"], "pathogen": local_by_key[key], "taxon": taxon_by_key[key]}
        )


def build_gejala(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    groups: dict[tuple[str, str], dict] = {}
    unmapped: list[dict] = []
    evidence_cache: dict[tuple, URIRef] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        canonicals = match_canonical_symptoms(record["text"])
        parts = text_parts(record["text"])
        if canonicals:
            for canonical in canonicals:
                key = (entry["local"], canonical)
                group = groups.setdefault(key, {"records": [], "parts": set(), "entry": entry})
                if not entry.get("legacy_local"):
                    group["entry"] = entry
                group["records"].append(record)
                group["parts"].update(parts)
                group["parts"].add(CANONICAL_SYMPTOMS[canonical]["part"])
        else:
            unmapped.append(record)
    for (disease_local, canonical), group in groups.items():
        entry = group["entry"]
        local = "Pengamatan" + disease_local + canonical
        uri = builder.individual(local, *(_part_classes(group["parts"]) or ["Gejala"]))
        builder.label(uri, f"{CANONICAL_SYMPTOMS[canonical]['label']} pada {entry['nama']}")
        builder.comment(uri, "Pengamatan gejala yang dipetakan ke konsep kanonik.")
        builder.link(uri, "memilikiGejalaKanonik", KBR[canonical])
        for part in sorted(group["parts"]):
            if part in PART_LABELS:
                builder.link(uri, "terdapatPada", KBR[part])
        description = ""
        for record in group["records"]:
            text = record["text"]
            if not description and is_complete_sentence(text):
                description = normalize_quote(text)
            reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
            evidence = make_evidence(
                builder,
                "BuktiGejala" + entry["local"],
                record,
                "BuktiGejala",
                reference,
                f"Bukti gejala {entry['nama']}",
                evidence_cache,
                report,
            )
            builder.link(uri, "didukungOleh", evidence)
        if description:
            builder.lang(uri, "deskripsiGejala", description)
        builder.link(KBR[entry["local"]], "memilikiGejala", uri)
        report["canonical_symptoms"]["used"][canonical] = report["canonical_symptoms"]["used"].get(canonical, 0) + 1

    for record in unmapped:
        entry = entries_by_id[record["disease_id"]]
        parts = text_parts(record["text"])
        local = unique_local("Pengamatan" + entry["local"], record["text"], builder)
        uri = builder.individual(local, *(_part_classes(parts) or ["Gejala"]))
        builder.label(uri, f"Pengamatan gejala {entry['nama']}")
        builder.comment(uri, "Pengamatan gejala yang belum dipetakan ke konsep kanonik.")
        for part in parts:
            builder.link(uri, "terdapatPada", KBR[part])
        if is_complete_sentence(record["text"]):
            builder.lang(uri, "deskripsiGejala", normalize_quote(record["text"]))
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiGejala" + entry["local"],
            record,
            "BuktiGejala",
            reference,
            f"Bukti gejala {entry['nama']}",
            evidence_cache,
            report,
        )
        builder.link(uri, "didukungOleh", evidence)
        builder.link(KBR[entry["local"]], "memilikiGejala", uri)
        report["data_quality"]["unmapped_symptoms"] += 1
    report["canonical_symptoms"]["total"] = len(groups) + len(unmapped)
    report["canonical_symptoms"]["canonical_groups"] = len(groups)
    report["canonical_symptoms"]["unmapped"] = len(unmapped)


def _part_classes(parts: set[str] | list[str]) -> list[str]:
    return [PART_SUBCLASS[part] for part in parts if part in PART_SUBCLASS]


def build_menyerang_bagian(builder: Builder, entries: list[dict[str, str]], report: dict) -> None:
    seen: set[str] = set()
    for entry in entries:
        if entry["local"] in seen:
            continue
        seen.add(entry["local"])
        parts = subsection_parts(entry["subsection"])
        if not parts:
            report["data_quality"]["diseases_without_explicit_part"] += 1
            continue
        for part in parts:
            builder.link(KBR[entry["local"]], "menyerangBagian", KBR[part])
            report["part_links"].append({"disease": entry["local"], "part": part})


def build_pengendalian(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    chapter_records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    cache: dict[tuple, URIRef] = {}
    action_description: dict[str, str] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        actions = match_control_actions(record["text"], record["category"], record["source"])
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiPengendalian" + entry["local"],
            record,
            "BuktiPengendalian",
            reference,
            f"Bukti pengendalian {entry['nama']}",
            cache,
            report,
        )
        builder.link(KBR[entry["local"]], "didukungOleh", evidence)
        if not actions:
            report["data_quality"]["unmapped_controls"] += 1
            continue
        for action in actions:
            builder.link(KBR[entry["local"]], "dikendalikanDengan", KBR[action])
            builder.link(KBR[action], "didukungOleh", evidence)
            if action not in action_description and is_complete_sentence(record["text"]):
                action_description[action] = normalize_quote(record["text"])
        report["controls"]["disease"].append(
            {"disease": entry["local"], "actions": actions, "category": record["category"], "source": record["source"]}
        )
    for record in chapter_records:
        plant_local = record["plant_local"]
        actions = match_control_actions(record["text"], record["category"], record["source"])
        evidence = make_evidence(
            builder,
            "BuktiPengendalianUmum" + plant_local,
            record,
            "BuktiPengendalian",
            "BukuDOC002",
            f"Bukti pengendalian umum {PLANT_LABELS[plant_local]}",
            cache,
            report,
        )
        builder.link(KBR[plant_local], "didukungOleh", evidence)
        if not actions:
            report["data_quality"]["unmapped_controls"] += 1
            continue
        for action in actions:
            builder.link(KBR[plant_local], "pengendalianUmum", KBR[action])
            builder.link(KBR[action], "didukungOleh", evidence)
            if action not in action_description and is_complete_sentence(record["text"]):
                action_description[action] = normalize_quote(record["text"])
        report["controls"]["chapter"].append(
            {"plant": plant_local, "actions": actions, "source": record["source"]}
        )
    for action, description in action_description.items():
        builder.lang(KBR[action], "deskripsiPengendalian", description)


def build_varietas(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    name_local: dict[str, str] = {}
    cache: dict[tuple, URIRef] = {}
    seen_links: set[tuple[str, str, str]] = set()
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        names = extract_varieties(record["text"])
        if not names:
            continue
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiVarietas" + entry["plant_local"],
            record,
            "BuktiSumber",
            reference,
            f"Bukti varietas {entry['nama']}",
            cache,
            report,
        )
        resist = bool(RESIST_MARKERS.search(record["text"]))
        vuln = bool(VULN_MARKERS.search(record["text"]))
        for name in names:
            if name not in name_local:
                base = "Varietas" + pascal(name)
                local = base
                counter = 2
                while local in builder.used_locals:
                    local = f"{base}{counter}"
                    counter += 1
                name_local[name] = local
            local = name_local[name]
            uri = builder.ensure_individual(local, "Varietas")
            builder.label(uri, name)
            builder.comment(uri, "Varietas tanaman yang disebut pada sumber.")
            builder.link(KBR[entry["plant_local"]], "memilikiVarietas", uri)
            builder.link(uri, "didukungOleh", evidence)
            if resist and not vuln:
                builder.link(uri, "tahanTerhadap", KBR[entry["local"]])
                report["varieties"]["resistant_links"].append({"variety": local, "disease": entry["local"]})
            elif vuln and not resist:
                builder.link(uri, "rentanTerhadap", KBR[entry["local"]])
                report["varieties"]["susceptible_links"].append({"variety": local, "disease": entry["local"]})
            key = (local, entry["disease_id"], record.get("source_id", ""))
            if key not in seen_links:
                seen_links.add(key)
                report["varieties"]["items"].append(
                    {"local": local, "name": name, "plant": entry["plant_local"], "disease": entry["local"]}
                )


def build_fase(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    cache: dict[tuple, URIRef] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        phases = extract_phases(record["text"])
        if not phases:
            continue
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        evidence = make_evidence(
            builder,
            "BuktiFase" + entry["local"],
            record,
            "BuktiSumber",
            reference,
            f"Bukti fase pertumbuhan {entry['nama']}",
            cache,
            report,
        )
        for phase in phases:
            spec = PHASE_DEFS[phase]
            uri = builder.ensure_individual(phase, spec["class"])
            builder.label(uri, spec["label"])
            builder.comment(uri, "Fase pertumbuhan yang disebut pada sumber.")
            builder.link(KBR[entry["local"]], "menyerangFase", uri)
            builder.link(uri, "didukungOleh", evidence)
            report["phases"]["links"].append({"disease": entry["local"], "phase": phase})


def build_lingkungan(
    builder: Builder,
    entries: list[dict[str, str]],
    records: list[dict],
    report: dict,
) -> None:
    entries_by_id = {e["disease_id"]: e for e in entries}
    cache: dict[tuple, URIRef] = {}
    observation_cache: dict[tuple, URIRef] = {}
    condition_cache: dict[str, URIRef] = {}
    for record in records:
        entry = entries_by_id[record["disease_id"]]
        reference = "BukuDOC005" if record["source"] == "DOC005" else "BukuDOC002"
        observations = parse_env_observations(record["text"])
        qualities = qualitative_matches(record["text"])
        if not observations and not qualities:
            continue
        evidence = make_evidence(
            builder,
            "BuktiLingkungan" + entry["local"],
            record,
            "BuktiSumber",
            reference,
            f"Bukti faktor lingkungan {entry['nama']}",
            cache,
            report,
        )
        for obs in observations:
            key = (
                record["disease_id"],
                obs["factor"],
                obs["class"],
                obs["min"],
                obs["max"],
                obs["single"],
                obs["operator"],
                obs["unit"],
            )
            if key in observation_cache:
                uri = observation_cache[key]
            else:
                local = "Observasi" + entry["local"] + obs["factor"] + value_slug(obs)
                uri = builder.individual(local, "ObservasiLingkungan", obs["class"])
                builder.label(uri, f"{obs['factor']} {value_slug(obs)} pada {entry['nama']}")
                builder.comment(uri, "Observasi faktor lingkungan yang diekstrak dari sumber.")
                if obs.get("min") is not None:
                    builder.decimal(uri, "nilaiMin", obs["min"])
                if obs.get("max") is not None:
                    builder.decimal(uri, "nilaiMaks", obs["max"])
                if obs.get("single") is not None:
                    builder.decimal(uri, "nilaiTunggal", obs["single"])
                builder.plain(uri, "operatorNilai", obs["operator"])
                builder.plain(uri, "satuan", obs["unit"])
                if obs.get("condition"):
                    builder.lang(uri, "kondisi", obs["condition"])
                    builder.lang(uri, "klasifikasiTurunan", obs["condition"])
                observation_cache[key] = uri
                report["environment"]["numeric"].append(
                    {
                        "disease": entry["local"],
                        "factor": obs["factor"],
                        "min": fmt_number(obs.get("min")),
                        "max": fmt_number(obs.get("max")),
                        "value": fmt_number(obs.get("single")),
                        "operator": obs["operator"],
                        "unit": obs["unit"],
                    }
                )
            builder.link(KBR[entry["local"]], "dipengaruhiOleh", uri)
            builder.link(uri, "didukungOleh", evidence)
            builder.link(KBR[entry["local"]], "didukungOleh", evidence)
        for local, cls, label in qualities:
            if local not in condition_cache:
                uri = builder.ensure_individual(local, cls)
                builder.label(uri, label)
                builder.comment(uri, "Kondisi lingkungan kualitatif yang dinyatakan sumber.")
                condition_cache[local] = uri
            uri = condition_cache[local]
            builder.link(KBR[entry["local"]], "dipengaruhiOleh", uri)
            builder.link(uri, "didukungOleh", evidence)
            builder.link(KBR[entry["local"]], "didukungOleh", evidence)
            report["environment"]["qualitative"].append({"disease": entry["local"], "condition": local})


def build() -> tuple[Graph, dict, list[str], Builder]:
    report: dict = {
        "summary": {},
        "controls": {"disease": [], "chapter": []},
        "canonical_symptoms": {"used": {}, "total": 0, "canonical_groups": 0, "unmapped": 0},
        "environment": {"numeric": [], "qualitative": []},
        "varieties": {"items": [], "resistant_links": [], "susceptible_links": []},
        "phases": {"links": []},
        "pathogen_links": [],
        "part_links": [],
        "data_quality": {
            "fragment_quotes": 0,
            "unmapped_symptoms": 0,
            "unmapped_controls": 0,
            "unknown_pathogens": 0,
            "diseases_without_explicit_part": 0,
        },
    }
    builder = Builder()
    tbox.build_tbox(builder.graph)
    builder.graph.bind("ptp", KBR)
    builder.graph.bind("prov", PROV)
    builder.graph.bind("skos", SKOS)

    entries = penyakit_entries()
    unique_disease_entries = unique_diseases(entries)
    symptom_rows, symptom_errors = symptom_records(entries)
    builder.errors.extend(symptom_errors)
    pathogen_rows = pathogen_records(entries)
    control_rows = control_records(entries)
    chapter_rows = chapter_control_records()

    build_referensi(builder)
    build_tanaman(builder)
    build_bagi_tanaman(builder)
    build_canonical_symptoms(builder)
    build_canonical_controls(builder)
    build_kondisi_katalog(builder)
    build_penyakit(builder, entries, report)
    build_patogen(builder, entries, pathogen_rows, report)
    build_gejala(builder, entries, symptom_rows, report)
    build_menyerang_bagian(builder, entries, report)
    build_pengendalian(builder, entries, control_rows, chapter_rows, report)
    build_varietas(builder, entries, all_context_records(symptom_rows, control_rows), report)
    build_fase(builder, entries, all_context_records(symptom_rows, control_rows), report)
    build_lingkungan(builder, entries, all_context_records(symptom_rows, control_rows), report)

    report["summary"] = {
        "plants": len(plant_rows_merged()),
        "diseases": len(unique_disease_entries),
        "symptom_records": len(symptom_rows),
        "pathogen_links": len(pathogen_rows),
        "control_records_disease": len(control_rows),
        "control_records_chapter": len(chapter_rows),
        "named_individuals": sum(1 for _ in builder.graph.subjects(RDF.type, OWL.NamedIndividual)),
        "triples": len(builder.graph),
    }
    report["coverage"] = {
        plant: {
            "diseases": sum(1 for e in unique_disease_entries if e["plant_local"] == plant),
            "symptoms": sum(1 for r in symptom_rows if e_plant(entries, r["disease_id"]) == plant),
            "controls": sum(1 for r in control_rows if e_plant(entries, r["disease_id"]) == plant),
        }
        for plant in PLANT_ORDER
    }
    report["data_quality"]["diseases_without_pathogen"] = sorted(
        e["local"] for e in unique_disease_entries if not any(builder.graph.objects(KBR[e["local"]], KBR["disebabkanOleh"]))
    )
    report["data_quality"]["diseases_without_control"] = sorted(
        e["local"] for e in unique_disease_entries if not any(builder.graph.objects(KBR[e["local"]], KBR["dikendalikanDengan"]))
    )
    report["data_quality"]["diseases_without_environment"] = sorted(
        e["local"] for e in unique_disease_entries if not any(builder.graph.objects(KBR[e["local"]], KBR["dipengaruhiOleh"]))
    )
    report["data_quality"]["diseases_without_scientific_name"] = sorted(
        e["local"] for e in unique_disease_entries if not any(builder.graph.objects(KBR[e["local"]], KBR["memilikiGejala"]))
    )
    errors = validate(builder.graph, builder, entries)
    return builder.graph, report, errors, builder


def e_plant(entries: list[dict[str, str]], disease_id: str) -> str:
    for entry in entries:
        if entry["disease_id"] == disease_id:
            return entry["plant_local"]
    return ""


def type_closure(graph: Graph, node: URIRef, cls: URIRef) -> bool:
    if (node, RDF.type, cls) in graph:
        return True
    for direct in graph.objects(node, RDF.type):
        if not isinstance(direct, URIRef):
            continue
        stack = [direct]
        seen: set[URIRef] = set()
        while stack:
            current = stack.pop()
            if current == cls:
                return True
            if current in seen:
                continue
            seen.add(current)
            for parent in graph.objects(current, RDFS.subClassOf):
                if isinstance(parent, URIRef):
                    stack.append(parent)
    return False


def validate(graph: Graph, builder: Builder, entries: list[dict[str, str]]) -> list[str]:
    errors = list(builder.errors)
    try:
        reparsed = Graph()
        reparsed.parse(data=graph.serialize(format="turtle"), format="turtle")
    except Exception as exc:  # noqa: BLE001
        return errors + [f"parse ulang gagal: {exc}"]

    for node in graph.subjects(RDF.type, OWL.NamedIndividual):
        local = str(node).split("#")[-1]
        if not re.match(r"^[A-Z][A-Za-z0-9]*$", local):
            errors.append(f"local name tidak PascalCase/ASCII: {local}")
        if "_" in local or "-" in local or re.search(r"[0-9a-f]{16,}", local):
            errors.append(f"local name mengandung hash/underscore: {local}")
        if not any(graph.objects(node, RDFS.label)):
            errors.append(f"individu tanpa label: {local}")
        if not any(graph.objects(node, SKOS.prefLabel)):
            errors.append(f"individu tanpa prefLabel: {local}")
        if not any(t for t in graph.objects(node, RDF.type) if t != OWL.NamedIndividual):
            errors.append(f"individu tanpa tipe domain: {local}")
        if KBR[local] in set(graph.subjects(RDF.type, OWL.Class)):
            errors.append(f"local name dipakai kelas dan individu: {local}")

    for cls in graph.subjects(RDF.type, OWL.Class):
        if not isinstance(cls, URIRef) or not str(cls).startswith(tbox.PTP):
            continue
        local = str(cls).split("#")[-1]
        if not any(graph.objects(cls, RDFS.label)):
            errors.append(f"kelas tanpa label: {local}")
        if not any(graph.objects(cls, SKOS.prefLabel)):
            errors.append(f"kelas tanpa prefLabel: {local}")
        if not any(graph.objects(cls, RDFS.comment)):
            errors.append(f"kelas tanpa komentar: {local}")
        if local != "EntitasKBR" and not any(graph.objects(cls, RDFS.subClassOf)):
            errors.append(f"kelas tanpa parent: {local}")

    for name, spec in tbox.OBJECT_PROPERTIES.items():
        prop = KBR[name]
        if not any(graph.objects(prop, RDFS.label)) or not any(graph.objects(prop, SKOS.prefLabel)):
            errors.append(f"properti objek tanpa label: {name}")
        if not any(graph.objects(prop, RDFS.comment)):
            errors.append(f"properti objek tanpa komentar: {name}")
        domain = spec.get("domain")
        if domain and not any(graph.objects(prop, RDFS.domain)):
            errors.append(f"properti objek tanpa domain: {name}")
        if not any(graph.objects(prop, RDFS.range)):
            errors.append(f"properti objek tanpa range: {name}")
        inverse = spec.get("inverse")
        if inverse and (prop, OWL.inverseOf, KBR[inverse]) not in graph:
            errors.append(f"inverseOf hilang: {name} -> {inverse}")
        for subject, obj in graph.subject_objects(prop):
            if domain and not type_closure(graph, subject, KBR[domain]):
                errors.append(f"subjek {subject} tidak bertipe {domain} untuk {name}")
            if not type_closure(graph, obj, KBR[spec["range"]]):
                errors.append(f"objek {obj} tidak bertipe {spec['range']} untuk {name}")

    for name, spec in tbox.DATA_PROPERTIES.items():
        prop = KBR[name]
        if not any(graph.objects(prop, RDFS.label)) or not any(graph.objects(prop, SKOS.prefLabel)):
            errors.append(f"properti data tanpa label: {name}")
        if not any(graph.objects(prop, RDFS.comment)):
            errors.append(f"properti data tanpa komentar: {name}")
        for subject, obj in graph.subject_objects(prop):
            if not type_closure(graph, subject, KBR[spec["domain"]]):
                errors.append(f"subjek data {subject} tidak bertipe {spec['domain']} untuk {name}")
            if not isinstance(obj, Literal):
                errors.append(f"nilai data bukan literal untuk {name}: {obj}")
            elif spec["range"] == RDF.PlainLiteral and obj.language != "id":
                errors.append(f"literal {name} tidak berbahasa id: {obj}")
            elif spec["range"] == XSD.integer and obj.datatype != XSD.integer:
                errors.append(f"literal {name} bukan integer: {obj}")
            elif spec["range"] == XSD.decimal and obj.datatype != XSD.decimal:
                errors.append(f"literal {name} bukan decimal: {obj}")
            elif spec["range"] == XSD.string and obj.language:
                errors.append(f"literal {name} seharusnya string tanpa bahasa: {obj}")

    for local in tbox.TOP_DOMAINS:
        if not any(graph.objects(KBR[local], OWL.disjointWith)):
            errors.append(f"disjointWith hilang untuk domain: {local}")

    all_disjoint_nodes = list(graph.subjects(RDF.type, OWL.AllDisjointClasses))
    if len(all_disjoint_nodes) < len(tbox.ALL_DISJOINT_GROUPS):
        errors.append("jumlah AllDisjointClasses kurang")
    for group in tbox.ALL_DISJOINT_GROUPS:
        found = False
        for node in all_disjoint_nodes:
            for members in graph.objects(node, OWL.members):
                values = {str(item) for item in graph.items(members)}
                if {str(KBR[name]) for name in group} <= values:
                    found = True
        if not found:
            errors.append(f"AllDisjointClasses hilang untuk {group[0]}")

    for name, _patogen in tbox.EQUIVALENT_CLASSES:
        if not any(graph.objects(KBR[name], OWL.equivalentClass)):
            errors.append(f"equivalentClass hilang: {name}")
    if not any(graph.objects(KBR["Penyakit"], RDFS.subClassOf)):
        errors.append("restriksi Penyakit hilang")
    if not list(graph.objects(None, OWL.propertyChainAxiom)):
        errors.append("propertyChainAxiom hilang")
    for sub_prop, super_prop in tbox.SUBPROPERTY_OF:
        if (KBR[sub_prop], RDFS.subPropertyOf, KBR[super_prop]) not in graph:
            errors.append(f"subPropertyOf hilang: {sub_prop} -> {super_prop}")

    explicit_disease_categories = set(tbox.CLASSES) - {"Penyakit", "PenyakitPenyebabTidakDiketahui"}
    for category in explicit_disease_categories:
        if not category.startswith("Penyakit"):
            continue
        if any(graph.subjects(RDF.type, KBR[category])):
            errors.append(f"kategori penyakit di-assert eksplisit: {category}")

    for entry in entries:
        uri = KBR[entry["local"]]
        for prop in ("menyerangTanaman", "memilikiGejala", "memilikiReferensi", "didukungOleh"):
            if not any(graph.objects(uri, KBR[prop])):
                errors.append(f"penyakit {entry['local']} tanpa {prop}")
    for book in ("BukuDOC002", "BukuDOC005"):
        years = list(graph.objects(KBR[book], KBR["tahunTerbit"]))
        if len(years) != 1:
            errors.append(f"{book} harus punya tepat 1 tahunTerbit, ditemukan {len(years)}")

    for ev in graph.subjects(RDF.type, KBR["BuktiSumber"]):
        if not any(graph.objects(ev, KBR["kutipanSumber"])):
            errors.append(f"bukti tanpa kutipan: {ev}")
        if not any(graph.objects(ev, KBR["dokumenSumber"])):
            errors.append(f"bukti tanpa dokumen: {ev}")
        if not any(graph.objects(ev, PROV.wasDerivedFrom)):
            errors.append(f"bukti tanpa prov:wasDerivedFrom: {ev}")

    for subject, obj in graph.subject_objects(KBR["nilaiMin"]):
        max_values = list(graph.objects(subject, KBR["nilaiMaks"]))
        if max_values and Decimal(str(obj)) > Decimal(str(max_values[0])):
            errors.append(f"nilaiMin > nilaiMaks pada {subject}")
    for subject, unit in graph.subject_objects(KBR["satuan"]):
        if str(unit) not in ("°C", "%", "mm"):
            errors.append(f"satuan tidak dikenal pada {subject}: {unit}")

    for prop in ("deskripsiGejala", "deskripsiPengendalian", "deskripsiPenyakit", "deskripsiTanaman"):
        for obj in graph.objects(None, KBR[prop]):
            value = normalize_quote(str(obj))
            if re.search(r"\b(et al\.|dkk\.)\s*$", value, re.I):
                errors.append(f"{prop} berakhir et al.: {subject}")
            if value and not is_complete_sentence(value):
                errors.append(f"{prop} bukan kalimat lengkap: {subject}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bangun ontologi Penyakit Tanaman Pangan Indonesia.")
    parser.add_argument("--out", type=Path, default=DEFAULT_TTL, help="path keluaran TTL")
    args = parser.parse_args(argv)

    graph, report, errors, _builder = build()
    if errors:
        print("VALIDASI GAGAL:", file=sys.stderr)
        for error in errors[:80]:
            print(f"  - {error}", file=sys.stderr)
        if len(errors) > 80:
            print(f"  ... {len(errors) - 80} error lain", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(args.out), format="turtle")
    owl_path = args.out.with_suffix(".owl")
    graph.serialize(destination=str(owl_path), format="xml")
    report["summary"]["triples"] = len(graph)
    report["summary"]["named_individuals"] = sum(1 for _ in graph.subjects(RDF.type, OWL.NamedIndividual))
    report["summary"]["classes"] = sum(
        1 for cls in graph.subjects(RDF.type, OWL.Class) if isinstance(cls, URIRef) and str(cls).startswith(tbox.PTP)
    )
    report["summary"]["object_properties"] = sum(
        1 for prop in graph.subjects(RDF.type, OWL.ObjectProperty) if isinstance(prop, URIRef) and str(prop).startswith(tbox.PTP)
    )
    report["summary"]["data_properties"] = sum(
        1 for prop in graph.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(prop, URIRef) and str(prop).startswith(tbox.PTP)
    )
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ontologi ditulis: {args.out} dan {owl_path}")
    print(f"laporan ekstraksi: {REPORT_PATH}")
    print(
        f"triple: {len(graph)} | individu: {report['summary']['named_individuals']} | "
        f"penyakit: {report['summary']['diseases']} | gejala: {report['canonical_symptoms']['canonical_groups']} kanonik + "
        f"{report['canonical_symptoms']['unmapped']} tak dipetakan | pengendalian: {len(report['controls']['disease']) + len(report['controls']['chapter'])} | "
        f"varietas: {len(report['varieties']['items'])} | fase: {len(report['phases']['links'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
