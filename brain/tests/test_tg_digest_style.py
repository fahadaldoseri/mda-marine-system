#!/usr/bin/env python3
"""رسالة تلغرام: جمل مكتملة بلا «…» وتجتاز مدقق الأسلوب (19 نوفمبر 2026).

بعد إزالة القص (PR 648) صارت البنود الثلاثة بلا علامة نهاية فدمجها مدقق الأسلوب
في جملة من 45 كلمة، فمنع سطح «رسالة تلغرام» في تغطية الأسطح. يُبنى الملخص لأيام
محفوظة ويُفحص بالمدقق نفسه وبالتجريد نفسه الذي تستعمله audit_style_coverage.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(B / "tools"))
import audit_style_coverage as audit  # noqa: E402

fails = 0
days = [d for d in ("2026-11-11", "2026-11-17", "2026-11-18")
        if (B / "web" / "meta" / f"{d}.json").is_file()]
with tempfile.TemporaryDirectory() as td:
    for d in days:
        out = Path(td) / f"{d}.html"
        r = subprocess.run([sys.executable, str(B / "tools" / "make_tg_digest.py"), "--date", d,
                            "--out", str(out), "--base-url", "https://mda-bh.pages.dev"],
                           capture_output=True, text=True)
        html = out.read_text(encoding="utf-8") if out.exists() else ""
        txt = Path(td) / f"{d}.txt"
        txt.write_text(audit.strip_html(html), encoding="utf-8")
        s = subprocess.run([sys.executable, str(B / "validators" / "check_style.py"), str(txt)],
                           capture_output=True, text=True)
        ok = r.returncode == 0 and "…" not in html and s.returncode == 0
        fails += not ok
        print(("  ✔" if ok else "  ✘"), d, f"build={r.returncode} style={s.returncode}",
              "بلا «…»" if "…" not in html else "فيه «…»")
if not days:
    print("  ✘ لا بيانات إصدار للاختبار")
    fails += 1
sys.exit(1 if fails else 0)
