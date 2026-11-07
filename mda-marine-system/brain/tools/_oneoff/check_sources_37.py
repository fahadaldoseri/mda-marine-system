#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص فعلي للمصادر السبعة والثلاثين: هل تفتح؟ وهل يمكن جلب بيانات منها؟

الاستخدام:
  python3 validators/check_sources_37.py [--out /path/result.json] [--workers 8]

المنهج: طلب HTTP حقيقي بهوية متصفح واقعية، مع تتبع التحويلات، ثم تصنيف النتيجة:
  يعمل            : استجابة 200 بمحتوى فعلي يحتوي عناصر صفحة
  يعمل بقيود      : استجابة 200 لكن المحتوى ديناميكي/فارغ يحتاج متصفحًا كاملًا
  محجوب           : 403/429 أو صفحة تحدٍّ أمني أو CAPTCHA
  تعذر الاتصال     : فشل شبكي أو مهلة
  خطأ خادم        : 5xx
  رابط محوّل      : تحويل إلى صفحة أخرى تُسجَّل معه
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# قائمة المصادر كما هي في brain/approved-sources-37.md
SOURCES = [
    (1, "UKMTO — الحوادث الأخيرة", "https://www.ukmto.org/recent-incidents"),
    (2, "UKMTO — التحذيرات 2026", "https://www.ukmto.org/ukmto-products/warnings/2026"),
    (3, "UKMTO — النشرات الاستشارية 2026", "https://www.ukmto.org/ukmto-products/advisories/2026"),
    (4, "UKMTO — التقارير الأسبوعية 2026", "https://www.ukmto.org/ukmto-products/weekly-reports/2026"),
    (5, "المنظمة البحرية الدولية IMO — حوادث الشرق الأوسط", "https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx"),
    (6, "straits.live", "https://straits.live/"),
    (7, "gCaptain", "https://gcaptain.com"),
    (8, "TradeWinds", "https://www.tradewindsnews.com"),
    (9, "Seatrade Maritime", "https://www.seatrade-maritime.com"),
    (10, "الجزيرة نت مباشر", "https://www.ajnet.me/"),
    (11, "الجزيرة الإنجليزية — إيران", "https://www.aljazeera.com/where/iran/"),
    (12, "OFAC — الإجراءات الأخيرة", "https://ofac.treasury.gov/recent-actions"),
    (13, "ShipNext — سفينة", "https://shipnext.com/vessel/9315159-cameroon-prosperity"),
    (14, "قناة العربية", "https://www.alarabiya.net/"),
    (15, "حساب UKMTO على X", "https://x.com/UK_MTO"),
    (16, "حساب BNA العربية على X", "https://x.com/bna_ar"),
    (17, "حساب BNA الإنجليزية على X", "https://x.com/bna_en"),
    (18, "حساب الخارجية البحرينية على X", "https://x.com/bahdiplomatic"),
    (19, "حساب الأسطول الخامس على X", "https://x.com/us5thfleet"),
    (20, "جريدة الأيام", "https://www.alayam.com/"),
    (21, "أخبار الخليج", "https://akhbar-alkhaleej.com/"),
    (22, "جريدة البلاد", "https://www.albiladpress.com/"),
    (23, "Gulf Daily News", "https://www.gdnonline.com"),
    (24, "وكالة الأنباء القطرية قنا", "https://qna.org.qa/"),
    (25, "وكالة وام الإماراتية", "https://www.wam.ae/ar"),
    (26, "وكالة واس السعودية", "https://www.spa.gov.sa"),
    (27, "وكالة كونا الكويتية", "https://www.kuna.net.kw"),
    (28, "وكالة الأنباء العُمانية", "https://omannews.gov.om"),
    (29, "البحرية الملكية البريطانية", "https://www.royalnavy.mod.uk/news"),
    (30, "القيادة المركزية سنتكوم", "https://www.centcom.mil/MEDIA/PRESS-RELEASES/"),
    (31, "JMIC", "https://combinedmaritimeforces.com/jmic/"),
    (32, "غرفة التجارة الدولية IMB", "https://iccwbo.org/global-insights/trade/maritime-piracy-and-armed-robbery"),
    (33, "MARAD / MSCI", "https://www.maritime.dot.gov/msci"),
    (34, "MSCIO", "https://www.mscio.eu"),
    (35, "Splash 247", "https://splash247.com"),
    (36, "Lloyd's List", "https://www.lloydslist.com"),
    (37, "MarineLink", "https://www.marinelink.com"),
]

