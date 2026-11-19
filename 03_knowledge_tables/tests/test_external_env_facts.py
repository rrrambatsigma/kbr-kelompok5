"""Gate test kontrak sumber eksternal lingkungan."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TABLE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TABLE_DIR / "src"))

import build_external_env_facts as ext  # noqa: E402

DISEASE = "PenyakitBlasPadi"
SOURCE_ID = "SRC_EXT_001"
CARD_ID = "CARD_EXT_001"
OBS_ID = "OBS_EXT_001"


def source_row(*, source_id: str = SOURCE_ID, status: str = "verified") -> dict[str, str]:
    return {
        "source_id": source_id,
        "title": "Sumber uji",
        "authors": "",
        "year": "2024",
        "source_type": "jurnal",
        "url": "https://example.test/source",
        "doi": "",
        "publisher": "",
        "accessed_at": "2026-11-15",
        "language": "id",
        "license": "",
        "verification_status": status,
        "notes": "",
    }


def card_row(
    *,
    relation: str = "direct",
    quote: str = "Penyakit meningkat pada musim hujan.",
    review: str = "verified",
    source_id: str = SOURCE_ID,
    card_id: str = CARD_ID,
) -> dict[str, str]:
    return {
        "card_id": card_id,
        "source_id": source_id,
        "plant": "Padi",
        "disease_local": DISEASE,
        "factor_local": "MusimHujan",
        "factor_class": "Musim",
        "relation_type": relation,
        "min_value": "",
        "max_value": "",
        "unit": "",
        "locator": "halaman 1",
        "quote": quote,
        "confidence": "high",
        "review_status": review,
        "notes": "",
    }


def observation_row(
    *,
    quote: str = "Penyakit meningkat pada musim hujan.",
    review: str = "verified",
    source_id: str = SOURCE_ID,
    card_id: str = CARD_ID,
    obs_id: str = OBS_ID,
) -> dict[str, str]:
    return {
        "obs_id": obs_id,
        "card_id": card_id,
        "plant": "Padi",
        "disease_local": DISEASE,
        "factor_local": "MusimHujan",
        "factor_class": "Musim",
        "min_value": "",
        "max_value": "",
        "unit": "",
        "operator": "",
        "condition": "",
        "quote": quote,
        "source_id": source_id,
        "confidence": "high",
        "review_status": review,
        "notes": "",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestExternalEnvironmentFacts(unittest.TestCase):
    def test_current_dataset_is_valid(self) -> None:
        _entities, _facts, _descriptions, report, errors = ext.build()
        self.assertEqual(errors, [])
        self.assertEqual(report["validation_errors"], [])
        self.assertEqual(
            report["observations_generated"],
            sum(report["relation_counts"].values()),
        )
        self.assertEqual(report["relation_counts"].get("control_only", 0), 0)

    def test_vector_requires_vector_and_environment_evidence(self) -> None:
        vector_quote = "Penyakit ditularkan oleh wereng pada musim hujan."
        source = source_row()
        card = card_row(relation="vector_mediated", quote=vector_quote)
        obs = observation_row(quote=vector_quote)
        self.assertEqual(ext.validate([source], [card], [obs], {DISEASE}), [])

        no_environment = card_row(
            relation="vector_mediated",
            quote="Penyakit ditularkan oleh wereng.",
        )
        no_environment_obs = observation_row(quote="Penyakit ditularkan oleh wereng.")
        errors = ext.validate([source], [no_environment], [no_environment_obs], {DISEASE})
        self.assertTrue(
            any("tanpa bukti faktor lingkungan" in error for error in errors),
            errors,
        )

        no_vector = card_row(
            relation="vector_mediated",
            quote="Penyakit meningkat pada musim hujan.",
        )
        no_vector_obs = observation_row(quote="Penyakit meningkat pada musim hujan.")
        errors = ext.validate([source], [no_vector], [no_vector_obs], {DISEASE})
        self.assertTrue(any("tanpa bukti vektor" in error for error in errors), errors)

        wind_quote = "Penyakit dibawa oleh angin pada musim hujan."
        wind_card = card_row(relation="vector_mediated", quote=wind_quote)
        wind_obs = observation_row(quote=wind_quote)
        errors = ext.validate([source], [wind_card], [wind_obs], {DISEASE})
        self.assertTrue(any("tanpa bukti vektor" in error for error in errors), errors)

    def test_vector_guardrail_accepts_english_source_terms(self) -> None:
        source = source_row()
        source["language"] = "en"
        quote = "Tungro incidence is greatest in rainy seasons because leafhopper vectors increase."
        card = card_row(relation="vector_mediated", quote=quote)
        obs = observation_row(quote=quote)
        self.assertEqual(ext.validate([source], [card], [obs], {DISEASE}), [])

        no_environment = "The disease is transmitted by leafhoppers."
        card = card_row(relation="vector_mediated", quote=no_environment)
        obs = observation_row(quote=no_environment)
        errors = ext.validate([source], [card], [obs], {DISEASE})
        self.assertTrue(
            any("tanpa bukti faktor lingkungan" in error for error in errors),
            errors,
        )

        no_vector = "Tungro is more severe in rainy seasons."
        card = card_row(relation="vector_mediated", quote=no_vector)
        obs = observation_row(quote=no_vector)
        errors = ext.validate([source], [card], [obs], {DISEASE})
        self.assertTrue(any("tanpa bukti vektor" in error for error in errors), errors)

    def test_one_sided_bounds_are_emitted(self) -> None:
        card = card_row(quote="Penyakit berat pada suhu 30 derajat atau lebih.")
        card["min_value"] = "30"
        card["unit"] = "°C"
        obs = observation_row(quote=card["quote"])
        obs["min_value"] = "30"
        obs["unit"] = "°C"
        obs["operator"] = ">="
        _entities, facts, _descriptions, report = self._build(card, obs)
        self.assertEqual(report["validation_errors"], [])
        values = {
            fact["predicate"]: fact["literal_value"]
            for fact in facts
            if fact["subject_local"] == OBS_ID
        }
        self.assertEqual(values.get("nilaiMin"), "30")
        self.assertNotIn("nilaiMaks", values)
        self.assertEqual(values.get("operatorNilai"), ">=")

    def test_control_only_is_skipped(self) -> None:
        entities, facts, descriptions, report = self._build(
            card_row(relation="control_only"),
            observation_row(),
        )
        self.assertEqual(entities, [])
        self.assertEqual(facts, [])
        self.assertEqual(descriptions, [])
        self.assertEqual(report["observations_generated"], 0)
        self.assertEqual(report["relation_counts"], {})
        self.assertIn("control_only", {row["reason"] for row in report["skipped"]})

    def test_unverified_observation_is_skipped(self) -> None:
        entities, facts, _descriptions, report = self._build(
            card_row(),
            observation_row(review="needs_review"),
        )
        self.assertEqual(entities, [])
        self.assertEqual(facts, [])
        self.assertIn("review_status=needs_review", {row["reason"] for row in report["skipped"]})

    def test_source_mismatch_is_skipped(self) -> None:
        entities, facts, _descriptions, report = self._build(
            card_row(),
            observation_row(source_id="SRC_EXT_002"),
            extra_sources=[source_row(source_id="SRC_EXT_002")],
        )
        self.assertEqual(entities, [])
        self.assertEqual(facts, [])
        self.assertIn(
            "source_id tidak cocok dengan card",
            {row["reason"] for row in report["skipped"]},
        )

    def test_blocked_source_is_skipped(self) -> None:
        entities, facts, _descriptions, report = self._build(
            card_row(),
            observation_row(),
            source=source_row(status="blocked_403"),
        )
        self.assertEqual(entities, [])
        self.assertEqual(facts, [])
        self.assertIn("sumber belum dapat dipakai", {row["reason"] for row in report["skipped"]})

    def test_vector_observation_is_generated_with_quality_note(self) -> None:
        quote = "Penyakit ditularkan oleh wereng pada musim hujan."
        entities, facts, descriptions, report = self._build(
            card_row(relation="vector_mediated", quote=quote),
            observation_row(quote=quote),
        )
        self.assertEqual(report["validation_errors"], [])
        self.assertEqual(report["relation_counts"], {"vector_mediated": 1})
        self.assertEqual(report["observations_generated"], 1)
        self.assertTrue(entities)
        self.assertTrue(descriptions)
        predicates = {fact["predicate"] for fact in facts}
        self.assertIn("dipengaruhiOleh", predicates)
        quality_notes = [
            fact["literal_value"]
            for fact in facts
            if fact["predicate"] == "catatanKualitas"
        ]
        self.assertTrue(quality_notes)
        self.assertTrue(all("relation_type=vector_mediated" in note for note in quality_notes))

    def test_numeric_bounds_and_unknown_vocabulary_are_rejected(self) -> None:
        source = source_row()
        card = card_row()
        card["min_value"] = "30"
        card["max_value"] = "20"
        obs = observation_row()
        errors = ext.validate([source], [card], [obs], {DISEASE})
        self.assertTrue(any("min_value > max_value" in error for error in errors), errors)

        unknown = card_row()
        unknown["disease_local"] = "PenyakitTidakAda"
        unknown["factor_class"] = "KelasTidakAda"
        obs_unknown = observation_row()
        obs_unknown["disease_local"] = "PenyakitTidakAda"
        obs_unknown["factor_class"] = "KelasTidakAda"
        errors = ext.validate([source], [unknown], [obs_unknown], {DISEASE})
        self.assertTrue(any("disease_local tidak dikenal" in error for error in errors), errors)
        self.assertTrue(any("factor_class tidak dikenal" in error for error in errors), errors)

    def test_empty_quote_is_rejected(self) -> None:
        source = source_row()
        card = card_row(quote="")
        obs = observation_row(quote="")
        errors = ext.validate([source], [card], [obs], {DISEASE})
        self.assertTrue(any("quote kosong" in error for error in errors), errors)

    def _build(
        self,
        card: dict[str, str],
        observation: dict[str, str],
        *,
        source: dict[str, str] | None = None,
        extra_sources: list[dict[str, str]] | None = None,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict]:
        sources = [source or source_row()]
        sources.extend(extra_sources or [])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "sources.csv"
            card_path = root / "cards.csv"
            obs_path = root / "observations.csv"
            conditions_path = root / "conditions.csv"
            write_csv(source_path, sources)
            write_csv(card_path, [card])
            write_csv(obs_path, [observation])
            conditions_path.write_text(
                "obs_id,condition_local,condition_label,reason,confidence,review_status\n",
                encoding="utf-8",
            )
            with (
                patch.object(ext, "SOURCE_REGISTRY", source_path),
                patch.object(ext, "CARDS_CSV", card_path),
                patch.object(ext, "OBSERVATIONS_CSV", obs_path),
                patch.object(ext, "CONDITIONS_CSV", conditions_path),
            ):
                entities, facts, descriptions, report, _errors = ext.build()
        return entities, facts, descriptions, report


if __name__ == "__main__":
    unittest.main()
