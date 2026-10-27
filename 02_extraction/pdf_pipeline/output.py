"""Penulisan output, manifest, report, dan kebijakan overwrite/backup."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import config


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSONL tidak valid di {path.name} baris {line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"Baris JSONL bukan object di {path.name} baris {line_number}"
                )
            records.append(value)
    return records


def _atomic_write(path: Path, writer: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8", newline="\n") as handle:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def write_json(path: Path, data: Any) -> None:
    def writer(handle: Any) -> None:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")

    _atomic_write(path, writer)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    def writer(handle: Any) -> None:
        for record in records:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
            )
            handle.write("\n")

    _atomic_write(path, writer)


def write_text(path: Path, text: str) -> None:
    def writer(handle: Any) -> None:
        handle.write(text)
        if text and not text.endswith("\n"):
            handle.write("\n")

    _atomic_write(path, writer)


def document_output_paths(
    paths: config.ProjectPaths, document_id: str
) -> dict[str, Path]:
    return {
        "blocks": paths.extracted_text_dir / f"{document_id}.blocks.jsonl",
        "pages": paths.extracted_text_dir / f"{document_id}.pages.jsonl",
        "notes": paths.extraction_notes_dir
        / f"{document_id}.extraction_notes.json",
    }


def all_target_paths(
    paths: config.ProjectPaths, document_ids: list[str]
) -> list[Path]:
    targets: list[Path] = []
    for document_id in document_ids:
        targets.extend(document_output_paths(paths, document_id).values())
    targets.extend([paths.manifest, paths.report])
    return targets


def existing_paths(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def backup_files(
    paths: config.ProjectPaths, files: list[Path], stamp: Optional[str] = None
) -> Path:
    backup_root = paths.backup_dir / (stamp or utc_stamp())
    if backup_root.exists():
        base = backup_root
        counter = 2
        while backup_root.exists():
            backup_root = base.with_name(f"{base.name}_{counter}")
            counter += 1
    for source in files:
        if not source.exists():
            continue
        try:
            relative = source.resolve().relative_to(paths.root.resolve())
        except ValueError:
            relative = Path(source.name)
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return backup_root


def load_manual_metadata(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, []

    try:
        data = read_json(path)
    except (OSError, ValueError) as exc:
        return {}, [f"manual_metadata_invalid_json:{type(exc).__name__}"]

    if not isinstance(data, dict):
        return {}, ["manual_metadata_invalid_structure"]
    documents = data.get("documents")
    if not isinstance(documents, dict):
        return {}, ["manual_metadata_missing_documents_object"]

    cleaned: dict[str, Any] = {}
    for document_id, entry in documents.items():
        if isinstance(document_id, str) and isinstance(entry, dict):
            cleaned[document_id] = entry
    return cleaned, []


def _text_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def resolve_metadata(
    document_id: str,
    pdf_metadata: dict[str, Any],
    manual_documents: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Optional[str]], list[str]]:
    """Menggabungkan metadata manual dan PDF tanpa menebak nilai.

    Prioritas: manual_metadata.json > metadata PDF > null.
    """

    manual = manual_documents.get(document_id, {})
    if not isinstance(manual, dict):
        manual = {}

    notes: list[str] = []
    source: dict[str, Optional[str]] = {
        "title": None,
        "authors": None,
        "publication_year": None,
        "publisher": None,
        "language": None,
    }

    manual_title = _text_or_none(manual.get("title"))
    pdf_title = _text_or_none(pdf_metadata.get("title"))
    title = manual_title or pdf_title
    if manual_title:
        source["title"] = "manual_metadata.json"
    elif pdf_title:
        source["title"] = "pdf_metadata"

    manual_authors = manual.get("authors")
    authors: list[str] = []
    if isinstance(manual_authors, list):
        authors = [
            str(item).strip()
            for item in manual_authors
            if str(item).strip()
        ]
    elif manual_authors is not None:
        notes.append("manual_metadata_authors_not_list")

    if authors:
        source["authors"] = "manual_metadata.json"
    else:
        pdf_author = _text_or_none(pdf_metadata.get("author"))
        if pdf_author:
            authors = [pdf_author]
            source["authors"] = "pdf_metadata"

    manual_year = manual.get("publication_year")
    publication_year: Optional[int] = None
    if manual_year is not None:
        if isinstance(manual_year, bool):
            notes.append("manual_metadata_publication_year_invalid")
        elif isinstance(manual_year, int):
            publication_year = manual_year
        elif isinstance(manual_year, str) and manual_year.strip().isdigit():
            publication_year = int(manual_year.strip())
        else:
            notes.append("manual_metadata_publication_year_invalid")
    if publication_year is not None:
        source["publication_year"] = "manual_metadata.json"

    publisher = _text_or_none(manual.get("publisher"))
    if publisher:
        source["publisher"] = "manual_metadata.json"

    language = _text_or_none(manual.get("language"))
    if language:
        source["language"] = "manual_metadata.json"

    manual_notes = manual.get("notes")
    if isinstance(manual_notes, list):
        notes.extend(str(item) for item in manual_notes if str(item).strip())
    elif manual_notes is not None:
        notes.append("manual_metadata_notes_not_list")

    return (
        {
            "title": title,
            "authors": authors,
            "publication_year": publication_year,
            "publisher": publisher,
            "language": language,
        },
        source,
        notes,
    )


def build_document_entry(
    document: dict[str, Any],
    parsed: dict[str, Any],
    paths: config.ProjectPaths,
    manual_documents: dict[str, Any],
    output_files: dict[str, Path],
) -> dict[str, Any]:
    metadata, metadata_source, metadata_notes = resolve_metadata(
        document["document_id"],
        document.get("pdf_metadata", {}),
        manual_documents,
    )
    notes = list(parsed.get("document_notes", [])) + metadata_notes
    notes = list(dict.fromkeys(notes))

    relative_outputs = {
        key: config.to_relative_posix(path, paths.root)
        for key, path in output_files.items()
    }

    return {
        "document_id": document["document_id"],
        "document_name": document["document_name"],
        "source_path": document["source_path"],
        "source_sha256": document["source_sha256"],
        "source_sha256_after": document.get(
            "source_sha256_after", document["source_sha256"]
        ),
        "file_size_bytes": document["file_size_bytes"],
        "title": metadata["title"],
        "authors": metadata["authors"],
        "publication_year": metadata["publication_year"],
        "publisher": metadata["publisher"],
        "language": metadata["language"],
        "total_pdf_pages": document["total_pdf_pages"],
        "document_type": document.get("document_type", "pdf"),
        "extraction_status": parsed["extraction_status"],
        "notes": notes,
        "pdf_metadata": document.get("pdf_metadata", {}),
        "metadata_source": metadata_source,
        "statistics": parsed["statistics"],
        "output_files": relative_outputs,
    }


def build_failed_entry(
    source: dict[str, Any],
    paths: config.ProjectPaths,
    manual_documents: dict[str, Any],
    error_message: str,
    notes_path: Path,
) -> dict[str, Any]:
    metadata, metadata_source, metadata_notes = resolve_metadata(
        source["document_id"], {}, manual_documents
    )
    source_path = Path(source["path"])
    notes = [f"extraction_failed:{error_message}", *metadata_notes]

    return {
        "document_id": source["document_id"],
        "document_name": source_path.name,
        "source_path": config.to_relative_posix(source_path, paths.root),
        "source_sha256": None,
        "source_sha256_after": None,
        "file_size_bytes": (
            source_path.stat().st_size if source_path.exists() else None
        ),
        "title": metadata["title"],
        "authors": metadata["authors"],
        "publication_year": metadata["publication_year"],
        "publisher": metadata["publisher"],
        "language": metadata["language"],
        "total_pdf_pages": None,
        "document_type": "pdf",
        "extraction_status": "failed",
        "notes": notes,
        "pdf_metadata": {},
        "metadata_source": metadata_source,
        "statistics": {
            "pages_with_text": 0,
            "pages_without_text": 0,
            "pages_with_errors": 0,
            "pages_flagged": 0,
            "blocks_total": 0,
            "blocks_by_content_type": {},
            "tables_detected": 0,
            "tables_needs_review": 0,
            "headings_detected": 0,
            "printed_page_numbers_detected": 0,
            "characters_total": 0,
        },
        "output_files": {
            "blocks": None,
            "pages": None,
            "notes": config.to_relative_posix(notes_path, paths.root),
        },
    }


def build_manifest(
    paths: config.ProjectPaths,
    entries: list[dict[str, Any]],
    settings: dict[str, Any],
    extractor_version: str,
    global_notes: Optional[list[str]] = None,
    merge_existing: bool = True,
) -> dict[str, Any]:
    merged: dict[str, dict[str, Any]] = {}

    if merge_existing and paths.manifest.exists():
        try:
            existing = read_json(paths.manifest)
            if isinstance(existing, dict) and isinstance(
                existing.get("documents"), list
            ):
                for entry in existing["documents"]:
                    if isinstance(entry, dict) and entry.get("document_id"):
                        merged[str(entry["document_id"])] = entry
        except (OSError, ValueError):
            pass

    for entry in entries:
        merged[str(entry["document_id"])] = entry

    order = {item.document_id: index for index, item in enumerate(config.SOURCE_DOCUMENTS)}

    documents = sorted(
        merged.values(),
        key=lambda entry: (
            order.get(str(entry.get("document_id")), len(order)),
            str(entry.get("document_id", "")),
        ),
    )

    return {
        "schema_version": config.SCHEMA_VERSION,
        "generated_at": utc_now(),
        "pipeline": {
            "name": config.PIPELINE_NAME,
            "version": config.PIPELINE_VERSION,
            "extractor": "PyMuPDF",
            "extractor_version": extractor_version,
        },
        "settings": settings,
        "notes": list(global_notes or []),
        "documents": documents,
    }


def _escape_markdown(value: Any) -> str:
    return str(value).replace("|", "\\|")


def build_report(
    manifest: dict[str, Any],
    global_notes: Optional[list[str]] = None,
) -> str:
    lines: list[str] = [
        "# Extraction Report",
        "",
        f"- Generated at: `{manifest.get('generated_at')}`",
        f"- Schema: `{manifest.get('schema_version')}`",
        f"- Pipeline: `{manifest.get('pipeline', {}).get('version')}`",
        (
            "- Extractor: "
            f"`{manifest.get('pipeline', {}).get('extractor')}` "
            f"`{manifest.get('pipeline', {}).get('extractor_version')}`"
        ),
        "",
        "## Ringkasan dokumen",
        "",
        "| Dokumen | Halaman | Halaman berteks | Blok | Tabel | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for document in manifest.get("documents", []):
        stats = document.get("statistics", {})
        lines.append(
            "| {doc} | {pages} | {with_text} | {blocks} | {tables} | {status} |".format(
                doc=_escape_markdown(document.get("document_id")),
                pages=_escape_markdown(document.get("total_pdf_pages")),
                with_text=_escape_markdown(stats.get("pages_with_text")),
                blocks=_escape_markdown(stats.get("blocks_total")),
                tables=_escape_markdown(stats.get("tables_detected")),
                status=_escape_markdown(document.get("extraction_status")),
            )
        )

    lines.extend(["", "## Detail dokumen", ""])

    for document in manifest.get("documents", []):
        stats = document.get("statistics", {})
        lines.extend(
            [
                f"### {document.get('document_id')} — {document.get('document_name')}",
                "",
                f"- Source: `{document.get('source_path')}`",
                f"- SHA-256: `{document.get('source_sha256')}`",
                f"- Total halaman PDF: {document.get('total_pdf_pages')}",
                f"- Status ekstraksi: `{document.get('extraction_status')}`",
                f"- Halaman berteks: {stats.get('pages_with_text')}",
                f"- Halaman tanpa teks: {stats.get('pages_without_text')}",
                f"- Halaman error: {stats.get('pages_with_errors')}",
                f"- Blok: {stats.get('blocks_total')}",
                f"- Tabel: {stats.get('tables_detected')} "
                f"(review: {stats.get('tables_needs_review')})",
                f"- Judul: {document.get('title')}",
                f"- Penulis: {', '.join(document.get('authors') or []) or 'null'}",
                f"- Tahun: {document.get('publication_year')}",
                f"- Penerbit: {document.get('publisher')}",
                f"- Bahasa: {document.get('language')}",
                "",
            ]
        )

        output_files = document.get("output_files", {})
        lines.append("Output:")
        for key in ("blocks", "pages", "notes"):
            value = output_files.get(key)
            if value:
                lines.append(f"- `{key}`: `{value}`")
        lines.append("")

        notes = document.get("notes") or []
        if notes:
            lines.append("Catatan:")
            for note in notes:
                lines.append(f"- `{note}`")
            lines.append("")

    combined_notes = list(manifest.get("notes", [])) + list(global_notes or [])
    combined_notes = list(dict.fromkeys(combined_notes))
    if combined_notes:
        lines.extend(["## Catatan pipeline", ""])
        for note in combined_notes:
            lines.append(f"- `{note}`")
        lines.append("")

    lines.extend(
        [
            "## Langkah berikutnya",
            "",
            "1. Periksa `extraction_notes` setiap dokumen.",
            "2. Bandingkan sampel halaman dengan PDF asli.",
            "3. Tinjau tabel yang berstatus `needs_manual_review`.",
            "4. Jalankan `validate` dan baca `validation_report.json`.",
            "5. Jangan melanjutkan ke tahap pengetahuan sebelum hasil diperiksa.",
            "",
        ]
    )

    return "\n".join(lines)
