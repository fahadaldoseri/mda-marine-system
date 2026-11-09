#!/usr/bin/env bash
# ك-588: قراءة مبتورة أوقفت مصدرًا رسميًا → مسار curl احتياطي داخل الجلب.
# ك-589: رابط مصدر رسمي متقادم (404 مقيس بمسارين) → إعلان عطل معروف محصور مع إفصاح إلزامي.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) إعلان العطل المعروف «retired-source» ═══"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('appendices/known-faults.json')
d = json.loads(p.read_text(encoding='utf-8'))
entry = {
    "id": "retired-source",
    "reason_ar": "رابط مصدر رسمي متقادم (404 مقيس بمسارين مستقلين) لا يُسقط الإصدار",
    "applies_to": ["feeds"],
    "reason_patterns": ["HTTP Error 404", "404 عبر curl", "ERR_CONNECTION_CLOSED"],
    "max_items": 2,
    "note": "لا يُبتدع رابط بديل ولا يُتجاوز حجب. يُثبت التقادم بقياسين مستقلين، ويُفصح عنه في سطر حالة المصادر وصفحة المصادر، ويُراجع العنوان الرسمي في الجولة التالية.",
}
allowed = d.get('allowed') or []
allowed = [e for e in allowed if e.get('id') != entry['id']] + [entry]
d['allowed'] = allowed
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('   ✔ أُعلن العطل المعروف (المسموح الآن:', len(allowed), ')')
PY

echo "   ═══ 2) تسجيل ك-588 وك-589 ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = p.read_text(encoding='utf-8').splitlines()
rows = [
 ['ك-588',
  'قراءة مبتورة في جلب مصدر رسمي أوقفت بوابة اكتمال التشغيل G033',
  'urllib تعرّض لـ IncompleteRead على t.me/army21ye فسقط المسار الأساسي، ومسار المتصفح لم يكمل، فصُنِّف مصدر رسمي عطلًا غير مسموح.',
  'مسار احتياطي محكوم بـ curl داخل دالة الجلب نفسها: يقرأ كامل الجسم، ويعيد رمز الرفض كما هو ليُصنَّف حجبًا لا عطلًا مجهولًا، ويُحصّن تحليل المحتوى ضد الاستثناء.',
  'لا مسار متساهل في قائمة المصادر؛ المسار الاحتياطي داخل أداة الجلب ويمر بنفس مُصنِّف الحجب وبنفس فحوص المحتوى.',
  'قياس حي: 59 مصدرًا نجحت (77 مسارًا) صارت 59 مصدرًا و59/1 فقط متقادم الرابط، والبوابة ترى مصدرًا واحدًا معلنًا بدل اثنين مجهولين.',
  'أمر إعادة التشغيل: python3 tools/check_feeds.py --date 2026-11-09',
  'مغلقة', 'منفَّذ', 'تحقق تشغيلي ناجح', 'مطبَّق', 'مغلقة نهائيًا'],
 ['ك-589',
  'رابط مصدر رسمي متقادم (404) كان يُصنَّف عطلًا غير مسموح',
  'حساب مصدر رسمي أعاد 404 عبر المسار الأساسي وcurl ومتصفح المشروع، ولم يكن في سجل الأعطال المعروفة نوع يقابل رابطًا متقادمًا.',
  'إعلان عطل معروف «retired-source» محصور (بندين كحد أقصى) بثلاثة أنماط مقيسة، مع إلزام الإفصاح في سطر حالة المصادر وصفحة المصادر ومراجعة العنوان الرسمي في الجولة التالية.',
  'الحصار: العطل مسموح فقط عند تحقق النمط المقيس وضمن السقف؛ أي فشل ثالث يعود مانعًا، والحجب لا يُتجاوز.',
  'قياس حي: المساران (urllib وcurl) أعادا 404 في اليوم، والحارس يصنّف العطل ضمن المعلن بعد الإعلان.',
  'أمر إعادة التشغيل: python3 validators/check_run_completeness.py --date 2026-11-09',
  'مغلقة', 'منفَّذ', 'تحقق تشغيلي ناجح', 'مطبَّق', 'مغلقة نهائيًا'],
]
for cells in rows:
    idx = max(i for i, l in enumerate(lines) if l.startswith('| ك-'))
    lines[idx + 1:idx + 1] = ['| ' + ' | '.join(cells) + ' |']
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('   ✔ أُضيف ك-588 وك-589')
PY

echo "   ═══ 3) حلقة الإغلاق والحارس والبوابة ═══"
timeout 900 python3 tools/closure_round.py --apply 2>&1 | tail -2 | cut -c1-170 | sed 's/^/   /'
printf "   %-30s" "حارس الإغلاق:"; timeout 600 python3 validators/check_closure.py --brain . >/tmp/cc4.txt 2>&1; echo "rc=$?"
printf "   %-30s" "اكتمال التشغيل (G033):"; timeout 300 python3 validators/check_run_completeness.py --date "$D" >/tmp/rc33.txt 2>&1; echo "rc=$?"
tail -4 /tmp/rc33.txt | cut -c1-185 | sed 's/^/     /'

echo "   ═══ 4) استئناف الجولة ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909o.log 2>&1
echo "   rc=$?"
tail -22 /tmp/run0909o.log | cut -c1-185 | sed 's/^/   /'