#!/usr/bin/env python3
"""يكتب خطوات الوكيل (W010 وW030 وW020 وB004) بنموذج متوافق مع واجهة OpenAI بلا جلسة Claude.

الاستعمال (من مجلد brain، مع BRAIN_DIR وSITE_DIR):
  python3 tools/agent_write_llm.py --date D [--max-steps 8] [--tries 2]

الحلقة: `runbook.py run` ← إن توقف عند خطوة وكيل (رمز 10) يُبنى البرومت نفسه الذي يطبعه المحرّك
مع ملفات reads، ويُطلب من النموذج إرجاع ملفات writes المعلنة للخطوة فقط، ثم `runbook.py complete`.
إن رُفض الإتمام تُعاد المحاولة مع نص الرفض (حتى --tries)، ثم يتوقف بالرمز 2 ولا يتجاوز أي بوابة.

المتغيرات: LLM_BASE_URL (مثال http://127.0.0.1:3001/v1 من freellmapi_up.sh) وLLM_API_KEY وLLM_MODEL (افتراضي auto).
لا يطبع المفتاح. رموز الخروج: 0 انتهى الخط بلا خطوة وكيل معلّقة، 2 فشل، غير ذلك رمز runbook.py run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "tools"))
import runbook  # noqa: E402

MAX_FILE = 150_000  # حدّ كل ملف قراءة داخل البرومت (بايت)
FILE_RE = re.compile(r"<<<FILE (.+?)>>>\n(.*?)\n<<<END>>>", re.S)


def sh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "tools/runbook.py", *args, "--root", str(ROOT)],
                          cwd=ROOT, capture_output=True, text=True)


def waiting_step(date: str) -> dict | None:
    m = runbook.load(str(ROOT))
    ledger = runbook.read_ledger(str(ROOT), m, date)
    for s in m["steps"]:
        e = ledger.get(s["id"])
        if s.get("kind") == "agent" and e and e["status"] == "waiting_agent":
            return s
    return None


def build_prompt(s: dict, date: str, problems: str = "") -> str:
    parts = [runbook.render_prompt(str(ROOT), s["prompt"], date)]
    for rel in s.get("reads", []):
        rel = rel.replace("{date}", date)
        if rel == s["prompt"]:
            continue
        p = ROOT / rel
        if p.is_file():
            txt = p.read_text(encoding="utf-8", errors="replace")
            if len(txt.encode()) > MAX_FILE:
                txt = txt.encode()[:MAX_FILE].decode("utf-8", "ignore") + "\n…[اقتُطع]"
            parts.append(f"\n## الملف: {rel}\n```\n{txt}\n```")
    writes = [w.replace("{date}", date) for w in s.get("writes", [])]
    parts.append(
        "\n## صيغة الإخراج (إلزامية)\n"
        "أرجع كل ملف تكتبه بالمحتوى الكامل بين علامتين حرفيًا، ولا شيء خارجهما:\n"
        "<<<FILE المسار>>>\nالمحتوى\n<<<END>>>\n"
        f"المسارات المسموحة فقط: {', '.join(writes)}. لا تختلق وقائع ولا مصادر ولا أوقات استرجاع؛ "
        "خذ كل واقعة من الملفات المضمّنة أعلاه.")
    if problems:
        parts.append(f"\n## رفض المحرّك المحاولة السابقة لهذه الأسباب، فأصلحها:\n{problems}")
    return "\n".join(parts)


def chat(prompt: str) -> str:
    base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    if not base or not key:
        raise RuntimeError("LLM_BASE_URL أو LLM_API_KEY غير مضبوط")
    body = json.dumps({"model": os.environ.get("LLM_MODEL", "auto"), "temperature": 0.2, "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "32000")),
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    last: Exception | None = None
    for i, wait in enumerate((0, 30, 90)):  # أخطاء مؤقتة (429/5xx) لدى المزوّد المجاني
        if wait:
            time.sleep(wait)
        req = urllib.request.Request(f"{base}/chat/completions", data=body, method="POST",
                                     headers={"content-type": "application/json", "authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                resp = json.load(r)
            c = resp["choices"][0]["message"]["content"]
            return "".join(x.get("text", "") for x in c) if isinstance(c, list) else (c or "")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400].replace(key, "***")
            print(f"  ⚠ HTTP {exc.code} (حجم البرومت {len(prompt)} حرفًا، محاولة {i + 1}/3): {detail}")
            last = exc
            if exc.code not in (429, 500, 502, 503, 504):
                break
        except Exception as exc:  # انقطاع أو مهلة
            print(f"  ⚠ {type(exc).__name__}: {str(exc)[:200]}")
            last = exc
    raise last  # type: ignore[misc]


def write_outputs(s: dict, date: str, text: str) -> list[str]:
    allowed = {w.replace("{date}", date) for w in s.get("writes", [])}
    done = []
    for path, content in FILE_RE.findall(text):
        path = path.strip()
        if path not in allowed:
            print(f"  ⚠ تجاهل مسار غير معلن للخطوة: {path}")
            continue
        out = (ROOT / path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content.rstrip("\n") + "\n", encoding="utf-8")
        done.append(path)
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--max-steps", type=int, default=8)
    ap.add_argument("--tries", type=int, default=2)
    a = ap.parse_args()
    for _ in range(a.max_steps):
        r = sh(["run", "--date", a.date])
        print(r.stdout[-3000:])
        if r.returncode != 10:
            return r.returncode
        s = waiting_step(a.date)
        if not s:
            print("✘ المحرّك أرجع 10 بلا خطوة وكيل معلّقة")
            return 2
        problems = ""
        for t in range(1, a.tries + 1):
            print(f"▶ {s['id']}: محاولة {t} عبر النموذج")
            try:
                files = write_outputs(s, a.date, chat(build_prompt(s, a.date, problems)))
            except Exception as exc:  # الشبكة أو المزوّد
                print(f"✘ نداء النموذج فشل: {type(exc).__name__}: {str(exc)[:300]}")
                files = []
            if not files:
                problems = "لم تُرجَع أي ملفات بالصيغة المطلوبة."
                continue
            c = sh(["complete", s["id"], "--date", a.date])
            print(c.stdout[-1500:])
            if c.returncode == 0:
                break
            problems = c.stdout[-1500:]
        else:
            print(f"✘ تعذّر إتمام {s['id']} بعد {a.tries} محاولات — يلزم تدخّل")
            return 2
    print("✘ تجاوز الحد الأعلى لخطوات الوكيل")
    return 2


if __name__ == "__main__":
    sys.exit(main())
