from __future__ import annotations
import json
import hashlib
import http.server
import os
import shutil
import socketserver
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class LiveContractTests(unittest.TestCase):
    def test_live_response_requires_get_content_type_and_date_marker(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        from publish_channels import verify_live_response
        self.assertFalse(verify_live_response(200, b"report 2026-11-07", "2026-11-07", "application/octet-stream")["ok"])
        self.assertFalse(verify_live_response(200, b"report 2026-11-07", "2026-11-07", "text/plain; charset=utf-8")["ok"])
        raw = verify_live_response(200, b"report 2026-11-07", "2026-11-07", "text/plain; charset=utf-8", allow_text_plain=True)
        self.assertTrue(raw["ok"])
        self.assertFalse(raw["presentation_eligible"])

    def test_308_is_followed_and_extensionless_pages_path_succeeds(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        from publish_channels import verify_live_url

        date = "2026-11-07"
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == f"/reports/{date}":
                    self.send_response(308)
                    self.send_header("Location", f"/reports/{date}.html")
                    self.end_headers()
                    return
                body = f"<html>report {date}</html>".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_args: object) -> None:
                pass

        server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/reports/{date}"
            result = verify_live_url(url, date)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], 200)
        self.assertTrue(result["redirected"])
        self.assertEqual(result["redirects"][0]["status"], 308)
        self.assertTrue(result["final_url"].endswith(f"/reports/{date}.html"))

    def test_pages_hash_and_minimum_size_are_required(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        from publish_channels import verify_live_response
        body = b"<html>report 2026-11-07</html>"
        digest = hashlib.sha256(body).hexdigest()
        self.assertTrue(verify_live_response(200, body, "2026-11-07", "text/html; charset=utf-8", min_bytes=10, expected_sha256=digest)["ok"])
        self.assertFalse(verify_live_response(200, body, "2026-11-07", "text/html", min_bytes=1000, expected_sha256=digest)["ok"])
        self.assertFalse(verify_live_response(200, body, "2026-11-07", "text/html", expected_sha256="0" * 64)["ok"])

    def test_check_live_rejects_unknown_option_without_waiting(self):
        with tempfile.TemporaryDirectory(prefix="live-contract-") as td:
            brain = Path(td) / "brain"
            (brain / "logs").mkdir(parents=True)
            (brain / "tools").mkdir()
            script = brain / "tools" / "check_live.sh"
            shutil.copy2(ROOT / "tools" / "check_live.sh", script)
            result = subprocess.run(["bash", str(script), "--help"], text=True, capture_output=True, timeout=5,
                                    env=dict(os.environ, BRAIN_DIR=str(brain)))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("معامل غير معروف", result.stdout + result.stderr)

    def test_d020_uses_live_urls_not_file_urls(self):
        manifest = json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))
        d020 = next(step for step in manifest["steps"] if step["id"] == "D020")
        command = " ".join(d020["command"])
        self.assertNotIn("file://$SITE", command)
        self.assertIn("publish-", command)

    def test_runbook_invalid_assert_fails_closed_without_nameerror(self):
        with tempfile.TemporaryDirectory(prefix="runbook-assert-") as td:
            root = Path(td)
            (root / "tools").mkdir()
            (root / "runbook").mkdir()
            shutil.copy2(ROOT / "tools" / "runbook.py", root / "tools" / "runbook.py")
            manifest = {
                "version": 1, "ledger_dir": "logs/runbook", "sections": [],
                "exempt": ["runbook/*", "tools/runbook.py"],
                "exempt_reasons": {"runbook/*": "test", "tools/runbook.py": "test"},
                "phase_order": ["gates"], "steps": [{
                    "id": "BAD", "title": "bad", "kind": "script", "phase": "gates",
                    "command": ["true"], "assert": [{"type": "cmd", "command": []}],
                    "links": {"rules": ["test"], "files": ["tools/runbook.py"], "folders": [], "gates": [], "tests": []},
                    "on_fail": "stop"
                }]
            }
            (root / "runbook" / "runbook.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run(["python3", str(root / "tools" / "runbook.py"), "run", "--root", str(root), "--date", "2026-11-07"],
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertNotIn("NameError", result.stdout + result.stderr)
            self.assertIn("CMD_SHAPE_V1", result.stdout + result.stderr)

    def test_cloudflare_pages_is_primary_and_enabled(self):
        manifest = json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))
        text = json.dumps(manifest, ensure_ascii=False)
        self.assertIn("cloudflare-pages", text)
        self.assertIn("mda-bh.pages.dev", text)
        channel = next(item for item in manifest.get("publish_channels", []) if item.get("name") == "cloudflare-pages")
        self.assertTrue(channel["enabled"])
        self.assertEqual(channel["base_url"], "https://mda-bh.pages.dev")
        self.assertEqual(manifest.get("publish_channel_order"), ["cloudflare-pages", "raw-githack", "raw.githubusercontent-verify-only"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
