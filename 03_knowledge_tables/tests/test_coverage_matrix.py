from __future__ import annotations

import sys
import unittest
from pathlib import Path

TABLE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TABLE_DIR / "src"))

import build_coverage_matrix as coverage  # noqa: E402


class TestCoverageMatrix(unittest.TestCase):
    def test_all_diseases_are_listed_once(self) -> None:
        rows = coverage.build()
        self.assertEqual(len(rows), 53)
        self.assertEqual(len({row["disease_local"] for row in rows}), 53)

    def test_status_and_observation_counts_are_consistent(self) -> None:
        rows = coverage.build()
        for row in rows:
            self.assertIn(
                row["status"],
                {"covered", "pending_3c", "no_verified_source"},
            )
            observations = int(row["observation_count"])
            external = int(row["external_observation_count"])
            internal = int(row["internal_observation_count"])
            self.assertEqual(observations, external + internal)
            if row["status"] == "covered":
                self.assertGreater(observations, 0)
                self.assertTrue(row["source_ids"])
            else:
                self.assertEqual(observations, 0)
                self.assertFalse(row["source_ids"])

    def test_uncovered_kedelai_is_pending(self) -> None:
        rows = coverage.build()
        for row in rows:
            if row["status"] == "pending_3c":
                self.assertEqual(row["plant"], "Kedelai")

    def test_external_and_internal_observation_totals(self) -> None:
        rows = coverage.build()
        external = sum(int(row["external_observation_count"]) for row in rows)
        internal = sum(int(row["internal_observation_count"]) for row in rows)
        self.assertEqual(external, 68)
        self.assertEqual(internal, 14)


if __name__ == "__main__":
    unittest.main()
