"""Rekonsiliasi verbatim keluaran LlamaParse dengan text layer PDF.

PDF DOC002 bersifat born-digital sehingga teks PyMuPDF adalah otoritas kata.
LlamaParse tetap dipakai untuk struktur (urutan baca, tabel, caption, nomor
halaman cetak), tetapi kata yang ditulis ulang atau dihilangkan parser
dikembalikan dari text layer. Setiap perubahan dicatat agar dapat dilacak.
"""

from __future__ import annotations

import difflib
import logging
import re
from collections import Counter
from typing import Any, Optional

from pdf_pipeline import config as base_config
from pdf_pipeline.output import utc_now, write_json, write_jsonl

from . import clean, config, structure


LOGGER = logging.getLogger("kbr_llamaparse")

TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+")

# Hanya kata bermakna yang direkonsiliasi. Token pendek dan angka dilewati
# agar label gambar ("a", "b"), satuan, dan nomor halaman tidak tersentuh.
MIN_TOKEN_CHARS = 4
MIN_BLOCK_TOKENS = 5
MIN_ALIGNMENT_RATIO = 0.5

BODY_CONTENT_TYPES = frozenset({"paragraph", "list_item", "figure_caption"})

# Halaman dianggap kehilangan teks bila sisa teks Llama sangat sedikit.
FALLBACK_MIN_BASELINE_CHARS = 100
FALLBACK_MAX_RATIO = 0.25

# Blok di ujung halaman yang hilang dipulihkan bila cukup panjang.
RECOVER_MIN_CHARS = 60
RECOVER_MAX_COVERAGE = 0.5
RECOVER_ANCHOR_COVERAGE = 0.5

# Sel tabel lebih pendek daripada paragraf, jadi ambang kecocokannya berbeda.
TABLE_CELL_MIN_TOKENS = 4
TABLE_CELL_MIN_OVERLAP = 0.5


# ----------------------------------------------------------------------
# Baseline PyMuPDF
# ----------------------------------------------------------------------
def load_baseline() -> dict[int, dict[str, Any]]:
    """Memuat snapshot baseline PyMuPDF per halaman (read-only)."""

    from . import baseline as baseline_store

    try:
        pages = baseline_store.load_pages()
        blocks = baseline_store.load_blocks()
    except (OSError, ValueError, RuntimeError) as exc:
        LOGGER.warning("Baseline PyMuPDF tidak tersedia: %s", exc)
        return {}

    heights = {
        int(page["page_number"]): float(page.get("page_height") or 0.0)
        for page in pages
    }
    grouped: dict[int, list[dict[str, Any]]] = {}
    for block in blocks:
        grouped.setdefault(int(block["page_number"]), []).append(block)

    return {
        page: {
            "height": heights.get(page, 0.0),
            "blocks": blocks,
        }
        for page, blocks in grouped.items()
    }


def _usable_baseline_blocks(
    blocks: list[dict[str, Any]], page_height: float
) -> list[dict[str, Any]]:
    """Membuang header/footer, nomor halaman, dan blok non-isi."""

    usable: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("content_type") not in BODY_CONTENT_TYPES:
            continue
        text = str(block.get("text") or "").strip()
        if len(text) < 3:
            continue
        if clean.is_standalone_page_number(text):
            continue
        bbox = block.get("bbox")
        if clean.is_running_edge_line(text, bbox, page_height):
            continue
        if _is_edge_chapter_header(text, bbox):
            continue
        usable.append(block)
    return usable


def _is_edge_chapter_header(text: str, bbox: Any) -> bool:
    """Header bab yang terbaca sebagai paragraf di tepi atas halaman."""

    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False
    try:
        top = float(bbox[1])
    except (TypeError, ValueError):
        return False
    if top > 95.0:
        return False
    value = " ".join(text.split())
    return len(value) <= 80 and bool(
        re.match(r"^(BAB|BAGIAN|CHAPTER)\b", value, re.IGNORECASE)
    )


def baseline_printed_page_number(baseline: Optional[dict[str, Any]]) -> Optional[int]:
    """Nomor halaman cetak dari blok angka yang berdiri sendiri."""

    if not baseline:
        return None
    for block in baseline.get("blocks") or []:
        text = str(block.get("text") or "").strip()
        if not clean.is_standalone_page_number(text):
            continue
        digits = re.sub(r"[^0-9]", "", text)
        if digits and len(digits) <= 4:
            number = int(digits)
            if 1 <= number <= 9999:
                return number
    return None


