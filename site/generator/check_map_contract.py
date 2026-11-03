#!/usr/bin/env python3
"""حارس عقد قسم الخريطة — يفحص الصفحة المبنية مقابل بيانات الواجهة ويفشل مغلقًا (رمز 2).

يمنع تكرار الأعطال المقيسة:
  1. تحوّل محددات CSS إلى محددات مركّبة ميتة عند البناء (ك-413).
  2. حقن وسم HTML داخل كتل الأنماط أو السكربت فيفسد الخطوط.
  3. مفتاح بلا شرح أو عناصر مفتاح فارغة.
  4. وصف بديل للقارئ الشاشي لا يطابق الرسم الفعلي.
  5. غياب الإطار الخرائطي (مقياس الرسم · سهم الشمال) وسطر المصادر.
  6. بقاء لوحة التكبير بجانب الخريطة على الجوال بدل تكديسها.
  7. عودة لفظ «الموضع» إلى أسطح الخريطة بعد اعتماد «الموقع» (ك-480).
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _style_blocks(html: str) -> list:
    return re.findall(r"<style\b[^>]*>(.*?)</style>", html, flags=re.S | re.I)


def _map_block(html: str) -> str:
    """كتلة قسم الخريطة وحدها: من أول إطار خريطة إلى نهاية القسم (ك-480)."""
    i = html.find('class="map-panel')
    if i < 0:
        i = html.find('class="map-viz')
    if i < 0:
        return ""
    j = html.find("</section>", i)
    return html[i:j if j > 0 else i + 20000]


def verify(html: str, meta: dict) -> list:
    v = []
    points = ((meta.get("map") or {}).get("points")) or []
    n = len(points)
    ap = sum(1 for p in points if p.get("precision") == "approximate")

    # ك-480: اللفظ المرئي المعتمد «الموقع»؛ لا يعود «الموضع» إلى أسطح الخريطة.
    map_block = _map_block(html)
    if map_block:
        banned = re.findall(r"(?<![\u0600-\u06FF])الموضع(?![\u0600-\u06FF])", map_block)
        if banned:
            v.append(f"لفظ «الموضع» ظهر {len(banned)} مرة في قسم الخريطة؛ المعتمد «الموقع» (ك-480)")

    for block in _style_blocks(html):
        for tag in ("<span", "<bdi", "<b>", "<i>", "<em"):
            if tag in block:
                v.append(f"وسم HTML «{tag}» داخل كتلة أنماط — إفساد CSS")
                break
        if re.search(r"\.mp-[a-z-]+\.[a-z]", block):
            bad = re.findall(r"\.[a-z0-9-]+\.mp-[a-z-]+\.[a-z0-9-]+", block)
            v.append(f"محدد CSS مركّب ميت (فُقدت المسافة قبل المحدد): {bad[:3] or ['مثال']}")

    if 'class="map-viz' not in html and "map-panel" not in html:
        v.append("لا يوجد قسم خريطة في الصفحة")

    svg_desc = re.search(r"<desc>(.*?)</desc>", html, flags=re.S)
    if not svg_desc:
        v.append("لا يوجد وصف <desc> لخريطة الشاشة")
    else:
        d = re.sub(r"<[^>]+>", " ", svg_desc.group(1))
        if n:
            if str(n) not in d:
                v.append(f"وصف الخريطة لا يذكر عدد الوقائع المرسومة ({n})")
            if ap and "تقريبي" not in d:
                v.append("وصف الخريطة لا يذكر أن المواقع تقريبية مع وجود مواضع تقريبية")
        elif "لا" not in d:
            v.append("وصف الخريطة غير صريح في غياب الوقائع")

    if n:
        items = re.findall(r'<ol[^>]*class="[^"]*map-legend[^"]*"[^>]*>(.*?)</ol>', html, flags=re.S)
        if not items:
            v.append("لا توجد قائمة مفتاح للوقائع مع وجود وقائع")
        else:
            lis = re.findall(r"<li>(.*?)</li>", items[0], flags=re.S)
            if len(lis) != n:
                v.append(f"عناصر مفتاح الوقائع {len(lis)} لا تساوي عدد الوقائع {n}")
            empty = sum(1 for li in lis if not re.sub(r"<[^>]+>", " ", li).strip())
            if empty:
                v.append(f"{empty} عنصر مفتاح بلا نص")
            if not any("موقع تقريبي" in li or "إحداثيات مذكورة" in li for li in lis):
                v.append("مفتاح الوقائع لا يعلن دقة الموقع")
        if 'class="map-key mp-key"' not in html:
            v.append("مفتاح الطبقات ورموزها غائب مع وجود وقائع")
        if "sw-mark-approx" not in html and ap:
            v.append("المفتاح لا يشرح العلامة المفرّغة للموضع التقريبي")

    if 'class="mp-north"' not in html:
        v.append("سهم الشمال غائب عن الخريطة")
    if "ميل بحري" not in html or "كيلومتر" not in html:
        v.append("مقياس الرسم (كيلومتر · ميل بحري) غائب عن الخريطة")
    for need in ("Natural Earth", "Marine Regions"):
        if need not in html:
            v.append(f"سطر المصادر لا يذكر {need}")

    if ".hmap-wrap:has(> .hmap-zoom)" not in html:
        v.append("قاعدة تكديس لوحة التكبير على الجوال غائبة عن الأنماط")

    labels = re.findall(r'aria-label="([^"]*)"', html)
    if not any("خريطة" in x for x in labels):
        v.append("لا يوجد اسم وصولي (aria-label) للخريطة")
    if any(x.strip() == "Section" for x in labels):
        v.append("اسم وصولي عام «Section» بدل وصف الخريطة")
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--html")
    args = ap.parse_args()
    html_p = pathlib.Path(args.html) if args.html else ROOT / "dist" / "reports" / f"{args.date}.html"
    meta_p = ROOT / "sources" / "meta" / f"{args.date}.json"
    if not html_p.exists() or not meta_p.exists():
        print(f"  ✘ حارس عقد الخريطة: مدخل مفقود ({html_p} · {meta_p})")
        return 2
    html = html_p.read_text(encoding="utf-8")
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    v = verify(html, meta)
    n = len(((meta.get("map") or {}).get("points")) or [])
    if v:
        print(f"  ✘ حارس عقد الخريطة: {len(v)} مخالفة ({html_p.name} · {n} واقعة)")
        for x in v:
            print(f"    · {x}")
        return 2
    print(f"  ✔ حارس عقد الخريطة: مطابق ({n} واقعة · مفتاح · وصف · إطار خرائطي · مصادر · تكديس الجوال)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
