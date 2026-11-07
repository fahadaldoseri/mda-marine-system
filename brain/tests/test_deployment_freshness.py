"""اختبار انحدار: حارس حداثة النشر يفشل مغلقًا عند بناء أقدم، ولا يقبل قياسًا ناقصًا.

الحالات: كل الملفات مطابقة (0) · ملف مخدوم مختلف = بناء أقدم (2) · ملف غائب (2) ·
dist غير موجود (1) · تعذّر جلب كل الملفات (2 لأنها غائبة عن القناة).
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    'freshness', BRAIN / 'validators' / 'check_deployment_freshness.py')
fr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fr)

DATE = '2026-11-07'
FILES = {'index.html': b'<html>home</html>', 'feed.xml': b'<rss/>',
         'sitemap.xml': b'<urlset/>', 'reports/index.html': b'<html>archive</html>',
         'sources.html': b'<html>sources</html>', 'additions.html': b'<html>add</html>',
         f'reports/{DATE}.html': b'<html>report</html>'}


def _dist(tmp_path: Path) -> Path:
    root = tmp_path / 'site'
    (root / 'dist' / 'reports').mkdir(parents=True)
    for rel, body in FILES.items():
        (root / 'dist' / rel).write_bytes(body)
    return root


def _serve(monkeypatch, mapping: dict[str, tuple[int, bytes]]) -> None:
    def fake_fetch(url: str, timeout: int = 45):
        rel = url.split('/', 3)[3]
        return mapping.get(rel, (404, b''))
    monkeypatch.setattr(fr, 'fetch', fake_fetch)


def _all_match() -> dict[str, tuple[int, bytes]]:
    return {rel: (200, body) for rel, body in FILES.items()}


def test_all_files_match(tmp_path: Path, monkeypatch) -> None:
    root = _dist(tmp_path)
    _serve(monkeypatch, _all_match())
    result = fr.probe(root, DATE, 'https://x')
    assert len(result['stale']) == 0 and len(result['missing']) == 0
    assert result['match'] == len(FILES)


def test_stale_served_file_is_detected(tmp_path: Path, monkeypatch) -> None:
    root = _dist(tmp_path)
    mapping = _all_match()
    mapping['reports/index.html'] = (200, b'<html>OLD</html>')
    _serve(monkeypatch, mapping)
    result = fr.probe(root, DATE, 'https://x')
    assert [r['file'] for r in result['stale']] == ['reports/index.html']


def test_missing_served_file_is_detected(tmp_path: Path, monkeypatch) -> None:
    root = _dist(tmp_path)
    mapping = _all_match()
    del mapping['reports/index.html']
    _serve(monkeypatch, mapping)
    result = fr.probe(root, DATE, 'https://x')
    assert [r['file'] for r in result['missing']] == ['reports/index.html']


def test_identical_fingerprint_requires_byte_equality(tmp_path: Path, monkeypatch) -> None:
    """اختلاف بايت واحد يُعدّ بناءً أقدم، لا مطابقة."""
    root = _dist(tmp_path)
    mapping = _all_match()
    mapping['feed.xml'] = (200, FILES['feed.xml'] + b' ')
    _serve(monkeypatch, mapping)
    result = fr.probe(root, DATE, 'https://x')
    assert [r['file'] for r in result['stale']] == ['feed.xml']
    assert hashlib.sha256(FILES['feed.xml']).hexdigest() != result['stale'][0]['live_sha256']


def test_no_dist_is_not_satisfied(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / 'empty'
    root.mkdir()
    monkeypatch.setattr(fr, 'site_root', lambda: root)
    rc = fr.main(['--date', DATE])
    assert rc == 1


def test_exit_code_two_on_stale(tmp_path: Path, monkeypatch) -> None:
    root = _dist(tmp_path)
    monkeypatch.setattr(fr, 'site_root', lambda: root)
    mapping = _all_match()
    mapping['index.html'] = (200, b'<html>OLD</html>')
    _serve(monkeypatch, mapping)
    assert fr.main(['--date', DATE]) == 2


def test_exit_code_zero_on_fresh(tmp_path: Path, monkeypatch) -> None:
    root = _dist(tmp_path)
    monkeypatch.setattr(fr, 'site_root', lambda: root)
    _serve(monkeypatch, _all_match())
    assert fr.main(['--date', DATE]) == 0