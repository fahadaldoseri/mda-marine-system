#!/usr/bin/env python3
"""تجربة جافة: يعدّ رموز طلبات الكتابة بعدّاد Gemini الرسمي (countTokens). لا يولّد نصًا ولا ينشر ولا يرسل،
ولا يطبع أي محتوى ولا أسرار: أرقامًا فقط."""
import json, os, sys, urllib.request, urllib.error, importlib.util
from pathlib import Path

ROOT = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "tools"))
import runbook  # noqa: E402
spec = importlib.util.spec_from_file_location("a", ROOT / "tools" / "agent_write_llm.py")
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)

KEY = os.environ.get("FREELLMAPI_GOOGLE_KEY", "")
BASE = "https://generativelanguage.googleapis.com/v1beta"


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"x-goog-api-key": KEY, "content-type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        print("  HTTP", e.code, e.read().decode("utf-8", "replace")[:160].replace(KEY, "***") if KEY else "")
        return None


def count(model, text):
    r = call(f"/models/{model}:countTokens", {"contents": [{"parts": [{"text": text}]}]})
    return None if r is None else r.get("totalTokens")


def main():
    if not KEY:
        print("✘ لا مفتاح Google"); return 2
    date = sys.argv[1]
    models = call("/models?pageSize=200") or {}
    names = [m["name"].split("/")[-1] for m in models.get("models", [])
             if "countTokens" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]]
    print("نماذج flash المتاحة للعدّ:", names[:8])
    chosen = names[:2]
    m = runbook.load(str(ROOT))
    for model in chosen:
        print(f"\n=== النموذج {model}")
        for s in m["steps"]:
            if s.get("kind") != "agent":
                continue
            p = a.build_prompt(s, date)
            print(f"{s['id']}: {len(p)} حرفًا → {count(model, p)} رمزًا")
            if s["id"] == "W010":
                s2 = dict(s); s2["reads"] = [r for r in s["reads"] if "web/meta" not in r]
                p2 = a.build_prompt(s2, date)
                print(f"W010 بلا ملف الواجهة (يوم جديد): {len(p2)} حرفًا → {count(model, p2)} رمزًا")
                print("  الثابت (تعليمات+معجم+أمثلة+أقسام):", count(model, runbook.render_prompt(str(ROOT), s["prompt"], date)))
                for rel in ("cumulative-2026/daily/{date}.json", "feeds/feeds-{date}.md", "web/meta/{date}.json"):
                    f = ROOT / rel.replace("{date}", date)
                    if f.is_file():
                        print(f"  {rel}: {count(model, f.read_text(encoding='utf-8', errors='replace'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
