#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس أزواج العربية والإنجليزية في سجل البطاقات الحاكم (ك-596).

السبب المقيس: حقل `badges` في بطاقة عبور IMO حمل بندًا عربيًا واحدًا
(«آخر تحديث سبتمبر 2026») مقابل بندين إنجليزيين
(«For public information» و«Last updated September 2026»). المستهلك يقرأ
القائمتين بالمقابلة بالموضع، فقُرئ البند العربي بترجمة عبارة أخرى، فدخل المعجم
الإنجليزية مدخلًا خاطئًا: «آخر تحديث سبتمبر 2026» → «For public information»؛
وعند ترجمة الإصدار رُفض لأن سنة المفتاح غابت عن قيمته (حارس ك-592) فأوقف البناء.

المخالفتان اللتان يحرسهما هذا المدقق:
  1. طول قائمة عربية لا يساوي طول نظيرتها الإنجليزية في الحقل نفسه (مقابلة موضعية مكسورة).
  2. مفتاح عربي يحمل رقمًا (سنة أو تاريخ أو عددًا) لا يظهر في نظيره الإنجليزي (فقد بيانات).

الاستعمال: python3 brain/validators/check_card_registry_pairs.py
الرمز: 0 سليم · 2 مخالفة مانعة.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

B = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = B / "appendices" / "card_registry.json"
DIGITS = re.compile(r"\d{2,}")


def _numbers(value: str) -> set[str]:
    return set(DIGITS.findall(value or ""))


def check(registry_path: pathlib.Path = REGISTRY) -> list[str]:
    """يعيد قائمة المخالفات بصيغة «المسار — السبب»؛ وقائمة فارغة تعني سليمًا."""
    if not registry_path.is_file():
        return [f"سجل البطاقات غير موجود: {registry_path}"]
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    bad: list[str] = []

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("_en"):
                    ar_key = key[:-3]
                    if ar_key in node:
                        ar, en = node[ar_key], value
                        where = f"{path}.{ar_key}"
                        if isinstance(ar, list) and isinstance(en, list) and len(ar) != len(en):
                            bad.append(
                                f"{where} — طول القائمة مختلف: عربي={len(ar)} إنجليزي={len(en)} "
                                f"(المقابلة بالموضع مكسورة)"
                            )
                        elif isinstance(ar, list) and isinstance(en, list):
                            # ك-596: القائمتان متساويتان طولًا لا يعني سلامة المقابلة؛
                            # يُفحص كل بند مقابل نظيره بالموضع نفسه (أرقام وتواريخ).
                            for i, (a_item, e_item) in enumerate(zip(ar, en)):
                                if isinstance(a_item, str) and isinstance(e_item, str):
                                    missing = _numbers(a_item) - _numbers(e_item)
                                    if missing:
                                        bad.append(
                                            f"{where}[{i}] — أرقام في العربي غائبة عن الإنجليزي: "
                                            f"{sorted(missing)}"
                                        )
                        elif isinstance(ar, str) and isinstance(en, str):
                            missing = _numbers(ar) - _numbers(en)
                            if missing:
                                bad.append(
                                    f"{where} — أرقام في العربي غائبة عن الإنجليزي: {sorted(missing)}"
                                )
                walk(value, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")

    for section in ("hero_kpis", "official_cards", "cards"):
        if section in data:
            walk(data[section], section)
    return bad


def main() -> int:
    bad = check()
    if bad:
        print(f"   ✘ مخالفات في سجل البطاقات: {len(bad)}")
        for item in bad:
            print(f"      · {item}")
        return 2
    print("   ✔ سجل البطاقات: أزواج العربية والإنجليزية متطابقة الطول ومحافظة على الأرقام")
    return 0


if __name__ == "__main__":
    sys.exit(main())
