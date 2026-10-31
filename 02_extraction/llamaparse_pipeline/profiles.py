"""Profil per dokumen untuk pipeline LlamaParse.

Setiap PDF sumber punya nomor halaman, offset halaman cetak, dan ekspektasi
struktur yang berbeda. Semua nilai di sini dibaca dari dokumen aslinya
(kolofon, daftar isi, dan pemindaian halaman), bukan ditebak.

``gate_mode`` menentukan cara verifikasi:

- ``baseline``: bandingkan dengan snapshot PyMuPDF (dipakai DOC002).
- ``internal``: tanpa baseline; verifikasi memakai cakupan halaman, lantai
  karakter, offset halaman cetak, jumlah bagian, dan tabel yang diharapkan.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentProfile:
    document_id: str
    filename: str
    expected_pages: int
    printed_offset: int
    body_start: int
    body_end: int
    pilot_pages: tuple[int, ...]
    expected_sections: int
    gate_mode: str
    blank_pages: frozenset[int] = field(default_factory=frozenset)
    non_content_pages: dict[int, str] = field(default_factory=dict)
    table_pages: tuple[int, ...] = ()
    chapter_titles: tuple[str, ...] = ()
    chapter_plants: dict[str, str] = field(default_factory=dict)
    lettered_subsections: bool = False
    lettered_subsection_level: int = 0
    ignored_headings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    source_dir: str = "pdf_original"


DOC002 = DocumentProfile(
    document_id="DOC002",
    filename="PenyakitTanamanPangan.pdf",
    expected_pages=274,
    printed_offset=24,
    body_start=25,
    body_end=274,
    pilot_pages=(1, 9, 23, 25, 27, 40, 41, 91, 92, 94, 95, 134, 148, 158,
                 168, 178, 196, 212, 224, 274),
    expected_sections=15,
    gate_mode="baseline",
    non_content_pages={1: "researchgate_cover_page"},
    notes=(
        "Baseline PyMuPDF dibekukan; gate memakai perbandingan CER.",
        "Halaman 92/94/95 multi-kolom dan diperiksa manual.",
    ),
)

DOC003 = DocumentProfile(
    document_id="DOC003",
    filename="porang.pdf",
    expected_pages=56,
    printed_offset=8,
    body_start=9,
    body_end=55,
    pilot_pages=(29, 30, 40),
    expected_sections=9,
    gate_mode="internal",
    blank_pages=frozenset({8, 56}),
    non_content_pages={
        1: "front_matter_cover",
        2: "front_matter_colophon",
        3: "front_matter_preface",
        4: "front_matter_acknowledgement",
        5: "front_matter_toc",
        6: "front_matter_table_list",
        7: "front_matter_figure_list",
        8: "blank_page_viii",
        56: "blank_page_48",
    },
    table_pages=(29,),
    chapter_titles=(
        "PENDAHULUAN",
        "KLASIFIKASI DAN DESKRIPSI",
        "PERSYARATAN TUMBUH",
        "PERKEMBANGBIAKAN DAN PERTUMBUHAN",
        "TEKNOLOGI BUDIDAYA",
        "HAMA PENYAKIT DAN PENGENDALIANNYA",
        "KANDUNGAN NUTRISI DAN PEMANFAATAN",
        "NILAI EKONOMI DAN ANALISIS USAHATANI",
        "DAFTAR PUSTAKA",
    ),
    lettered_subsections=True,
    notes=(
        "Halaman cetak 1 = PDF 9 (offset +8).",
        "Tabel 2 (PDF 29) memuat penyakit Amorphophallus spp. dan dipakai "
        "sebagai tabel KB terpisah dari penyakit porang.",
    ),
)

DOC004 = DocumentProfile(
    document_id="DOC004",
    filename="TPTPkhususjamilah.pdf",
    expected_pages=65,
    printed_offset=-60,
    body_start=12,
    body_end=55,
    pilot_pages=(12, 24, 47),
    expected_sections=1,
    gate_mode="internal",
    blank_pages=frozenset(),
    non_content_pages={
        1: "front_matter_cover",
        2: "front_matter_title_page",
        3: "front_matter_colophon",
        4: "front_matter_preface",
        5: "front_matter_preface",
        6: "front_matter_synopsis",
        7: "front_matter_toc",
        8: "front_matter_toc",
        9: "front_matter_toc",
        10: "front_matter_toc",
        11: "front_matter_toc",
        64: "author_profile",
        65: "back_cover",
    },
    table_pages=(),
    chapter_titles=("PENGELOLAAN NUTRISI TANAMAN",),
    ignored_headings=("Teknologi Produksi Tanaman Pangan",),
    notes=(
        "PDF adalah cuplikan Bab 7 saja: halaman cetak 72-115 (PDF 12-55), "
        "daftar pustaka cetak 116-123 (PDF 56-63), profil penulis cetak 204 "
        "(PDF 64), dan sampul belakang (PDF 65).",
        "Daftar isi mencantumkan Bab 1-9, tetapi isinya tidak ada di PDF ini.",
    ),
)

DOC005 = DocumentProfile(
    document_id="DOC005",
    filename="PenyakitTanamanKedelaiKacangTanahKacangHijau.pdf",
    expected_pages=84,
    printed_offset=13,
    body_start=14,
    body_end=71,
    pilot_pages=(2, 14, 17, 18, 19, 26, 31, 38, 44, 52, 57, 72),
    expected_sections=4,
    gate_mode="internal",
    blank_pages=frozenset({3, 9, 12, 13}),
    non_content_pages={
        1: "front_matter_cover",
        2: "front_matter_title_page",
        3: "front_matter_colophon",
        4: "front_matter_preface",
        5: "front_matter_toc",
        6: "front_matter_toc",
        7: "front_matter_toc",
        8: "front_matter_toc",
        9: "front_matter_toc",
        10: "front_matter_toc",
        11: "front_matter_toc",
        12: "front_matter_toc",
        13: "blank_page",
        84: "back_cover",
    },
    table_pages=(44, 45, 49, 56, 57, 58, 69),
    chapter_titles=(
        "PENDAHULUAN",
        "KEDELAI",
        "KACANG TANAH",
        "KACANG HIJAU",
        "DAFTAR PUSTAKA",
    ),
    chapter_plants={
        "KEDELAI": "Kedelai",
        "KACANG TANAH": "Kacang tanah",
        "KACANG HIJAU": "Kacang hijau",
    },
    lettered_subsections=True,
    lettered_subsection_level=3,
    ignored_headings=(
        "Penyakit utama pada tanaman kedelai, kacang tanah dan kacang hijau",
    ),
    notes=(
        "Halaman cetak 1 = PDF 14 (offset +13).",
        "Bab inang memakai judul HURUF BESAR tanpa label Bab.",
        "Subbab a.-e. harus berada di level 3 agar tidak menimpa section penyakit.",
        "Tabel 1-7 diperkirakan berada di PDF 44, 45, 49, 56, 57, 58, dan 69.",
        "PDF 9 dan 12 tidak punya blok mandiri karena tabelnya digabung ke PDF 8 dan 11.",
    ),
    source_dir="pdf_sources",
)

PROFILES = {
    profile.document_id: profile
    for profile in (DOC002, DOC003, DOC004, DOC005)
}

DEFAULT_DOCUMENT_ID = DOC002.document_id


def get(document_id: str) -> DocumentProfile:
    try:
        return PROFILES[document_id]
    except KeyError as exc:
        raise ValueError(
            f"document_id tidak dikenal: {document_id}. Pilihan: {sorted(PROFILES)}"
        ) from exc


def document_ids() -> tuple[str, ...]:
    return tuple(PROFILES)


def from_run_id(run_id: str) -> DocumentProfile:
    """Menebak profil dari prefix ``DOCxxx`` pada run_id."""

    prefix = str(run_id).split("_", 1)[0]
    if prefix not in PROFILES:
        raise ValueError(f"run_id tidak memuat document_id yang dikenal: {run_id}")
    return PROFILES[prefix]
