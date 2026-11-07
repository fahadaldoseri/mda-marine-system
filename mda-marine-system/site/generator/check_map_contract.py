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


POLICY_FROM = "2026-11-03"   # قرار المالك 2026-11-04: يسري على هذا التقرير وما بعده


def verify(html: str, meta: dict, date: str = "") -> list:
    v = []
    check_no_map_note(meta.get("map") or {})
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

    descs = re.findall(r"<desc>(.*?)</desc>", html, flags=re.S)
    if not descs:
        v.append("لا يوجد وصف <desc> لخريطة الشاشة")
    else:
        d = " ".join(re.sub(r"<[^>]+>", " ", x) for x in descs)
        if n:
            if str(n) not in d:
                v.append(f"وصف الخريطة لا يذكر عدد الوقائع المرسومة ({n})")
            if ap and "تقريبي" not in d:
                v.append("وصف الخريطة لا يذكر أن المواقع تقريبية مع وجود مواضع تقريبية")
        elif "لا" not in d:
            v.append("وصف الخريطة غير صريح في غياب الوقائع")

    if n and 'class="map-key mp-key"' not in html:
        v.append("مفتاح العلامات الثلاثي غائب عن الخريطة")
    if "sw-mark-approx" not in html and ap:
        v.append("المفتاح لا يشرح العلامة المفرّغة للموقع التقريبي")

    if 'class="mp-north"' not in html:
        v.append("سهم الشمال غائب عن الخريطة")
    if "ميل بحري" not in html or "كيلومتر" not in html:
        v.append("مقياس الرسم (كيلومتر · ميل بحري) غائب عن الخريطة")
    new_policy = True   # القرار يسري على كل إصدار يُبنى بعد التعديل
    if new_policy:
        # ملاحظة المالك 6 (2026-11-04): يُحذف سطر المصادر أسفل الخريطة ويُنقل إلى صفحة المصادر.
        for need in ("Natural Earth", "Marine Regions", "Ships' Routeing", "VLIZ"):
            if need in map_block:
                v.append(f"عودة المصطلح المرجعي «{need}» إلى قسم الخريطة — محذوف بقرار المالك (ملاحظة 6)")
        # ملاحظة المالك 2 و3: لا تظهر رموز القطاعات Z على سطح يقرأه القارئ.
        zc = re.findall(r"(?<![A-Za-z0-9])Z[1-5](?![0-9])", map_block)
        if zc:
            v.append(f"رمز قطاع داخلي ظاهر للقارئ في قسم الخريطة: {sorted(set(zc))} (ملاحظة 2)")
        # ملاحظة المالك 8: مفتاح الخريطة ثلاثة أسطر فقط.
        if 'class="map-key mp-key"' not in html:
            v.append("مفتاح العلامات الثلاثي غائب عن الخريطة")
        else:
            m = re.search(r'<ul class="map-key mp-key"[^>]*>(.*?)</ul>', html, flags=re.S)
            items = re.findall(r"<li>(.*?)</li>", m.group(1), flags=re.S) if m else []
            texts = [re.sub(r"<[^>]+>", " ", x).strip() for x in items]
            want = ("واقعة مؤكدة", "موقع تقريبي", "بلاغ غير مؤهل")
            if len(items) != 3 or any(w not in " ".join(texts) for w in want):
                v.append(f"مفتاح الخريطة يجب أن يكون ثلاثة أسطر فقط ({texts}) — ملاحظة 8")
        # ملاحظة المالك 6: لا يعود ملخّص العدّ (وصف الخريطة المرئي) إلى القسم.
        for frag in ("تتركز البنود المرمزة", "ويشمل العد", "وتوزيع الحالة", "وقائع خارج نطاق الخريطة",
                     "اليابسة والحدود السياسية", "هذه الخريطة سياق إخباري"):
            if frag in map_block:
                v.append(f"عودة النص المحذوف أسفل الخريطة: «{frag}» (ملاحظة 6)")
    else:
        pass

    if ".hmap-wrap:has(> .hmap-zoom)" not in html:
        v.append("قاعدة تكديس لوحة التكبير على الجوال غائبة عن الأنماط")

    labels = re.findall(r'aria-label="([^"]*)"', html)
    if not any("خريطة" in x for x in labels):
        v.append("لا يوجد اسم وصولي (aria-label) للخريطة")
    if any(x.strip() == "Section" for x in labels):
        v.append("اسم وصولي عام «Section» بدل وصف الخريطة")
    return v


def check_no_map_note(mp: dict) -> None:
    """ملاحظة المالك (6): لا نص وصف ولا ملاحظة أسفل الخريطة في أي إصدار."""
    for k in ("caption", "points_note"):
        if str(mp.get(k) or "").strip():
            raise SystemExit(f"✘ وصف الخريطة يجب أن يكون فارغًا ({k}) — قرار المالك")


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
    v = verify(html, meta, args.date)
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
