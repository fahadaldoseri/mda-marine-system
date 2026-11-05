#!/usr/bin/env python3
"""اختبار انحدار: نسخ المهارات القانونية المؤقتة لا تُحسب انحرافًا في التماثل — عطل ك-524.
العلّة: أنشأت جولة الإغلاق نسخة محلية `brain/logs/skills-canon-<طابع>/SKILL.md.bak`،
فعدّها فاحص التماثل «مفقودة من المستودع» وأوقف خطوة النسخة الاحتياطية D005.
القاعدة الجذرية: النسخ المؤقتة تحت `brain/logs/` محلية بطبيعتها (مثل `skills-sync-`
و`apply-`)، وتُعلن في `LOCAL_ONLY_PATTERNS` بسبب مكتوب، فلا تُنقل ولا تُعدّ انحرافًا.
رمز الخروج: 0 سليم · 1 مخالفة.
"""
from __future__ import annotations

import importlib.util
import pathlib

B = pathlib.Path(__file__).resolve().parent.parent
V = B / "validators" / "check_backup_parity.py"
PREFIX = "brain/logs/skills-canon-"
SAMPLE = PREFIX + "20261105-034405/SKILL.md.bak"


def _module():
    spec = importlib.util.spec_from_file_location("cbp_test", V)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = _module()
    patterns = tuple(getattr(mod, "LOCAL_ONLY_PATTERNS", ()))
    if PREFIX not in patterns:
        print(f"  ✘ البادئة «{PREFIX}» غير معلنة في LOCAL_ONLY_PATTERNS")
        return 1
    # نفس الشرط المستعمل في فاحص التماثل عند عدّ المفقود من المستودع
    skipped = any(SAMPLE.startswith(p) or f"/{p}" in SAMPLE for p in patterns)
    if not skipped:
        print(f"  ✘ الملف «{SAMPLE}» ما زال يُعدّ انحرافًا مانعًا")
        return 1
    # لا يُوسَّع الاستثناء إلى سجل تشغيل عام أو ملف حاكم
    for must_count in ("brain/reports/2026-11-05-sectioned.md",
                       "brain/validators/check_backup_parity.py"):
        if any(must_count.startswith(p) or f"/{p}" in must_count for p in patterns):
            print(f"  ✘ الاستثناء شمل ملفًا حاكمًا: {must_count}")
            return 1
    print(f"  ✔ نسخ المهارات المحلية مستثناة ببادئة معلنة ({len(patterns)} بادئة)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())