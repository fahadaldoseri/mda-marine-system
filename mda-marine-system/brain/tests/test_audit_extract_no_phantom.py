#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار موجب وسالب لدالة استخراج النص في أداة تدقيق تغطية الأسلوب.

العطل المرجعي (2026-11-02): تحويل الوسوم إلى نصوص كان يُنتج عيوبًا لا يراها القارئ:
  1) فراغًا قبل علامة الترقيم إذا وقع الوسم بين الرمز والعلامة («B/2) .» في الاستخراج · 0 في المتصفح)؛
  2) حرفًا عربيًا مضاعفًا إذا التصق نصُّ عنصرين متجاورين («جدًا» + «التقرير» ⇒ «االتقرير» · 0 في المتصفح)؛
  3) فراغًا قبل الترقيم العربية لأن علاماتها (U+060C · U+061B · U+061F) وقعت داخل مدى الحروف العربية.

الموجب: النص المستخرج يطابق ما يعرضه المتصفح في الحالات الثلاث.
السالب: عيوب المصدر الحقيقية لا تُخفى، وتبقى بوابة عيوب الصياغة ترصدها بمنع.

الرمز: 0 نجاح · 2 فشل.
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import tempfile

B = pathlib.Path(__file__).resolve().parent.parent
fails: list[str] = []


def load():
    spec = importlib.util.spec_from_file_location("asc", B / "tools" / "audit_style_coverage.py")
    m = importlib.util.module_from_spec(spec)
    sys.argv = ["audit_style_coverage.py", "--date", "2026-11-01"]
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass
    return m


def check(cond: bool, name: str, why: str = "") -> None:
    print(("  ✓ " if cond else "  ✘ ") + name + ("" if cond else f" — {why}"))
    if not cond:
        fails.append(name)


m = load()


def flat(src: str) -> str:
    return " ".join(m.strip_html(src).split())


# 1) موجب: وسم وسيط بين رمز لاتيني وعلامة ترقيم عربية ⇒ لا فراغ
got = flat('<p>الجهة <span class="ltr">IMO</span>؛ استمرار</p>')
check("IMO؛" in got and "IMO ؛" not in got, "لا فراغ وهمي قبل «؛» بعد رمز لاتيني", repr(got))

# 2) موجب: وسم وسيط ثم نقطة
got = flat('<p>موقعها <bdi dir="ltr">(01-01; B/2)</bdi>.</p>')
check("B/2)." in got and ") ." not in got, "النقطة ملتصقة بالقوس في النص المستخرج", repr(got))

# 3) موجب: عنصران متجاوران لا يُنتجان حرفًا مضاعفًا
got = flat("<li><span>مرتفع جدًا</span><span>التقرير اليومي</span></li>")
check("االتقرير" not in got and "جدًا التقرير" in got, "لا حرف مضاعف من التصاق عنصرين", repr(got))

# 4) موجب: فراغ حقيقي مكتوب في المصدر يبقى محفوظًا
got = flat("<p><span>أول</span> <span>ثانٍ</span></p>")
check("أول ثانٍ" in got, "الفراغ الحقيقي بين كلمتين محفوظ", repr(got))

# 5) سالب: عيوب حقيقية في المصدر لا يُصلحها الاستخراج ولا يُخفيها
for i, src in enumerate(["جملة فيها فراغ قبل النقطة .\n", "االتقرير اليومي بخطأ مطبعي\n"], 1):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(src)
        tmp = pathlib.Path(fh.name)
    r = subprocess.run([sys.executable, str(B / "validators" / "check_prose_defects.py"), "--md", str(tmp)],
                       capture_output=True, text=True)
    check(r.returncode == 2, f"سالـب {i}: البوابة تمنع العيب الحقيقي (rc={r.returncode})", f"rc={r.returncode}")

print(f"── الاختبارات: {len(fails)} فشل")
sys.exit(2 if fails else 0)
