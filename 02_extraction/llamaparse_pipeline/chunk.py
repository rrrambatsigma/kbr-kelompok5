"""Structure-aware chunking untuk penyusunan knowledge table.

Chunk dibentuk dari batas konteks (bab/penyakit/kategori), bukan dari
fixed-size window. Setiap chunk menyimpan id blok sumber dan rentang halaman.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from pdf_pipeline.output import read_jsonl

from . import config, store


LOGGER = logging.getLogger("kbr_llamaparse")

MAX_CHUNK_CHARS = 2200
MIN_CHUNK_CHARS = 40
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_long_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    sentences = SENTENCE_SPLIT_RE.split(text)
    parts: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            parts.append(current)
        if len(sentence) <= max_chars:
            current = sentence
        else:
            # Fallback: potong pada spasi terdekat.
            start = 0
            while start < len(sentence):
                end = min(start + max_chars, len(sentence))
                if end < len(sentence):
                    space = sentence.rfind(" ", start, end)
                    if space > start:
                        end = space
                parts.append(sentence[start:end].strip())
                start = end
            current = ""
    if current:
        parts.append(current)
    return [part for part in parts if part]


def _source_reference(
    page_start: int,
    page_end: int,
    printed_start: Optional[int],
    printed_end: Optional[int],
) -> str:
    pages = (
        f"hlm. {page_start}"
        if page_start == page_end
        else f"hlm. {page_start}-{page_end}"
    )
    reference = f"{config.DOCUMENT_ID} PDF {pages}"
    if printed_start is not None:
        printed = (
            str(printed_start)
            if printed_end in (None, printed_start)
            else f"{printed_start}-{printed_end}"
        )
        reference += f" (cetak {printed})"
    return reference


class ChunkBuilder:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.chunks: list[dict[str, Any]] = []
        self._current: Optional[dict[str, Any]] = None
        self._keys: dict[str, Any] = {}
        self._page_counter: dict[int, int] = {}

    # ------------------------------------------------------------------
    def _new_chunk(
        self, block: dict[str, Any], chunk_type: str, content_type: str
    ) -> dict[str, Any]:
        page = int(block["page_number"])
        index = self._page_counter.get(page, 0) + 1
        self._page_counter[page] = index
        self._keys = {
            "chunk_type": chunk_type,
            "chapter": block.get("chapter"),
            "section": block.get("section"),
            "subsection": block.get("subsection"),
        }
        return {
            "chunk_id": f"{config.DOCUMENT_ID}_C{page:03d}_{index:02d}",
            "document_id": config.DOCUMENT_ID,
            "segment_id": "S1",
            "run_id": self.run_id,
            "chunk_type": chunk_type,
            "content_type": content_type,
            "chapter": block.get("chapter"),
            "section": block.get("section"),
            "section_source": block.get("section_source"),
            "subsection": block.get("subsection"),
            "plant_name": block.get("plant_name"),
            "plant_name_source": block.get("plant_name_source"),
            "disease_name": block.get("disease_name"),
            "disease_name_source": block.get("disease_name_source"),
            "page_start": page,
            "page_end": page,
            "printed_page_start": block.get("printed_page_number"),
            "printed_page_end": block.get("printed_page_number"),
            "text_markdown": "",
            "plain_text": "",
            "char_count": 0,
            "source_block_ids": [],
            "tables": [],
            "images": [],
            "parser_confidence_min": block.get("parser_confidence"),
            "validation_status": "auto_validated",
            "review_reasons": [],
            "text_source": block.get("text_source") or "llamaparse",
        }

    def _append_block(self, block: dict[str, Any], chunk_type: str) -> None:
        content_type = str(block.get("content_type"))
        if self._current is None:
            self._current = self._new_chunk(block, chunk_type, content_type)

        chunk = self._current
        chunk["page_end"] = int(block["page_number"])
        if block.get("printed_page_number") is not None:
            chunk["printed_page_end"] = block.get("printed_page_number")
            if chunk["printed_page_start"] is None:
                chunk["printed_page_start"] = block.get("printed_page_number")
        chunk["source_block_ids"].append(block.get("block_id"))

        if content_type == "chapter_heading" and block.get("chapter"):
            chunk["chapter"] = block.get("chapter")
        source = str(block.get("text_source") or "llamaparse")
        if chunk.get("text_source") != source and chunk.get("source_block_ids"):
            chunk["text_source"] = "mixed"
        if block.get("plant_name") and not chunk.get("plant_name"):
            chunk["plant_name"] = block.get("plant_name")
            chunk["plant_name_source"] = block.get("plant_name_source")
        if block.get("disease_name") and not chunk.get("disease_name"):
            chunk["disease_name"] = block.get("disease_name")
            chunk["disease_name_source"] = block.get("disease_name_source")

        text = str(block.get("text") or "")
        if text:
            chunk["text_markdown"] = (
                f"{chunk['text_markdown']}\n\n{text}"
                if chunk["text_markdown"]
                else text
            )

        if content_type == "table" and block.get("table"):
            chunk["tables"].append(block["table"])
        if content_type == "figure_caption":
            chunk["images"].append({"caption": text})

        confidence = block.get("parser_confidence")
        if confidence is not None:
            if chunk["parser_confidence_min"] is None:
                chunk["parser_confidence_min"] = float(confidence)
            else:
                chunk["parser_confidence_min"] = min(
                    float(chunk["parser_confidence_min"]), float(confidence)
                )

        reasons = set(chunk.get("review_reasons") or [])
        if block.get("extraction_status") == "needs_manual_review":
            reasons.update(block.get("parsing_notes") or [])
        if not block.get("chapter") or not block.get("section"):
            if content_type not in {"chapter_heading"}:
                reasons.add("context_missing")
        chunk["review_reasons"] = sorted(reasons)

    def _finalize(self) -> None:
        chunk = self._current
        if chunk is None:
            return
        text = chunk["text_markdown"].strip()
        if chunk.get("tables"):
            chunk["content_type"] = "table"
        elif chunk.get("images") and len(text) <= len(
            chunk["images"][0].get("caption") or ""
        ) + 5:
            chunk["content_type"] = "figure_caption"
        else:
            chunk["content_type"] = "mixed"

        chunk["plain_text"] = text
        chunk["char_count"] = len(text)
        chunk["validation_status"] = (
            "needs_manual_review" if chunk["review_reasons"] else "auto_validated"
        )
        chunk["source_reference"] = _source_reference(
            int(chunk["page_start"]),
            int(chunk["page_end"]),
            chunk["printed_page_start"],
            chunk["printed_page_end"],
        )
        if chunk["parser_confidence_min"] is not None:
            chunk["parser_confidence_min"] = round(
                float(chunk["parser_confidence_min"]), 4
            )

        if chunk["char_count"] <= MAX_CHUNK_CHARS:
            if chunk["char_count"] > 0:
                self.chunks.append(chunk)
        else:
            parts = _split_long_text(text, MAX_CHUNK_CHARS)
            total = len(parts)
            for index, part in enumerate(parts, start=1):
                self.chunks.append(
                    {
                        **chunk,
                        "chunk_id": f"{chunk['chunk_id']}_{index:02d}",
                        "text_markdown": part,
                        "plain_text": part,
                        "char_count": len(part),
                        "part_index": index,
                        "part_total": total,
                    }
                )
        self._current = None
        self._keys = {}

    # ------------------------------------------------------------------
    def add(self, block: dict[str, Any]) -> None:
        content_type = str(block.get("content_type"))
        chunk_type = str(block.get("chunk_type") or "unclassified")
        is_standalone = content_type in {"table", "figure_caption"}
        block_text_length = len(str(block.get("text") or ""))

        if self._current is not None:
            chapter_heading_run = (
                content_type == "chapter_heading"
                and self._keys.get("chunk_type") == "chapter_intro"
            )
            boundary = (
                is_standalone
                or self._keys.get("chunk_type") != chunk_type
                or self._keys.get("chapter") != block.get("chapter")
                or self._keys.get("section") != block.get("section")
                or (
                    content_type == "subsection_heading"
                    and self._keys.get("subsection") != block.get("subsection")
                )
            )
            if chapter_heading_run:
                boundary = False
            over_limit = (
                len(self._current["text_markdown"]) + block_text_length
                > MAX_CHUNK_CHARS
            )
            if boundary or over_limit:
                self._finalize()

        self._append_block(block, chunk_type)
        if content_type == "subsection_heading":
            self._keys["subsection"] = block.get("subsection")
        if is_standalone:
            self._finalize()

    def finish(self) -> list[dict[str, Any]]:
        self._finalize()
        return self.chunks


def build_chunks(run_id: str) -> dict[str, Any]:
    paths = config.normalized_paths()
    blocks = read_jsonl(paths["blocks"])
    builder = ChunkBuilder(run_id)
    for block in blocks:
        builder.add(block)
    chunks = builder.finish()
    store.dump_jsonl(paths["chunks"], chunks)

    by_type: dict[str, int] = {}
    for chunk in chunks:
        key = str(chunk.get("chunk_type"))
        by_type[key] = by_type.get(key, 0) + 1

    summary = {
        "run_id": run_id,
        "chunks": len(chunks),
        "chunks_by_type": dict(sorted(by_type.items())),
        "chunks_needs_review": sum(
            1
            for chunk in chunks
            if chunk.get("validation_status") == "needs_manual_review"
        ),
        "output": str(paths["chunks"]),
    }
    LOGGER.info("Chunking selesai: %s chunk", summary["chunks"])
    return summary
