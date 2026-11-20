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


# ── منشورات X: المتصفح الآلي يتلقى 403، فيُثبت المنشور عبر oEmbed الرسمي ──
# قياس 2026-11-20: x.com يرد 403 على Chromium الآلي، وpublish.twitter.com/oembed يرد 200
# بنص المنشور وحسابه. الاختبار يحاكي الحالتين محليًا دون شبكة.
POST_TEXT = "JMIC Advisory Note Update 115<br><br>Distributed by UKMTO"


class XLikeHandler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802 - واجهة BaseHTTPRequestHandler
        import json as _json
        from urllib.parse import parse_qs, urlsplit
        sp = urlsplit(self.path)
        if sp.path == "/source.html":
            port = self.server.server_port
            links = self.server.links_html.replace("{port}", str(port))
            return self._send(200, f"<!doctype html><html><body>{links}</body></html>")
        if sp.path == "/oembed":
            asked = parse_qs(sp.query)["url"][0]
            if not asked.endswith("/UK_MTO/status/2123425162758619611"):
                return self._send(404, "{}", "application/json")
            data = {"url": "https://x.com/UK_MTO/status/2123425162758619611",
                    "author_name": "UKMTO Operations Centre",
                    "html": f'<blockquote class="twitter-tweet"><p lang="en">{POST_TEXT}</p></blockquote>'}
            return self._send(200, _json.dumps(data), "application/json")
        # صفحة المنشور نفسها: كما يرد X على المتصفح الآلي
        return self._send(403, "<html><body>blocked</body></html>")

    def log_message(self, *_args):
        return


def _run_x(links_html):
    module = load_measure_module()
    server = ThreadingHTTPServer(("127.0.0.1", 0), XLikeHandler)
    server.links_html = links_html
    port = server.server_port
    module.X_HOSTS = set(module.X_HOSTS) | {"127.0.0.1"}
    module.X_OEMBED_ENDPOINT = f"http://127.0.0.1:{port}/oembed"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = module.measure(f"http://127.0.0.1:{port}/source.html", [800], [], [])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    d = result["widths"]["800"]
    return module, d


def test_b03_x_post_verified_by_official_oembed_despite_browser_403():
    _m, d = _run_x('<a href="http://127.0.0.1:{port}/UK_MTO/status/2123425162758619611'
                   '#:~:text=JMIC%20Advisory%20Note%20Update%20115">UKMTO</a>')
    (key, ok), = d["anchor_targets"].items()
    assert ok is True
    assert d["anchor_target_details"][key]["method"] == "x_oembed"


def test_b03_x_post_rejects_fragment_absent_from_post():
    _m, d = _run_x('<a href="http://127.0.0.1:{port}/UK_MTO/status/2123425162758619611'
                   '#:~:text=%D9%86%D8%B5%20%D9%85%D8%AE%D8%AA%D9%84%D9%82">UKMTO</a>')
    (key, ok), = d["anchor_targets"].items()
    assert ok is False
    assert "نص المرساة" in d["anchor_target_details"][key]["error"]


def test_b03_x_post_rejects_missing_post_and_wrong_account():
    _m, d = _run_x('<a href="http://127.0.0.1:{port}/UK_MTO/status/1#:~:text=JMIC">a</a>'
                   '<a href="http://127.0.0.1:{port}/other/status/2123425162758619611#:~:text=JMIC">b</a>')
    assert d["anchor_targets"] and not any(d["anchor_targets"].values())
