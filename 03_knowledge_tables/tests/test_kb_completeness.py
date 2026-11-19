"""Gate inti kelengkapan KB pada ontology_md.ttl."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TABLE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TABLE_DIR / "src"))

import build_kb_completeness_report as completeness  # noqa: E402


class TestKbCompleteness(unittest.TestCase):
    def test_core_gaps_are_closed(self) -> None:
        report = completeness.build()
        summary = report["summary"]
        self.assertEqual(summary["environment_missing"], 0)
        self.assertEqual(summary["pathogen_missing"], 0)
        self.assertEqual(summary["pathogen_unknown_taxon_unique"], 0)
        self.assertEqual(summary["control_missing"], 0)
        self.assertEqual(summary["part_missing"], 0)
        self.assertEqual(summary["growth_conditions_missing_plants"], 0)

    def test_control_fallback_is_available(self) -> None:
        report = completeness.build()
        self.assertGreater(report["summary"]["control_fallback"], 0)

    def test_scope_is_fixed(self) -> None:
        report = completeness.build()
        self.assertEqual(report["summary"]["diseases"], 53)
        self.assertEqual(report["summary"]["plants"], 7)


if __name__ == "__main__":
    unittest.main()
