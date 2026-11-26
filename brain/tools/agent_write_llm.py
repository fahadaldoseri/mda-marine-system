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

MAX_FILE = 60_000  # حدّ كل ملف قراءة داخل البرومت (حرفًا)
FILE_RE = re.compile(r"<<<\s*FILE:?[ \t]*([^\n>]+?)[ \t]*(?:>{1,3})?[ \t]*\r?\n(.*?)\r?\n[ \t]*<<<\s*END\s*>{0,3}[ \t]*(?=\r?\n|$)", re.S)


def sh(args: list[str]) -> subprocess.CompletedProcess:
    # الخطوتان الاختياريتان S080 وS090 تستعملان LLM_BASE_URL؛ تُحجب عنهما كي لا تستهلكا حصة المزوّد المجاني.
    env = {k: v for k, v in os.environ.items() if k not in ("LLM_BASE_URL", "LLM_API_KEY", "ANTHROPIC_API_KEY")}
    return subprocess.run([sys.executable, "tools/runbook.py", *args, "--root", str(ROOT)],
                          cwd=ROOT, capture_output=True, text=True, env=env)


def waiting_step(date: str) -> dict | None:
    m = runbook.load(str(ROOT))
    ledger = runbook.read_ledger(str(ROOT), m, date)
    for s in m["steps"]:
        e = ledger.get(s["id"])
        if s.get("kind") == "agent" and e and e["status"] == "waiting_agent":
            return s
    return None


def compact_estimates(raw: str) -> str:
    """سجل رموز EST- مختصرًا: آخر 25 رمزًا بمعناها فقط (الأصل 40 ألف حرف ولا يحتاجه النموذج كله)."""
    try:
        codes = json.loads(raw)["codes"]
    except Exception:
        return raw
    keys = sorted(codes)[-25:]
    lines = [f"{k}: {str(codes[k].get('statement', ''))[:110]}" for k in keys]
    return ("رموز تقديرات قائمة (لا تُعد إسناد رمز لمعنى آخر، ولا تُنشئ رمز EST- جديدًا لأنك لا تشغّل أداة التسجيل؛ "
            "عبّر عن التقدير الجديد بنص احتمالي بلا رمز، أو أعد ذكر رمز قائم بمعناه حرفيًا):\n" + "\n".join(lines))


def build_prompt(s: dict, date: str, problems: str = "") -> str:
    prompt_src = (ROOT / s["prompt"]).read_text(encoding="utf-8")
    included = {runbook.sub(i, date, None).lstrip("./") for i in runbook.INCLUDE_RE.findall(prompt_src)}
    parts = [runbook.render_prompt(str(ROOT), s["prompt"], date)]
    for rel in s.get("reads", []):
        rel = rel.replace("{date}", date)
        # لا تكرار لما ضُمّن في البرومت، ولا أدوات ولا مهارات (النموذج لا يشغّلها).
        if rel == s["prompt"] or rel in included or rel.startswith("tools/") or rel.endswith("SKILL.md"):
            continue
        p = ROOT / rel
        if p.is_file():
            txt = p.read_text(encoding="utf-8", errors="replace")
            if rel.endswith("estimate-code-map.json"):
                txt = compact_estimates(txt)
            if len(txt) > MAX_FILE:
                txt = txt[:MAX_FILE] + "\n…[اقتُطع]"
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
    for i, wait in enumerate((0, 30, 90, 90)):
        if wait:
            time.sleep(wait)
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            detail_full = exc.read().decode("utf-8", "replace").replace(secret, "***")
            detail = detail_full[:400]
            print(f"  ⚠ HTTP {exc.code} (حجم البرومت {len(body)} بايت، محاولة {i + 1}/4): {detail}")
            last = exc
            if exc.code not in (429, 500, 502, 503, 504, 529):
                break
            if exc.code == 429:  # حدّ المزوّد: انتظر موعد الإتاحة المعلن (حتى 5.5 دقيقة)
                try:
                    at = json.loads(detail_full)["error"]["retryAtMs"] / 1000
                    time.sleep(max(15, min(at - time.time(), 330)))
                except Exception:
                    pass
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
        fb_dir = ROOT / "fallback" / a.date
        answer = fb_dir / f"{s['id']}.answer.txt"
        for t in range(1, a.tries + 1):
            print(f"▶ {s['id']}: محاولة {t} عبر " + ("إجابة Claude الاحتياطية" if answer.is_file() else "النموذج"))
            prompt = build_prompt(s, a.date, problems)
            if answer.is_file():
                files = write_outputs(s, a.date, answer.read_text(encoding="utf-8"))
            else:
                time.sleep(int(os.environ.get("LLM_GAP_SECONDS", "20")))  # تخفيف حد الدقيقة للمزوّد المجاني
                try:
                    files = write_outputs(s, a.date, chat(prompt))
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
            fb_dir.mkdir(parents=True, exist_ok=True)
            (fb_dir / f"{s['id']}.prompt.md").write_text(build_prompt(s, a.date), encoding="utf-8")
            print(f"✘ تعذّر إتمام {s['id']} بعد {a.tries} محاولات — حُفظ البرومت الكامل في fallback/{a.date}/{s['id']}.prompt.md "
                  f"ليكتب Claude الإجابة في {s['id']}.answer.txt بصيغة <<<FILE>>> نفسها")
            return 2
    print("✘ تجاوز الحد الأعلى لخطوات الوكيل")
    return 2


if __name__ == "__main__":
    sys.exit(main())
