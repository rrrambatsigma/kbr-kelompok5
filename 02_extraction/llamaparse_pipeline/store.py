"""Penyimpanan hasil mentah LlamaParse dan manifest run.

Semua artefak ditulis di namespace terpisah (``02_extraction/llamaparse/``)
sehingga output canonical PyMuPDF tidak tersentuh.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from pdf_pipeline.output import (
    read_json,
    read_jsonl,
    utc_now,
    write_json,
    write_jsonl,
    write_text,
)

from . import config


LOGGER = logging.getLogger("kbr_llamaparse")


def _dump(value: Any) -> Any:
    """Mengubah model Pydantic (atau struktur lain) menjadi tipe JSON murni."""

    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=False)
    if isinstance(value, dict):
        return {str(key): _dump(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def get_attr(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _pages_dir(run_id: str) -> Path:
    path = config.run_paths(run_id)["pages_dir"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _page_tag(page_number: int) -> str:
    return f"page_{page_number:04d}"


def persist_response(
    result: Any,
    run_id: str,
    base_manifest: dict[str, Any],
    download_images: bool = True,
) -> dict[str, Any]:
    """Menyimpan respons lengkap + turunannya dan mengembalikan manifest final."""

    payload = _dump(result)
    paths = config.run_paths(run_id)
    paths["root"].mkdir(parents=True, exist_ok=True)
    write_json(paths["response"], payload)

    job = payload.get("job") or {}
    markdown_block = payload.get("markdown") or {}
    items_block = payload.get("items") or {}
    metadata_block = payload.get("metadata") or {}
    images_block = payload.get("images_content_metadata") or {}

    markdown_pages = {
        int(page.get("page_number")): page
        for page in (markdown_block.get("pages") or [])
        if page.get("page_number") is not None
    }
    items_pages = {
        int(page.get("page_number")): page
        for page in (items_block.get("pages") or [])
        if page.get("page_number") is not None
    }
    metadata_pages = {
        int(page.get("page_number")): page
        for page in (metadata_block.get("pages") or [])
        if page.get("page_number") is not None
    }

    page_numbers = sorted(
        set(markdown_pages) | set(items_pages) | set(metadata_pages)
    )

    markdown_parts: list[str] = []
    table_count = 0
    image_caption_count = 0
    pages_success = 0
    pages_failed = 0
    page_summaries: list[dict[str, Any]] = []

    tables_dir = paths["tables_dir"]
    tables_dir.mkdir(parents=True, exist_ok=True)

    for page_number in page_numbers:
        tag = _page_tag(page_number)
        markdown_page = markdown_pages.get(page_number, {})
        items_page = items_pages.get(page_number, {})
        metadata_page = metadata_pages.get(page_number, {})

        success = bool(markdown_page.get("success", items_page.get("success", True)))
        if success:
            pages_success += 1
        else:
            pages_failed += 1

        markdown_text = markdown_page.get("markdown") or ""
        write_text(_pages_dir(run_id) / f"{tag}.md", markdown_text)
        if markdown_text:
            markdown_parts.append(markdown_text)

        page_meta = {
            "page_number": page_number,
            "success": success,
            "error": markdown_page.get("error") or items_page.get("error"),
            "header": markdown_page.get("header"),
            "footer": markdown_page.get("footer"),
            "markdown_char_count": len(markdown_text),
            "confidence": metadata_page.get("confidence"),
            "printed_page_number": metadata_page.get("printed_page_number"),
            "original_orientation_angle": metadata_page.get("original_orientation_angle"),
            "cost_optimized": metadata_page.get("cost_optimized"),
            "watermark": metadata_page.get("watermark"),
            "page_width": items_page.get("page_width"),
            "page_height": items_page.get("page_height"),
            "item_count": len(items_page.get("items") or []),
        }
        write_json(_pages_dir(run_id) / f"{tag}.meta.json", page_meta)
        page_summaries.append(page_meta)

        items = items_page.get("items") or []
        write_json(_pages_dir(run_id) / f"{tag}.items.json", _dump(items))

        table_index = 0
        for item in items:
            item_type = item.get("type")
            if item_type == "table":
                table_index += 1
                table_count += 1
                base = tables_dir / f"{tag}_table_{table_index:02d}"
                if item.get("csv"):
                    write_text(base.with_suffix(".csv"), item["csv"])
                if item.get("md"):
                    write_text(base.with_suffix(".md"), item["md"])
                write_json(base.with_suffix(".json"), item)
            elif item_type == "image" and (item.get("caption") or "").strip():
                image_caption_count += 1

    write_text(paths["markdown_full"], "\n\n".join(markdown_parts))

    image_stats = {"downloaded": 0, "failed": 0, "skipped": 0}
    if download_images:
        image_stats = _download_images(run_id, items_pages, images_block)

    usage = (job.get("usage") or {}).get("credits") if isinstance(job, dict) else None
    manifest = {
        **base_manifest,
        "run_id": run_id,
        "job_id": job.get("id"),
        "job_status": job.get("status"),
        "job_error": job.get("error_message"),
        "job_tier": job.get("tier"),
        "job_created_at": job.get("created_at"),
        "job_updated_at": job.get("updated_at"),
        "credits_used": usage,
        "completed_at": utc_now(),
        "pages_expected": len(page_numbers),
        "pages_success": pages_success,
        "pages_failed": pages_failed,
        "tables_detected": table_count,
        "image_captions_detected": image_caption_count,
        "images": image_stats,
        "page_summaries": page_summaries,
    }
    write_json(paths["manifest"], manifest)

    write_json(
        config.report_paths()["cost"],
        {
            "run_id": run_id,
            "generated_at": utc_now(),
            "tier": manifest.get("options", {}).get("tier"),
            "version": manifest.get("options", {}).get("version"),
            "pages_expected": manifest.get("pages_expected"),
            "credits_used": usage,
            "usd_per_1000_credits": 1.25,
            "estimated_usd": (
                round(float(usage) * 1.25 / 1000, 4) if usage is not None else None
            ),
            "job_status": manifest.get("job_status"),
            "job_error": manifest.get("job_error"),
        },
    )
    return manifest


def _image_extension(url: str, content_type: Optional[str]) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    suffix = Path(urlparse(url).path).suffix
    return suffix or ".png"


def _download_images(
    run_id: str,
    items_pages: dict[int, dict[str, Any]],
    images_block: Any,
) -> dict[str, int]:
    """Mengunduh gambar segera karena presigned URL cepat kedaluwarsa."""

    import httpx

    stats = {"downloaded": 0, "failed": 0, "skipped": 0}
    images_dir = config.run_paths(run_id)["images_dir"]
    images_dir.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, Any]] = []
    downloaded_item_names: set[str] = set()

    def fetch(url: str) -> bytes:
        response = httpx.get(url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        return response.content

    for page_number, page in sorted(items_pages.items()):
        image_index = 0
        for item in page.get("items") or []:
            if item.get("type") != "image":
                continue
            url = item.get("url")
            if not url or not str(url).lower().startswith(("http://", "https://")):
                # Pada sebagian item, "url" berisi label gambar ("a", "b"),
                # bukan URL. Gambar asli diambil dari images_content_metadata.
                stats["skipped"] += 1
                continue
            image_index += 1
            ext = _image_extension(url, None)
            filename = f"{_page_tag(page_number)}_img_{image_index:02d}{ext}"
            target = images_dir / filename
            downloaded_item_names.add(Path(urlparse(url).path).name)
            try:
                content = fetch(url)
                target.write_bytes(content)
                stats["downloaded"] += 1
                index.append(
                    {
                        "page_number": page_number,
                        "filename": filename,
                        "source": "item",
                        "caption": item.get("caption"),
                        "bbox": item.get("bbox"),
                        "size_bytes": len(content),
                    }
                )
            except Exception as exc:
                stats["failed"] += 1
                LOGGER.warning(
                    "Gagal mengunduh gambar halaman %s: %s",
                    page_number,
                    type(exc).__name__,
                )

    for image in (get_attr(images_block, "images", None) or []):
        url = get_attr(image, "presigned_url")
        name = get_attr(image, "filename")
        if not url or not name:
            stats["skipped"] += 1
            continue
        if name in downloaded_item_names:
            stats["skipped"] += 1
            continue
        target = images_dir / f"meta_{name}"
        if target.exists():
            continue
        page_match = re.search(r"_p(\d+)_", name)
        page_number = int(page_match.group(1)) if page_match else None
        try:
            target.write_bytes(fetch(url))
            stats["downloaded"] += 1
            index.append(
                {
                    "page_number": page_number,
                    "filename": target.name,
                    "source": "images_content_metadata",
                    "category": get_attr(image, "category"),
                    "bbox": _dump(get_attr(image, "bbox")),
                    "size_bytes": target.stat().st_size,
                }
            )
        except Exception:
            stats["failed"] += 1

    write_json(images_dir / "index.json", index)
    return stats


def _image_index_path(run_id: str) -> Path:
    return config.run_paths(run_id)["images_dir"] / "index.json"


def pending_images(run_id: str) -> list[str]:
    """Nama gambar dari metadata yang belum tersimpan lokal.

    Presigned URL cepat kedaluwarsa sehingga sebagian unduhan gagal saat
    parsing. Nama yang belum ada di ``index.json`` bisa diambil ulang tanpa
    membuat job baru (tanpa kredit).
    """

    response = load_response(run_id)
    block = response.get("images_content_metadata") or {}
    expected = [
        str(get_attr(image, "filename"))
        for image in (get_attr(block, "images", None) or [])
        if get_attr(image, "filename")
    ]
    existing: set[str] = set()
    path = _image_index_path(run_id)
    if path.exists():
        for entry in read_json(path) or []:
            name = str(entry.get("filename") or "")
            if name.startswith("meta_"):
                existing.add(name[len("meta_") :])
    return sorted(set(expected) - existing)


def download_images(run_id: str, images: Any) -> dict[str, int]:
    """Mengunduh gambar hasil ``parsing.get`` dan memperbarui index lokal."""

    import httpx

    stats = {"downloaded": 0, "failed": 0, "skipped": 0}
    images_dir = config.run_paths(run_id)["images_dir"]
    images_dir.mkdir(parents=True, exist_ok=True)
    index_path = _image_index_path(run_id)
    index = read_json(index_path) if index_path.exists() else []
    if not isinstance(index, list):
        index = []

    for image in images or []:
        url = get_attr(image, "presigned_url")
        name = get_attr(image, "filename")
        if not url or not name:
            stats["skipped"] += 1
            continue
        target = images_dir / f"meta_{name}"
        if target.exists():
            stats["skipped"] += 1
            continue
        try:
            response = httpx.get(url, timeout=60.0, follow_redirects=True)
            response.raise_for_status()
            target.write_bytes(response.content)
        except Exception as exc:  # pragma: no cover - jaringan
            stats["failed"] += 1
            LOGGER.warning(
                "Gagal mengunduh gambar %s: %s", name, type(exc).__name__
            )
            continue
        stats["downloaded"] += 1
        page_match = re.search(r"_p(\d+)_", str(name))
        index.append(
            {
                "page_number": int(page_match.group(1)) if page_match else None,
                "filename": target.name,
                "source": "images_content_metadata",
                "category": get_attr(image, "category"),
                "bbox": _dump(get_attr(image, "bbox")),
                "size_bytes": target.stat().st_size,
            }
        )

    write_json(index_path, index)
    return stats


def update_image_stats(run_id: str, stats: Optional[dict[str, int]] = None) -> dict[str, Any]:
    """Menyelaraskan statistik gambar manifest dengan isi direktori run."""

    manifest = load_manifest(run_id)
    index = read_json(_image_index_path(run_id)) or []
    if not isinstance(index, list):
        index = []
    current = dict(manifest.get("images") or {})
    current["downloaded"] = len(index)
    current["failed"] = len(pending_images(run_id))
    manifest["images"] = current
    manifest["images_refreshed_at"] = utc_now()
    write_json(config.run_paths(run_id)["manifest"], manifest)
    return manifest


def load_manifest(run_id: str) -> dict[str, Any]:
    path = config.run_paths(run_id)["manifest"]
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"run manifest tidak valid: {path}")
    return data


def load_response(run_id: str) -> dict[str, Any]:
    path = config.run_paths(run_id)["response"]
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"response tidak valid: {path}")
    return data


def ensure_normalized(run_id: str) -> dict[str, list[dict[str, Any]]]:
    """Memuat hasil normalisasi dan memastikan berasal dari run yang diminta."""

    paths = config.normalized_paths()
    pages = read_jsonl(paths["pages"]) if paths["pages"].exists() else []
    blocks = read_jsonl(paths["blocks"]) if paths["blocks"].exists() else []
    chunks = read_jsonl(paths["chunks"]) if paths["chunks"].exists() else []
    if not pages:
        raise RuntimeError(
            f"Belum ada hasil normalisasi. Jalankan: build --run {run_id}"
        )
    stored_run = str(pages[0].get("run_id") or "")
    if stored_run != run_id:
        raise RuntimeError(
            f"Hasil normalisasi berasal dari run lain ({stored_run or 'tidak diketahui'}). "
            f"Jalankan: build --run {run_id}"
        )
    return {"pages": pages, "blocks": blocks, "chunks": chunks}


def list_runs() -> list[dict[str, Any]]:
    base = config.RAW_DIR / config.DOCUMENT_ID
    runs: list[dict[str, Any]] = []
    if not base.exists():
        return runs
    for directory in sorted(base.iterdir(), reverse=True):
        manifest_path = directory / "run_manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = read_json(manifest_path)
        except (OSError, ValueError):
            continue
        if isinstance(manifest, dict):
            runs.append(manifest)
    return runs


def dump_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    write_jsonl(path, records)


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(_dump(value), ensure_ascii=False))
