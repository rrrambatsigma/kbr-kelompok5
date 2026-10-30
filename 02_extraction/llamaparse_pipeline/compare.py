"""Perbandingan keluaran LlamaParse dengan baseline PyMuPDF DOC002."""

from __future__ import annotations

import logging
import re
import statistics
from collections import Counter
from typing import Any, Optional

from pdf_pipeline.output import utc_now, write_json

from . import config, clean, quality, store


LOGGER = logging.getLogger("kbr_llamaparse")

CER_THRESHOLD = 0.01
MAX_PAGE_CONTENT_LOSS = 0.10
REPEATED_LINE_PAGE_RATIO = 0.30
EDGE_LINE_PAGE_RATIO = 0.10
EXPECTED_CHAPTER_COUNT = 15
MULTI_COLUMN_PAGES = (92, 94, 95)
# Halaman 1 adalah sampul ResearchGate (judul, sitasi, profil penulis), bukan
# isi buku. Parser memindahkan teks pembungkusnya ke header/footer halaman,
# jadi halaman ini tidak dipakai sebagai pembanding CER.
NON_CONTENT_PAGES = {
    1: "researchgate_cover_page",
}

PAGE_NUMBER_ONLY_RE = re.compile(r"^[-–—\s]*\d{1,4}[-–—\s]*$")
CHAPTER_LINE_RE = re.compile(
    r"^(bab|bagian|chapter)\s+(?:\d+|[ivxlcdm]+)\b", re.IGNORECASE
)


def levenshtein(first: str, second: str) -> int:
    """Jarak edit Myers bit-parallel (cepat untuk teks per halaman)."""

    if first == second:
        return 0
    if not first:
        return len(second)
    if not second:
        return len(first)
    if len(first) > len(second):
        first, second = second, first

    length = len(first)
    mask = (1 << length) - 1
    peq: dict[str, int] = {}
    for index, char in enumerate(first):
        peq[char] = peq.get(char, 0) | (1 << index)

    pv = mask
    mv = 0
    score = length
    last = 1 << (length - 1)

    for char in second:
        eq = peq.get(char, 0)
        xv = eq | mv
        xh = (((eq & pv) + pv) ^ pv) | eq
        ph = (mv | ~(xh | pv)) & mask
        mh = pv & xh
        if ph & last:
            score += 1
        elif mh & last:
            score -= 1
        ph = ((ph << 1) | 1) & mask
        mh = (mh << 1) & mask
        pv = (mh | ~(xv | ph)) & mask
        mv = ph & xv

    return int(score)


