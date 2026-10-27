"""Entry point pipeline ekstraksi PDF KBR.

Contoh:
    python 02_extraction\run_extraction.py extract --dry-run
    python 02_extraction\run_extraction.py extract
    python 02_extraction\run_extraction.py validate
"""

from __future__ import annotations

import sys
from pathlib import Path


EXTRACTION_DIR = Path(__file__).resolve().parent
if str(EXTRACTION_DIR) not in sys.path:
    sys.path.insert(0, str(EXTRACTION_DIR))

from pdf_pipeline.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
