#!/usr/bin/env python3
"""ك-146: عدّ المصادر بلا شبكة — يثبت الثابت (مفحوصة = ناجحة + متعذّرة) وعدم الحساب المزدوج."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("cf", ROOT / 'tools/check_feeds.py')
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)

# مصدر واحد نجح على مسار وفشل على آخر (46) + مصدر فشل (10) + مصدر بمسار متصفحي (3)
res = [{"num": 46, "ok": True}, {"num": 46, "ok": False}, {"num": 10, "ok": False}, {"num": 3, "ok": True}]
a, o, f = cf.count_sources(res, {3, 9})
assert a == {46, 10, 3, 9}, a
assert o == {46, 3} and f == {10, 9}, (o, f)
assert len(a) == len(o) + len(f)
print(f"  · مفحوصة {len(a)} = ناجحة {len(o)} + متعذّرة {len(f)} · والحساب المزدوج ممتنع")
