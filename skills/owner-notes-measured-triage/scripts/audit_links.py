#!/usr/bin/env python3
"""تدقيق الروابط والمعرّفات في موقع مبني (HTML) — قراءة فقط.

الاستخدام:
    python3 audit_links.py --root dist
    python3 audit_links.py --root dist --strict --json /tmp/links.json
    python3 audit_links.py --root dist --net 14

يفحص:
  1) روابط داخلية (#x) ومعرّفاتها: مكسورة؟ · ومعرّفات غير مستعملة.
  2) روابط نسبية بلا هدف موجود في جذر المخرج.
  3) روابط فارغة "" أو "#" وحدها أو javascript:.
  4) روابط http غير مشفّرة.
  5) جرد الروابط الخارجية والنطاقات، وفحص شبكي اختياري لعيّنة.

رموز الخروج: 0 سليم · 2 عيوب (وبـ--strict تُعدّ الروابط الفارغة وhttp عيوبًا أيضًا).
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import ssl
import sys
import urllib.request

HREF = re.compile(r'href="([^"]*)"')
ID = re.compile(r'\sid="([^"]+)"')


def scan(root: pathlib.Path) -> dict:
    pages = sorted(root.rglob("*.html"))
    dead: list[tuple[str, str]] = []
    missing: list[tuple[str, str]] = []
    empty: collections.Counter = collections.Counter()
    insecure: collections.Counter = collections.Counter()
    external: collections.Counter = collections.Counter()
    ids_total = 0
    ids_unused = 0
    anchors_total = 0

    for page in pages:
        html = page.read_text(encoding="utf-8", errors="replace")
        ids = set(ID.findall(html))
        ids_total += len(ids)
        used: set[str] = set()
        for href in HREF.findall(html):
            if href.startswith(("http://", "https://")):
                external[href] += 1
                if href.startswith("http://"):
                    insecure[href] += 1
                continue
            if href.startswith(("#", "mailto:", "javascript:", "data:")):
                if href.startswith("#"):
                    target = href[1:]
                    if target:
                        anchors_total += 1
                        used.add(target)
                        if target not in ids:
                            dead.append((str(page), href))
                    else:
                        empty["#"] += 1
                continue
            if href == "":
                empty["(فارغ)"] += 1
                continue
            clean = href.split("#")[0].split("?")[0]
            if not clean:
                continue
            candidates = [clean, clean.rstrip("/") + ".html", clean.rstrip("/") + "/index.html"]
            if not any((root / c.lstrip("/")).is_file() for c in candidates):
                missing.append((str(page), href))
        ids_unused += len(ids - used)

    return {
        "root": str(root),
        "pages": len(pages),
        "internal_anchors": anchors_total,
        "dead_anchors": dead,
        "ids_total": ids_total,
        "ids_unused": ids_unused,
        "missing_targets": missing,
        "empty_href": dict(empty),
        "insecure_href": dict(insecure),
        "external_unique": len(external),
        "external_occurrences": sum(external.values()),
        "external_domains": dict(collections.Counter(
            re.sub(r"^https?://([^/]+).*$", r"\1", u) for u in external for _ in range(external[u])
        ).most_common(15)),
        "external_top": external.most_common(20),
    }


def network_check(urls: list[str], limit: int) -> list[tuple[str, str]]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    out: list[tuple[str, str]] = []
    for url in urls[:limit]:
        try:
            req = urllib.request.Request(
                url, method="HEAD",
                headers={"User-Agent": "Mozilla/5.0 (compatible; LinkAudit/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                out.append((str(resp.status), url))
        except Exception as exc:  # noqa: BLE001 - تقرير الحالة كما هي
            code = getattr(exc, "code", None)
            out.append((str(code or type(exc).__name__), url))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="تدقيق الروابط والمعرّفات في موقع مبني")
    ap.add_argument("--root", required=True, help="جذر المخرج المبنى (مثال: dist)")
    ap.add_argument("--strict", action="store_true", help="عدّ الروابط الفارغة وhttp عيوبًا")
    ap.add_argument("--net", type=int, default=0, help="فحص شبكي لأكثر N رابط خارجي ورودًا")
    ap.add_argument("--json", help="كتابة النتيجة إلى ملف JSON")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    if not root.is_dir():
        print(f"   ✘ الجذر غير موجود: {root}", file=sys.stderr)
        return 2

    r = scan(root)
    print(f"═══ تدقيق الروابط — {r['root']} ═══")
    print(f"   صفحات: {r['pages']} · معرّفات: {r['ids_total']} (غير مستعملة: {r['ids_unused']})")
    print(f"   روابط داخلية بين الأقسام: {r['internal_anchors']} · مكسورة: {len(r['dead_anchors'])}")
    for page, href in r["dead_anchors"][:10]:
        print(f"      ✘ {page} → {href}")
    print(f"   روابط نسبية بلا هدف: {len(r['missing_targets'])}")
    for page, href in r["missing_targets"][:10]:
        print(f"      ✘ {page} → {href}")
    print(f"   روابط فارغة/# وحدها: {sum(r['empty_href'].values())} {r['empty_href'] or ''}")
    print(f"   روابط غير مشفّرة http: {sum(r['insecure_href'].values())} (فريدة {len(r['insecure_href'])})")
    print(f"   روابط خارجية: {r['external_unique']} فريدًا · {r['external_occurrences']} موضعًا")
    for domain, n in r["external_domains"].items():
        print(f"      {domain} → {n}")

    if args.net:
        print(f"═══ فحص شبكي لأكثر {args.net} رابطًا ورودًا (403 غالبًا حجب آلي لا كسر) ═══")
        for status, url in network_check([u for u, _ in r["external_top"]], args.net):
            print(f"      {status}  {url[:96]}")

    defects = len(r["dead_anchors"]) + len(r["missing_targets"])
    if args.strict:
        defects += sum(r["empty_href"].values()) + sum(r["insecure_href"].values())
    print(f"═══ العيوب المانعة: {defects} {'(نمط strict)' if args.strict else ''} ═══")
    print("   ✔ سليم" if defects == 0 else "   ✘ يوجد ما يمنع")

    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"   حُفظ التقرير: {args.json}")
    return 0 if defects == 0 else 2


if __name__ == "__main__":
    sys.exit(main())