"""Command-line interface untuk ekstraksi dan validasi."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Optional

from . import config, extract, output, parse, validate


LOGGER = logging.getLogger("kbr_extraction")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def _progress(page_number: int, total_pages: int) -> None:
    if page_number == 1 or page_number % 25 == 0 or page_number == total_pages:
        LOGGER.info("  halaman %d/%d", page_number, total_pages)


def _empty_statistics() -> dict[str, Any]:
    return {
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
    }


def _build_notes_payload(
    document: dict[str, Any], parsed: dict[str, Any]
) -> dict[str, Any]:
    pages_with_issues = [
        page
        for page in parsed["pages"]
        if page.get("flags")
        or page.get("notes")
        or page.get("extraction_status") != "text_extracted"
    ]
    return {
        "schema_version": config.SCHEMA_VERSION,
        "document_id": document["document_id"],
        "document_name": document["document_name"],
        "generated_at": output.utc_now(),
        "summary": parsed["statistics"],
        "document_notes": parsed["document_notes"],
        "pages_with_issues": pages_with_issues,
        "repeated_lines": parsed["repeated_lines"],
        "table_issues": parsed["table_issues"],
        "structure_issues": parsed["structure_issues"],
    }


def _build_failed_notes_payload(
    source: dict[str, Any], error_message: str
) -> dict[str, Any]:
    return {
        "schema_version": config.SCHEMA_VERSION,
        "document_id": source["document_id"],
        "document_name": Path(source["path"]).name,
        "generated_at": output.utc_now(),
        "summary": _empty_statistics(),
        "document_notes": [f"extraction_failed:{error_message}"],
        "pages_with_issues": [],
        "repeated_lines": {
            "threshold": 0,
            "header_candidates": [],
            "footer_candidates": [],
        },
        "table_issues": [],
        "structure_issues": {},
    }


def command_extract(args: argparse.Namespace, paths: config.ProjectPaths) -> int:
    sources, unregistered = extract.discover_sources(paths, args.doc)
    manual_documents, manual_notes = output.load_manual_metadata(
        paths.manual_metadata
    )

    global_notes: list[str] = []
    for name in unregistered:
        global_notes.append(f"unregistered_pdf_ignored:{name}")
    global_notes.extend(manual_notes)

    if unregistered:
        LOGGER.warning(
            "PDF tidak terdaftar di registry dan dilewati: %s",
            ", ".join(unregistered),
        )
    for note in manual_notes:
        LOGGER.warning("Metadata manual: %s", note)

    document_ids = [source["document_id"] for source in sources]
    targets = output.all_target_paths(paths, document_ids)
    existing = output.existing_paths(targets)

    if existing and not args.overwrite and not args.dry_run:
        LOGGER.error(
            "Output sudah ada. Gunakan --overwrite untuk membackup lalu menimpa:"
        )
        for path in existing:
            LOGGER.error("  %s", path)
        return 1

    if existing and args.overwrite and not args.dry_run:
        backup_root = output.backup_files(paths, existing, output.utc_stamp())
        relative_backup = config.to_relative_posix(backup_root, paths.root)
        global_notes.append(f"previous_outputs_backed_up:{relative_backup}")
        LOGGER.info("Output lama dibackup ke %s", relative_backup)

    settings = {
        "reading_order": "native",
        "tables_enabled": not args.no_tables,
        "printed_page_detection_enabled": not args.no_printed_page_detection,
        "ocr_enabled": False,
        "dehyphenation": "enabled" if args.dehyphenate else "disabled",
    }

    entries: list[dict[str, Any]] = []
    extractor_versions: list[str] = []
    failed_documents = 0

    for source in sources:
        document_id = source["document_id"]
        LOGGER.info("Memproses %s (%s)", document_id, source["document_name"])
        document_paths = output.document_output_paths(paths, document_id)

        try:
            document = extract.extract_document(
                source,
                paths,
                tables_enabled=not args.no_tables,
                progress=_progress,
            )
            parsed = parse.parse_document(
                document,
                dehyphenate=args.dehyphenate,
                detect_printed_pages=not args.no_printed_page_detection,
            )
            extractor_versions.append(str(document.get("extractor_version", "unknown")))

            if not args.dry_run:
                output.write_jsonl(document_paths["pages"], parsed["pages"])
                output.write_jsonl(document_paths["blocks"], parsed["blocks"])
                output.write_json(
                    document_paths["notes"],
                    _build_notes_payload(document, parsed),
                )

            entry = output.build_document_entry(
                document, parsed, paths, manual_documents, document_paths
            )
            entries.append(entry)

            LOGGER.info(
                "  status=%s halaman=%s blok=%s tabel=%s",
                parsed["extraction_status"],
                document["total_pdf_pages"],
                parsed["statistics"]["blocks_total"],
                parsed["statistics"]["tables_detected"],
            )
            if args.dry_run:
                LOGGER.info("  dry-run: tidak ada file yang ditulis")

        except Exception as exc:
            failed_documents += 1
            message = f"{type(exc).__name__}: {exc}"
            LOGGER.error("Gagal memproses %s: %s", document_id, message)

            if not args.dry_run:
                try:
                    output.write_json(
                        document_paths["notes"],
                        _build_failed_notes_payload(source, message),
                    )
                except OSError as write_exc:
                    LOGGER.error(
                        "Gagal menulis catatan kegagalan %s: %s",
                        document_id,
                        write_exc,
                    )

            entries.append(
                output.build_failed_entry(
                    source,
                    paths,
                    manual_documents,
                    message,
                    document_paths["notes"],
                )
            )

    if args.dry_run:
        LOGGER.info(
            "Dry-run selesai: %d dokumen diproses, %d gagal. Tidak ada output ditulis.",
            len(sources),
            failed_documents,
        )
        return 1 if failed_documents else 0

    extractor_version = next(
        (version for version in extractor_versions if version != "unknown"),
        "unknown",
    )

    manifest = output.build_manifest(
        paths,
        entries,
        settings,
        extractor_version,
        global_notes=global_notes,
        merge_existing=True,
    )
    output.write_json(paths.manifest, manifest)
    output.write_text(paths.report, output.build_report(manifest, global_notes))

    LOGGER.info("Manifest: %s", paths.manifest)
    LOGGER.info("Report: %s", paths.report)
    LOGGER.info(
        "Selesai: %d dokumen, %d gagal.",
        len(entries),
        failed_documents,
    )
    return 1 if failed_documents else 0


def command_validate(args: argparse.Namespace, paths: config.ProjectPaths) -> int:
    report = validate.validate_outputs(paths, strict=args.strict)
    output.write_json(paths.validation_report, report)

    summary = report.get("summary", {})
    LOGGER.info(
        "Validasi selesai: %s dokumen, %s error, %s warning.",
        summary.get("documents", 0),
        summary.get("errors", 0),
        summary.get("warnings", 0),
    )
    for document in report.get("documents", []):
        LOGGER.info(
            "  %s: %s (%s error, %s warning)",
            document.get("document_id"),
            document.get("status"),
            len(document.get("errors", [])),
            len(document.get("warnings", [])),
        )
        for issue in document.get("errors", [])[:10]:
            LOGGER.error("    %s", issue)
        for issue in document.get("warnings", [])[:10]:
            LOGGER.warning("    %s", issue)

    LOGGER.info("Laporan validasi: %s", paths.validation_report)
    return validate.validation_exit_code(report, strict=args.strict)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_extraction.py",
        description=(
            "Pipeline ekstraksi dan parsing PDF untuk proyek KBR. "
            "Tidak menggunakan OCR, API eksternal, atau LLM."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser(
        "extract",
        help="Ekstrak PDF menjadi blocks/pages JSONL dan manifest.",
    )
    extract_parser.add_argument(
        "--doc",
        choices=list(config.document_ids()),
        help="Proses hanya satu document_id.",
    )
    extract_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Backup output lama lalu tulis output baru.",
    )
    extract_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Jalankan ekstraksi tanpa menulis file output.",
    )
    extract_parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Matikan deteksi tabel.",
    )
    extract_parser.add_argument(
        "--no-printed-page-detection",
        action="store_true",
        help="Matikan deteksi nomor halaman tercetak.",
    )
    extract_parser.add_argument(
        "--dehyphenate",
        action="store_true",
        help=(
            "Gabungkan kata yang terpotong hyphen di akhir baris. "
            "Nonaktif secara default karena dapat mengubah istilah majemuk."
        ),
    )
    extract_parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Root proyek alternatif (default: lokasi folder proyek).",
    )
    extract_parser.add_argument("--verbose", action="store_true")

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validasi output ekstraksi yang sudah ada.",
    )
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Anggap warning sebagai kegagalan (exit code 1).",
    )
    validate_parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Root proyek alternatif (default: lokasi folder proyek).",
    )
    validate_parser.add_argument("--verbose", action="store_true")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(bool(getattr(args, "verbose", False)))

    try:
        paths = config.build_paths(args.project_root)
        if args.command == "extract":
            return command_extract(args, paths)
        if args.command == "validate":
            return command_validate(args, paths)
        parser.error(f"Perintah tidak dikenal: {args.command}")
        return 2
    except extract.ExtractionError as exc:
        LOGGER.error("%s", exc)
        return 1
    except Exception as exc:  # pragma: no cover - fallback terakhir
        if bool(getattr(args, "verbose", False)):
            LOGGER.exception("Kesalahan tak terduga: %s", exc)
        else:
            LOGGER.error("Kesalahan tak terduga: %s", exc)
        return 1
