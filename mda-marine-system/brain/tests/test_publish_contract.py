#!/usr/bin/env python3
"""عقد النشر: رأس النسخة المقصودة إلى main والتحقق المغلق من 404.

يُشغّل على نسخة قديمة لإثبات RED ثم على الإصلاح لإثبات GREEN:
1. رأس بلا صفحة التقرير المقصودة يُرفض ولا يغيّر origin/main.
2. رأس يحوي الصفحة المقصودة يُدفع إلى origin/main نفسه.
3. check_live لا يسجل نجاحًا لمسار تقرير يرد 404/0.
"""
from __future__ import annotations

import http.server
import json
import os
from pathlib import Path
import shutil
import socketserver
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "tools" / "publish_site.sh"
CHECK_LIVE = ROOT / "tools" / "check_live.sh"
DATE = "2099-01-01"


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=60, check=False)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(repo), *args])


class PublishContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="publish-contract-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_brain(self) -> Path:
        brain = self.tmp / "brain"
        (brain / "tools").mkdir(parents=True)
        (brain / "validators").mkdir()
        (brain / "logs").mkdir()
        shutil.copy2(PUBLISH, brain / "tools" / "publish_site.sh")
        (brain / "tools" / "runbook.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        (brain / "tools" / "gate_verdict.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        (brain / "validators" / "check_en_parity.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        return brain

    def make_site(self) -> tuple[Path, Path, str]:
        remote = self.tmp / "remote.git"
        seed = self.tmp / "seed"
        self.assertEqual(run(["git", "init", "-q", "--bare", str(remote)]).returncode, 0)
        self.assertEqual(run(["git", "init", "-q", "-b", "main", str(seed)]).returncode, 0)
        self.assertEqual(git(seed, "config", "user.email", "test@example.invalid").returncode, 0)
        self.assertEqual(git(seed, "config", "user.name", "Publish Contract").returncode, 0)
        (seed / "README.md").write_text("base\n", encoding="utf-8")
        self.assertEqual(git(seed, "add", "-A").returncode, 0)
        self.assertEqual(git(seed, "commit", "-qm", "base").returncode, 0)
        base = git(seed, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(git(seed, "remote", "add", "origin", str(remote)).returncode, 0)
        self.assertEqual(git(seed, "push", "-q", "origin", "main").returncode, 0)
        site = self.tmp / "site"
        self.assertEqual(run(["git", "clone", "-q", str(remote), str(site)]).returncode, 0)
        self.assertEqual(git(site, "config", "user.email", "test@example.invalid").returncode, 0)
        self.assertEqual(git(site, "config", "user.name", "Publish Contract").returncode, 0)
        self.assertEqual(git(site, "branch", "-f", "main", "origin/main").returncode, 0)
        self.assertEqual(git(site, "switch", "-qc", "publish", "main").returncode, 0)
        return site, remote, base

    def publish(self, brain: Path, site: Path) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, BRAIN_DIR=str(brain), SITE_DIR=str(site))
        return run(["bash", str(PUBLISH), DATE], env=env)

    def remote_head(self, site: Path) -> str:
        return git(site, "ls-remote", "origin", "refs/heads/main").stdout.split()[0]

    def test_wrong_head_refuses_without_remote_change(self) -> None:
        brain = self.make_brain()
        site, _remote, base = self.make_site()
        result = self.publish(brain, site)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.remote_head(site), base)
        doc = json.loads((brain / "logs" / f"publish-{DATE}.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "failed")
        self.assertIn("intended", doc.get("why", ""))

    def test_pushes_head_and_origin_main_matches_it(self) -> None:
        brain = self.make_brain()
        site, _remote, base = self.make_site()
        (site / "dist" / "reports").mkdir(parents=True)
        (site / "dist" / "reports" / f"{DATE}.html").write_text("<html>daily report</html>\n", encoding="utf-8")
        (site / "dist" / "manus-routes.json").write_text(json.dumps({"routes": [{"path": f"/reports/{DATE}.html"}]}), encoding="utf-8")
        result = self.publish(brain, site)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        head = git(site, "rev-parse", "HEAD").stdout.strip()
        self.assertNotEqual(head, base)
        self.assertEqual(self.remote_head(site), head)
        doc = json.loads((brain / "logs" / f"publish-{DATE}.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["head"], head)
        self.assertEqual(doc["origin_main"], head)
        script = PUBLISH.read_text(encoding="utf-8")
        self.assertIn("git push -q origin HEAD:main", script)
        self.assertNotIn("git push -q origin main", script)

    def test_check_live_rejects_404_as_non_success(self) -> None:
        brain = self.tmp / "live-brain"
        site = self.tmp / "live-site"
        (brain / "logs").mkdir(parents=True)
        (site / "sources").mkdir(parents=True)
        (site / "sources" / "site.json").write_text(json.dumps({"base_url": "http://127.0.0.1:1"}), encoding="utf-8")
        shutil.copy2(CHECK_LIVE, brain / "check_live.sh")
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path in {"/", "/sources.html"}:
                    body = b"ok"
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, *_args: object) -> None:
                pass
        server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        sleeper = self.tmp / "sleep"
        sleeper.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        sleeper.chmod(0o755)
        try:
            env = dict(os.environ, BRAIN_DIR=str(brain), SITE_DIR=str(site), LIVE_BASE_URL=f"http://127.0.0.1:{server.server_address[1]}", PATH=f"{self.tmp}:{os.environ['PATH']}")
            result = run(["bash", str(brain / "check_live.sh"), DATE], env=env)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        doc = json.loads((brain / "logs" / f"live-{DATE}.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], "failed")
        self.assertEqual(doc["paths"][f"/reports/{DATE}.html"]["code"], 404)
        self.assertEqual(doc["paths"][f"/reports/{DATE}.html"]["bytes"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
