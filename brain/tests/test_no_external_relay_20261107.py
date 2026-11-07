#!/usr/bin/env python3
"""حاجز فشل مغلق: لا وسيط خارجي يحمل رمز البوت في مسار إرسال تلغرام.

ثلاث حالات: (1) فحص ساكن لملف الأداة: لا عنوان خارج api.telegram.org ولا ثابت RELAY.
(2) فحص سلوكي: عند فشل الإرسال المباشر لا يُجرَّب أي نطاق آخر إطلاقًا (نداء واحد فقط).
(3) فحص سالب: نسخة محقونة بالوسيط تُكشف — لإثبات أن الحاجز يقظ لا نائم.
"""
from __future__ import annotations

import pathlib
import re
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "telegram_send.py"
ALLOWED = "api.telegram.org"


def static_offenders(text: str) -> list[str]:
    out: list[str] = []
    if re.search(r"^\s*RELAY\s*=", text, re.M):
        out.append("ثابت RELAY محظور")
    for m in re.finditer(r"https?://[^\s\"')+]+", text):
        host = re.sub(r"^https?://", "", m.group(0)).split("/")[0]
        if host != ALLOWED:
            out.append(f"نطاق غير مسموح: {m.group(0)[:60]}")
    return out


def behavioral_calls() -> tuple[list[list[str]], bool]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("tg_probe", TOOL)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    calls: list[list[str]] = []

    def fake_curl(args, timeout=120):  # noqa: ANN001
        calls.append(list(args))
        return '{"ok":false,"error_code":400,"description":"فشل مُصطنع للقياس"}'

    mod.curl = fake_curl
    route: list[str] = []
    sent = mod.send_text("123456:PROBE", "-1000000000000", "قياس", route)
    return calls, bool(sent)


def main() -> int:
    ok = True
    text = TOOL.read_text(encoding="utf-8")
    bad = static_offenders(text)
    print(f"STATIC_OFFENDERS={len(bad)}")
    for b in bad[:5]:
        print(f"   {b}")
    ok &= not bad

    calls, sent = behavioral_calls()
    hosts = [a for c in calls for a in c if isinstance(a, str) and "http" in a]
    bad_hosts = [h for h in hosts if ALLOWED not in h]
    print(f"BEHAVIORAL_CALLS={len(calls)} · HOSTS={len(hosts)} · OFFHOST={len(bad_hosts)} · SENT={sent}")
    ok &= (len(calls) == 1) and not bad_hosts and not sent

    with tempfile.TemporaryDirectory() as tmp:
        inj = pathlib.Path(tmp) / "telegram_send.py"
        inj.write_text(text + '\nRELAY = "https://r.jina.ai/"\n', encoding="utf-8")
        neg = static_offenders(inj.read_text(encoding="utf-8"))
    print(f"NEGATIVE_INJECTED_OFFENDERS={len(neg)}")
    ok &= len(neg) >= 1

    print("NO_EXTERNAL_RELAY=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
