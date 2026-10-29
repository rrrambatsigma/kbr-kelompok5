"""Entry point pipeline LlamaParse untuk DOC002.

Contoh:
    python 02_extraction\run_llamaparse.py env-check
    python 02_extraction\run_llamaparse.py smoke --page 25
    python 02_extraction\run_llamaparse.py parse --tier cost_effective --pages "25,27,91-95"
"""

from __future__ import annotations

import sys
from pathlib import Path


EXTRACTION_DIR = Path(__file__).resolve().parent
if str(EXTRACTION_DIR) not in sys.path:
    sys.path.insert(0, str(EXTRACTION_DIR))

from llamaparse_pipeline.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
