"""Snapshot beku baseline PyMuPDF untuk DOC002.

Output canonical ``extracted_text/DOC002.*`` sudah digantikan hasil LlamaParse.
Membacanya setiap kali build akan membandingkan keluaran parser dengan dirinya
sendiri, sehingga rekonsiliasi dan gate kehilangan makna. Modul ini menyalin
baseline PyMuPDF sekali dari backup ``pre_llamaparse_*`` ke
``llamaparse/baseline/`` dan memakai salinan itu sebagai otoritas pembanding.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from pdf_pipeline import config as base_config
from pdf_pipeline.output import read_json, read_jsonl, utc_now, write_json

from . import config


LOGGER = logging.getLogger("kbr_llamaparse")

FILE_KEYS = ("pages", "blocks")


def _file_name(key: str) -> str:
    return f"{config.DOCUMENT_ID}.{key}.jsonl"


def paths() -> dict[str, Path]:
    return {key: config.BASELINE_DIR / _file_name(key) for key in FILE_KEYS}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _looks_like_pymupdf(pages_path: Path) -> bool:
    """True bila halaman baseline berasal dari PyMuPDF, bukan LlamaParse."""

    try:
        for page in read_jsonl(pages_path):
            return str(page.get("text_source") or "") != "llamaparse"
    except (OSError, ValueError):
        return False
    return False


def _backup_candidates() -> list[Path]:
    """Backup ``pre_llamaparse_*`` yang memuat baseline, terlama lebih dulu."""

    root = base_config.build_paths().backup_dir
    if not root.is_dir():
        return []
    candidates = []
    for directory in sorted(root.glob("pre_llamaparse_*")):
        extracted = (
            directory / "02_extraction" / "extracted_text" / _file_name("pages")
        )
        if extracted.is_file():
            candidates.append(directory)
    return candidates


def _discover_source() -> tuple[Path, str]:
    """Direktori sumber baseline dan label asalnya."""

    for directory in _backup_candidates():
        pages_path = directory / "02_extraction" / "extracted_text" / _file_name("pages")
        blocks_path = (
            directory / "02_extraction" / "extracted_text" / _file_name("blocks")
        )
        if not blocks_path.is_file() or not _looks_like_pymupdf(pages_path):
            continue
        return directory / "02_extraction" / "extracted_text", f"backup:{directory.name}"

    extracted = base_config.build_paths().extracted_text_dir
    pages_path = extracted / _file_name("pages")
    if pages_path.is_file() and (extracted / _file_name("blocks")).is_file():
        if _looks_like_pymupdf(pages_path):
            return extracted, "canonical:extracted_text"

    raise RuntimeError(
        "Baseline PyMuPDF tidak ditemukan. Output canonical sudah berisi hasil "
        "LlamaParse dan tidak ada backup pre_llamaparse_* yang memuat baseline."
    )


def ensure_snapshot() -> dict[str, Any]:
    """Membuat snapshot baseline bila belum ada; idempoten."""

    targets = paths()
    manifest_path = config.BASELINE_MANIFEST
    if all(path.is_file() for path in targets.values()):
        if manifest_path.is_file():
            return read_json(manifest_path)
        return {"files": {key: str(path) for key, path in targets.items()}}

    source_dir, source_label = _discover_source()
    config.BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    files: dict[str, Any] = {}
    for key in FILE_KEYS:
        source = source_dir / _file_name(key)
        target = targets[key]
        shutil.copy2(source, target)
        files[key] = {
            "path": base_config.to_relative_posix(target, config.PROJECT_ROOT),
            "sha256": _sha256(target),
            "size_bytes": target.stat().st_size,
            "source": source_label,
        }
    manifest = {
        "schema_version": "1.0.0",
        "document_id": config.DOCUMENT_ID,
        "created_at": utc_now(),
        "authority": "pymupdf_text_layer",
        "source": source_label,
        "source_path": base_config.to_relative_posix(
            source_dir, config.PROJECT_ROOT
        ),
        "files": files,
        "note": (
            "Snapshot beku sebelum promosi LlamaParse; dipakai sebagai "
            "pembanding rekonsiliasi dan gate."
        ),
    }
    write_json(manifest_path, manifest)
    LOGGER.info(
        "Snapshot baseline dibuat dari %s; rekonsiliasi memakai salinan beku",
        source_label,
    )
    return manifest


def load_pages() -> list[dict[str, Any]]:
    ensure_snapshot()
    return read_jsonl(paths()["pages"])


def load_blocks() -> list[dict[str, Any]]:
    ensure_snapshot()
    return read_jsonl(paths()["blocks"])


def verify() -> Optional[str]:
    """Pesan kesalahan bila snapshot tidak cocok dengan manifest, selain None."""

    manifest_path = config.BASELINE_MANIFEST
    if not manifest_path.is_file():
        return "baseline_manifest_missing"
    manifest = read_json(manifest_path)
    for key, expected in (manifest.get("files") or {}).items():
        path = config.BASELINE_DIR / _file_name(key)
        if not path.is_file():
            return f"baseline_file_missing:{key}"
        if _sha256(path) != expected.get("sha256"):
            return f"baseline_hash_mismatch:{key}"
    return None
