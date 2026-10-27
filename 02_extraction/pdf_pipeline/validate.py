"""Validasi kualitas output ekstraksi tanpa mengubah data."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from . import config, output
from .extract import sha256_file


BLOCK_ID_RE = re.compile(r"^[A-Za-z0-9]+_P\d+_B\d+$")


def _error(issues: list[str], code: str, message: str) -> None:
    issues.append(f"{code}: {message}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _has_control_characters(value: str) -> bool:
    return any(
        unicodedata.category(char) == "Cc" and char not in "\n\t"
        for char in value
    )


def _resolve_source_path(paths: config.ProjectPaths, source_path: str) -> Path:
    candidate = Path(source_path)
    if candidate.is_absolute():
        return candidate
    return paths.root / candidate


def _resolve_output_path(paths: config.ProjectPaths, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        return candidate
    return paths.root / candidate


def _read_document_outputs(
    paths: config.ProjectPaths,
    document: dict[str, Any],
    errors: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    document_id = str(document.get("document_id", "unknown"))
    output_files = document.get("output_files")
    if not isinstance(output_files, dict):
        _error(errors, "output_files_missing", document_id)
        return [], [], False

    blocks_path = output_files.get("blocks")
    pages_path = output_files.get("pages")
    notes_path = output_files.get("notes")

    if not isinstance(blocks_path, str) or not isinstance(pages_path, str):
        _error(errors, "output_files_incomplete", document_id)
        return [], [], False

    blocks_file = _resolve_output_path(paths, blocks_path)
    pages_file = _resolve_output_path(paths, pages_path)

    pages: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []

    if not pages_file.is_file():
        _error(errors, "pages_file_missing", str(pages_file))
    else:
        try:
            pages = output.read_jsonl(pages_file)
        except (OSError, ValueError) as exc:
            _error(errors, "pages_file_invalid", f"{pages_file}: {exc}")

    if not blocks_file.is_file():
        _error(errors, "blocks_file_missing", str(blocks_file))
    else:
        try:
            blocks = output.read_jsonl(blocks_file)
        except (OSError, ValueError) as exc:
            _error(errors, "blocks_file_invalid", f"{blocks_file}: {exc}")

    if isinstance(notes_path, str):
        notes_file = _resolve_output_path(paths, notes_path)
        if not notes_file.is_file():
            _error(errors, "notes_file_missing", str(notes_file))
        else:
            try:
                notes_data = output.read_json(notes_file)
            except (OSError, ValueError) as exc:
                _error(errors, "notes_file_invalid", f"{notes_file}: {exc}")
            else:
                if not isinstance(notes_data, dict):
                    _error(errors, "notes_not_object", str(notes_file))
                else:
                    for key in (
                        "schema_version",
                        "document_id",
                        "document_name",
                        "generated_at",
                        "summary",
                        "document_notes",
                        "pages_with_issues",
                        "repeated_lines",
                        "table_issues",
                        "structure_issues",
                    ):
                        if key not in notes_data:
                            _error(
                                errors,
                                "notes_required_field_missing",
                                f"{key} ({notes_file.name})",
                            )
                    if notes_data.get("document_id") not in (None, document_id):
                        _error(
                            errors,
                            "notes_document_id_mismatch",
                            f"{notes_data.get('document_id')} != {document_id}",
                        )
                    if not isinstance(notes_data.get("document_notes"), list):
                        _error(errors, "notes_document_notes_invalid", document_id)
    else:
        _error(errors, "notes_path_missing", document_id)

    return pages, blocks, True


def _validate_pages(
    document: dict[str, Any],
    pages: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> dict[int, dict[str, Any]]:
    document_id = str(document.get("document_id"))
    total_pages = document.get("total_pdf_pages")
    if not isinstance(total_pages, int) or isinstance(total_pages, bool) or total_pages <= 0:
        _error(errors, "total_pdf_pages_invalid", str(total_pages))
        total_pages = 0

    by_page: dict[int, dict[str, Any]] = {}
    pages_without_text = 0
    ocr_candidates = 0
    multi_column_pages: list[int] = []
    repeated_headers = 0
    repeated_footers = 0
    unknown_flags: set[str] = set()
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            _error(errors, "page_not_object", f"index {index}")
            continue
        for key in config.PAGE_REQUIRED_KEYS:
            if key not in page:
                _error(errors, "page_required_field_missing", f"{document_id} index {index}: {key}")
        if page.get("document_id") != document_id:
            _error(errors, "page_document_id_mismatch", f"{document_id} index {index}")

        page_number = page.get("page_number")
        if not isinstance(page_number, int) or isinstance(page_number, bool):
            _error(errors, "page_number_invalid", f"{document_id} index {index}")
            continue
        if page_number in by_page:
            _error(errors, "page_number_duplicate", f"{document_id} halaman {page_number}")
        by_page[page_number] = page

        status = page.get("extraction_status")
        if not isinstance(status, str) or status not in config.PAGE_STATUS_SET:
            _error(errors, "page_status_invalid", f"{document_id} halaman {page_number}: {status}")

        raw_text = page.get("raw_text")
        if not isinstance(raw_text, str):
            _error(errors, "page_raw_text_invalid", f"{document_id} halaman {page_number}")
        else:
            if page.get("text_char_count") != len(raw_text):
                _error(
                    errors,
                    "page_char_count_mismatch",
                    f"{document_id} halaman {page_number}",
                )
            if _has_control_characters(raw_text):
                warnings.append(
                    f"page_raw_control_characters: "
                    f"{document_id} halaman {page_number}"
                )

        for key in ("page_width", "page_height", "image_coverage_ratio"):
            if not _is_number(page.get(key)):
                _error(errors, "page_numeric_field_invalid", f"{document_id} halaman {page_number}: {key}")

        if not isinstance(page.get("block_count"), int) or isinstance(page.get("block_count"), bool):
            _error(errors, "page_block_count_invalid", f"{document_id} halaman {page_number}")
        if not isinstance(page.get("image_count"), int) or isinstance(page.get("image_count"), bool):
            _error(errors, "page_image_count_invalid", f"{document_id} halaman {page_number}")

        printed = page.get("printed_page_number")
        if printed is not None and not isinstance(printed, str):
            _error(errors, "page_printed_number_invalid", f"{document_id} halaman {page_number}")
        printed_source = page.get("printed_page_number_source")
        if printed_source not in (None, "pdf_page_labels", "text_sequence"):
            _error(errors, "page_printed_source_invalid", f"{document_id} halaman {page_number}")

        flags = page.get("flags")
        if not isinstance(flags, list):
            _error(errors, "page_flags_invalid", f"{document_id} halaman {page_number}")
        else:
            for flag in flags:
                if not isinstance(flag, str) or flag not in config.PAGE_FLAG_SET:
                    unknown_flags.add(str(flag))
            if "possible_multi_column_layout" in flags:
                multi_column_pages.append(page_number)

        notes = page.get("notes")
        if not isinstance(notes, list):
            _error(errors, "page_notes_invalid", f"{document_id} halaman {page_number}")

        flags_list = flags if isinstance(flags, list) else []
        if status == "no_text_extracted":
            pages_without_text += 1
        if "ocr_candidate" in flags_list:
            ocr_candidates += 1
        if "repeated_header_candidate" in flags_list:
            repeated_headers += 1
        if "repeated_footer_candidate" in flags_list:
            repeated_footers += 1

    if unknown_flags:
        warnings.append(
            f"unknown_page_flags: {document_id}: {', '.join(sorted(unknown_flags))}"
        )
    if pages_without_text:
        warnings.append(
            f"pages_without_text: {document_id}: {pages_without_text}"
        )
    if ocr_candidates:
        warnings.append(
            f"ocr_candidates: {document_id}: {ocr_candidates}"
        )
    if multi_column_pages:
        shown = ", ".join(str(number) for number in multi_column_pages[:20])
        suffix = " ..." if len(multi_column_pages) > 20 else ""
        warnings.append(
            f"possible_multi_column_layout: {document_id}: "
            f"{len(multi_column_pages)} halaman ({shown}{suffix})"
        )
    if repeated_headers:
        warnings.append(
            f"repeated_header_candidates: {document_id}: {repeated_headers} halaman"
        )
    if repeated_footers:
        warnings.append(
            f"repeated_footer_candidates: {document_id}: {repeated_footers} halaman"
        )

    if total_pages:
        expected = set(range(1, total_pages + 1))
        actual = set(by_page)
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            _error(
                errors,
                "page_numbers_missing",
                f"{document_id}: {missing[:20]}",
            )
        if extra:
            _error(
                errors,
                "page_numbers_out_of_range",
                f"{document_id}: {extra[:20]}",
            )

    return by_page


def _validate_blocks(
    document: dict[str, Any],
    pages_by_number: dict[int, dict[str, Any]],
    blocks: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> Counter:
    document_id = str(document.get("document_id"))
    block_counts: Counter = Counter()
    seen_ids: set[str] = set()
    seen_sequences: set[int] = set()
    unclassified = 0
    table_review = 0
    replacement_characters = 0
    manual_review_blocks = 0

    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict):
            _error(errors, "block_not_object", f"index {index}")
            continue

        for key in config.BLOCK_REQUIRED_KEYS:
            if key not in block:
                _error(errors, "block_required_field_missing", f"{document_id} index {index}: {key}")

        block_id = block.get("block_id")
        if not isinstance(block_id, str) or not BLOCK_ID_RE.match(block_id):
            _error(errors, "block_id_invalid", f"{document_id} index {index}: {block_id}")
        elif block_id in seen_ids:
            _error(errors, "block_id_duplicate", block_id)
        else:
            seen_ids.add(block_id)
            if not block_id.startswith(f"{document_id}_P"):
                _error(errors, "block_id_document_mismatch", block_id)

        if block.get("document_id") != document_id:
            _error(errors, "block_document_id_mismatch", f"{block_id}")
        if block.get("schema_version") != config.SCHEMA_VERSION:
            _error(errors, "block_schema_version_mismatch", f"{block_id}")

        sequence = block.get("sequence_number")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            _error(errors, "block_sequence_invalid", f"{block_id}")
        else:
            if sequence != index:
                _error(
                    errors,
                    "block_sequence_not_contiguous",
                    f"{block_id}: {sequence} != {index}",
                )
            if sequence in seen_sequences:
                _error(errors, "block_sequence_duplicate", f"{block_id}: {sequence}")
            seen_sequences.add(sequence)

        page_number = block.get("page_number")
        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number not in pages_by_number
        ):
            _error(errors, "block_page_number_invalid", f"{block_id}: {page_number}")
        else:
            block_counts[page_number] += 1

        content_type = block.get("content_type")
        if not isinstance(content_type, str) or content_type not in config.CONTENT_TYPE_SET:
            _error(errors, "block_content_type_invalid", f"{block_id}: {content_type}")
        if content_type == "heading_unclassified":
            unclassified += 1

        status = block.get("extraction_status")
        if not isinstance(status, str) or status not in config.BLOCK_STATUS_SET:
            _error(errors, "block_status_invalid", f"{block_id}: {status}")

        text = block.get("text")
        if not isinstance(text, str):
            _error(errors, "block_text_invalid", block_id)
        elif not text.strip() and content_type != "table":
            _error(errors, "block_text_empty", block_id)
        elif _has_control_characters(text):
            _error(errors, "block_text_control_characters", block_id)
        if isinstance(text, str) and "\ufffd" in text:
            replacement_characters += 1

        notes = block.get("parsing_notes")
        if not isinstance(notes, list) or not all(
            isinstance(note, str) for note in notes
        ):
            _error(errors, "block_parsing_notes_invalid", block_id)

        bbox = block.get("bbox")
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(_is_number(value) for value in bbox)
        ):
            _error(errors, "block_bbox_invalid", block_id)

        for key in ("chapter", "section", "subsection", "printed_page_number"):
            value = block.get(key)
            if value is not None and not isinstance(value, str):
                _error(errors, "block_context_field_invalid", f"{block_id}: {key}")

        cleaning_actions = block.get("cleaning_actions")
        if not isinstance(cleaning_actions, list):
            _error(errors, "block_cleaning_actions_invalid", block_id)
        raw_text = block.get("raw_text")
        if raw_text is not None and not isinstance(raw_text, str):
            _error(errors, "block_raw_text_invalid", block_id)

        table = block.get("table")
        if content_type == "table":
            if not isinstance(table, dict):
                _error(errors, "table_payload_missing", block_id)
            else:
                cells = table.get("cells")
                if not isinstance(cells, list):
                    _error(errors, "table_cells_invalid", block_id)
                else:
                    row_count = table.get("row_count")
                    column_count = table.get("column_count")
                    if row_count != len(cells):
                        _error(errors, "table_row_count_mismatch", block_id)
                    actual_columns = max(
                        (len(row) for row in cells if isinstance(row, list)),
                        default=0,
                    )
                    if column_count != actual_columns:
                        _error(errors, "table_column_count_mismatch", block_id)
                if not isinstance(table.get("review_required"), bool):
                    _error(errors, "table_review_flag_invalid", block_id)
                if table.get("review_required") is True:
                    table_review += 1
        elif table is not None:
            warnings.append(f"unexpected_table_payload: {block_id}")

        if status == "needs_manual_review" and content_type != "table":
            manual_review_blocks += 1

    if unclassified:
        warnings.append(f"unclassified_headings: {document_id}: {unclassified}")
    if table_review:
        warnings.append(f"tables_need_review: {document_id}: {table_review}")
    if replacement_characters:
        warnings.append(
            f"replacement_characters_in_text: {document_id}: {replacement_characters} blok"
        )
    if manual_review_blocks:
        warnings.append(
            f"blocks_need_manual_review: {document_id}: {manual_review_blocks}"
        )

    # Konsistensi block_count per halaman.
    for page_number, page in pages_by_number.items():
        expected_count = block_counts.get(page_number, 0)
        if page.get("block_count") != expected_count:
            _error(
                errors,
                "page_block_count_mismatch",
                f"{document_id} halaman {page_number}: "
                f"{page.get('block_count')} != {expected_count}",
            )

    return block_counts


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _expected_statistics(
    pages: list[dict[str, Any]], blocks: list[dict[str, Any]]
) -> dict[str, Any]:
    valid_pages = [page for page in pages if isinstance(page, dict)]
    valid_blocks = [block for block in blocks if isinstance(block, dict)]
    by_type = Counter(
        block["content_type"]
        for block in valid_blocks
        if isinstance(block.get("content_type"), str)
    )
    tables = [block for block in valid_blocks if block.get("content_type") == "table"]
    return {
        "pages_with_text": sum(
            1 for page in valid_pages if page.get("extraction_status") == "text_extracted"
        ),
        "pages_without_text": sum(
            1
            for page in valid_pages
            if page.get("extraction_status") == "no_text_extracted"
        ),
        "pages_with_errors": sum(
            1
            for page in valid_pages
            if page.get("extraction_status") == "extraction_error"
        ),
        "pages_flagged": sum(1 for page in valid_pages if page.get("flags")),
        "blocks_total": len(valid_blocks),
        "blocks_by_content_type": {
            key: by_type[key] for key in sorted(by_type)
        },
        "tables_detected": len(tables),
        "tables_needs_review": sum(
            1
            for block in tables
            if block.get("extraction_status") == "needs_manual_review"
        ),
        "headings_detected": sum(
            1
            for block in valid_blocks
            if isinstance(block.get("content_type"), str)
            and block["content_type"] in config.HEADING_CONTENT_TYPES
        ),
        "printed_page_numbers_detected": sum(
            1 for page in valid_pages if page.get("printed_page_number") is not None
        ),
        "characters_total": sum(
            _safe_int(page.get("text_char_count", 0)) for page in valid_pages
        ),
    }


def _validate_statistics(
    document: dict[str, Any],
    pages: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    statistics = document.get("statistics")
    if not isinstance(statistics, dict):
        _error(errors, "statistics_invalid", str(document.get("document_id")))
        return

    expected = _expected_statistics(pages, blocks)
    for key, value in expected.items():
        if statistics.get(key) != value:
            _error(
                errors,
                "statistics_mismatch",
                f"{document.get('document_id')} {key}: "
                f"{statistics.get(key)} != {value}",
            )


def _validate_source(
    document: dict[str, Any],
    paths: config.ProjectPaths,
    errors: list[str],
) -> None:
    document_id = str(document.get("document_id"))
    source_path = document.get("source_path")
    if not isinstance(source_path, str) or not source_path:
        _error(errors, "source_path_missing", document_id)
        return

    source_file = _resolve_source_path(paths, source_path)
    if not source_file.is_file():
        _error(errors, "source_file_missing", str(source_file))
        return

    expected_hash = document.get("source_sha256")
    if not isinstance(expected_hash, str) or not expected_hash:
        if document.get("extraction_status") != "failed":
            _error(errors, "source_sha256_missing", document_id)
        return

    try:
        actual_hash = sha256_file(source_file)
    except OSError as exc:
        _error(errors, "source_hash_error", f"{source_file}: {exc}")
        return

    if actual_hash != expected_hash:
        _error(
            errors,
            "source_hash_mismatch",
            f"{document_id}: {actual_hash} != {expected_hash}",
        )

    hash_after = document.get("source_sha256_after")
    if isinstance(hash_after, str) and hash_after != expected_hash:
        _error(errors, "source_changed_during_extraction", document_id)


def _validate_document(
    document: dict[str, Any],
    paths: config.ProjectPaths,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    document_id = str(document.get("document_id", "unknown"))

    for key in config.DOCUMENT_REQUIRED_KEYS:
        if key not in document:
            _error(errors, "document_required_field_missing", f"{document_id}: {key}")

    status = document.get("extraction_status")
    if status not in config.DOCUMENT_STATUS_SET:
        _error(errors, "document_status_invalid", f"{document_id}: {status}")

    _validate_source(document, paths, errors)

    if status == "failed":
        _error(errors, "document_extraction_failed", document_id)
        return {
            "document_id": document_id,
            "status": "fail",
            "errors": errors,
            "warnings": warnings,
            "checks": {},
        }

    pages, blocks, outputs_readable = _read_document_outputs(
        paths, document, errors
    )
    pages_by_number: dict[int, dict[str, Any]] = {}
    if outputs_readable:
        pages_by_number = _validate_pages(document, pages, errors, warnings)
        _validate_blocks(document, pages_by_number, blocks, errors, warnings)
        _validate_statistics(document, pages, blocks, errors)

    if document.get("title") is None:
        warnings.append(f"document_title_not_available: {document_id}")
    if not document.get("authors"):
        warnings.append(f"document_authors_not_available: {document_id}")
    if document.get("publication_year") is None:
        warnings.append(f"document_publication_year_not_available: {document_id}")

    checks = {
        "pages": len(pages),
        "blocks": len(blocks),
        "has_text": bool(
            any(page.get("extraction_status") == "text_extracted" for page in pages)
        ),
        "source_hash_verified": not any(
            issue.startswith(
                (
                    "source_hash_mismatch",
                    "source_hash_error",
                    "source_file_missing",
                    "source_sha256_missing",
                )
            )
            for issue in errors
        ),
    }

    if errors:
        overall = "fail"
    elif warnings:
        overall = "warn"
    else:
        overall = "pass"

    return {
        "document_id": document_id,
        "status": overall,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def validate_outputs(
    paths: config.ProjectPaths, strict: bool = False
) -> dict[str, Any]:
    """Memvalidasi seluruh output dan mengembalikan laporan."""

    manifest_errors: list[str] = []
    manifest_warnings: list[str] = []
    document_reports: list[dict[str, Any]] = []

    if not paths.manifest.is_file():
        _error(manifest_errors, "manifest_missing", str(paths.manifest))
    else:
        try:
            manifest = output.read_json(paths.manifest)
        except (OSError, ValueError) as exc:
            _error(manifest_errors, "manifest_invalid", f"{paths.manifest}: {exc}")
            manifest = None

        if manifest is not None:
            if not isinstance(manifest, dict):
                _error(manifest_errors, "manifest_not_object", str(paths.manifest))
            else:
                if manifest.get("schema_version") != config.SCHEMA_VERSION:
                    _error(
                        manifest_errors,
                        "manifest_schema_version_mismatch",
                        str(manifest.get("schema_version")),
                    )
                documents = manifest.get("documents")
                if not isinstance(documents, list):
                    _error(manifest_errors, "manifest_documents_invalid", "bukan list")
                else:
                    seen_ids: set[str] = set()
                    for document in documents:
                        if not isinstance(document, dict):
                            _error(
                                manifest_errors,
                                "manifest_document_not_object",
                                "entri documents bukan object",
                            )
                            continue
                        document_id = str(document.get("document_id", ""))
                        if not document_id:
                            _error(
                                manifest_errors,
                                "manifest_document_id_missing",
                                "entri tanpa document_id",
                            )
                            continue
                        if document_id in seen_ids:
                            _error(
                                manifest_errors,
                                "manifest_document_id_duplicate",
                                document_id,
                            )
                        seen_ids.add(document_id)
                        document_reports.append(
                            _validate_document(document, paths)
                        )

                    if not documents:
                        _error(manifest_errors, "manifest_no_documents", str(paths.manifest))

                    registered = set(config.document_ids())
                    missing = sorted(registered - seen_ids)
                    if missing:
                        manifest_warnings.append(
                            "registered_documents_not_in_manifest: "
                            + ", ".join(missing)
                        )

    all_errors = list(manifest_errors)
    all_warnings = list(manifest_warnings)
    for report in document_reports:
        all_errors.extend(report["errors"])
        all_warnings.extend(report["warnings"])

    return {
        "schema_version": config.SCHEMA_VERSION,
        "validated_at": output.utc_now(),
        "strict": bool(strict),
        "summary": {
            "documents": len(document_reports),
            "errors": len(all_errors),
            "warnings": len(all_warnings),
        },
        "manifest_errors": manifest_errors,
        "manifest_warnings": manifest_warnings,
        "documents": document_reports,
    }


def validation_exit_code(report: dict[str, Any], strict: bool = False) -> int:
    summary = report.get("summary", {})
    errors = int(summary.get("errors", 0) or 0)
    warnings = int(summary.get("warnings", 0) or 0)
    if errors:
        return 1
    if strict and warnings:
        return 1
    return 0
