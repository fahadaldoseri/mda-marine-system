#!/usr/bin/env python3
"""اختبار انحدار ب-03: المرساة التي تُضاف بعد تحميل HTML يجب أن تُثبت حيًا."""
from __future__ import annotations

import importlib.util
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_measure_module():
    spec = importlib.util.spec_from_file_location("browser_measure_regression", ROOT / "tools/browser_measure.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DynamicAnchorHandler(BaseHTTPRequestHandler):
    anchor = "dynamic-anchor"

    def do_GET(self):  # noqa: N802 - واجهة BaseHTTPRequestHandler
        if self.path.split("?", 1)[0] == "/source.html":
            body = (
                '<!doctype html><html><body>'
                '<a href="/target.html#dynamic-anchor">مصدر رسمي</a>'
                '</body></html>'
            )
        elif self.path.split("?", 1)[0] == "/target.html":
            body = (
                '<!doctype html><html><body><main id="app"></main>'
                '<script>setTimeout(() => {'
                'const el = document.createElement("section");'
                'el.id = "dynamic-anchor"; el.textContent = "official incident";'
                'document.getElementById("app").appendChild(el);'
                '}, 1500);</script></body></html>'
            )
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        return


class Dynamic403AnchorHandler(DynamicAnchorHandler):
    def do_GET(self):  # noqa: N802 - واجهة BaseHTTPRequestHandler
        if self.path.split("?", 1)[0] != "/target.html":
            return super().do_GET()
        body = (
            '<!doctype html><html><body><main id="app"></main>'
            '<script>setTimeout(() => {'
            'const el = document.createElement("section");'
            'el.id = "dynamic-anchor"; el.textContent = "official incident";'
            'document.getElementById("app").appendChild(el);'
            '}, 150);</script></body></html>'
        )
        payload = body.encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class ContextBoundAnchorHandler(DynamicAnchorHandler):
    def do_GET(self):  # noqa: N802 - واجهة BaseHTTPRequestHandler
        if self.path.split("?", 1)[0] != "/target.html":
            return super().do_GET()
        if "Firefox" not in self.headers.get("User-Agent", ""):
            self.send_response(403)
            self.end_headers()
            return
        body = '<!doctype html><html><body><section id="dynamic-anchor">official incident</section></body></html>'
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def test_b03_waits_for_javascript_anchor_target():
    module = load_measure_module()
    server = ThreadingHTTPServer(("127.0.0.1", 0), DynamicAnchorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/source.html"
        result = module.measure(url, [800], [], [])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    target = result["widths"]["800"]["anchor_targets"]["/target.html#dynamic-anchor"]
    assert target is True


def test_b03_keeps_browser_context_for_external_anchor_target():
    module = load_measure_module()
    server = ThreadingHTTPServer(("127.0.0.1", 0), ContextBoundAnchorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/source.html"
        result = module.measure(url, [800], [], [])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    target = result["widths"]["800"]["anchor_targets"]["/target.html#dynamic-anchor"]
    assert target is True


def test_b03_checks_dom_anchor_before_rejecting_http_error():
    module = load_measure_module()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Dynamic403AnchorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/source.html"
        result = module.measure(url, [800], [], [])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    target = result["widths"]["800"]["anchor_targets"]["/target.html#dynamic-anchor"]
    assert target is True