# ----------------------------------------------------------------------
# Token
# ----------------------------------------------------------------------
def _token_spans(text: str) -> list[re.Match[str]]:
    return list(TOKEN_RE.finditer(text or ""))


def _token_key(value: str) -> str:
    return value.lower()


def _baseline_tokens(
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for block in blocks:
        for match in _token_spans(str(block.get("text") or "")):
            tokens.append(
                {
                    "key": _token_key(match.group(0)),
                    "original": match.group(0),
                    "block_id": block.get("block_id"),
                    "bbox": block.get("bbox"),
                }
            )
    return tokens


def _token_counter(blocks: list[dict[str, Any]]) -> Counter[str]:
    """Token halaman untuk mengukur apakah isi baseline masih ada.

    Blok tabel ikut dihitung karena isi tabel tetap informasi halaman; yang
    tidak boleh disentuh restorasi token hanyalah teks di dalam tabel.
    """

    counter: Counter[str] = Counter()
    for block in blocks:
        counter.update(
            _token_key(match.group(0))
            for match in _token_spans(str(block.get("text") or ""))
        )
    return counter


def _coverage(text: str, counter: Counter[str]) -> float:
    keys = [_token_key(match.group(0)) for match in _token_spans(text)]
    if not keys:
        return 1.0
    local = Counter(keys)
    matched = sum(min(count, counter[key]) for key, count in local.items())
    return matched / len(keys)


def _overlap_score(llama_keys: list[str], baseline_keys: list[str]) -> float:
    if not llama_keys or not baseline_keys:
        return 0.0
    return len(set(llama_keys) & set(baseline_keys)) / len(set(llama_keys))


def _plausible_pair(before: str, after: str) -> bool:
    """Substitusi wajar bila awal kata tetap atau kedua kata sangat mirip.

    Parser yang salah memasangkan blok dapat menghasilkan pasangan seperti
    ``jember`` -> ``image``. Pasangan seperti itu tidak boleh masuk ke teks.
    """

    if not before or not after:
        return False
    if before[0].lower() == after[0].lower():
        return True
    return (
        difflib.SequenceMatcher(None, before.lower(), after.lower()).ratio() >= 0.75
    )


def _collect_edits(
    text: str, base_tokens: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Pasangan token 1:1 yang berbeda antara keluaran parser dan baseline."""

    matches = _token_spans(text)
    if len(matches) < MIN_BLOCK_TOKENS or not base_tokens:
        return []

    llama_keys = [_token_key(match.group(0)) for match in matches]
    base_keys = [token["key"] for token in base_tokens]
    matcher = difflib.SequenceMatcher(None, base_keys, llama_keys, autojunk=False)
    opcodes = matcher.get_opcodes()

    aligned = sum(
        j2 - j1 for tag, _i1, _i2, j1, j2 in opcodes if tag in {"equal", "replace"}
    )
    if aligned / len(llama_keys) < MIN_ALIGNMENT_RATIO:
        return []

    edits: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag != "replace" or (i2 - i1) != (j2 - j1):
            continue
        for offset in range(i2 - i1):
            base = base_tokens[i1 + offset]
            llama_match = matches[j1 + offset]
            llama_key = llama_keys[j1 + offset]
            if base["key"] == llama_key:
                continue
            if len(base["key"]) < MIN_TOKEN_CHARS or len(llama_key) < MIN_TOKEN_CHARS:
                continue
            if base["key"].isdigit() or llama_key.isdigit():
                continue
            if not _plausible_pair(llama_match.group(0), base["original"]):
                continue
            edits.append(
                {
                    "start": llama_match.start(),
                    "end": llama_match.end(),
                    "before": llama_match.group(0),
                    "after": base["original"],
                    "baseline_block_id": base.get("block_id"),
                    "baseline_bbox": base.get("bbox"),
                    "context": text[
                        max(0, llama_match.start() - 30) : llama_match.end() + 30
                    ],
                }
            )
    return edits


def local_baseline_tokens(
    text: str, base_blocks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Token baseline pada jendela blok yang paling cocok dengan satu blok.

    Alignment per halaman bisa memilih pasangan yang salah ketika blok
    LlamaParse bergeser dari blok baseline. Jendela lokal membuat pasangan
    substitusi tetap satu-lawan-satu; stream satu halaman dipakai bila blok
    parser menggabungkan beberapa blok baseline.
    """

    llama_keys = [_token_key(match.group(0)) for match in _token_spans(text)]
    if not llama_keys or not base_blocks:
        return []

    best_index = 0
    best_score = 0.0
    for index, block in enumerate(base_blocks):
        block_keys = [
            _token_key(match.group(0))
            for match in _token_spans(str(block.get("text") or ""))
        ]
        score = _overlap_score(llama_keys, block_keys)
        if score > best_score:
            best_score = score
            best_index = index
    if best_score <= 0.0:
        return []

    windows = [
        base_blocks[best_index : best_index + 1],
        base_blocks[max(0, best_index - 1) : min(len(base_blocks), best_index + 2)],
        base_blocks,
    ]
    best_stream: list[dict[str, Any]] = []
    best_key: tuple[int, float] = (0, 0.0)
    for window in windows:
        stream = _baseline_tokens(window)
        edits = _collect_edits(text, stream)
        if not edits:
            continue
        base_keys = [token["key"] for token in stream]
        llama_keys_all = [_token_key(m.group(0)) for m in _token_spans(text)]
        matcher = difflib.SequenceMatcher(
            None, base_keys, llama_keys_all, autojunk=False
        )
        aligned = sum(
            j2 - j1
            for tag, _i1, _i2, j1, j2 in matcher.get_opcodes()
            if tag in {"equal", "replace"}
        )
        ratio = aligned / len(llama_keys_all)
        key = (len(edits), ratio)
        if key > best_key:
            best_key = key
            best_stream = stream
    return best_stream


# ----------------------------------------------------------------------
# Restorasi token
# ----------------------------------------------------------------------
def restore_block_tokens(
    text: str,
    base_tokens: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Mengembalikan token yang disubstitusi parser dengan kata dari PDF.

    Hanya pasangan satu-lawan-satu pada blok yang sebagian besar isinya cocok
    dengan baseline yang dipulihkan. Tambahan parser dan penghapusan kecil
    dibiarkan untuk direview terpisah.
    """

    edits = _collect_edits(text, base_tokens)
    if not edits:
        return text, []

    for edit in sorted(edits, key=lambda item: item["start"], reverse=True):
        text = text[: edit["start"]] + edit["after"] + text[edit["end"] :]

    return text, edits


# ----------------------------------------------------------------------
# Restorasi sel tabel
# ----------------------------------------------------------------------
def _edit_distance_one(before: str, after: str) -> bool:
    """True bila kedua kata berbeda tepat satu sisip/hapus/ganti huruf."""

    if before == after:
        return False
    first, second = before.lower(), after.lower()
    if abs(len(first) - len(second)) > 1:
        return False
    if len(first) == len(second):
        return sum(1 for a, b in zip(first, second) if a != b) == 1
    if len(first) > len(second):
        first, second = second, first
    index = 0
    skipped = False
    while index < len(first) and index + (1 if skipped else 0) < len(second):
        if first[index] == second[index + (1 if skipped else 0)]:
            index += 1
        elif skipped:
            return False
        else:
            skipped = True
    return True


def _table_edit_plausible(before: str, after: str) -> bool:
    """Syarat ketat untuk sel tabel: salah ketik satu huruf, awal sama."""

    if not _plausible_pair(before, after):
        return False
    if before[0].lower() != after[0].lower():
        return False
    if _edit_distance_one(before, after):
        return True
    return (
        difflib.SequenceMatcher(None, before.lower(), after.lower()).ratio() >= 0.9
    )


def _baseline_table_cells(
    baseline_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sel tabel baseline PyMuPDF beserta token dan koordinatnya."""

    cells: list[dict[str, Any]] = []
    for block in baseline_blocks:
        if str(block.get("content_type")) != "table":
            continue
        table = block.get("table") or {}
        rows = table.get("cells") or table.get("rows") or []
        if not isinstance(rows, list):
            continue
        for row_index, row in enumerate(rows):
            if not isinstance(row, list):
                continue
            for column_index, value in enumerate(row):
                text = str(value or "")
                tokens = _baseline_tokens(
                    [
                        {
                            "text": text,
                            "block_id": block.get("block_id"),
                            "bbox": block.get("bbox"),
                        }
                    ]
                )
                if not tokens:
                    continue
                cells.append(
                    {
                        "row": row_index,
                        "column": column_index,
                        "block_id": block.get("block_id"),
                        "text": text,
                        "tokens": tokens,
                    }
                )
    return cells


def _replace_in_line(line: str, before: str, after: str) -> tuple[str, int]:
    pattern = re.compile(
        rf"(?<![0-9A-Za-z]){re.escape(before)}(?![0-9A-Za-z])"
    )
    return pattern.subn(after, line)


def restore_table_tokens(
    block: dict[str, Any],
    baseline_blocks: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Mengembalikan salah ketik parser di sel tabel dari baseline PDF.

    Tabel tetap mempertahankan struktur parser; yang diganti hanya kata di
    dalam sel. Syaratnya lebih ketat daripada teks biasa karena sel pendek dan
    mudah salah pasang: huruf awal sama dan beda tepat satu huruf.
    """

    table = block.get("table") or {}
    rows = table.get("cells")
    if not isinstance(rows, list) or not rows:
        return block, []
    baseline_cells = _baseline_table_cells(baseline_blocks)
    if not baseline_cells:
        return block, []

    edits: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list):
            continue
        for column_index, value in enumerate(row):
            text = str(value or "")
            matches = _token_spans(text)
            if len(matches) < TABLE_CELL_MIN_TOKENS:
                continue
            llama_keys = [_token_key(match.group(0)) for match in matches]

            best: Optional[dict[str, Any]] = None
            best_score = 0.0
            for candidate in baseline_cells:
                score = _overlap_score(
                    llama_keys, [token["key"] for token in candidate["tokens"]]
                )
                if score > best_score:
                    best_score = score
                    best = candidate
            if best is None or best_score < TABLE_CELL_MIN_OVERLAP:
                continue

            base_tokens = best["tokens"]
            base_keys = [token["key"] for token in base_tokens]
            matcher = difflib.SequenceMatcher(
                None, base_keys, llama_keys, autojunk=False
            )
            opcodes = matcher.get_opcodes()
            aligned = sum(
                j2 - j1
                for tag, _i1, _i2, j1, j2 in opcodes
                if tag in {"equal", "replace"}
            )
            if aligned / len(llama_keys) < TABLE_CELL_MIN_OVERLAP:
                continue

            cell_edits: list[dict[str, Any]] = []
            for tag, i1, i2, j1, j2 in opcodes:
                if tag != "replace" or (i2 - i1) != (j2 - j1):
                    continue
                for offset in range(i2 - i1):
                    base = base_tokens[i1 + offset]
                    match = matches[j1 + offset]
                    if base["key"] == llama_keys[j1 + offset]:
                        continue
                    if (
                        len(base["key"]) < MIN_TOKEN_CHARS
                        or len(llama_keys[j1 + offset]) < MIN_TOKEN_CHARS
                    ):
                        continue
                    if base["key"].isdigit() or llama_keys[j1 + offset].isdigit():
                        continue
                    if not _table_edit_plausible(match.group(0), base["original"]):
                        continue
                    cell_edits.append(
                        {
                            "start": match.start(),
                            "end": match.end(),
                            "before": match.group(0),
                            "after": base["original"],
                            "baseline_block_id": base.get("block_id"),
                            "baseline_cell": {
                                "row": best["row"],
                                "column": best["column"],
                            },
                        }
                    )

            if not cell_edits:
                continue
            restored = text
            for edit in sorted(
                cell_edits, key=lambda item: item["start"], reverse=True
            ):
                restored = (
                    restored[: edit["start"]]
                    + edit["after"]
                    + restored[edit["end"] :]
                )
            rows[row_index][column_index] = restored
            for edit in cell_edits:
                edits.append(
                    {
                        **edit,
                        "row": row_index,
                        "column": column_index,
                        "context": text.strip()[:120],
                    }
                )

    if not edits:
        return block, []

    # Sel sudah berubah; representasi markdown/csv dan teks blok diselaraskan
    # agar tidak ada dua versi isi tabel yang berbeda.
    for edit in edits:
        line_index = edit["row"] + 1
        md_lines = str(table.get("md") or "").splitlines()
        if 0 <= line_index < len(md_lines):
            md_lines[line_index], _ = _replace_in_line(
                md_lines[line_index], edit["before"], edit["after"]
            )
            table["md"] = "\n".join(md_lines)

        csv_lines = str(table.get("csv") or "").splitlines()
        if 0 <= edit["row"] < len(csv_lines):
            csv_lines[edit["row"]], _ = _replace_in_line(
                csv_lines[edit["row"]], edit["before"], edit["after"]
            )
            table["csv"] = "\n".join(csv_lines)

    if isinstance(table.get("md"), str) and table["md"]:
        if not block.get("raw_text"):
            block["raw_text"] = block.get("text")
        block["text"] = table["md"]
    # ``rows`` dan ``cells`` bisa menjadi objek berbeda setelah serialisasi.
    if table.get("rows") is not rows:
        table["rows"] = rows
    block["table"] = table
    return block, edits


# ----------------------------------------------------------------------
# Blok baru dari baseline
# ----------------------------------------------------------------------
def _context_fields(context: structure.DocumentContext) -> dict[str, Any]:
    return {
        "chapter": context.chapter,
        "section": context.section,
        "section_source": context.section_source,
        "subsection": context.subsection,
        "plant_name": context.plant_name,
        "plant_name_source": context.plant_source,
        "disease_name": context.disease_name,
        "disease_name_source": context.disease_source,
    }


def _make_baseline_block(
    page_number: int,
    sequence: int,
    text: str,
    bbox: Any,
    content_type: str,
    context: structure.DocumentContext,
    page_meta: dict[str, Any],
    options: dict[str, Any],
    notes: list[str],
) -> dict[str, Any]:
    if content_type not in BODY_CONTENT_TYPES:
        content_type = "paragraph"
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        bbox = [0.0, 0.0, 0.0, 0.0]
        notes = list(notes) + ["bbox_unavailable"]
    return {
        "schema_version": base_config.SCHEMA_VERSION,
        "block_id": f"{config.DOCUMENT_ID}_P{page_number:03d}_B{sequence:03d}",
        "document_id": config.DOCUMENT_ID,
        "page_number": page_number,
        "printed_page_number": page_meta.get("printed_page_number_parsed"),
        "chapter": context.chapter,
        "section": context.section,
        "section_source": context.section_source,
        "subsection": context.subsection,
        "content_type": content_type,
        "sequence_number": sequence,
        "text": text,
        "extraction_status": "needs_manual_review",
        "parsing_notes": list(notes),
        "bbox": bbox,
        "cleaning_actions": ["recovered_from_pymupdf_text_layer"],
        "raw_text": None,
        "table": None,
        "text_source": "pymupdf_text_layer",
        "parser_engine": "LlamaParse+PyMuPDF",
        "parser_tier": page_meta.get("parser_tier"),
        "parser_version": page_meta.get("parser_version"),
        "parser_confidence": page_meta.get("confidence"),
        "parser_item_type": "baseline_text",
        "heading_level": None,
        "plant_name": context.plant_name,
        "plant_name_source": context.plant_source,
        "disease_name": context.disease_name,
        "disease_name_source": context.disease_source,
        "chunk_type": structure.chunk_type_for_block(context, content_type),
    }


def _next_sequence(blocks: list[dict[str, Any]]) -> int:
    return max((int(block.get("sequence_number") or 0) for block in blocks), default=0) + 1


# ----------------------------------------------------------------------
# Rekonsiliasi per halaman
# ----------------------------------------------------------------------
def reconcile_page(
    page_number: int,
    blocks: list[dict[str, Any]],
    baseline: Optional[dict[str, Any]],
    context: structure.DocumentContext,
    page_meta: dict[str, Any],
    options: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Merekonsiliasi satu halaman; mengembalikan blok, ringkasan, dan event."""

    summary: dict[str, Any] = {
        "page_number": page_number,
        "tokens_restored": 0,
        "table_tokens_restored": 0,
        "blocks_recovered": 0,
        "fallback": False,
        "baseline_chars": 0,
        "llamaparse_chars": 0,
    }
    events: list[dict[str, Any]] = []
    if not baseline:
        return blocks, summary, events

    base_blocks = _usable_baseline_blocks(
        baseline.get("blocks") or [], float(baseline.get("height") or 0.0)
    )
    if not base_blocks:
        return blocks, summary, events

    baseline_chars = sum(len(str(block.get("text") or "")) for block in base_blocks)
    llama_chars = sum(
        len(str(block.get("text") or ""))
        for block in blocks
        if block.get("content_type") != "table" and not block.get("table")
    )
    summary["baseline_chars"] = baseline_chars
    summary["llamaparse_chars"] = llama_chars

    # 1. Halaman yang teksnya hilang hampir seluruhnya.
    if baseline_chars >= FALLBACK_MIN_BASELINE_CHARS and llama_chars < (
        baseline_chars * FALLBACK_MAX_RATIO
    ):
        recovered: list[dict[str, Any]] = []
        for index, base in enumerate(base_blocks, start=1):
            text = str(base.get("text") or "").strip()
            recovered.append(
                _make_baseline_block(
                    page_number=page_number,
                    sequence=index,
                    text=text,
                    bbox=base.get("bbox"),
                    content_type=str(base.get("content_type") or "paragraph"),
                    context=context,
                    page_meta=page_meta,
                    options=options,
                    notes=[
                        "page_text_recovered_from_baseline",
                        "parser_lost_page_text",
                    ],
                )
            )
        summary["fallback"] = True
        summary["blocks_recovered"] = len(recovered)
        events.append(
            {
                "scope": "page",
                "page_number": page_number,
                "action": "page_fallback",
                "reason": "parser_lost_page_text",
                "baseline_chars": baseline_chars,
                "llamaparse_chars": llama_chars,
                "blocks_recovered": len(recovered),
                "baseline_block_ids": [b.get("block_id") for b in base_blocks],
            }
        )
        LOGGER.info(
            "Rekonsiliasi halaman %s: teks dipulihkan dari baseline (%s blok)",
            page_number,
            len(recovered),
        )
        return recovered, summary, events

    # 2. Kembalikan kata yang disubstitusi parser.
    for block in blocks:
        content_type = str(block.get("content_type"))
        if content_type not in BODY_CONTENT_TYPES or block.get("table"):
            continue
        text = str(block.get("text") or "")
        local_tokens = local_baseline_tokens(text, base_blocks)
        restored, edits = restore_block_tokens(text, local_tokens)
        if not edits:
            continue
        block["text"] = restored
        notes = list(block.get("parsing_notes") or [])
        if "verbatim_token_restored" not in notes:
            notes.append("verbatim_token_restored")
        block["parsing_notes"] = notes
        if str(block.get("text_source") or "llamaparse") == "llamaparse":
            block["text_source"] = "llamaparse+baseline"
        summary["tokens_restored"] += len(edits)
        for edit in edits:
            events.append(
                {
                    "scope": "block",
                    "page_number": page_number,
                    "block_id": block.get("block_id"),
                    "action": "token_restore",
                    "before": edit["before"],
                    "after": edit["after"],
                    "similarity": round(
                        difflib.SequenceMatcher(
                            None, edit["before"].lower(), edit["after"].lower()
                        ).ratio(),
                        3,
                    ),
                    "context": edit["context"],
                    "baseline_block_id": edit["baseline_block_id"],
                    "baseline_bbox": edit["baseline_bbox"],
                }
            )

    # 2b. Salah ketik parser di dalam sel tabel.
    for block in blocks:
        if str(block.get("content_type")) != "table" or not block.get("table"):
            continue
        restored_block, edits = restore_table_tokens(
            block, baseline.get("blocks") or []
        )
        if not edits:
            continue
        notes = list(restored_block.get("parsing_notes") or [])
        if "verbatim_table_token_restored" not in notes:
            notes.append("verbatim_table_token_restored")
        restored_block["parsing_notes"] = notes
        if str(restored_block.get("text_source") or "llamaparse") == "llamaparse":
            restored_block["text_source"] = "llamaparse+baseline"
        summary["table_tokens_restored"] += len(edits)
        for edit in edits:
            events.append(
                {
                    "scope": "table_cell",
                    "page_number": page_number,
                    "block_id": restored_block.get("block_id"),
                    "action": "table_token_restore",
                    "row": edit.get("row"),
                    "column": edit.get("column"),
                    "before": edit["before"],
                    "after": edit["after"],
                    "similarity": round(
                        difflib.SequenceMatcher(
                            None, edit["before"].lower(), edit["after"].lower()
                        ).ratio(),
                        3,
                    ),
                    "context": edit["context"],
                    "baseline_block_id": edit.get("baseline_block_id"),
                    "baseline_cell": edit.get("baseline_cell"),
                }
            )

    # 3. Pulihkan blok di ujung halaman yang hilang seluruhnya.
    counter = _token_counter(blocks)
    body = [
        block
        for block in base_blocks
        if block.get("content_type") in BODY_CONTENT_TYPES
        and len(str(block.get("text") or "")) >= RECOVER_MIN_CHARS
    ]
    if body:
        start = len(body)
        while start > 0 and _coverage(str(body[start - 1].get("text") or ""), counter) < (
            RECOVER_MAX_COVERAGE
        ):
            start -= 1
        trailing = body[start:]
        previous = body[start - 1] if start > 0 else None
        anchored = previous is None or _coverage(
            str(previous.get("text") or ""), counter
        ) >= RECOVER_ANCHOR_COVERAGE
        if trailing and anchored:
            sequence = _next_sequence(blocks)
            for base in trailing:
                blocks.append(
                    _make_baseline_block(
                        page_number=page_number,
                        sequence=sequence,
                        text=str(base.get("text") or "").strip(),
                        bbox=base.get("bbox"),
                        content_type=str(base.get("content_type") or "paragraph"),
                        context=context,
                        page_meta=page_meta,
                        options=options,
                        notes=[
                            "block_recovered_from_baseline",
                            "recovered_at_page_end",
                        ],
                    )
                )
                summary["blocks_recovered"] += 1
                events.append(
                    {
                        "scope": "block",
                        "page_number": page_number,
                        "block_id": blocks[-1]["block_id"],
                        "action": "block_recover",
                        "reason": "trailing_block_missing_in_parser_output",
                        "baseline_block_id": base.get("block_id"),
                        "baseline_bbox": base.get("bbox"),
                        "text": str(base.get("text") or "")[:200],
                    }
                )
                sequence += 1
            if trailing:
                LOGGER.info(
                    "Rekonsiliasi halaman %s: %s blok ujung dipulihkan",
                    page_number,
                    len(trailing),
                )

    return blocks, summary, events


# ----------------------------------------------------------------------
# Laporan
# ----------------------------------------------------------------------
def write_reports(
    run_id: str,
    page_summaries: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    reconciled = [
        item
        for item in page_summaries
        if item.get("tokens_restored")
        or item.get("table_tokens_restored")
        or item.get("blocks_recovered")
        or item.get("fallback")
    ]
    summary = {
        "schema_version": "1.0.0",
        "document_id": config.DOCUMENT_ID,
        "run_id": run_id,
        "generated_at": utc_now(),
        "authority": "pymupdf_text_layer",
        "baseline_snapshot": str(
            config.BASELINE_MANIFEST.relative_to(config.PROJECT_ROOT)
        ).replace("\\", "/"),
        "pages_scanned": len(page_summaries),
        "pages_reconciled": len(reconciled),
        "tokens_restored": sum(int(item.get("tokens_restored") or 0) for item in page_summaries),
        "table_tokens_restored": sum(
            int(item.get("table_tokens_restored") or 0) for item in page_summaries
        ),
        "blocks_recovered": sum(
            int(item.get("blocks_recovered") or 0) for item in page_summaries
        ),
        "fallback_pages": sorted(
            int(item["page_number"]) for item in page_summaries if item.get("fallback")
        ),
        "restored_by_page": {
            str(item["page_number"]): int(item.get("tokens_restored") or 0)
            for item in reconciled
            if item.get("tokens_restored")
        },
        "table_restored_by_page": {
            str(item["page_number"]): int(item.get("table_tokens_restored") or 0)
            for item in reconciled
            if item.get("table_tokens_restored")
        },
        "recovered_by_page": {
            str(item["page_number"]): int(item.get("blocks_recovered") or 0)
            for item in reconciled
            if item.get("blocks_recovered")
        },
        "event_count": len(events),
    }
    paths = config.report_paths()
    write_json(paths["reconciliations"], summary)
    write_jsonl(paths["reconciliation_events"], events)
    LOGGER.info(
        "Rekonsiliasi selesai: %s halaman, %s token teks, %s token tabel, "
        "%s blok, fallback=%s",
        summary["pages_reconciled"],
        summary["tokens_restored"],
        summary["table_tokens_restored"],
        summary["blocks_recovered"],
        summary["fallback_pages"],
    )
    return summary
