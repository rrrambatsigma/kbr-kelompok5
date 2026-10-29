"""Klien tipis untuk LlamaParse API (llama-cloud SDK).

Tanggung jawab modul ini:
- memuat API key dari ``.env`` tanpa mencetak nilainya,
- mengunggah PDF sekali per hash (idempotensi),
- menjalankan parsing dan mengembalikan respons bertipe.

Tidak ada penulisan artefak di sini; penyimpanan dilakukan oleh ``store.py``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from pdf_pipeline.output import read_json, write_json


LOGGER = logging.getLogger("kbr_llamaparse")

UPLOAD_REGISTRY_NAME = "uploads.json"


class LlamaParseConfigError(RuntimeError):
    """Konfigurasi lokal tidak lengkap (mis. API key tidak ada)."""


def load_environment(env_path: Path) -> dict[str, bool]:
    """Memuat ``.env`` dan memetakan alias key ke nama yang dibaca SDK.

    Mengembalikan status saja (tanpa nilai) agar aman dicetak ke log.
    """

    try:
        from dotenv import load_dotenv
    except ImportError as exc:  # pragma: no cover - dependensi terpasang
        raise LlamaParseConfigError(
            "python-dotenv belum terpasang; jalankan pip install python-dotenv"
        ) from exc

    loaded = load_dotenv(dotenv_path=env_path, override=False)

    # SDK membaca LLAMA_CLOUD_API_KEY. Nilai lama di .env boleh memakai alias.
    resolved_from: Optional[str] = None
    if os.environ.get("LLAMA_CLOUD_API_KEY"):
        resolved_from = "LLAMA_CLOUD_API_KEY"
    else:
        for alias in ("LLAMA_KEY", "LLAMAPARSE_API_KEY"):
            value = os.environ.get(alias)
            if value:
                os.environ["LLAMA_CLOUD_API_KEY"] = value
                resolved_from = alias
                break

    return {
        "dotenv_file_found": env_path.exists(),
        "dotenv_loaded": bool(loaded),
        "api_key_present": bool(os.environ.get("LLAMA_CLOUD_API_KEY")),
        "api_key_from_alias": resolved_from is not None
        and resolved_from != "LLAMA_CLOUD_API_KEY",
    }


def redact(text: str, secret: Optional[str]) -> str:
    if not secret:
        return text
    return text.replace(secret, "[REDACTED]")


def _safe_message(exc: BaseException) -> str:
    secret = os.environ.get("LLAMA_CLOUD_API_KEY")
    message = f"{type(exc).__name__}: {exc}"
    message = redact(message, secret)
    return message[:800]


class LlamaParseClient:
    """Wrapper LlamaCloud dengan unggah sekali per hash dokumen."""

    def __init__(
        self,
        registry_dir: Optional[Path] = None,
        timeout_seconds: float = 180.0,
        max_retries: int = 5,
    ) -> None:
        if not os.environ.get("LLAMA_CLOUD_API_KEY"):
            raise LlamaParseConfigError(
                "API key LlamaCloud tidak ditemukan. Isi .env dengan "
                "LLAMA_CLOUD_API_KEY (atau alias LLAMA_KEY)."
            )

        try:
            import httpx
            from llama_cloud import LlamaCloud
        except ImportError as exc:  # pragma: no cover - dependensi terpasang
            raise LlamaParseConfigError(
                "llama-cloud belum terpasang; jalankan pip install 'llama-cloud>=2.8'"
            ) from exc

        self._httpx = httpx
        self._client = LlamaCloud(
            timeout=httpx.Timeout(timeout_seconds, connect=20.0),
            max_retries=max_retries,
        )
        self._registry_dir = registry_dir
        self._secret = os.environ.get("LLAMA_CLOUD_API_KEY")

    # ------------------------------------------------------------------
    # Unggah
    # ------------------------------------------------------------------
    def _registry_path(self) -> Optional[Path]:
        if self._registry_dir is None:
            return None
        return self._registry_dir / UPLOAD_REGISTRY_NAME

    def _read_registry(self) -> dict[str, Any]:
        path = self._registry_path()
        if path is None or not path.exists():
            return {}
        try:
            data = read_json(path)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_registry(self, data: dict[str, Any]) -> None:
        path = self._registry_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, data)

    def upload(
        self,
        pdf_path: Path,
        source_sha256: str,
        reuse: bool = True,
    ) -> dict[str, Any]:
        """Mengunggah PDF bila belum ada di registry.

        ``external_file_id`` memakai hash dokumen supaya unggahan ganda bisa
        dikenali di sisi server.
        """

        registry = self._read_registry()
        entry = registry.get(source_sha256)
        if reuse and isinstance(entry, dict) and entry.get("file_id"):
            LOGGER.info(
                "Menggunakan file_id tersimpan untuk %s (tanpa unggah ulang)",
                pdf_path.name,
            )
            return {**entry, "reused": True}

        LOGGER.info("Mengunggah %s ke LlamaCloud (sekali untuk hash ini)", pdf_path.name)
        external_file_id = f"{pdf_path.stem}-{source_sha256[:16]}"
        try:
            handle = self._client.files.create(
                file=pdf_path,
                purpose="parse",
                external_file_id=external_file_id,
            )
            record = {
                "file_id": handle.id,
                "file_name": getattr(handle, "name", pdf_path.name),
                "external_file_id": getattr(
                    handle, "external_file_id", external_file_id
                ),
                "uploaded_at": getattr(handle, "last_modified_at", None),
            }
        except Exception as exc:
            # external_file_id sudah dipakai (mis. unggahan sebelumnya gagal
            # sebelum registry tersimpan). Ambil file yang sudah ada.
            existing_file = self.find_by_external_id(external_file_id)
            if existing_file is None:
                raise
            LOGGER.warning(
                "Unggah ditolak (%s); memakai file yang sudah ada",
                type(exc).__name__,
            )
            record = {
                "file_id": existing_file["id"],
                "file_name": existing_file.get("name"),
                "external_file_id": external_file_id,
                "uploaded_at": existing_file.get("last_modified_at"),
            }
        registry[source_sha256] = record
        self._write_registry(registry)
        LOGGER.info("Upload selesai; file_id disimpan")
        return {**record, "reused": False}

    def find_by_external_id(self, external_file_id: str) -> Optional[dict[str, Any]]:
        """Mencari file yang sudah diunggah berdasarkan ``external_file_id``."""

        try:
            page = self._client.files.list(
                external_file_id=external_file_id, page_size=10
            )
            for item in page:
                payload = item.model_dump(mode="json")
                if payload.get("external_file_id") == external_file_id:
                    return payload
        except Exception as exc:  # pragma: no cover - diagnostik
            LOGGER.debug("Pencarian file gagal: %s", type(exc).__name__)
        return None

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def parse(
        self,
        file_id: str,
        options: dict[str, Any],
        poll_timeout_seconds: float = 7200.0,
        verbose: bool = False,
    ) -> Any:
        """Menjalankan ``parsing.parse`` dan menunggu hingga selesai."""

        LOGGER.info(
            "Memulai parse: tier=%s version=%s pages=%s",
            options.get("tier"),
            options.get("version"),
            (options.get("page_ranges") or {}).get("target_pages", "semua"),
        )
        kwargs: dict[str, Any] = {}
        if options.get("page_ranges"):
            kwargs["page_ranges"] = options["page_ranges"]
        return self._client.parsing.parse(
            file_id=file_id,
            tier=options["tier"],
            version=options["version"],
            expand=options.get("expand"),
            output_options=options.get("output_options"),
            processing_options=options.get("processing_options"),
            processing_control=options.get("processing_control"),
            disable_cache=options.get("disable_cache", False),
            polling_interval=2.0,
            max_interval=10.0,
            timeout=poll_timeout_seconds,
            backoff="linear",
            verbose=verbose,
            **kwargs,
        )

    def get(
        self,
        job_id: str,
        expand: Optional[list[str]] = None,
        image_filenames: Optional[str] = None,
    ) -> Any:
        """Mengambil hasil job yang sudah ada tanpa membuat job baru."""

        kwargs: dict[str, Any] = {}
        if image_filenames:
            kwargs["image_filenames"] = image_filenames
        return self._client.parsing.get(job_id=job_id, expand=expand, **kwargs)

    def list_versions(self) -> dict[str, Any]:
        """Daftar versi parser per tier; tidak memakai kredit."""

        result = self._client.parsing.list_versions()
        data = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        if not isinstance(data, dict):
            raise ValueError("Format daftar versi tidak dikenali")
        return data

    def download(self, url: str) -> bytes:
        response = self._httpx.get(url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        return response.content

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # pragma: no cover - best effort
            pass


def describe_exception(exc: BaseException) -> str:
    """Pesan error aman untuk log dan laporan."""

    return _safe_message(exc)
