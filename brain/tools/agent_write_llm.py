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
FILE_RE = re.compile(r"<<<\s*FILE:?\s*(.+?)\s*>>>[ \t]*\r?\n(.*?)\r?\n[ \t]*<<<\s*END\s*>{0,3}[ \t]*(?=\r?\n|$)", re.S)


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


def _post(url: str, headers: dict, body: bytes, secret: str) -> dict:
    """نداء JSON مع إعادة محاولة عند 429 وأخطاء الخادم المؤقتة؛ لا يطبع المفتاح أبدًا."""
    last: Exception | None = None
    for i, wait in enumerate((0, 30, 90)):
        if wait:
            time.sleep(wait)
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400].replace(secret, "***")
            print(f"  ⚠ HTTP {exc.code} (حجم البرومت {len(body)} بايت، محاولة {i + 1}/3): {detail}")
            last = exc
            if exc.code not in (429, 500, 502, 503, 504, 529):
                break
        except Exception as exc:  # انقطاع أو مهلة
            print(f"  ⚠ {type(exc).__name__}: {str(exc)[:200]}")
            last = exc
    raise last  # type: ignore[misc]


def chat(prompt: str) -> str:
    """Anthropic إن وُجد ANTHROPIC_API_KEY، وإلا واجهة متوافقة مع OpenAI (freellmapi)."""
    akey = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if akey:
        body = json.dumps({"model": os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5"),
                           "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "16000")),
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        resp = _post("https://api.anthropic.com/v1/messages",
                     {"content-type": "application/json", "x-api-key": akey,
                      "anthropic-version": "2023-06-01"}, body, akey)
        u = resp.get("usage", {})
        print(f"  ℹ رموز الإدخال {u.get('input_tokens')} والإخراج {u.get('output_tokens')} · سبب التوقف {resp.get('stop_reason')}")
        return "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    if not base or not key:
        raise RuntimeError("لا ANTHROPIC_API_KEY ولا LLM_BASE_URL/LLM_API_KEY")
    body = json.dumps({"model": os.environ.get("LLM_MODEL", "auto"), "temperature": 0.2,
                       "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "32000")),
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    resp = _post(f"{base}/chat/completions",
                 {"content-type": "application/json", "authorization": f"Bearer {key}"}, body, key)
    c = resp["choices"][0]["message"]["content"]
    return "".join(x.get("text", "") for x in c) if isinstance(c, list) else (c or "")


def _norm(path: str) -> str:
    return path.strip().strip("`\"' ").removeprefix("./")


def write_outputs(s: dict, date: str, text: str) -> list[str]:
    allowed = {_norm(w.replace("{date}", date)) for w in s.get("writes", [])}
    done = []
    for path, content in FILE_RE.findall(text):
        path = _norm(path)
        if path not in allowed:
            print(f"  ⚠ تجاهل مسار غير معلن للخطوة: {path!r} (المسموح: {sorted(allowed)})")
            continue
        out = (ROOT / path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content.rstrip("\n") + "\n", encoding="utf-8")
        done.append(path)
    if not done:
        print(f"  ⚠ لا ملفات بالصيغة المطلوبة؛ طول الرد {len(text)} وبدايته: {text[:160]!r}")
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
            time.sleep(int(os.environ.get("LLM_GAP_SECONDS", "20")))  # تخفيف حد الدقيقة للمزوّد المجاني
            try:
                files = write_outputs(s, a.date, chat(build_prompt(s, a.date, problems)))
            except Exception as exc:  # الشبكة أو المزوّد
                print(f"✘ نداء النموذج فشل: {type(exc).__name__}: {str(exc)[:300]}")
                files = []
            if not files:
                problems = "لم تُرجَع أي ملفات بالصيغة المطلوبة."
                continue
            c = sh(["complete", s["id"], "--date", a.date])
            print("\n".join("✘ رفض: " + ln for ln in c.stdout[-1500:].splitlines() if ln.strip()))
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
