#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يضيف مصدرًا جديدًا بعد مسحه: السجل + الموثوقية + الفهرس (الأسلوب المعتمد)."""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
import argparse, json, re
from pathlib import Path
R = Path(f'{BRAIN}')

def main():
    a = argparse.ArgumentParser()
    for f in ('num', 'name', 'url', 'type', 'rel', 'cred', 'basis'):
        a.add_argument('--' + f, required=True)
    g = a.parse_args()
    num = int(g.num)
    js = R / 'appendices/source-reliability-40.json'
    data = json.loads(js.read_text(encoding='utf-8'))
    if any(r[0] == num for r in data):
        print(f"  ✘ الرقم {num} مستخدم"); return 1
    data.append([num, g.name, g.url, g.type, g.rel, int(g.cred), g.basis])
    js.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    md = R / 'appendices/source-reliability-40.md'
    md.write_text(md.read_text(encoding='utf-8').replace(
        '## قواعد ملزمة', f"| {num} | [{g.name}]({g.url}) | {g.type} | **{g.rel}** | **{int(g.cred)}** | {g.basis} |\n\n## قواعد ملزمة"),
        encoding='utf-8')
    src = R / 'sections/10-sources.md'
    src.write_text(src.read_text(encoding='utf-8').rstrip() +
        f"\n\n| {num} | {g.name} | {g.url} | {g.type} | {g.rel} · {int(g.cred)} | — (نُفّذ بروتوكول المسح) |\n", encoding='utf-8')
    print(f"  ✔ أُضيف المصدر {num}: {g.name} ({g.rel}·{int(g.cred)}) — شغّل بروتوكول المسح ثم أعد البيانات")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
