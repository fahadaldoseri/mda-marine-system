#!/usr/bin/env python3
"""مراجعة 23 أكتوبر 2026 — الجولة الثالثة: أولًا (الاختبارات تمنع) وثالثًا-2 (اختبار الحارس) وثالثًا-6."""
import ast
import re
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')

# ── ثالثًا-2: اختبار ربط الحارس بتحليل الشيفرة (ast) بدل البحث النصي
p = B / 'tests/test_review2.sh'
s = p.read_text(encoding='utf-8')
start = s.index('echo "── (ب)')
end = s.index('echo "── (د)')
new_block = '''echo "── (ب) ربط الحارس الموحّد: تحليل شيفرة (ast) لا بحث نصي"
python3 - <<'PY'
import ast, sys
from pathlib import Path
bad, good = [], 0
for p in sorted(Path('validators').glob('*.py')):
    if p.name == '_guard.py':
        continue
    src = p.read_text(encoding='utf-8')
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        bad.append(f"{p.name}: خطأ صياغة {e}"); continue
    if not any(isinstance(n, ast.If) and "__main__" in ast.dump(n.test) for n in tree.body):
        continue                                    # لا كتلة تنفيذ: لا يُشترط
    ok = False
    for n in tree.body:
        if not (isinstance(n, ast.If) and "__main__" in ast.dump(n.test)):
            continue
        for sub in ast.walk(n):
            # استيراد run من _guard فعلًا
            if isinstance(sub, ast.ImportFrom) and (sub.module or '').endswith('_guard'):
                if any(a.name == 'run' for a in sub.names):
                    # ثم نداء run(...) داخل الكتلة
                    ok = any(isinstance(c, ast.Call) and getattr(c.func, 'id', '') == 'run'
                             for c in ast.walk(n))
    if ok:
        good += 1
    else:
        bad.append(f"{p.name}: كتلة التنفيذ لا تستدعي run من _guard فعليًا")
print('مخالفات:', bad)
print(f'ملفات موصولة فعليًا: {good}')
sys.exit(1 if bad else 0)
PY
if [ $? -ne 0 ]; then bad "ملف مدقق غير موصول بالحارس"; else ok "كل المدققات موصولة بالحارس (ast)"; fi
# إثبات أن الاختبار يكشف ملفًا غير موصول (حالة مصطنعة) + ملفًا يذكر الحارس في تعليق فقط
cat > validators/_tmp_nowire.py <<'PY'
#!/usr/bin/env python3
# سنربطه بـ _guard لاحقًا (تعليق لا يستدعي الحارس)
import sys
def main():
    return 0
if __name__ == "__main__":
    sys.exit(main())
PY
python3 - <<'PY'
import ast, sys
from pathlib import Path
src = Path('validators/_tmp_nowire.py').read_text(encoding='utf-8')
tree = ast.parse(src)
ok = False
for n in tree.body:
    if isinstance(n, ast.If) and "__main__" in ast.dump(n.test):
        for sub in ast.walk(n):
            if isinstance(sub, ast.ImportFrom) and (sub.module or '').endswith('_guard') \\
               and any(a.name == 'run' for a in sub.names):
                ok = any(isinstance(c, ast.Call) and getattr(c.func, 'id', '') == 'run' for c in ast.walk(n))
print('  · الحالة المصطنعة (تعليق فقط):', 'كُشفت ✘' if not ok else 'مرّت خطأً')
sys.exit(0 if not ok else 2)
PY
if [ $? -eq 0 ]; then ok "الاختبار يكشف التعليق الكاذب (استيراد لم يحدث)"; else bad "الاختبار لم يكشف التعليق الكاذب"; fi
rm -f validators/_tmp_nowire.py

'''
s = s[:start] + new_block + s[end:]
s = s.replace("print(f\"  ✔ {f.name}: التغيير المسموح الوحيد (ةة) — {diff} موضعًا\")",
              "print(f\"  ✔ {f.name}: {diff} تغييرًا مطابقًا للقواعد المعلنة فقط\")")
p.write_text(s, encoding='utf-8')
print("  ✔ test_review2.sh: اختبار الربط بتحليل الشيفرة (ast) + حالتان مصطنعتان")

