#!/usr/bin/env python3
"""إعادة تجميد نمط الطباعة المعتمد بعد تغيير مشروع، مع سجل تغيير موثق.

الاستخدام:
  python3 refreeze_print_css.py --brain <مشروع> \
      --reason "ما تغيّر ولماذا" \
      --evidence "مخرج البوابتين قبل/بعد" \
      [--validator validators/check_pdf_format.py] [--source web/build_report.py] \
      [--approved-by "اسم المالك"] [--dry-run]

السلوك:
  1. يستورد المدقق المعتمد ليقرأ نمط الطباعة الحالي (`@media print`) والبروفايل المقفل،
     فلا يوجد مصدر حقيقة ثانٍ.
  2. يقارن بصمة النمط الحالي ببصمة الملف المقفل.
  3. إن تطابقتا: لا يفعل شيئًا (خرج 0).
  4. إن اختلفتا: يكتب الملف المقفل، ويضيف سجل تغيير إلى البروفايل (date/change/evidence/approved_by)،
     ثم يطبع البصمتين ويطلب تشغيل المدقق للتأكيد.
مع --dry-run لا يكتب شيئًا.

لا يُستعمل هذا السكربت لتخفيف عتبة بوابة؛ تغيير النمط يعني إعادة تجميد فقط.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location('_validator', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description='إعادة تجميد نمط الطباعة المعتمد')
    ap.add_argument('--brain', required=True)
    ap.add_argument('--validator', default='validators/check_pdf_format.py')
    ap.add_argument('--source', default='web/build_report.py',
                    help='ملف البناء الذي يحوي @media print (يُقرأ عبر المدقق)')
    ap.add_argument('--reason', required=True)
    ap.add_argument('--evidence', required=True)
    ap.add_argument('--approved-by', default=None)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    brain = Path(a.brain).expanduser().resolve()
    vpath = (brain / a.validator) if not Path(a.validator).is_absolute() else Path(a.validator)
    if not vpath.exists():
        print(f'✘ المدقق غير موجود: {vpath}')
        return 2

    mod = load_module(vpath)
    profile = Path(getattr(mod, 'PROFILE'))
    frozen = Path(getattr(mod, 'FROZEN_CSS'))
    current = mod.current_print_css()
    if not current.strip():
        print('✘ لم يُقرأ نمط الطباعة من المصدر — تحقق من --source ومن وجود @media print')
        return 2

    new_hash = sha16(current)
    old_hash = sha16(frozen.read_text(encoding='utf-8')) if frozen.exists() else '—'
    print(f'  النمط المقفل: {old_hash}')
    print(f'  النمط الحالي: {new_hash}')
    if old_hash == new_hash:
        print('  ✓ مطابق — لا حاجة إلى تجميد')
        return 0

    prof = json.loads(profile.read_text(encoding='utf-8')) if profile.exists() else {}
    approved = a.approved_by or prof.get('approved_by') or 'المالك'
    entry = {
        'date': dt.date.today().isoformat(),
        'change': f'تصحيح نمط الطباعة من {old_hash} إلى {new_hash}: {a.reason}',
        'evidence': a.evidence,
        'approved_by': approved,
    }
    if a.dry_run:
        print('  (تجربة بلا كتابة) سجل التغيير المقترح:')
        print('   ', json.dumps(entry, ensure_ascii=False)[:400])
        return 0

    frozen.parent.mkdir(parents=True, exist_ok=True)
    frozen.write_text(current, encoding='utf-8')
    prof.setdefault('changes', []).append(entry)
    prof['print_css_sha16'] = new_hash
    profile.write_text(json.dumps(prof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'  ✔ جُمّد النمط الجديد {new_hash} وأُضيف سجل تغيير إلى {profile.name}')
    print('  ↳ أكّد الآن بتشغيل المدقق: python3 ' + str(vpath.relative_to(brain)) +
          ' --pdf <pdf>')
    return 0


if __name__ == '__main__':
    sys.exit(main())