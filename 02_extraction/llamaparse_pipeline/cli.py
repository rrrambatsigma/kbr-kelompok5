"""Command-line interface pipeline LlamaParse DOC002."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Optional

from pdf_pipeline.output import read_json, utc_now, write_json

from . import baseline, chunk, compare, config, normalize, promote, quality, store
from .client import (
    LlamaParseClient,
    LlamaParseConfigError,
    describe_exception,
    load_environment,
)


LOGGER = logging.getLogger("kbr_llamaparse")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    # SDK mencetak URL presigned pada level INFO; jangan simpan ke log.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def _pdf_page_count(pdf_path: Path) -> int:
    try:
        import pymupdf
    except ImportError:  # pragma: no cover - PyMuPDF terpasang
        import fitz as pymupdf
    with pymupdf.open(pdf_path) as document:
        return int(document.page_count)


def count_range_pages(target_pages: Optional[str], total_pages: int) -> int:
    """Menghitung jumlah halaman pada string ``page_ranges`` 1-based."""

    if not target_pages:
        return total_pages
    selected: set[int] = set()
    for part in target_pages.split(","):
        piece = part.strip()
        if not piece:
            continue
        if "-" in piece:
            start_text, end_text = piece.split("-", 1)
            selected.update(range(int(start_text), int(end_text) + 1))
        else:
            selected.add(int(piece))
    return len({page for page in selected if 1 <= page <= total_pages})


def _poll_timeout(pages: int) -> float:
    return float(
        config.JOB_TIMEOUT_BASE_SECONDS + config.JOB_TIMEOUT_PER_PAGE_SECONDS * pages
    )


def _plan_run(
    tier: str,
    version: str,
    target_pages: Optional[str],
    label: Optional[str],
    with_images: bool,
) -> dict[str, Any]:
    if tier not in config.TIERS:
        raise ValueError(f"Tier tidak dikenal: {tier}. Pilihan: {config.TIERS}")
    if not re.match(r"^(?:latest|\d{4}-\d{2}-\d{2})$", version):
        raise ValueError(
            "Versi harus 'latest' atau tanggal YYYY-MM-DD "
            "(lihat perintah versions untuk daftar per tier)"
        )
    total_pages = _pdf_page_count(config.PDF_PATH)
    page_ranges = {"target_pages": target_pages} if target_pages else None
    selected_pages = count_range_pages(target_pages, total_pages)
    options = config.build_parse_options(
        tier=tier,
        version=version,
        page_ranges=page_ranges,
        page_count=selected_pages,
        with_images=with_images,
    )
    source_sha256 = config.sha256_file(config.PDF_PATH)
    return {
        "tier": tier,
        "version": version,
        "total_pages": total_pages,
        "selected_pages": selected_pages,
        "page_ranges": page_ranges,
        "options": options,
        "source_sha256": source_sha256,
        "run_id": config.make_run_id(source_sha256, options, label),
    }


def _existing_run(
    run_id: str,
    require_completed: bool = True,
) -> Optional[dict[str, Any]]:
    manifest_path = config.run_paths(run_id)["manifest"]
    if not manifest_path.exists():
        return None
    try:
        manifest = read_json(manifest_path)
    except (OSError, ValueError):
        return None
    if not isinstance(manifest, dict):
        return None
    if require_completed and manifest.get("job_status") != "COMPLETED":
        return None
    return manifest


def _summary(manifest: dict[str, Any]) -> str:
    return json.dumps(
        {
            "run_id": manifest.get("run_id"),
            "job_id": manifest.get("job_id"),
            "job_status": manifest.get("job_status"),
            "tier": (manifest.get("options") or {}).get("tier"),
            "version": (manifest.get("options") or {}).get("version"),
            "pages_expected": manifest.get("pages_expected"),
            "pages_success": manifest.get("pages_success"),
            "pages_failed": manifest.get("pages_failed"),
            "tables_detected": manifest.get("tables_detected"),
            "credits_used": manifest.get("credits_used"),
            "job_error": manifest.get("job_error"),
        },
        ensure_ascii=False,
        indent=2,
    )


def _latest_completed_run() -> Optional[dict[str, Any]]:
    for manifest in store.list_runs():
        if manifest.get("job_status") == "COMPLETED":
            return manifest
    return None


def _run_id_from_args(args: argparse.Namespace) -> str:
    if getattr(args, "run", None):
        return str(args.run)
    manifest = _latest_completed_run()
    if manifest is None:
        raise RuntimeError("Belum ada run yang selesai. Jalankan parse terlebih dahulu.")
    return str(manifest["run_id"])


# ----------------------------------------------------------------------
# Parse commands
# ----------------------------------------------------------------------
def _run_parse(
    tier: str,
    version: str,
    target_pages: Optional[str],
    label: Optional[str],
    force: bool,
    download_images: bool,
    dry_run: bool,
) -> tuple[int, Optional[str]]:
    if not config.PDF_PATH.exists():
        LOGGER.error("PDF tidak ditemukan: %s", config.PDF_PATH)
        return 1, None

    plan = _plan_run(tier, version, target_pages, label, download_images)
    run_id = plan["run_id"]
    LOGGER.info(
        "Rencana parse: dokumen=%s halaman=%s tier=%s version=%s run_id=%s",
        config.DOCUMENT_ID,
        target_pages or f"1-{plan['total_pages']}",
        tier,
        version,
        run_id,
    )

    if dry_run:
        print(json.dumps({"run_id": run_id, "options": plan["options"]}, indent=2))
        return 0, run_id

    existing = _existing_run(run_id)
    if existing and not force:
        LOGGER.info("Run sudah selesai; tidak memanggil API lagi")
        print(_summary(existing))
        return 0, run_id

    load_environment(config.ENV_PATH)

    base_manifest = {
        "schema_version": config.base_config.SCHEMA_VERSION,
        "pipeline": {
            "name": config.PIPELINE_NAME,
            "version": config.PIPELINE_VERSION,
        },
        "document_id": config.DOCUMENT_ID,
        "source_file": config.PDF_PATH.name,
        "source_path": config.base_config.to_relative_posix(
            config.PDF_PATH, config.PROJECT_ROOT
        ),
        "source_sha256": plan["source_sha256"],
        "file_size_bytes": config.PDF_PATH.stat().st_size,
        "total_pdf_pages": plan["total_pages"],
        "selected_pages": plan["selected_pages"],
        "options": plan["options"],
        "options_fingerprint": config.options_fingerprint(plan["options"]),
        "started_at": utc_now(),
    }

    client: Optional[LlamaParseClient] = None
    try:
        client = LlamaParseClient(registry_dir=config.RAW_DIR / config.DOCUMENT_ID)
        upload = client.upload(
            config.PDF_PATH, plan["source_sha256"], reuse=not force
        )
        base_manifest["file_id"] = upload.get("file_id")
        base_manifest["upload_reused"] = upload.get("reused")

        result = client.parse(
            file_id=str(upload["file_id"]),
            options=plan["options"],
            poll_timeout_seconds=_poll_timeout(plan["selected_pages"]),
            verbose=False,
        )
        manifest = store.persist_response(
            result, run_id, base_manifest, download_images=download_images
        )
        print(_summary(manifest))
        if manifest.get("job_status") != "COMPLETED":
            LOGGER.error("Job tidak selesai normal: %s", manifest.get("job_status"))
            return 2, run_id
        return 0, run_id
    except LlamaParseConfigError as exc:
        LOGGER.error("Konfigurasi: %s", exc)
        return 1, None
    except Exception as exc:  # noqa: BLE001 - batas CLI
        message = describe_exception(exc)
        LOGGER.error("Parse gagal: %s", message)
        failure = {
            **base_manifest,
            "run_id": run_id,
            "job_status": "FAILED",
            "job_error": message,
            "completed_at": utc_now(),
        }
        try:
            write_json(config.run_paths(run_id)["manifest"], failure)
        except OSError:
            pass
        return 2, run_id
    finally:
        if client is not None:
            client.close()


def command_env_check(args: argparse.Namespace, paths: Any = None) -> int:
    status = load_environment(config.ENV_PATH)
    print(json.dumps(status, indent=2))
    if not status["api_key_present"]:
        print("API key tidak ditemukan. Isi .env dengan LLAMA_CLOUD_API_KEY.")
        return 1
    print("API key terdeteksi (nilai tidak ditampilkan).")
    return 0


def command_versions(args: argparse.Namespace, paths: Any = None) -> int:
    """Menampilkan versi parser per tier (tanpa memakai kredit)."""

    load_environment(config.ENV_PATH)
    client = LlamaParseClient(registry_dir=config.RAW_DIR / config.DOCUMENT_ID)
    try:
        data = client.list_versions()
    except Exception as exc:  # noqa: BLE001 - pesan sudah disanitasi
        LOGGER.error("Gagal membaca daftar versi: %s", describe_exception(exc))
        return 2
    finally:
        client.close()

    tiers = {key: value for key, value in data.items() if key != "latest"}
    print(
        json.dumps(
            {
                "latest": data.get("latest"),
                "tiers": {key: value[:5] for key, value in tiers.items()},
            },
            indent=2,
        )
    )
    return 0


def command_smoke(args: argparse.Namespace, paths: Any = None) -> int:
    code, _ = _run_parse(
        tier=args.tier,
        version=args.version,
        target_pages=str(args.page),
        label="smoke",
        force=args.force,
        download_images=not args.no_images,
        dry_run=args.dry_run,
    )
    return code


def command_parse(args: argparse.Namespace, paths: Any = None) -> int:
    code, _ = _run_parse(
        tier=args.tier,
        version=args.version,
        target_pages=args.pages,
        label=args.label,
        force=args.force,
        download_images=not args.no_images,
        dry_run=args.dry_run,
    )
    return code


# ----------------------------------------------------------------------
# Build / quality / compare
# ----------------------------------------------------------------------
def _build_outputs(run_id: str) -> dict[str, Any]:
    snapshot = baseline.ensure_snapshot()
    normalization = normalize.normalize_run(run_id)
    chunking = chunk.build_chunks(run_id)
    report = quality.evaluate_run(run_id)
    return {
        "baseline": snapshot.get("source"),
        "normalization": normalization,
        "chunking": chunking,
        "quality": report,
    }


def command_build(args: argparse.Namespace, paths: Any = None) -> int:
    run_id = _run_id_from_args(args)
    result = _build_outputs(run_id)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "baseline_snapshot": result["baseline"],
                "pages": result["normalization"]["pages"],
                "blocks": result["normalization"]["blocks"],
                "chunks": result["chunking"]["chunks"],
                "quality_status": result["quality"]["status"],
                "issues": result["quality"]["issues"],
            },
            indent=2,
        )
    )
    return 0 if result["quality"]["status"] != "fail" else 2


def command_quality(args: argparse.Namespace, paths: Any = None) -> int:
    run_id = _run_id_from_args(args)
    report = quality.evaluate_run(run_id)
    print(json.dumps({k: v for k, v in report.items() if k != "page_stats"}, indent=2))
    return 0 if report["status"] != "fail" else 2


def command_compare(args: argparse.Namespace, paths: Any = None) -> int:
    run_id = _run_id_from_args(args)
    report = compare.compare_run(run_id)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "gate_passed": report["gate_passed"],
                "text_similarity": report["text_similarity"],
                "headings": {
                    "count": report["headings"]["llamaparse_chapter_count"],
                    "expected": report["headings"]["expected_chapter_count"],
                    "chapters": report["headings"]["llamaparse_chapter_headings"],
                },
                "printed_page_numbers": report["printed_page_numbers"],
                "tables": report["tables"],
                "gates": report["gates"],
            },
            indent=2,
        )
    )
    return 0 if report["gate_passed"] else 2


def command_images(args: argparse.Namespace, paths: Any = None) -> int:
    """Mengambil ulang gambar yang gagal diunduh saat parsing (tanpa kredit)."""

    run_id = _run_id_from_args(args)
    pending = store.pending_images(run_id)
    if not pending:
        store.update_image_stats(run_id)
        print(
            json.dumps(
                {"run_id": run_id, "pending": 0, "message": "semua gambar tersimpan"},
                indent=2,
            )
        )
        return 0
    if args.dry_run:
        print(
            json.dumps(
                {"run_id": run_id, "pending": len(pending), "filenames": pending},
                indent=2,
            )
        )
        return 0

    manifest = store.load_manifest(run_id)
    job_id = str(manifest.get("job_id") or "")
    if not job_id:
        raise RuntimeError("Manifest tidak memuat job_id; gambar tidak bisa diambil ulang.")

    load_environment(config.ENV_PATH)
    client = LlamaParseClient(registry_dir=config.LLAMAPARSE_DIR)
    try:
        result = client.get(
            job_id,
            expand=["images_content_metadata"],
            image_filenames=",".join(pending),
        )
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        block = (payload or {}).get("images_content_metadata") or {}
        stats = store.download_images(run_id, block.get("images") or [])
    finally:
        client.close()

    store.update_image_stats(run_id, stats)
    remaining = store.pending_images(run_id)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "requested": len(pending),
                "downloaded": stats["downloaded"],
                "failed": stats["failed"],
                "skipped": stats["skipped"],
                "remaining": len(remaining),
            },
            indent=2,
        )
    )
    return 0 if not remaining else 2


def command_runs(args: argparse.Namespace, paths: Any = None) -> int:
    runs = store.list_runs()
    if not runs:
        print("Belum ada run LlamaParse.")
        return 0
    for manifest in runs:
        print(
            "{run_id} | {status} | tier={tier} | pages={pages} | credits={credits}".format(
                run_id=manifest.get("run_id"),
                status=manifest.get("job_status"),
                tier=(manifest.get("options") or {}).get("tier"),
                pages=manifest.get("pages_expected"),
                credits=manifest.get("credits_used"),
            )
        )
    return 0


# ----------------------------------------------------------------------
# Pilot / full run
# ----------------------------------------------------------------------
def command_pilot(args: argparse.Namespace, paths: Any = None) -> int:
    tiers = [item.strip() for item in args.tiers.split(",") if item.strip()]
    invalid = [tier for tier in tiers if tier not in config.TIERS]
    if invalid:
        print(f"Tier tidak dikenal: {invalid}; pilihan: {config.TIERS}")
        return 1

    pages = ",".join(str(page) for page in config.PILOT_PAGES)
    results: list[dict[str, Any]] = []

    for tier in tiers:
        LOGGER.info("=== Pilot tier %s ===", tier)
        code, run_id = _run_parse(
            tier=tier,
            version=args.version,
            target_pages=pages,
            label="pilot",
            force=args.force,
            download_images=not args.no_images,
            dry_run=False,
        )
        if code != 0 or run_id is None:
            results.append({"tier": tier, "status": "parse_failed"})
            continue

        built = _build_outputs(run_id)
        comparison = compare.compare_run(run_id)
        manifest = store.load_manifest(run_id)
        results.append(
            {
                "tier": tier,
                "run_id": run_id,
                "status": "ok",
                "pages": built["normalization"]["pages"],
                "blocks": built["normalization"]["blocks"],
                "chunks": built["chunking"]["chunks"],
                "credits": manifest.get("credits_used"),
                "quality_status": built["quality"]["status"],
                "quality_issues": built["quality"]["issues"],
                "cer_mean": comparison["text_similarity"]["cer_mean"],
                "cer_noise_adjusted_mean": comparison["text_similarity"][
                    "cer_noise_adjusted_mean"
                ],
                "chapter_count": comparison["headings"]["llamaparse_chapter_count"],
                "printed_page_numbers": comparison["printed_page_numbers"]["detected"],
                "tables": len(comparison["tables"]["llamaparse_pages"]),
                "gate_passed": comparison["gate_passed"],
                "tables_pages": comparison["tables"]["llamaparse_pages"],
            }
        )

    ok_results = [item for item in results if item.get("status") == "ok"]

    def _score(item: dict[str, Any]) -> tuple[float, float]:
        cer = item.get("cer_noise_adjusted_mean")
        credits = float(item.get("credits") or 0)
        return (float(cer) if cer is not None else 1.0, credits)

    recommendation = min(ok_results, key=_score) if ok_results else None

    report = {
        "schema_version": "1.0.0",
        "document_id": config.DOCUMENT_ID,
        "generated_at": utc_now(),
        "version": args.version,
        "pages": list(config.PILOT_PAGES),
        "results": results,
        "recommended_tier": recommendation.get("tier") if recommendation else None,
        "recommendation_basis": (
            "CER terendah (noise-adjusted), lalu kredit terendah"
            if recommendation
            else "tidak ada run yang berhasil"
        ),
    }
    path = config.REPORTS_DIR / f"{config.DOCUMENT_ID}.pilot.json"
    write_json(path, report)
    print(json.dumps(report, indent=2))
    return 0 if ok_results else 2


def command_full(args: argparse.Namespace, paths: Any = None) -> int:
    code, run_id = _run_parse(
        tier=args.tier,
        version=args.version,
        target_pages=None,
        label="full",
        force=args.force,
        download_images=not args.no_images,
        dry_run=False,
    )
    if code != 0 or run_id is None:
        return code

    built = _build_outputs(run_id)
    comparison = compare.compare_run(run_id)
    manifest = store.load_manifest(run_id)
    summary: dict[str, Any] = {
        "run_id": run_id,
        "tier": args.tier,
        "version": args.version,
        "credits": manifest.get("credits_used"),
        "pages": built["normalization"]["pages"],
        "blocks": built["normalization"]["blocks"],
        "chunks": built["chunking"]["chunks"],
        "quality_status": built["quality"]["status"],
        "gate_passed": comparison["gate_passed"],
        "cer_mean": comparison["text_similarity"]["cer_mean"],
        "cer_noise_adjusted_mean": comparison["text_similarity"]["cer_noise_adjusted_mean"],
        "cer_content_loss_mean": comparison["text_similarity"].get(
            "cer_content_loss_mean"
        ),
        "chapter_count": comparison["headings"]["llamaparse_chapter_count"],
        "printed_page_numbers": comparison["printed_page_numbers"]["detected"],
        "tables": comparison["tables"],
        "promoted": False,
    }

    if comparison["gate_passed"] and not args.no_promote:
        promotion = promote.promote(run_id, built["quality"], comparison)
        summary["promoted"] = True
        summary["promotion"] = {
            "backup": promotion["backup"],
            "outputs": promotion["outputs"],
        }
    elif not comparison["gate_passed"]:
        LOGGER.warning(
            "Gate tidak lolos; output canonical tidak diubah. "
            "Lihat reports/DOC002.comparison.json"
        )

    print(json.dumps(summary, indent=2))
    return 0 if comparison["gate_passed"] or args.allow_failed_gate else 2


def command_promote(args: argparse.Namespace, paths: Any = None) -> int:
    """Mempromosikan run yang sudah lolos gate tanpa memanggil API lagi."""

    run_id = _run_id_from_args(args)
    quality_report = quality.evaluate_run(run_id)
    comparison = compare.compare_run(run_id)
    manifest = store.load_manifest(run_id)
    if not comparison.get("is_full_run"):
        print("Promosi hanya untuk full run 274 halaman.")
        return 1
    if not comparison.get("gate_passed"):
        print("Gate belum lolos; output canonical tidak diubah.")
        return 2

    promotion = promote.promote(run_id, quality_report, comparison)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "tier": (manifest.get("options") or {}).get("tier"),
                "version": (manifest.get("options") or {}).get("version"),
                "backup": promotion["backup"],
                "outputs": promotion["outputs"],
                "validation": promotion["validation"],
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_llamaparse",
        description="Pipeline LlamaParse untuk DOC002 (PenyakitTanamanPangan).",
    )
    parser.add_argument("--verbose", action="store_true", help="log debug")
    subparsers = parser.add_subparsers(dest="command", required=True)

    env_parser = subparsers.add_parser(
        "env-check", help="cek keberadaan API key tanpa memanggil API"
    )
    env_parser.set_defaults(func=command_env_check)

    versions = subparsers.add_parser(
        "versions", help="daftar versi parser per tier (tanpa kredit)"
    )
    versions.set_defaults(func=command_versions)

    smoke = subparsers.add_parser("smoke", help="parse satu halaman sebagai uji koneksi")
    smoke.add_argument("--page", type=int, default=25, help="nomor halaman PDF (1-based)")
    smoke.add_argument("--tier", default="cost_effective", choices=config.TIERS)
    smoke.add_argument("--version", default=config.DEFAULT_VERSION)
    smoke.add_argument("--force", action="store_true", help="abaikan cache run lokal")
    smoke.add_argument("--no-images", action="store_true", help="jangan unduh gambar")
    smoke.add_argument("--dry-run", action="store_true")
    smoke.set_defaults(func=command_smoke)

    parse = subparsers.add_parser("parse", help="jalankan parsing (subset atau penuh)")
    parse.add_argument("--tier", default=config.DEFAULT_TIER, choices=config.TIERS)
    parse.add_argument("--version", default=config.DEFAULT_VERSION)
    parse.add_argument("--pages", default=None, help='contoh: "25,27,91-95"')
    parse.add_argument("--label", default=None, help="label run, mis. pilot atau full")
    parse.add_argument("--force", action="store_true")
    parse.add_argument("--no-images", action="store_true")
    parse.add_argument("--dry-run", action="store_true")
    parse.set_defaults(func=command_parse)

    build = subparsers.add_parser(
        "build", help="normalisasi, chunking, dan quality untuk run tertentu"
    )
    build.add_argument("--run", default=None, help="run_id (default: run terakhir)")
    build.set_defaults(func=command_build)

    quality_parser = subparsers.add_parser("quality", help="hitung ulang laporan kualitas")
    quality_parser.add_argument("--run", default=None)
    quality_parser.set_defaults(func=command_quality)

    compare_parser = subparsers.add_parser(
        "compare", help="bandingkan dengan baseline PyMuPDF"
    )
    compare_parser.add_argument("--run", default=None)
    compare_parser.set_defaults(func=command_compare)

    images_parser = subparsers.add_parser(
        "images", help="ambil ulang gambar yang gagal diunduh (tanpa kredit)"
    )
    images_parser.add_argument("--run", default=None)
    images_parser.add_argument("--dry-run", action="store_true")
    images_parser.set_defaults(func=command_images)

    runs = subparsers.add_parser("runs", help="daftar run yang tersimpan")
    runs.set_defaults(func=command_runs)

    pilot = subparsers.add_parser(
        "pilot", help="uji beberapa tier pada halaman sampel"
    )
    pilot.add_argument("--tiers", default="fast,cost_effective,agentic")
    pilot.add_argument("--version", default=config.DEFAULT_VERSION)
    pilot.add_argument("--force", action="store_true")
    pilot.add_argument("--no-images", action="store_true")
    pilot.set_defaults(func=command_pilot)

    full = subparsers.add_parser("full", help="proses 274 halaman lalu bandingkan")
    full.add_argument("--tier", default=config.DEFAULT_TIER, choices=config.TIERS)
    full.add_argument("--version", default=config.DEFAULT_VERSION)
    full.add_argument("--force", action="store_true")
    full.add_argument("--no-images", action="store_true")
    full.add_argument(
        "--no-promote",
        action="store_true",
        help="jangan timpa output canonical meski gate lolos",
    )
    full.add_argument(
        "--allow-failed-gate",
        action="store_true",
        help="kembalikan exit code 0 meski gate gagal (tidak mempromosikan)",
    )
    full.set_defaults(func=command_full)

    promote_parser = subparsers.add_parser(
        "promote", help="promosikan run yang lolos gate ke output canonical"
    )
    promote_parser.add_argument("--run", default=None)
    promote_parser.set_defaults(func=command_promote)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
