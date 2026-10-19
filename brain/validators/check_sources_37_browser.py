#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
الفحص الحقيقي للمصادر السبعة والثلاثين بمتصفح كامل (نمط غير متزامن).

يفتح كل مصدر بمتصفح Chromium، ينتظر التحميل، ثم يقيس عنوان الصفحة وطول النص الظاهر
ووجود تحدٍّ أمني أو جدار تسجيل، ويصنّف: يعمل / يعمل بقيود / محجوب / فشل.

الاستخدام: python3 validators/check_sources_37_browser.py [--out file.json] [--conc 4]
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_sources_37 import SOURCES  # noqa: E402

from playwright.async_api import async_playwright  # noqa: E402

CHALLENGE = ["just a moment", "attention required", "verify you are human", "are you a robot",
             "checking your browser", "cf-challenge", "access denied", "request blocked",
             "تحقق من أنك إنسان", "captcha"]
LOGIN_WALL = ["sign in to x", "log in to continue", "subscribe to continue", "subscription required",
              "تسجيل الدخول للمتابعة", "اشترك للاستمرار", "become a member"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


async def check(sem, browser, item):
    num, name, url = item
    async with sem:
        rec = {"num": num, "name": name, "url": url}
        t0 = time.time()
        ctx = await browser.new_context(user_agent=UA, locale="ar",
                                        viewport={"width": 1366, "height": 900})
        page = await ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3500)
            text = await page.evaluate(
                "() => document.body ? document.body.innerText.replace(/\\s+/g,' ').trim() : ''")
            title = (await page.title() or "").strip()
            low = text.lower()
            rec.update({"title": title[:140], "text_len": len(text),
                        "sample": text[:180], "ms": int((time.time() - t0) * 1000)})
            if any(s in low for s in CHALLENGE) and len(text) < 1500:
                rec.update({"status": "محجوب", "note": "صفحة تحدٍّ أمني"})
            elif any(s in low for s in LOGIN_WALL) and len(text) < 1200:
                rec.update({"status": "يعمل بقيود", "note": "جدار تسجيل أو اشتراك"})
            elif len(text) >= 1200:
                rec.update({"status": "يعمل", "note": ""})
            elif len(text) >= 300:
                rec.update({"status": "يعمل بقيود", "note": "محتوى ظاهر محدود (تحميل ديناميكي)"})
            else:
                rec.update({"status": "فشل", "note": "لا نص ظاهر"})
        except Exception as e:
            rec.update({"status": "فشل", "note": type(e).__name__, "text_len": 0,
                        "ms": int((time.time() - t0) * 1000)})
        finally:
            await ctx.close()
        print(f"{rec['num']:>2} {rec['status']:<14} {rec.get('text_len',0):>7} حرف  "
              f"{rec['name']}  {rec.get('note','')}", flush=True)
        return rec


async def run(conc, out_path):
    sem = asyncio.Semaphore(conc)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/chromium",
                                          args=["--no-sandbox", "--disable-dev-shm-usage"])
        tasks = [check(sem, browser, it) for it in SOURCES]
        results = await asyncio.gather(*tasks)
        await browser.close()
    results = sorted(results, key=lambda r: r["num"])
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    out = {"checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "total": len(results), "summary": summary, "rows": results}
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nالملخص:", json.dumps(summary, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/home/ubuntu/brain-marine-news/validators/sources-37-browser.json")
    ap.add_argument("--conc", type=int, default=4)
    a = ap.parse_args()
    return asyncio.run(run(a.conc, a.out))


if __name__ == "__main__":
    sys.exit(main())