#!/usr/bin/env python3
"""عقود الأصل الإنجليزي ومعجم الواجهة ذي المصدر الواحد: موجب وسوالب."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_en_master.py"
SYNC = ROOT / "tools" / "i18n_assets_sync.py"
DATE = "2026-11-10"


def invoke(script: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class EnglishMasterContractTests(unittest.TestCase):
    def run_validator(self, ar_text: str, en_text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="en-master-contract-") as raw:
            base = pathlib.Path(raw)
            ar = base / "ar.md"
            en = base / "en.md"
            ar.write_text(ar_text, encoding="utf-8")
            en.write_text(en_text, encoding="utf-8")
            return invoke(VALIDATOR, "--arabic", str(ar), "--english", str(en))

    def test_accepts_same_structure_and_number_sequence(self) -> None:
        result = self.run_validator(
            "# تقرير\n\n| الموقع | العدد |\n|---|---|\n| خليج | 12 |\n- واقعة 3\n",
            "# Report\n\n| Location | Count |\n|---|---|\n| Gulf | 12 |\n- Incident 3\n",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("arabic_chars=0", result.stdout)
        self.assertIn("number_tokens=2", result.stdout)

    def test_rejects_a_changed_number(self) -> None:
        result = self.run_validator(
            "# تقرير\n- واقعة 12\n",
            "# Report\n- Incident 13\n",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("NUMBER_MISMATCH", result.stdout + result.stderr)

    def test_rejects_an_untranslated_arabic_character(self) -> None:
        result = self.run_validator(
            "# تقرير\n- واقعة 12\n",
            "# Report\n- واقعة 12\n",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("ARABIC_REMAINS", result.stdout + result.stderr)

    def test_rejects_a_different_table_shape(self) -> None:
        result = self.run_validator(
            "# تقرير\n| الموقع | العدد |\n|---|---|\n| خليج | 12 |\n",
            "# Report\n| Location | Count | Extra |\n|---|---|---|\n| Gulf | 12 | x |\n",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("STRUCTURE_MISMATCH", result.stdout + result.stderr)


class I18nAssetSyncTests(unittest.TestCase):
    def prepare_roots(self, base: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path]:
        repo = base / "repo"
        brain = repo / "brain"
        canonical = repo / "site" / "sources" / "i18n" / "en"
        operational = base / "operational-site" / "sources" / "i18n" / "en"
        canonical.mkdir(parents=True)
        operational.mkdir(parents=True)
        glossary = {"entries": {"تحذير": "Warning"}}
        (canonical / "glossary.json").write_text(
            json.dumps(glossary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        (canonical / f"{DATE}-sectioned.en.md").write_text(
            "# Report\n| Area | Count |\n|---|---|\n| Gulf | 12 |\n", encoding="utf-8"
        )
        (operational / "glossary.json").write_text('{"entries":{}}\n', encoding="utf-8")
        (operational / f"{DATE}-sectioned.en.md").write_text("stale\n", encoding="utf-8")
        return repo, brain, canonical, operational

    def sync_args(self, brain: pathlib.Path, operational: pathlib.Path, mode: str) -> tuple[str, ...]:
        site_root = operational.parents[2]
        return (
            mode,
            "--brain",
            str(brain),
            "--site",
            str(site_root),
            "--date",
            DATE,
        )

    def test_check_detects_drift_without_writing_then_sync_repairs_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="i18n-asset-sync-") as raw:
            base = pathlib.Path(raw)
            _, brain, canonical, operational = self.prepare_roots(base)
            glossary_target = operational / "glossary.json"
            report_target = operational / f"{DATE}-sectioned.en.md"
            before = (glossary_target.read_bytes(), report_target.read_bytes())

            checked = invoke(SYNC, *self.sync_args(brain, operational, "--check"))
            self.assertEqual(checked.returncode, 2, checked.stdout + checked.stderr)
            self.assertIn("I18N_ASSET_MISMATCH", checked.stdout + checked.stderr)
            self.assertEqual(before, (glossary_target.read_bytes(), report_target.read_bytes()))

            synced = invoke(SYNC, *self.sync_args(brain, operational, "--sync"))
            self.assertEqual(synced.returncode, 0, synced.stdout + synced.stderr)
            self.assertEqual(glossary_target.read_bytes(), (canonical / "glossary.json").read_bytes())
            self.assertEqual(report_target.read_bytes(), (canonical / f"{DATE}-sectioned.en.md").read_bytes())

            verified = invoke(SYNC, *self.sync_args(brain, operational, "--check"))
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            self.assertIn("I18N_ASSET_PARITY=PASS", verified.stdout)

    def test_sync_fails_closed_when_the_canonical_glossary_is_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="i18n-asset-missing-") as raw:
            base = pathlib.Path(raw)
            repo = base / "repo"
            brain = repo / "brain"
            site = base / "operational-site"
            (repo / "site" / "sources" / "i18n" / "en").mkdir(parents=True)
            target_dir = site / "sources" / "i18n" / "en"
            target_dir.mkdir(parents=True)
            (target_dir / f"{DATE}-sectioned.en.md").write_text("old\n", encoding="utf-8")
            result = invoke(
                SYNC,
                "--sync",
                "--brain",
                str(brain),
                "--site",
                str(site),
                "--date",
                DATE,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("CANONICAL_ASSET_MISSING", result.stdout + result.stderr)
            self.assertEqual(
                (target_dir / f"{DATE}-sectioned.en.md").read_text(encoding="utf-8"), "old\n"
            )

class RunbookEnglishAssetPipelineTests(unittest.TestCase):
    def test_manifest_orders_producer_sync_gate_and_consumer_fail_closed(self) -> None:
        manifest = json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))
        steps = manifest["steps"]
        ids = [step["id"] for step in steps]
        for required in ("B004", "B004A", "B005", "B009"):
            self.assertIn(required, ids)
        positions = {step_id: ids.index(step_id) for step_id in ("B004", "B004A", "B005", "B009")}
        self.assertLess(positions["B004"], positions["B004A"])
        self.assertLess(positions["B004A"], positions["B005"])
        self.assertLess(positions["B005"], positions["B009"])

        by_id = {step["id"]: step for step in steps}
        producer = by_id["B004"]
        self.assertEqual(producer["kind"], "agent")
        self.assertEqual(producer["prompt"], "runbook/prompts/write-en-master.md")
        self.assertEqual(producer["on_fail"], "stop")
        producer_asserts = " ".join(
            " ".join(assertion.get("command", [])) for assertion in producer["assert"]
        )
        self.assertIn("validate_en_master.py", producer_asserts)

        sync = by_id["B004A"]
        sync_command = " ".join(sync["command"])
        sync_asserts = " ".join(
            " ".join(assertion.get("command", [])) for assertion in sync["assert"]
        )
        self.assertEqual(sync["kind"], "script")
        self.assertIn("i18n_assets_sync.py", sync_command)
        self.assertIn("--sync", sync_command)
        self.assertIn("--check", sync_asserts)
        self.assertIn("{site}/sources/i18n/en/{date}-sectioned.en.md", sync["reads"])
        self.assertIn("{site}/sources/i18n/en/glossary.json", sync["reads"])
        self.assertNotIn("../site/", " ".join(sync["reads"] + sync["links"]["files"]))
        self.assertEqual(sync["on_fail"], "stop")

        gate = by_id["B005"]
        self.assertIn("B004", gate["title"])
        self.assertIn("B009", gate["title"])
        self.assertEqual(gate["on_fail"], "stop")


if __name__ == "__main__":
    unittest.main(verbosity=2)
