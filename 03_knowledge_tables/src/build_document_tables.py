"""Pembangun knowledge table untuk dokumen baru (DOC003, DOC004, DOC005).

Berbeda dari ``build_knowledge_tables.py`` yang menurunkan baris DOC002 secara
otomatis dari heading, builder ini membaca spesifikasi kurasi
``config/{DOC}_tables.json``. Setiap baris wajib menunjuk blok sumber dan
kutipan verbatim; builder memverifikasi kutipan itu benar-benar ada di blok dan
chunk yang dirujuk sebelum menulis CSV.

Input read-only:
- ``02_extraction/extracted_text/{DOC}.blocks.jsonl``
- ``02_extraction/extracted_text/{DOC}.chunks.jsonl``

Output:
- ``curated/{DOC}/*.csv``
- ``reports/{DOC}.tables.validation.json``

Jalankan::

    python 03_knowledge_tables/build_document_tables.py --doc DOC005

Keluar dengan kode 2 bila ada pelanggaran (verbatim, foreign key, ID, offset).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

TABLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TABLE_DIR.parent
EXTRACTION_DIR = PROJECT_ROOT / "02_extraction" / "extracted_text"
CONFIG_DIR = TABLE_DIR / "config"
CURATED_DIR = TABLE_DIR / "curated"
REPORTS_DIR = TABLE_DIR / "reports"

WS_RE = re.compile(r"\s+")

COLUMNS: dict[str, dict[str, list[str]]] = {
    "DOC003": {
        "plants": [
            "plant_id",
            "document_id",
            "plant_name_id",
            "plant_name_en",
            "scientific_name",
            "scientific_name_page",
            "chapter_number",
            "chapter_title",
            "page_start",
            "page_end",
            "evidence_chunk_id",
            "notes",
        ],
        "amorphophallus_spp_diseases": [
            "disease_id",
            "document_id",
            "plant_id",
            "host_verbatim",
            "disease_name_verbatim",
            "disease_name_en_verbatim",
            "pathogen_verbatim",
            "pathogen_id",
            "reference_verbatim",
            "page_start",
            "page_end",
            "source_block_id",
            "chunk_id",
            "source_type",
            "review_status",
            "notes",
        ],
        "pathogens": [
            "pathogen_id",
            "document_id",
            "scientific_name",
            "verbatim_text",
            "taxon_group",
            "taxon_evidence_chunk_id",
            "taxon_evidence_quote",
            "page",
            "chunk_id",
            "note",
            "review_status",
        ],
        "disease_pathogen": [
            "disease_id",
            "pathogen_id",
            "document_id",
            "evidence_chunk_id",
            "relation_note",
            "review_status",
        ],
        "symptoms": [
            "symptom_id",
            "document_id",
            "disease_id",
            "plant_id",
            "verbatim_text",
            "chunk_id",
            "page_start",
            "page_end",
            "char_start",
            "char_end",
            "review_status",
        ],
        "controls": [
            "control_id",
            "document_id",
            "disease_id",
            "plant_id",
            "verbatim_text",
            "chunk_id",
            "page_start",
            "page_end",
            "char_start",
            "char_end",
            "control_category",
            "scope",
            "review_status",
        ],
    },
    "DOC005": {
        "plants": [
            "plant_id",
            "document_id",
            "plant_name_id",
            "plant_name_en",
            "scientific_name",
            "scientific_name_page",
            "chapter_number",
            "chapter_title",
            "page_start",
            "page_end",
            "evidence_chunk_id",
            "notes",
        ],
        "diseases": [
            "disease_id",
            "document_id",
            "plant_id",
            "host_verbatim",
            "disease_name_verbatim",
            "disease_name_en_verbatim",
            "pathogen_verbatim",
            "pathogen_id",
            "reference_verbatim",
            "page_start",
            "page_end",
            "source_block_id",
            "chunk_id",
            "source_type",
            "review_status",
            "notes",
        ],
        "pathogens": [
            "pathogen_id",
            "document_id",
            "scientific_name",
            "verbatim_text",
            "taxon_group",
            "taxon_evidence_chunk_id",
            "taxon_evidence_quote",
            "page",
            "chunk_id",
            "note",
            "review_status",
        ],
        "disease_pathogen": [
            "disease_id",
            "pathogen_id",
            "document_id",
            "evidence_chunk_id",
            "relation_note",
            "review_status",
        ],
        "symptoms": [
            "symptom_id",
            "document_id",
            "disease_id",
            "plant_id",
            "verbatim_text",
            "chunk_id",
            "page_start",
            "page_end",
            "char_start",
            "char_end",
            "review_status",
        ],
        "controls": [
            "control_id",
            "document_id",
            "disease_id",
            "plant_id",
            "verbatim_text",
            "chunk_id",
            "page_start",
            "page_end",
            "char_start",
            "char_end",
            "control_category",
            "scope",
            "review_status",
        ],
    },
    "DOC004": {
        "nutrients": [
            "record_id",
            "document_id",
            "category",
            "subject",
            "attribute",
            "value",
            "unit",
            "verbatim_text",
            "page",
            "chunk_id",
            "source_block_id",
            "review_status",
            "notes",
        ],
        "fertilizers": [
            "record_id",
            "document_id",
            "category",
            "subject",
            "attribute",
            "value",
            "unit",
            "verbatim_text",
            "page",
            "chunk_id",
            "source_block_id",
            "review_status",
            "notes",
        ],
        "practices": [
            "record_id",
            "document_id",
            "category",
            "subject",
            "attribute",
            "value",
            "unit",
            "verbatim_text",
            "page",
            "chunk_id",
            "source_block_id",
            "review_status",
            "notes",
        ],
        "compost": [
            "record_id",
            "document_id",
            "category",
            "subject",
            "attribute",
            "value",
            "unit",
            "verbatim_text",
            "page",
            "chunk_id",
            "source_block_id",
            "review_status",
            "notes",
        ],
    },
}

ID_PATTERNS = {
    "plant_id": re.compile(r"^PLANT_\d{3}$"),
    "disease_id": re.compile(r"^DIS_\d{3}$"),
    "pathogen_id": re.compile(r"^PAT_\d{3}$"),
    "symptom_id": re.compile(r"^SYM_\d{3}$"),
    "control_id": re.compile(r"^CTL_\d{3}$"),
    "record_id": re.compile(r"^(?:NUT|FER|PRC|CMP)_\d{3}$"),
}

PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "plants": ("plant_id",),
    "amorphophallus_spp_diseases": ("disease_id",),
    "diseases": ("disease_id",),
    "pathogens": ("pathogen_id",),
    "disease_pathogen": ("disease_id", "pathogen_id"),
    "symptoms": ("symptom_id",),
    "controls": ("control_id",),
    "nutrients": ("record_id",),
    "fertilizers": ("record_id",),
    "practices": ("record_id",),
    "compost": ("record_id",),
}

FOREIGN_KEYS = {
    "DOC003": [
        ("amorphophallus_spp_diseases", "plant_id", "plants", "plant_id"),
        ("amorphophallus_spp_diseases", "pathogen_id", "pathogens", "pathogen_id"),
        (
            "disease_pathogen",
            "disease_id",
            "amorphophallus_spp_diseases",
            "disease_id",
        ),
        ("disease_pathogen", "pathogen_id", "pathogens", "pathogen_id"),
        ("symptoms", "disease_id", "amorphophallus_spp_diseases", "disease_id"),
        ("symptoms", "plant_id", "plants", "plant_id"),
        ("controls", "disease_id", "amorphophallus_spp_diseases", "disease_id"),
        ("controls", "plant_id", "plants", "plant_id"),
    ],
    "DOC005": [
        ("diseases", "plant_id", "plants", "plant_id"),
        ("diseases", "pathogen_id", "pathogens", "pathogen_id"),
        ("disease_pathogen", "disease_id", "diseases", "disease_id"),
        ("disease_pathogen", "pathogen_id", "pathogens", "pathogen_id"),
        ("symptoms", "disease_id", "diseases", "disease_id"),
        ("symptoms", "plant_id", "plants", "plant_id"),
        ("controls", "disease_id", "diseases", "disease_id"),
        ("controls", "plant_id", "plants", "plant_id"),
    ],
    "DOC004": [],
}


def norm(text: Any) -> str:
    """Normalisasi spasi saja; kata dan tanda baca tidak diubah."""

    return WS_RE.sub(" ", str(text or "")).strip()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def block_evidence(block: dict[str, Any]) -> str:
    """Teks blok plus sel tabel sebagai bahan verifikasi kutipan."""

    parts = [str(block.get("text") or block.get("raw_text") or "")]
    table = block.get("table") or {}
    for row in table.get("rows") or []:
        if not isinstance(row, list):
            continue
        cells = [
            str(cell).replace("<br/>", " ").replace("<br>", " ") for cell in row
        ]
        parts.append(" | ".join(cells))
        parts.extend(cells)
    return norm("\n".join(parts))


def chunk_evidence(chunk: dict[str, Any]) -> str:
    parts = [str(chunk.get("plain_text") or "")]
    for table in chunk.get("tables") or []:
        for row in (table or {}).get("rows") or []:
            if not isinstance(row, list):
                continue
            cells = [
                str(cell).replace("<br/>", " ").replace("<br>", " ") for cell in row
            ]
            parts.append(" | ".join(cells))
            parts.extend(cells)
    return norm("\n".join(parts))


def chunk_plain(chunk: dict[str, Any]) -> str:
    return norm(chunk.get("plain_text") or "")


class Builder:
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        self.blocks = read_jsonl(EXTRACTION_DIR / f"{document_id}.blocks.jsonl")
        self.chunks = read_jsonl(EXTRACTION_DIR / f"{document_id}.chunks.jsonl")
        self.block_by_id = {str(b.get("block_id")): b for b in self.blocks}
        self.chunk_by_id = {str(c.get("chunk_id")): c for c in self.chunks}
        self.chunks_by_block: dict[str, list[str]] = {}
        for chunk in self.chunks:
            for block_id in chunk.get("source_block_ids") or []:
                self.chunks_by_block.setdefault(str(block_id), []).append(
                    str(chunk.get("chunk_id"))
                )
        self.errors: list[str] = []
        self.warnings: list[str] = []

    # ------------------------------------------------------------------
    # Validasi
    # ------------------------------------------------------------------
    def error(self, table: str, row_id: str, message: str) -> None:
        self.errors.append(f"{table}:{row_id}:{message}")

    def warn(self, table: str, row_id: str, message: str) -> None:
        self.warnings.append(f"{table}:{row_id}:{message}")

    def resolve_chunk(
        self, table: str, row_id: str, row: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        block_id = str(row.get("block_id") or row.get("source_block_id") or "")
        if not block_id:
            self.error(table, row_id, "missing_block_id")
            return None
        block = self.block_by_id.get(block_id)
        if block is None:
            self.error(table, row_id, f"block_not_found:{block_id}")
            return None

        candidates = self.chunks_by_block.get(block_id) or []
        declared = str(
            row.get("chunk_id") or row.get("evidence_chunk_id") or ""
        )
        if declared:
            chunk = self.chunk_by_id.get(declared)
            if chunk is None:
                self.error(table, row_id, f"chunk_not_found:{declared}")
                return None
            if candidates and declared not in candidates:
                self.error(
                    table, row_id, f"chunk_does_not_own_block:{declared}"
                )
            return chunk
        if not candidates:
            self.error(table, row_id, f"block_without_chunk:{block_id}")
            return None
        if len(candidates) > 1:
            self.warn(
                table,
                row_id,
                f"multiple_chunks_for_block:{block_id}:{candidates[0]}",
            )
        return self.chunk_by_id[candidates[0]]

    def verify_quote(
        self,
        table: str,
        row_id: str,
        quote: str,
        block: dict[str, Any],
        chunk: dict[str, Any],
        *,
        require_block: bool = True,
    ) -> None:
        normalized = norm(quote)
        if not normalized:
            self.error(table, row_id, "empty_verbatim_text")
            return
        if normalized.casefold() in {"null", "none", "n/a"}:
            self.error(table, row_id, "placeholder_verbatim_text")
            return
        if require_block and normalized not in block_evidence(block):
            self.error(table, row_id, f"quote_not_in_block:{block.get('block_id')}")
        if normalized not in chunk_evidence(chunk):
            self.error(
                table, row_id, f"quote_not_in_chunk:{chunk.get('chunk_id')}"
            )

    def compute_offsets(
        self, chunk: dict[str, Any], quote: str
    ) -> tuple[Optional[int], Optional[int]]:
        text = chunk_plain(chunk)
        target = norm(quote)
        if not text or not target:
            return None, None
        index = text.find(target)
        if index < 0:
            return None, None
        return index, index + len(target)

    # ------------------------------------------------------------------
    # Penyusunan baris
    # ------------------------------------------------------------------
    def build_plant_disease_tables(
        self, spec: dict[str, Any], disease_table: str
    ) -> dict[str, list[dict[str, Any]]]:
        tables = spec.get("tables") or {}
        out: dict[str, list[dict[str, Any]]] = {}

        plants: list[dict[str, Any]] = []
        for row in tables.get("plants") or []:
            row_id = str(row.get("plant_id") or "")
            record = dict(row)
            record.setdefault("document_id", self.document_id)
            block_id = str(row.get("block_id") or "")
            block = self.block_by_id.get(block_id)
            chunk = self.resolve_chunk("plants", row_id, row)
            if block is None or chunk is None:
                continue
            quote = str(row.get("quote") or "")
            self.verify_quote("plants", row_id, quote, block, chunk)
            scientific = str(row.get("scientific_name") or "")
            if scientific and norm(scientific) not in norm(row.get("quote")):
                self.error("plants", row_id, "scientific_name_not_in_quote")
            name = str(row.get("plant_name_id") or "")
            if name and name.casefold() not in norm(row.get("quote")).casefold():
                self.warn("plants", row_id, "plant_name_not_in_quote")
            page = int(block.get("page_number") or 0)
            scientific_page = row.get("scientific_name_page")
            if scientific and scientific_page and int(scientific_page) != page:
                self.error(
                    "plants",
                    row_id,
                    f"scientific_name_page_mismatch:{scientific_page}!={page}",
                )
            if str(chunk.get("chapter") or "") != str(
                row.get("chapter_title") or ""
            ):
                self.error("plants", row_id, "chapter_title_mismatch")
            record["page_start"] = int(row.get("page_start") or 0)
            record["page_end"] = int(row.get("page_end") or 0)
            if not (
                record["page_start"]
                <= page
                <= record["page_end"]
            ):
                self.error("plants", row_id, f"block_page_outside_range:{page}")
            record["evidence_chunk_id"] = str(chunk.get("chunk_id"))
            plants.append(record)
        out["plants"] = plants

        diseases: list[dict[str, Any]] = []
        for row in tables.get(disease_table) or []:
            row_id = str(row.get("disease_id") or "")
            record = dict(row)
            record.setdefault("document_id", self.document_id)
            block = self.block_by_id.get(str(row.get("block_id") or ""))
            chunk = self.resolve_chunk(disease_table, row_id, row)
            if block is None or chunk is None:
                continue
            self.verify_quote(
                disease_table,
                row_id,
                str(row.get("quote") or ""),
                block,
                chunk,
            )
            quote_norm = norm(row.get("quote"))
            evidence = block_evidence(block)
            for field in ("disease_name_verbatim", "disease_name_en_verbatim"):
                value = norm(row.get(field))
                if value and value.casefold() not in quote_norm.casefold():
                    self.error(
                        disease_table,
                        row_id,
                        f"{field}_not_in_quote",
                    )
            for field in ("pathogen_verbatim", "reference_verbatim"):
                value = norm(row.get(field))
                if value and value.casefold() not in evidence.casefold():
                    self.error(
                        disease_table,
                        row_id,
                        f"{field}_not_in_block_evidence",
                    )
            record["page_start"] = int(chunk.get("page_start") or 0)
            record["page_end"] = int(chunk.get("page_end") or 0)
            record["source_block_id"] = str(block.get("block_id"))
            record["chunk_id"] = str(chunk.get("chunk_id"))
            diseases.append(record)
        out[disease_table] = diseases

        pathogens: list[dict[str, Any]] = []
        for row in tables.get("pathogens") or []:
            row_id = str(row.get("pathogen_id") or "")
            record = dict(row)
            record.setdefault("document_id", self.document_id)
            block = self.block_by_id.get(str(row.get("block_id") or ""))
            chunk = self.resolve_chunk("pathogens", row_id, row)
            if block is None or chunk is None:
                continue
            quote = str(row.get("quote") or "")
            self.verify_quote("pathogens", row_id, quote, block, chunk)
            scientific = str(row.get("scientific_name") or "")
            if scientific and norm(scientific).casefold() not in norm(quote).casefold():
                self.error("pathogens", row_id, "scientific_name_not_in_quote")
            verbatim = str(row.get("verbatim_text") or "")
            if verbatim and norm(verbatim).casefold() not in norm(quote).casefold():
                self.error("pathogens", row_id, "verbatim_text_not_in_quote")
            page = int(block.get("page_number") or 0)
            if row.get("page") and int(row["page"]) != page:
                self.error(
                    "pathogens",
                    row_id,
                    f"page_mismatch:{row['page']}!={page}",
                )
            record["page"] = page
            record["chunk_id"] = str(chunk.get("chunk_id"))
            taxon_chunk_id = str(row.get("taxon_evidence_chunk_id") or "")
            taxon_quote = str(row.get("taxon_evidence_quote") or "")
            if taxon_chunk_id or taxon_quote:
                taxon_chunk = self.chunk_by_id.get(taxon_chunk_id)
                if taxon_chunk is None:
                    self.error(
                        "pathogens",
                        row_id,
                        f"taxon_chunk_not_found:{taxon_chunk_id}",
                    )
                elif norm(taxon_quote) not in chunk_evidence(taxon_chunk):
                    self.error(
                        "pathogens",
                        row_id,
                        f"taxon_quote_not_in_chunk:{taxon_chunk_id}",
                    )
                elif str(row.get("taxon_group") or "").casefold() not in norm(
                    taxon_quote
                ).casefold():
                    self.error(
                        "pathogens", row_id, "taxon_group_not_in_taxon_quote"
                    )
            record.setdefault("taxon_evidence_chunk_id", "")
            record.setdefault("taxon_evidence_quote", "")
            pathogens.append(record)
        out["pathogens"] = pathogens

        links: list[dict[str, Any]] = []
        for row in tables.get("disease_pathogen") or []:
            row_id = f"{row.get('disease_id')}+{row.get('pathogen_id')}"
            record = dict(row)
            record.setdefault("document_id", self.document_id)
            chunk = self.resolve_chunk("disease_pathogen", row_id, row)
            if chunk is None:
                continue
            record["evidence_chunk_id"] = str(chunk.get("chunk_id"))
            links.append(record)
        out["disease_pathogen"] = links

        for name in ("symptoms", "controls"):
            rows: list[dict[str, Any]] = []
            for row in tables.get(name) or []:
                row_id = str(row.get("symptom_id") or row.get("control_id") or "")
                record = dict(row)
                record.setdefault("document_id", self.document_id)
                block = self.block_by_id.get(str(row.get("block_id") or ""))
                chunk = self.resolve_chunk(name, row_id, row)
                if block is None or chunk is None:
                    continue
                quote = str(row.get("quote") or "")
                self.verify_quote(name, row_id, quote, block, chunk)
                record["verbatim_text"] = quote
                record["chunk_id"] = str(chunk.get("chunk_id"))
                record["page_start"] = int(chunk.get("page_start") or 0)
                record["page_end"] = int(chunk.get("page_end") or 0)
                start, end = self.compute_offsets(chunk, quote)
                if start is None:
                    self.error(name, row_id, "quote_not_found_in_plain_text")
                    record["char_start"] = ""
                    record["char_end"] = ""
                else:
                    record["char_start"] = start
                    record["char_end"] = end
                rows.append(record)
            out[name] = rows

        return out

    def build_doc004(self, spec: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        tables = spec.get("tables") or {}
        out: dict[str, list[dict[str, Any]]] = {}
        for name in ("nutrients", "fertilizers", "practices", "compost"):
            rows: list[dict[str, Any]] = []
            for row in tables.get(name) or []:
                row_id = str(row.get("record_id") or "")
                record = dict(row)
                record.setdefault("document_id", self.document_id)
                block = self.block_by_id.get(str(row.get("block_id") or ""))
                chunk = self.resolve_chunk(name, row_id, row)
                if block is None or chunk is None:
                    continue
                quote = str(row.get("quote") or row.get("verbatim_text") or "")
                self.verify_quote(name, row_id, quote, block, chunk)
                value = norm(row.get("value"))
                unit = norm(row.get("unit"))
                if value and value not in norm(quote):
                    self.error(name, row_id, "value_not_in_verbatim_text")
                if unit and unit not in norm(quote):
                    self.error(name, row_id, "unit_not_in_verbatim_text")
                record["page"] = int(block.get("page_number") or 0)
                record["chunk_id"] = str(chunk.get("chunk_id"))
                record["source_block_id"] = str(block.get("block_id"))
                rows.append(record)
            out[name] = rows
        return out

    # ------------------------------------------------------------------
    # Pemeriksaan lintas tabel
    # ------------------------------------------------------------------
    def check_ids(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        for table_name, rows in tables.items():
            for row in rows:
                for field, pattern in ID_PATTERNS.items():
                    value = str(row.get(field) or "")
                    if value and not pattern.match(value):
                        self.error(table_name, value, "id_pattern_mismatch")
            key_fields = PRIMARY_KEYS.get(table_name, ())
            seen: set[tuple[str, ...]] = set()
            for row in rows:
                key = tuple(str(row.get(field) or "") for field in key_fields)
                if not any(key):
                    continue
                if key in seen:
                    self.error(table_name, "+".join(key), "duplicate_id")
                seen.add(key)

    def check_foreign_keys(
        self, tables: dict[str, list[dict[str, Any]]]
    ) -> None:
        for table_name, field, ref_table, ref_field in FOREIGN_KEYS.get(
            self.document_id, []
        ):
            if ref_table not in tables:
                self.error(table_name, "*", f"missing_reference_table:{ref_table}")
                continue
            allowed = {
                str(row.get(ref_field))
                for row in tables.get(ref_table, [])
                if row.get(ref_field)
            }
            for row in tables.get(table_name, []):
                value = str(row.get(field) or "")
                if value and value not in allowed:
                    row_id = str(row.get("disease_id") or row.get("symptom_id") or "")
                    self.error(table_name, row_id, f"foreign_key_missing:{field}={value}")

    def check_review_status(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        valid = {"auto_ok", "needs_review", "verified"}
        for table_name, rows in tables.items():
            for row in rows:
                status = str(row.get("review_status") or "auto_ok")
                if status not in valid:
                    row_id = next(
                        (
                            str(row[field])
                            for field in ID_PATTERNS
                            if row.get(field)
                        ),
                        "*",
                    )
                    self.error(table_name, row_id, f"invalid_review_status:{status}")

    def run(self) -> int:
        config_path = CONFIG_DIR / f"{self.document_id}_tables.json"
        spec = json.loads(config_path.read_text(encoding="utf-8"))
        if str(spec.get("document_id")) != self.document_id:
            self.errors.append(
                f"config:document_id_mismatch:{spec.get('document_id')}"
            )
        if self.document_id == "DOC003":
            tables = self.build_plant_disease_tables(
                spec, "amorphophallus_spp_diseases"
            )
        elif self.document_id == "DOC005":
            tables = self.build_plant_disease_tables(spec, "diseases")
        else:
            tables = self.build_doc004(spec)

        self.check_ids(tables)
        self.check_foreign_keys(tables)
        self.check_review_status(tables)

        columns_map = COLUMNS[self.document_id]
        table_report: dict[str, Any] = {}
        for name, rows in tables.items():
            columns = columns_map[name]
            for row in rows:
                for column in columns:
                    row.setdefault(column, "")
            path = CURATED_DIR / self.document_id / f"{name}.csv"
            write_csv(path, rows, columns)
            table_report[name] = {
                "file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "rows": len(rows),
                "columns": columns,
            }

        report = {
            "schema_version": "1.0.0",
            "document_id": self.document_id,
            "generated_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "sources": {
                "blocks": f"02_extraction/extracted_text/{self.document_id}.blocks.jsonl",
                "chunks": f"02_extraction/extracted_text/{self.document_id}.chunks.jsonl",
                "config": f"03_knowledge_tables/config/{self.document_id}_tables.json",
            },
            "tables": table_report,
            "checks": {
                "verbatim_in_block": "pass"
                if not any("quote_not_in_block" in e for e in self.errors)
                else "fail",
                "verbatim_in_chunk": "pass"
                if not any("quote_not_in_chunk" in e for e in self.errors)
                else "fail",
                "ids_unique": "pass"
                if not any("duplicate_id" in e for e in self.errors)
                else "fail",
                "foreign_keys": "pass"
                if not any("foreign_key" in e for e in self.errors)
                else "fail",
                "offsets": "pass"
                if not any("quote_not_found_in_plain_text" in e for e in self.errors)
                else "fail",
            },
            "errors": self.errors,
            "warnings": self.warnings,
            "status": "pass" if not self.errors else "fail",
        }
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / f"{self.document_id}.tables.validation.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print(f"=== {self.document_id} ===")
        for name, info in table_report.items():
            print(f"  {name}: {info['rows']} baris -> {info['file']}")
        print(
            f"  status={report['status']} errors={len(self.errors)} "
            f"warnings={len(self.warnings)}"
        )
        for error in self.errors:
            print(f"  ERROR {error}")
        for warning in self.warnings:
            print(f"  WARN  {warning}")
        return 0 if not self.errors else 2


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--doc",
        action="append",
        choices=sorted(COLUMNS),
        help="Dokumen yang dibangun (boleh diulang). Default: semua dokumen.",
    )
    args = parser.parse_args(argv)
    documents = args.doc or sorted(COLUMNS)
    exit_code = 0
    for document_id in documents:
        exit_code = max(exit_code, Builder(document_id).run())
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
