"""Utilitas reasoner OWL 2 untuk test ontologi.

Pellet 2.3.1 dibundel oleh owlready2. Pada owlready2 0.51, tiga kelas
``LangRDFXML`` di ``jena-arq-fixed2.10.0.jar`` dikompilasi untuk Java 25
sehingga gagal pada Java 21. Helper ini menaruh Jena ARQ 2.10.0 asli di depan
classpath Pellet agar kelas Java 21 yang kompatibel dipakai lebih dulu.
"""

from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

import owlready2.reasoning as _reasoning
from owlready2 import (
    OwlReadyInconsistentOntologyError,
    OwlReadyJavaError,
    sync_reasoner,
    sync_reasoner_pellet,
)

JENA_ARQ_FILENAME = "jena-arq-2.10.0.jar"
JENA_ARQ_URL = (
    "https://repo1.maven.org/maven2/org/apache/jena/jena-arq/2.10.0/"
    "jena-arq-2.10.0.jar"
)
JENA_ARQ_SHA256 = "f4c5ddff30d3e53f6cecb473a6adc60ceeba21ea7d7e363c696c2336480bc2aa"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_dir() -> Path:
    override = os.environ.get("KBR_PELLET_CACHE")
    if override:
        return Path(override)
    base = (
        os.environ.get("LOCALAPPDATA")
        or os.environ.get("XDG_CACHE_HOME")
        or str(Path.home() / ".cache")
    )
    return Path(base) / "kbr-pellet"


def _ensure_jena_arq_jar() -> Path:
    override = os.environ.get("KBR_PELLET_JENA_ARQ_JAR")
    if override:
        jar = Path(override)
        if not jar.is_file():
            raise FileNotFoundError(f"Jena ARQ jar tidak ditemukan: {jar}")
        if _sha256(jar) != JENA_ARQ_SHA256:
            raise RuntimeError(f"Checksum Jena ARQ tidak cocok: {jar}")
        return jar

    jar = _cache_dir() / JENA_ARQ_FILENAME
    if jar.is_file() and _sha256(jar) == JENA_ARQ_SHA256:
        return jar

    jar.parent.mkdir(parents=True, exist_ok=True)
    temporary = jar.with_suffix(".jar.tmp")
    try:
        urllib.request.urlretrieve(JENA_ARQ_URL, temporary)
        if _sha256(temporary) != JENA_ARQ_SHA256:
            raise RuntimeError(f"Checksum unduhan Jena ARQ tidak cocok: {temporary}")
        temporary.replace(jar)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return jar


def ensure_pellet_classpath() -> None:
    """Pastikan Jena ARQ yang kompatibel berada di depan classpath Pellet."""
    jar = str(_ensure_jena_arq_jar())
    classpath = _reasoning._PELLET_CLASSPATH
    if classpath.split(os.pathsep)[0] == jar:
        return
    _reasoning._PELLET_CLASSPATH = jar + os.pathsep + classpath


def sync_reasoner_for_tests(onto, *, infer_property_values: bool = False) -> str:
    """Jalankan Pellet; HermiT hanya dipakai bila diminta eksplisit."""
    choice = os.environ.get("KBR_REASONER", "pellet").strip().lower()
    if choice == "hermit":
        sync_reasoner(onto, debug=0, infer_property_values=infer_property_values)
        return "hermit"
    if choice != "pellet":
        raise ValueError(
            f"KBR_REASONER tidak dikenal: {choice!r}; gunakan 'pellet' atau 'hermit'"
        )

    ensure_pellet_classpath()
    try:
        sync_reasoner_pellet(
            onto, debug=0, infer_property_values=infer_property_values
        )
        return "pellet"
    except OwlReadyInconsistentOntologyError:
        raise
    except (OwlReadyJavaError, OSError) as exc:
        fallback = os.environ.get("KBR_REASONER_FALLBACK", "").strip().lower()
        if fallback in {"1", "true", "yes", "hermit"}:
            sync_reasoner(
                onto, debug=0, infer_property_values=infer_property_values
            )
            return "hermit"
        raise RuntimeError(
            "Pellet gagal dijalankan. Gunakan KBR_REASONER=hermit atau "
            "KBR_REASONER_FALLBACK=hermit untuk fallback HermiT."
        ) from exc