BLOCK_SIGNS = ["just a moment", "attention required", "captcha", "cf-challenge",
               "enable javascript", "access denied", "are you a robot", "challenge-platform",
               "cloudflare", "request blocked", "verify you are human"]
PAYWALL_SIGNS = ["subscribe to continue", "subscription required", "sign in to continue",
                 "become a member", "log in to read"]
JS_ONLY_SIGNS = ["__next", "ng-app", "id=\"root\"", "data-reactroot", "nuxt", "app-root"]


def fetch(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.8,en;q=0.6",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            body = r.read(400_000)
            return {
                "http": r.status, "final_url": r.geturl(),
                "ctype": r.headers.get("Content-Type", ""), "bytes": len(body),
                "ms": int((time.time() - t0) * 1000),
                "body": body.decode("utf-8", "ignore"),
            }
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(200_000)
        except Exception:
            pass
        return {"http": e.code, "final_url": url, "ctype": e.headers.get("Content-Type", "") if e.headers else "",
                "bytes": len(body), "ms": int((time.time() - t0) * 1000),
                "body": body.decode("utf-8", "ignore"), "error": f"HTTPError {e.code}"}
    except Exception as e:
        return {"http": 0, "final_url": url, "ctype": "", "bytes": 0,
                "ms": int((time.time() - t0) * 1000), "body": "",
                "error": f"{type(e).__name__}: {e}"}


def classify(res):
    body = (res.get("body") or "").lower()
    code = res.get("http", 0)
    if code == 0:
        return "تعذر الاتصال", res.get("error", "")
    if code in (403, 429, 401):
        return "محجوب", f"رمز {code}"
    if code >= 500:
        return "خطأ خادم", f"رمز {code}"
    if code == 404:
        return "رابط غير موجود", "404"
    if code in (301, 302) and res.get("final_url") and res["final_url"].rstrip("/") != "":
        pass
    if any(s in body for s in BLOCK_SIGNS):
        return "محجوب", "صفحة تحدٍّ أمني أو CAPTCHA"
    if any(s in body for s in PAYWALL_SIGNS):
        return "يعمل بقيود", "محتوى مدفوع أو يتطلب تسجيلًا"
    text_len = len(re.sub(r"<[^>]+>", " ", body))
    if text_len < 1200:
        return "يعمل بقيود", "محتوى قليل يحتاج متصفحًا كاملًا أو تحميلًا ديناميكيًا"
    if any(s in body for s in JS_ONLY_SIGNS) and text_len < 4000:
        return "يعمل بقيود", "صفحة تطبيق ديناميكي"
    return "يعمل", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=f"{BRAIN}/validators/sources-37-result.json")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    rows = []

    def work(item):
        num, name, url = item
        res = fetch(url)
        status, note = classify(res)
        return {
            "num": num, "name": name, "url": url, "status": status, "note": note,
            "http": res.get("http", 0), "bytes": res.get("bytes", 0),
            "ms": res.get("ms", 0), "final_url": res.get("final_url", url),
            "ctype": (res.get("ctype") or "").split(";")[0],
            "error": res.get("error", ""),
        }

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(work, SOURCES):
            rows.append(r)
            print(f"{r['num']:>2} {r['status']:<14} {r['http']:<4} {r['bytes']:>7}B {r['name']}")

    rows.sort(key=lambda r: r["num"])
    summary = {}
    for r in rows:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    out = {"checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "total": len(rows), "summary": summary, "rows": rows}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nالملخص:", json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())