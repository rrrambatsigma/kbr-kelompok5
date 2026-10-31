"""Deteksi struktur bab/subbab/penyakit dari heading LlamaParse."""

from __future__ import annotations

import re
from typing import Any, Optional


CHAPTER_LABEL_RE = re.compile(
    r"^(BAB|BAGIAN|CHAPTER)\s+([IVXLCDM]+|\d+)\b\s*[:.\-–—]?\s*(.*)$",
    re.IGNORECASE,
)
NUMBERED_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+)$")
DISEASE_PREFIX_RE = re.compile(r"^Penyakit\s+(.+)$", re.IGNORECASE)
PLANT_RE = re.compile(
    r"^Penyakit\s+(?:pada\s+)?(?:Tanaman\s+)?([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{1,40})$",
    re.IGNORECASE,
)

GENERIC_LABELS = {
    "pendahuluan",
    "pengantar",
    "latar belakang",
    "daftar isi",
    "daftar tabel",
    "daftar gambar",
    "daftar pustaka",
    "referensi",
    "bibliografi",
    "biodata penulis",
    "glosarium",
    "indeks",
    "penutup",
    "kesimpulan",
    "saran",
}

CATEGORY_PATTERNS = (
    ("symptoms", (r"gejala", r"tanda", r"serangan")),
    ("pathogen", (r"penyebab", r"patogen", r"jasad", r"organisme penyebab")),
    ("host", (r"inang", r"tanaman inang")),
    (
        "epidemiology",
        (r"penyebaran", r"epidemi", r"siklus hidup", r"faktor", r"kondisi", r"perkembangan"),
    ),
    (
        "control",
        (r"pengendalian", r"pencegahan", r"pengobatan", r"penanggulangan", r"pengelolaan"),
    ),
    ("overview", (r"deskripsi", r"identifikasi", r"morfologi", r"gambaran umum")),
    ("chapter_intro", (r"pendahuluan", r"pengantar", r"latar belakang")),
    ("reference", (r"daftar pustaka", r"referensi", r"bibliografi")),
)


FIGURE_CAPTION_RE = re.compile(
    r"^(Gambar|Figure|Foto|Diagram|Grafik)\s+\d+(?:\.\d+)*\b", re.IGNORECASE
)
TABLE_CAPTION_RE = re.compile(
    r"^(Tabel|Table)\s+\d+(?:\.\d+)*\b", re.IGNORECASE
)


def caption_kind(text: str) -> Optional[str]:
    """Mengenali judul gambar/tabel yang sering salah diklasifikasi sebagai heading."""

    value = normalize_heading(text)
    if FIGURE_CAPTION_RE.match(value):
        return "figure"
    if TABLE_CAPTION_RE.match(value):
        return "table"
    return None


def normalize_heading(text: str) -> str:
    value = " ".join((text or "").split())
    return value.strip(" .:;-–—")


def split_numbering(text: str) -> tuple[Optional[str], str]:
    """Memisahkan nomor bab/subbab dari judulnya."""

    value = normalize_heading(text)
    match = NUMBERED_RE.match(value)
    if match:
        return match.group(1), match.group(2).strip()
    return None, value


def is_chapter_label(text: str) -> bool:
    return bool(CHAPTER_LABEL_RE.match(normalize_heading(text)))


def chapter_label_parts(text: str) -> tuple[str, str, str]:
    """Mengembalikan (kata kunci, nomor, sisa judul) dari heading bab."""

    match = CHAPTER_LABEL_RE.match(normalize_heading(text))
    if not match:
        return "", "", normalize_heading(text)
    return match.group(1), match.group(2), match.group(3).strip()


def is_generic_label(text: str) -> bool:
    _, title = split_numbering(text)
    lowered = title.lower().strip(" .:;-–—")
    if lowered in GENERIC_LABELS:
        return True
    return any(lowered.startswith(label + " ") for label in GENERIC_LABELS)


def category_for(text: str) -> str:
    """Menentukan kategori chunk dari judul heading (bukan dari isi paragraf)."""

    _, title = split_numbering(text)
    lowered = title.lower()
    for chunk_type, patterns in CATEGORY_PATTERNS:
        if any(re.search(pattern, lowered) for pattern in patterns):
            return chunk_type
    return "unclassified"