# ── أولًا: step_strict — أي رمز غير صفري في خطوات الاختبار يمنع
p = B / 'tools/final_gate.sh'
g = p.read_text(encoding='utf-8')
g = g.replace('''  elif [ "$rc" -ge "$blockrc" ]; then status="block"; WORST=2''',
'''  elif [ "${STRICT:-0}" -eq 1 ] && [ "$rc" -ne 0 ]; then
    # مراجعة 23 أكتوبر 2026 (أولًا): أي خطوة اختبار تمنع عند أي رمز غير صفري
    status="block"; WORST=2
  elif [ "$rc" -ge "$blockrc" ]; then status="block"; WORST=2''')
g = g.replace('step "اختبارات البوابات (tests)" 2 bash "$B/tests/run_checks.sh"',
              'step_strict "اختبارات البوابات (tests)" bash "$B/tests/run_checks.sh"')
g = g.replace('step "اختبارات المراجعة الثانية (أ · ب · ج · د · هـ · ز)" 2 bash "$B/tests/test_review2.sh" "$D"',
              'step_strict "اختبارات المراجعة الثانية (أ · ب · ج · د · هـ · ز)" bash "$B/tests/test_review2.sh" "$D"\nstep_strict "اختبار انحدار المصلح (12→23)" bash "$B/tests/test_repair_regression.sh"')
if 'step_strict() {' not in g:
    anchor = 'step() {            #'
    g = g.replace(anchor, '''step_strict() {     # خطوة اختبار: أي فشل يمنع (مراجعة 23 أكتوبر 2026، أولًا)
  local name="$1"; shift
  STRICT=1 step "$name" 1 "$@"
}

step() {            #''', 1)
p.write_text(g, encoding='utf-8')
print("  ✔ final_gate.sh: step_strict · خطوات الاختبار تمنع عند أي رمز غير صفري")

# ── ثالثًا-1/6: استثناءات الفحص القبلي: نُصلح الضارّة ونُصنّف المُغلِقة
p = B / 'tools/preflight_check.py'
t = p.read_text(encoding='utf-8')
t = t.replace('''except Exception:
    helper = ''uite''', '')  # لا شيء
t = t.replace('''    helper = subprocess.run(['git', '-C', str(GEN.parent), 'config', '--get', 'credential.helper'],
                            capture_output=True, text=True).stdout.strip()
except Exception:
    helper = \'\'''',
'''    helper = subprocess.run(['git', '-C', str(GEN.parent), 'config', '--get', 'credential.helper'],
                            capture_output=True, text=True).stdout.strip()
except (subprocess.SubprocessError, OSError) as e:
    # لا ابتلاع: تعذّر قراءة مساعد الاعتماد يعني أننا لا نعرف كيف يُعتمد الدفع ⇒ مانع
    helper = ''
    fails.append(f"تعذّر قراءة مساعد اعتماد الدفع: {type(e).__name__}")''')
t = t.replace('''        for df in (B / 'cumulative-2026' / 'daily').glob('*.json'):
            try:
                for ev in json.loads(df.read_text(encoding='utf-8')):
                    if ev.get('date'):
                        ev_dates.append(ev['date'])
            except Exception:
                pass''',
'''        for df in (B / 'cumulative-2026' / 'daily').glob('*.json'):
            try:
                for ev in json.loads(df.read_text(encoding='utf-8')):
                    if ev.get('date'):
                        ev_dates.append(ev['date'])
            except (json.JSONDecodeError, OSError, TypeError, AttributeError) as e:
                # ملف يوم غير مقروء = الدفتر لا يُثبت تغطيته ⇒ مانع (لا تخطٍّ صامت)
                fails.append(f"ملف يوم غير مقروء ({df.name}): {type(e).__name__}")''')
p.write_text(t, encoding='utf-8')
ast.parse(t)
print("  ✔ preflight_check.py: الاستثناءان الضارّان → فشل مغلق بنطاق ضيّق")
print("  · المتبقي (مغلِق أصلًا):", [f"{i}:{l.strip()[:40]}" for i, l in enumerate(t.splitlines(), 1)
                                    if l.strip().startswith('except Exception')])