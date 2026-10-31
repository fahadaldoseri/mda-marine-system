#!/usr/bin/env python3
"""اختبار توصيفي لسلوك دفع النسخة الاحتياطية المعتمد وحاجز واجهتها."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "github_backup.sh"


class BackupPushSafetyTests(unittest.TestCase):
    def test_manifest_approved_main_push_is_explicit(self):
        """يثبت أن الدفع إلى main مقصود ومعلن، لا سلوكًا مخفيًا أو اختبارًا ميتًا."""
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("git push -q origin main", text)
        self.assertIn("الدفع المباشر إلى main مقصود ومعتمد في المانيفست", text)
        self.assertIn("التماثل تقارن بفرع main", text.replace("\n# ", " "))

    def test_unknown_arguments_fail_before_side_effects(self):
        """--help وأي معامل مجهول يُرفضان قبل إنشاء السجل أو تشغيل النسخ."""
        with tempfile.TemporaryDirectory() as tmp:
            isolated = Path(tmp)
            script = isolated / "github_backup.sh"
            shutil.copy2(SCRIPT, script)
            env = os.environ.copy()
            env.update(
                {
                    "BRAIN_DIR": str(isolated / "brain"),
                    "BACKUP_REPO_DIR": str(isolated / "repo"),
                }
            )
            for argument in ("--help", "--unknown"):
                result = subprocess.run(
                    ["bash", str(script), argument],
                    cwd=isolated,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("معامل غير معروف", result.stderr)
                self.assertFalse((isolated / "brain").exists())
                self.assertFalse((isolated / "repo").exists())


if __name__ == "__main__":
    unittest.main()