def plant_from_chapter(chapter: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Mengambil nama tanaman dari judul bab bila polanya eksplisit."""

    if not chapter:
        return None, None
    title = normalize_heading(chapter)
    # Buang label "Bab N —" bila ada.
    label_match = CHAPTER_LABEL_RE.match(title)
    if label_match and label_match.group(3):
        title = label_match.group(3)
    match = PLANT_RE.match(title)
    if not match:
        return None, None
    candidate = normalize_heading(match.group(1))
    if re.search(r"\bdan\b", candidate, re.IGNORECASE):
        return None, None
    if len(candidate.split()) > 4:
        return None, None
    return candidate, "chapter_heading"


def disease_from_section(section: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Mengambil nama penyakit dari heading section, tanpa menebak."""

    if not section:
        return None, None
    _, title = split_numbering(section)
    if not title or is_generic_label(title):
        return None, None
    lowered = title.lower()
    if lowered.startswith("penyakit ") and len(title.split()) <= 6:
        return normalize_heading(DISEASE_PREFIX_RE.sub(r"\1", title)), "section_heading"
    return title, "section_heading"


def is_known_chapter(text: str, known_chapters: set[str]) -> bool:
    """True bila teks sama persis dengan judul bab yang tercetak di daftar isi."""

    return bool(known_chapters) and normalize_heading(text).casefold() in known_chapters


def is_bare_chapter_label(text: str) -> bool:
    """True untuk baris nomor bab tanpa judul, mis. ``BAB 7``.

    Baris seperti ini hanya membawa nomor; judulnya ada di baris berikutnya,
    jadi tidak disimpan sebagai heading tersendiri.
    """

    match = CHAPTER_LABEL_RE.match(normalize_heading(text))
    return bool(match) and not match.group(3).strip()


def is_book_title(text: str, titles: tuple[str, ...]) -> bool:
    """True bila teks sama dengan judul buku/running header yang diabaikan."""

    if not titles:
        return False
    value = normalize_heading(text).casefold()
    return any(value == normalize_heading(title).casefold() for title in titles)


class DocumentContext:
    """Konteks yang dibawa antar halaman."""

    def __init__(
        self,
        known_chapters: tuple[str, ...] = (),
        lettered_subsections: bool = False,
    ) -> None:
        self.known_chapters = {
            normalize_heading(title).casefold()
            for title in known_chapters
            if normalize_heading(title)
        }
        self.lettered_subsections = lettered_subsections
        self.chapter: Optional[str] = None
        self.section: Optional[str] = None
        self.section_source: Optional[str] = None
        self.subsection: Optional[str] = None
        self.pending_chapter_label: Optional[str] = None
        self.plant_name: Optional[str] = None
        self.plant_source: Optional[str] = None
        self.disease_name: Optional[str] = None
        self.disease_source: Optional[str] = None
        self.chunk_type: str = "unclassified"

    def as_dict(self) -> dict[str, Any]:
        return {
            "chapter": self.chapter,
            "section": self.section,
            "section_source": self.section_source,
            "subsection": self.subsection,
            "plant_name": self.plant_name,
            "disease_name": self.disease_name,
        }


def resolve_heading_level(text: str, parser_level: int) -> int:
    """Menentukan level dari pola nomor, karena level parser tidak konsisten.

    ``1.2`` selalu section dan ``1.2.1`` selalu subsection, apa pun level yang
    dikirim parser.
    """

    value = normalize_heading(text)
    if is_chapter_label(value):
        return 1
    match = re.match(r"^(\d+(?:\.\d+)*)\.?\s+\S", value)
    if match:
        depth = match.group(1).count(".") + 1
        return max(2, min(depth, 3))
    return parser_level


def update_for_heading(
    context: DocumentContext,
    text: str,
    level: int,
) -> str:
    """Memperbarui konteks dan mengembalikan ``content_type`` heading."""

    heading = normalize_heading(text)
    level = resolve_heading_level(heading, level)
    known_chapter = heading.casefold() in context.known_chapters
    if known_chapter:
        # Judul bab yang tercetak HURUF BESAR tanpa label "Bab N"
        # (DOC003/DOC004) tetap dianggap level 1 karena judulnya diambil dari
        # daftar isi yang tercetak, bukan ditebak.
        level = 1
    elif context.lettered_subsections and re.match(r"^[a-z]\.\s+\S", heading):
        # Enumerasi "a.", "b.", ... adalah subbab, bukan bab.
        level = 2

    if level <= 1:
        if known_chapter:
            # Judul sudah pasti dari daftar isi; jangan digabung dengan label
            # bab yang mungkin masih tertunda.
            context.chapter = heading
            context.pending_chapter_label = None
        elif is_chapter_label(heading):
            _, _, title = chapter_label_parts(heading)
            if title:
                context.chapter = heading
                context.pending_chapter_label = None
            else:
                context.pending_chapter_label = heading
                context.chapter = heading
        elif context.pending_chapter_label:
            context.chapter = f"{context.pending_chapter_label} — {heading}"
            context.pending_chapter_label = None
        elif is_generic_label(heading) or context.chapter is None:
            context.chapter = heading
            context.pending_chapter_label = None
        else:
            # Level-1 tanpa label bab: jangan menimpa konteks bab yang valid.
            return "heading_unclassified"

        context.section = None
        context.section_source = None
        context.subsection = None
        context.disease_name = None
        context.disease_source = None
        plant, plant_source = plant_from_chapter(context.chapter)
        context.plant_name = plant
        context.plant_source = plant_source
        context.chunk_type = category_for(context.chapter)
        if context.chunk_type == "unclassified" and is_generic_label(context.chapter):
            context.chunk_type = "reference" if "pustaka" in context.chapter.lower() else "unclassified"
        return "chapter_heading"

    if level == 2:
        context.section = heading
        context.section_source = "section_heading"
        context.subsection = None
        disease, disease_source = disease_from_section(heading)
        context.disease_name = disease
        context.disease_source = disease_source
        context.chunk_type = category_for(heading)
        if context.chunk_type == "unclassified" and disease:
            context.chunk_type = "overview"
        return "section_heading"

    context.subsection = heading
    number = re.match(r"^(\d+)\.(\d+)\.", heading)
    if number:
        prefix = f"{number.group(1)}.{number.group(2)}"
        if not context.section or not context.section.startswith(prefix):
            # Section induk tidak terdeteksi: simpan nomornya saja, tanpa
            # mengarang judul.
            context.section = prefix
            context.section_source = "derived_from_subsection_number"
    category = category_for(heading)
    if category != "unclassified":
        context.chunk_type = category
    return "subsection_heading"


def chunk_type_for_block(context: DocumentContext, content_type: str) -> str:
    if content_type == "table":
        return "table"
    if content_type == "figure_caption":
        return "figure_caption"
    if content_type == "chapter_heading" and context.pending_chapter_label:
        return "chapter_intro"
    return context.chunk_type