def normalize_for_comparison(text: str) -> str:
    value = clean.strip_markdown(text or "").lower()
    value = re.sub(r"[^0-9a-zà-ÿ ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _repeated_lines(page_texts: list[str]) -> set[str]:
    counter: Counter[str] = Counter()
    pages_with_line: Counter[str] = Counter()
    for text in page_texts:
        lines = {
            normalize_for_comparison(line)
            for line in (text or "").split("\n")
            if normalize_for_comparison(line)
        }
        for line in lines:
            pages_with_line[line] += 1
        counter.update(lines)
    if not page_texts:
        return set()
    threshold = max(2, int(len(page_texts) * REPEATED_LINE_PAGE_RATIO))
    return {
        line
        for line, count in pages_with_line.items()
        if count >= threshold and len(line) <= 120
    }


def _remove_lines(text: str, lines: set[str]) -> str:
    kept = [
        line
        for line in (text or "").split("\n")
        if normalize_for_comparison(line) not in lines
    ]
    return "\n".join(kept)


def _edge_header_lines(page_texts: list[str]) -> set[str]:
    """Baris header/footer berulang yang muncul di tepi halaman.

    Baseline PyMuPDF menyimpan running header sebagai baris tersendiri
    ("16", "Penyakit Tanaman dan Pengendaliannya"), sedangkan LlamaParse
    memisahkannya ke metadata. Tanpa penyesuaian ini, pembuangan header yang
    benar justru terhitung sebagai kesalahan teks.
    """

    counter: Counter[str] = Counter()
    for text in page_texts:
        lines = [
            normalize_for_comparison(line) for line in (text or "").split("\n")
        ]
        edges = {line for line in lines[:2] + lines[-2:] if line}
        counter.update(edges)
    if not page_texts:
        return set()
    threshold = max(2, int(len(page_texts) * EDGE_LINE_PAGE_RATIO))
    return {
        line
        for line, count in counter.items()
        if count >= threshold and len(line) <= 120
    }


def _strip_edge_noise(
    text: str, repeated: set[str], edge_lines: set[str]
) -> str:
    """Membuang header/footer dari teks pembanding, bukan dari keluaran.

    Hanya baris pada dua baris awal/akhir halaman yang diperiksa agar baris isi
    di tengah halaman tidak ikut hilang.
    """

    lines = (text or "").split("\n")
    last_index = len(lines) - 1
    kept: list[str] = []
    for index, line in enumerate(lines):
        normalized = normalize_for_comparison(line)
        if not normalized:
            continue
        at_edge = index <= 1 or index >= last_index - 1
        if at_edge and (
            PAGE_NUMBER_ONLY_RE.match(normalized)
            or CHAPTER_LINE_RE.match(normalized)
            or normalized in repeated
            or normalized in edge_lines
        ):
            continue
        kept.append(line)
    return "\n".join(kept)


def content_loss_cer(baseline_tokens: list[str], new_tokens: list[str]) -> float:
    """CER terhadap isi baseline saja, mengabaikan tambahan dari parser.

    Token yang hanya ada di keluaran LlamaParse (mis. label diagram yang
    berhasil dibaca) dibuang lebih dulu, sehingga skor mengukur kehilangan
    informasi. Tambahan isi tetap dilaporkan terpisah untuk review manual.
    """

    allowed = Counter(baseline_tokens)
    kept: list[str] = []
    for token in new_tokens:
        if allowed[token] > 0:
            allowed[token] -= 1
            kept.append(token)
    baseline_text = " ".join(baseline_tokens)
    kept_text = " ".join(kept)
    return levenshtein(baseline_text, kept_text) / max(len(baseline_text), 1)


def content_recall_loss(baseline_tokens: list[str], new_tokens: list[str]) -> float:
    """Kehilangan isi tanpa terpengaruh urutan blok.

    Urutan baca yang lebih baik (mis. tabel dipindah ke tempat semestinya)
    bukan kehilangan informasi. Metrik ini mengukur token baseline yang tidak
    muncul kembali di keluaran, sehingga hanya isi yang benar-benar hilang
    yang dihitung.
    """

    if not baseline_tokens:
        return 0.0
    baseline = Counter(baseline_tokens)
    new = Counter(new_tokens)
    matched = sum(min(count, new[token]) for token, count in baseline.items())
    return 1.0 - matched / sum(baseline.values())


def _chapter_list(blocks: list[dict[str, Any]]) -> list[str]:
    chapters: list[str] = []
    for block in blocks:
        if block.get("content_type") != "chapter_heading":
            continue
        chapter = block.get("chapter")
        if not chapter:
            continue
        chapter = str(chapter)
        if chapters and chapters[-1] == chapter:
            continue
        # "Bab 1" lalu "Bab 1 — Penyakit Padi" adalah satu bab.
        if chapters and re.match(r"^(BAB|BAGIAN)\s+\S+$", chapters[-1], re.IGNORECASE):
            if chapter.startswith(chapters[-1]):
                chapters[-1] = chapter
                continue
        chapters.append(chapter)
    return chapters


def _chapter_numbers(chapters: list[str]) -> list[int]:
    """Nomor bab unik dari judul yang berawalan ``Bab N``."""

    numbers: list[int] = []
    for chapter in chapters:
        match = re.match(r"^(?:BAB|BAGIAN|CHAPTER)\s+(\d+)\b", chapter, re.IGNORECASE)
        if not match:
            continue
        number = int(match.group(1))
        if number not in numbers:
            numbers.append(number)
    return numbers


def _content_chapter_numbers(blocks: list[dict[str, Any]]) -> list[int]:
    """Nomor bab yang punya blok isi, bukan sekadar judul di daftar isi.

    Daftar bab di halaman sampul belakang sering terbaca sebagai heading;
    dengan menghitung bab yang punya isi, hitungan tidak terpengaruh.
    """

    chapters: list[str] = []
    for block in blocks:
        if block.get("content_type") not in {
            "paragraph",
            "list_item",
            "table",
            "figure_caption",
        }:
            continue
        chapter = block.get("chapter")
        if chapter and (not chapters or chapters[-1] != chapter):
            if chapter not in chapters:
                chapters.append(str(chapter))
    return _chapter_numbers(chapters)


def _table_pages(blocks: list[dict[str, Any]]) -> list[int]:
    return sorted(
        {
            int(block["page_number"])
            for block in blocks
            if block.get("content_type") == "table"
        }
    )


def _scope_pages(manifest: dict[str, Any]) -> list[int]:
    total = int(manifest.get("total_pdf_pages") or 0)
    target = ((manifest.get("options") or {}).get("page_ranges") or {}).get(
        "target_pages"
    )
    if not target:
        return list(range(1, total + 1))
    selected: set[int] = set()
    for part in str(target).split(","):
        piece = part.strip()
        if not piece:
            continue
        if "-" in piece:
            start_text, end_text = piece.split("-", 1)
            selected.update(range(int(start_text), int(end_text) + 1))
        else:
            selected.add(int(piece))
    return sorted(page for page in selected if 1 <= page <= total)


def compare_internal(run_id: str) -> dict[str, Any]:
    """Verifikasi tanpa baseline PyMuPDF (DOC003 dan DOC004).

    Tanpa pembanding text layer, gate memeriksa hal-hal yang bisa dibuktikan
    dari keluaran parser sendiri: kelengkapan halaman, lantai karakter,
    konsistensi nomor halaman cetak, jumlah bagian, dan tabel yang diharapkan
    muncul pada halaman tertentu.
    """

    profile = config.profile()
    normalized = store.ensure_normalized(run_id)
    pages = normalized["pages"]
    blocks = normalized["blocks"]
    manifest = store.load_manifest(run_id)
    options = manifest.get("options") or {}
    page_ranges = (options.get("page_ranges") or {}).get("target_pages")
    is_full_run = not page_ranges

    expected = quality._expected_pages(manifest)
    present = [int(page["page_number"]) for page in pages]
    missing_pages = sorted(set(expected) - set(present))

    short_pages = [
        int(page["page_number"])
        for page in pages
        if int(page.get("text_char_count") or 0) < quality.MIN_PAGE_CHARS
        and int(page["page_number"]) not in profile.blank_pages
    ]
    failed_pages = [
        int(page["page_number"])
        for page in pages
        if page.get("extraction_status") == "extraction_error"
    ]
    empty_pages = [
        int(page["page_number"])
        for page in pages
        if int(page.get("block_count") or 0) == 0
        and int(page["page_number"]) not in profile.blank_pages
    ]

    chapters: list[str] = []
    for block in blocks:
        if block.get("content_type") != "chapter_heading":
            continue
        if not (
            profile.body_start
            <= int(block.get("page_number") or 0)
            <= profile.body_end
        ):
            continue
        chapter = str(block.get("chapter") or "").strip()
        if chapter and chapter not in chapters:
            chapters.append(chapter)

    offsets: Counter[int] = Counter()
    offset_mismatch: list[int] = []
    for page in pages:
        page_number = int(page["page_number"])
        printed = page.get("printed_page_number")
        if printed is None or not (profile.body_start <= page_number <= profile.body_end):
            continue
        offset = page_number - int(printed)
        offsets[offset] += 1
        if offset != profile.printed_offset:
            offset_mismatch.append(page_number)

    dominant_offset = offsets.most_common(1)[0][0] if offsets else None
    printed_detected = sum(1 for page in pages if page.get("printed_page_number") is not None)
    printed_coverage = printed_detected / len(pages) if pages else 0.0

    table_pages = sorted(
        {int(block["page_number"]) for block in blocks if block.get("content_type") == "table"}
    )
    missing_table_pages = [page for page in profile.table_pages if page not in table_pages]

    body_blocks = [
        block
        for block in blocks
        if profile.body_start <= int(block.get("page_number") or 0) <= profile.body_end
        and block.get("content_type") != "chapter_heading"
    ]
    # Pada pilot yang dimulai di tengah bab, konteks bab baru terbentuk setelah
    # heading bab pertama; blok sebelumnya tidak dihitung sebagai kehilangan.
    first_chapter_page = min(
        (
            int(block["page_number"])
            for block in blocks
            if block.get("content_type") == "chapter_heading"
        ),
        default=profile.body_start,
    )
    body_blocks = [
        block
        for block in body_blocks
        if int(block.get("page_number") or 0) >= first_chapter_page
    ]
    with_context = sum(1 for block in body_blocks if block.get("chapter"))
    context_ratio = with_context / len(body_blocks) if body_blocks else 1.0

    gates: dict[str, dict[str, Any]] = {
        "pages_complete": {
            "passed": not missing_pages,
            "detail": f"missing={missing_pages[:20]}",
        },
        "no_failed_pages": {
            "passed": not failed_pages,
            "detail": f"failed={failed_pages[:20]}",
        },
        "page_text_floor": {
            "passed": not short_pages and not empty_pages,
            "detail": f"short={short_pages[:20]} empty={empty_pages[:20]}",
        },
        "printed_page_numbers": {
            "passed": (
                printed_detected > 0
                and dominant_offset == profile.printed_offset
                and not offset_mismatch
            ),
            "detail": (
                f"detected={printed_detected} coverage={printed_coverage:.2%} "
                f"dominant_offset={dominant_offset} expected={profile.printed_offset} "
                f"mismatch={offset_mismatch[:20]}"
            ),
        },
        "section_count": {
            "passed": (not is_full_run) or len(chapters) == profile.expected_sections,
            "detail": f"sections={len(chapters)} expected={profile.expected_sections}",
        },
        "tables_expected": {
            "passed": not missing_table_pages,
            "detail": (
                f"table_pages={table_pages} expected={list(profile.table_pages)} "
                f"missing={missing_table_pages}"
            ),
        },
        "context_coverage": {
            "passed": context_ratio >= 0.80,
            "detail": (
                f"blocks_with_chapter={with_context}/{len(body_blocks)} "
                f"ratio={context_ratio:.2%}"
            ),
        },
    }
    gate_passed = all(item["passed"] for item in gates.values())

    report = {
        "schema_version": "1.1.0",
        "document_id": config.DOCUMENT_ID,
        "run_id": run_id,
        "generated_at": utc_now(),
        "tier": options.get("tier"),
        "version": options.get("version"),
        "is_full_run": is_full_run,
        "gate_mode": "internal",
        "baseline": None,
        "pages_compared": len(present),
        "pages_missing_vs_baseline": missing_pages,
        "text_similarity": {
            "method": "not_computed_without_baseline",
            "cer_mean": None,
            "cer_noise_adjusted_mean": None,
            "cer_content_loss_mean": None,
            "cer_content_recall_mean": None,
        },
        "headings": {
            "baseline_chapter_headings": [],
            "llamaparse_chapter_headings": chapters,
            "llamaparse_chapter_count": len(chapters),
            "expected_chapter_count": profile.expected_sections,
        },
        "tables": {
            "baseline_pages": list(profile.table_pages),
            "llamaparse_pages": table_pages,
        },
        "printed_page_numbers": {
            "detected": printed_detected,
            "coverage": round(printed_coverage, 4),
            "dominant_offset": dominant_offset,
            "expected_offset": profile.printed_offset,
        },
        "multi_column_pages": [],
        "gates": gates,
        "gate_passed": gate_passed,
        "per_page": [],
    }
    write_json(config.report_paths()["comparison"], report)

    review: list[dict[str, Any]] = []
    for page_number in short_pages:
        review.append(
            {
                "scope": "page",
                "page_number": page_number,
                "reason": "page_text_too_short",
                "detail": "Teks halaman di bawah ambang minimum",
            }
        )
    for page_number in offset_mismatch:
        review.append(
            {
                "scope": "page",
                "page_number": page_number,
                "reason": "printed_page_offset_mismatch",
                "detail": f"expected_offset={profile.printed_offset}",
            }
        )
    for page_number in missing_table_pages:
        review.append(
            {
                "scope": "page",
                "page_number": page_number,
                "reason": "expected_table_missing",
                "detail": "Tabel yang diharapkan tidak terdeteksi pada halaman ini",
            }
        )
    quality.append_review(review)

    LOGGER.info(
        "Verifikasi internal (%s): halaman=%s/%s bagian=%s gate=%s",
        profile.document_id,
        len(present),
        len(expected),
        len(chapters),
        gate_passed,
    )
    return report


def compare_run(run_id: str) -> dict[str, Any]:
    if config.profile().gate_mode != "baseline":
        return compare_internal(run_id)

    from . import baseline as baseline_store

    baseline_pages = baseline_store.load_pages()
    baseline_blocks = baseline_store.load_blocks()

    normalized = store.ensure_normalized(run_id)
    pages = normalized["pages"]
    blocks = normalized["blocks"]
    manifest = store.load_manifest(run_id)
    options = manifest.get("options") or {}
    page_ranges = (options.get("page_ranges") or {}).get("target_pages")
    is_full_run = not page_ranges

    baseline_by_page = {int(page["page_number"]): page for page in baseline_pages}
    new_by_page = {int(page["page_number"]): page for page in pages}
    common_pages = sorted(set(baseline_by_page) & set(new_by_page))

    # Baris yang berulang atau berada di tepi halaman (running header/footer)
    # dibuang untuk perbandingan isi, bukan untuk mengubah keluaran.
    repeated = _repeated_lines(
        [str(baseline_by_page[page].get("raw_text") or "") for page in common_pages]
    )
    edge_lines = _edge_header_lines(
        [str(baseline_by_page[page].get("raw_text") or "") for page in common_pages]
    )

    per_page: list[dict[str, Any]] = []
    raw_cers: list[float] = []
    adjusted_cers: list[float] = []
    loss_cers: list[float] = []
    recall_cers: list[float] = []
    excluded_short_pages: list[int] = []

    for page_number in common_pages:
        baseline_text = str(baseline_by_page[page_number].get("raw_text") or "")
        new_text = str(
            new_by_page[page_number].get("text")
            or new_by_page[page_number].get("raw_text")
            or ""
        )
        baseline_clean = normalize_for_comparison(baseline_text)
        new_clean = normalize_for_comparison(new_text)
        baseline_adjusted = normalize_for_comparison(
            _strip_edge_noise(baseline_text, repeated, edge_lines)
        )
        new_adjusted = normalize_for_comparison(
            _strip_edge_noise(new_text, repeated, edge_lines)
        )

        raw_distance = levenshtein(baseline_clean, new_clean)
        adjusted_distance = levenshtein(baseline_adjusted, new_adjusted)
        raw_cer = raw_distance / max(len(baseline_clean), 1)
        adjusted_cer = adjusted_distance / max(len(baseline_adjusted), 1)
        baseline_tokens = baseline_adjusted.split()
        new_tokens = new_adjusted.split()
        loss_cer = content_loss_cer(baseline_tokens, new_tokens)
        recall_loss = content_recall_loss(baseline_tokens, new_tokens)

        if len(baseline_clean) < 100:
            excluded_short_pages.append(page_number)
        elif page_number in NON_CONTENT_PAGES:
            pass
        else:
            raw_cers.append(raw_cer)
            adjusted_cers.append(adjusted_cer)
            loss_cers.append(loss_cer)
            recall_cers.append(recall_loss)
        per_page.append(
            {
                "page_number": page_number,
                "baseline_chars": len(baseline_clean),
                "llamaparse_chars": len(new_clean),
                "cer": round(raw_cer, 5),
                "cer_noise_adjusted": round(adjusted_cer, 5),
                "cer_content_loss": round(loss_cer, 5),
                "cer_content_recall": round(recall_loss, 5),
                "extra_tokens": max(len(new_tokens) - len(baseline_tokens), 0),
                "printed_page_number": new_by_page[page_number].get(
                    "printed_page_number"
                ),
                "excluded_from_gate": NON_CONTENT_PAGES.get(page_number),
            }
        )

    gate_excluded = set(excluded_short_pages) | set(NON_CONTENT_PAGES)
    worst = sorted(
        (item for item in per_page if item["page_number"] not in gate_excluded),
        key=lambda item: item["cer_content_recall"],
        reverse=True,
    )[:10]

    baseline_chapters = _chapter_list(baseline_blocks)
    new_chapters = _chapter_list(blocks)
    chapter_numbers = _content_chapter_numbers(blocks)
    new_chapter_count = len(chapter_numbers)
    heading_chapter_numbers = _chapter_numbers(new_chapters)
    baseline_chapter_numbers = _content_chapter_numbers(baseline_blocks)

    missing_pages = sorted(set(baseline_by_page) - set(new_by_page))
    if is_full_run:
        missing_pages = sorted(
            set(range(1, int(manifest.get("total_pdf_pages") or 0) + 1))
            - set(new_by_page)
        )
    else:
        expected_scope = _scope_pages(manifest)
        missing_pages = sorted(set(expected_scope) - set(new_by_page))

    printed_detected = sum(
        1 for page in pages if page.get("printed_page_number") is not None
    )
    printed_coverage = printed_detected / len(pages) if pages else 0.0

    baseline_tables = _table_pages(baseline_blocks)
    new_tables = _table_pages(blocks)
    scope = set(_scope_pages(manifest))
    baseline_tables_in_scope = [page for page in baseline_tables if page in scope]

    mean_cer = statistics.fmean(raw_cers) if raw_cers else None
    mean_adjusted = statistics.fmean(adjusted_cers) if adjusted_cers else None
    mean_loss = statistics.fmean(loss_cers) if loss_cers else None
    mean_recall = statistics.fmean(recall_cers) if recall_cers else None
    gate_pages = [item for item in per_page if item["page_number"] not in gate_excluded]
    worst_by_recall = (
        max(gate_pages, key=lambda item: item["cer_content_recall"])
        if gate_pages
        else None
    )
    max_recall = worst_by_recall["cer_content_recall"] if worst_by_recall else None
    max_recall_page = worst_by_recall["page_number"] if worst_by_recall else None

    multi_column = [
        {
            "page_number": page,
            "baseline_flag": bool(
                "possible_multi_column_layout"
                in (baseline_by_page.get(page, {}).get("flags") or [])
            ),
            "llamaparse_flag": bool(
                "possible_multi_column_layout"
                in (new_by_page.get(page, {}).get("flags") or [])
            ),
            "manual_review_required": page in MULTI_COLUMN_PAGES,
        }
        for page in MULTI_COLUMN_PAGES
    ]

    content_blocks = [
        block
        for block in blocks
        if block.get("content_type")
        in {"paragraph", "list_item", "table", "figure_caption"}
    ]
    numbered_content = [
        block
        for block in content_blocks
        if re.match(
            r"^(?:BAB|BAGIAN|CHAPTER)\s+\d+\b",
            str(block.get("chapter") or ""),
            re.IGNORECASE,
        )
    ]
    body_start = min(
        (int(block["page_number"]) for block in numbered_content), default=1
    )
    reference_pages = [
        int(block["page_number"])
        for block in blocks
        if "daftar pustaka" in str(block.get("chapter") or "").lower()
    ]
    body_end = (min(reference_pages) - 1) if reference_pages else max(
        (int(block["page_number"]) for block in blocks), default=body_start
    )
    body_context_missing = [
        block
        for block in blocks
        if block.get("content_type") not in {"chapter_heading"}
        and body_start <= int(block.get("page_number", 0)) <= body_end
        and not block.get("chapter")
    ]

    gates: dict[str, dict[str, Any]] = {
        "pages_complete": {
            "passed": not missing_pages,
            "detail": f"missing={missing_pages[:20]}",
        },
        "content_recall": {
            "passed": mean_recall is not None and mean_recall <= CER_THRESHOLD,
            "detail": (
                f"content_recall_loss={mean_recall} threshold={CER_THRESHOLD} "
                f"excluded_short_baseline={excluded_short_pages} "
                f"excluded_non_content={sorted(NON_CONTENT_PAGES)}"
            ),
        },
        "content_loss_max_page": {
            "passed": max_recall is not None and max_recall <= MAX_PAGE_CONTENT_LOSS,
            "detail": (
                f"max_page_loss={max_recall} page={max_recall_page} "
                f"threshold={MAX_PAGE_CONTENT_LOSS}"
            ),
        },
        "chapter_count": {
            "passed": (not is_full_run) or new_chapter_count == EXPECTED_CHAPTER_COUNT,
            "detail": f"chapters={new_chapter_count} expected={EXPECTED_CHAPTER_COUNT}",
        },
        "printed_page_numbers": {
            "passed": printed_detected > 0,
            "detail": f"detected={printed_detected} coverage={printed_coverage:.2%}",
        },
        "tables": {
            "passed": len(new_tables) >= len(baseline_tables_in_scope),
            "detail": (
                f"llamaparse_pages={new_tables} "
                f"baseline_pages_in_scope={baseline_tables_in_scope}"
            ),
        },
        "context_coverage": {
            "passed": not body_context_missing,
            "detail": (
                f"body_pages={body_start}-{body_end} "
                f"blocks_missing={len(body_context_missing)}"
            ),
        },
    }
    gate_passed = all(item["passed"] for item in gates.values())

    report = {
        "schema_version": "1.0.0",
        "document_id": config.DOCUMENT_ID,
        "run_id": run_id,
        "generated_at": utc_now(),
        "tier": options.get("tier"),
        "version": options.get("version"),
        "is_full_run": is_full_run,
        "pages_compared": len(common_pages),
        "pages_missing_vs_baseline": missing_pages,
        "text_similarity": {
            "cer_mean": round(mean_cer, 5) if mean_cer is not None else None,
            "cer_median": round(statistics.median(raw_cers), 5) if raw_cers else None,
            "cer_p95": (
                round(sorted(raw_cers)[int(len(raw_cers) * 0.95)], 5) if raw_cers else None
            ),
            "cer_noise_adjusted_mean": (
                round(mean_adjusted, 5) if mean_adjusted is not None else None
            ),
            "cer_noise_adjusted_median": (
                round(statistics.median(adjusted_cers), 5) if adjusted_cers else None
            ),
            "cer_content_loss_mean": (
                round(mean_loss, 5) if mean_loss is not None else None
            ),
            "cer_content_loss_median": (
                round(statistics.median(loss_cers), 5) if loss_cers else None
            ),
            "cer_content_recall_mean": (
                round(mean_recall, 5) if mean_recall is not None else None
            ),
            "cer_content_recall_median": (
                round(statistics.median(recall_cers), 5) if recall_cers else None
            ),
            "cer_content_recall_max": (
                round(max_recall, 5) if max_recall is not None else None
            ),
            "cer_content_recall_max_page": max_recall_page,
            "excluded_short_baseline_pages": excluded_short_pages,
            "excluded_non_content_pages": {
                str(page): reason for page, reason in sorted(NON_CONTENT_PAGES.items())
            },
            "worst_pages": worst,
        },
        "headings": {
            "baseline_chapter_headings": baseline_chapters,
            "baseline_chapter_numbers": baseline_chapter_numbers,
            "llamaparse_chapter_headings": new_chapters,
            "llamaparse_chapter_numbers": chapter_numbers,
            "llamaparse_heading_chapter_numbers": heading_chapter_numbers,
            "llamaparse_chapter_count": new_chapter_count,
            "expected_chapter_count": EXPECTED_CHAPTER_COUNT,
        },
        "tables": {
            "baseline_pages": baseline_tables,
            "llamaparse_pages": new_tables,
        },
        "printed_page_numbers": {
            "detected": printed_detected,
            "coverage": round(printed_coverage, 4),
        },
        "multi_column_pages": multi_column,
        "gates": gates,
        "gate_passed": gate_passed,
        "per_page": per_page,
    }
    write_json(config.report_paths()["comparison"], report)
    quality.append_review(_review_entries(per_page, sorted(gate_excluded)))
    LOGGER.info(
        "Perbandingan: CER=%s (noise-adjusted %s, content-loss %s, recall-loss %s), gate=%s",
        report["text_similarity"]["cer_mean"],
        report["text_similarity"]["cer_noise_adjusted_mean"],
        report["text_similarity"]["cer_content_loss_mean"],
        report["text_similarity"]["cer_content_recall_mean"],
        gate_passed,
    )
    return report


MANUAL_REVIEW_CER = 0.02


def _review_entries(
    per_page: list[dict[str, Any]], excluded: list[int]
) -> list[dict[str, Any]]:
    """Halaman dengan perbedaan teks mencolok masuk antrean review manual.

    Catatan: pada halaman multi-kolom baseline PyMuPDF bisa lebih buruk
    daripada LlamaParse, jadi perbedaan teks bukan bukti kesalahan parser.
    """

    entries: list[dict[str, Any]] = []
    for item in per_page:
        page_number = int(item["page_number"])
        cer = float(item.get("cer_content_recall") or 0.0)
        extra = int(item.get("extra_tokens") or 0)
        if page_number in excluded:
            continue
        if cer >= MANUAL_REVIEW_CER:
            entries.append(
                {
                    "scope": "page",
                    "page_number": page_number,
                    "reason": "text_differs_from_baseline",
                    "detail": (
                        f"cer_content_recall={cer:.4f} "
                        f"baseline_chars={item.get('baseline_chars')} "
                        f"llamaparse_chars={item.get('llamaparse_chars')}; "
                        "bandingkan manual dengan PDF, terutama bila multi-kolom"
                    ),
                }
            )
        elif extra >= 20:
            entries.append(
                {
                    "scope": "page",
                    "page_number": page_number,
                    "reason": "parser_added_content",
                    "detail": (
                        f"extra_tokens={extra}; parser membaca teks yang tidak "
                        "tertangkap baseline (mis. label diagram) - cek apakah "
                        "isinya memang ada di PDF"
                    ),
                }
            )
    return entries
