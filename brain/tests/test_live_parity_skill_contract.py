#!/usr/bin/env python3
"""عقد مهارة استئناف الخطوة إلى المزامنة الحية (rerun-step-to-live-parity-ops).

يفحص ما يجعل المهارة معتمدة لا مكتوبة:
1) موجودة على الأسطح الثلاثة ببصمة واحدة.
2) بنيتها المعلنة موجودة (الأقسام + الأداة + المرجع).
3) أداة القياس تعمل: موجب (تطابق) · سالب (اختلاف حجم) · سالب (تعذّر الوصول).
4) المرجع لا ينحرف عن سياسة الاشتقاق الفعلية في المولّد.

كل الحالات تعمل بلا شبكة (روابط file://) لتصلح بوابةً داخل الكتيب.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

BRAIN = pathlib.Path(__file__).resolve().parents[1]
NAME = 'rerun-step-to-live-parity-ops'
SURFACES = [BRAIN / 'skills' / NAME, pathlib.Path('/home/ubuntu/skills') / NAME, BRAIN.parent / 'skills' / NAME]
TOOL = BRAIN / 'skills' / NAME / 'scripts' / 'live_parity.py'
REF = BRAIN / 'skills' / NAME / 'references' / 'closure-evidence-contract.md'
REQUIRED_SECTIONS = ['الحدود', 'المسار السبعي', 'القياس الحي', 'عقد الدليل والإغلاق', 'حلقة تعلّم ذاتي']
policy_keys = ('قاعدة_الإصلاح', 'قاعدة_التحقق', 'قاعدة_الحاجز', 'قاعدة_التشغيلية')

fails: list[str] = []


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_surfaces() -> None:
    for s in SURFACES:
        if not (s / 'SKILL.md').is_file():
            fails.append(f'سطح مفقود: {s}')
    present = [s for s in SURFACES if (s / 'SKILL.md').is_file()]
    if len(present) == len(SURFACES):
        digests = {sha(s / 'SKILL.md') for s in SURFACES}
        if len(digests) != 1:
            fails.append('SKILL.md غير متطابق بين الأسطح')
        for f in ('scripts/live_parity.py', 'references/closure-evidence-contract.md'):
            ds = {sha(s / f) for s in SURFACES if (s / f).is_file()}
            if len(ds) != 1:
                fails.append(f'{f} غير متطابق بين الأسطح')
    if not TOOL.is_file():
        fails.append('أداة القياس مفقودة')
    if not REF.is_file():
        fails.append('مرجع عقد الدليل مفقود')


def check_structure() -> None:
    body = (BRAIN / 'skills' / NAME / 'SKILL.md').read_text(encoding='utf-8')
    for sec in REQUIRED_SECTIONS:
        if sec not in body:
            fails.append(f'قسم مفقود في SKILL.md: {sec}')
    if 'live_parity.py' not in body or 'closure-evidence-contract.md' not in body:
        fails.append('SKILL.md لا يشير إلى أداته أو مرجعه')


def run_tool(args: list[str]) -> int:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True).returncode


def check_tool() -> None:
    if not TOOL.is_file():
        return
    if run_tool(['--help']) != 0:
        fails.append('أداة القياس: --help لا يعمل')
    same = BRIAN_FIXTURE
    if run_tool(['--url', same.as_uri(), '--local', str(same), '--min-bytes', '1', '--expect-html']) != 0:
        fails.append('حالة موجبة فشلت: الملف نفسه يجب أن يُحكم «مطابق»')
    other = TMP / 'other.html'
    other.write_text('<html><body>مغاير</body></html>\n', encoding='utf-8')
    if run_tool(['--url', same.as_uri(), '--local', str(other)]) != 2:
        fails.append('حالة سالبة فشلت: ملف محلي مغاير يجب أن يُحكم «مختلف» برمز 2')
    if run_tool(['--url', (TMP / 'لا-يوجد.html').as_uri()]) != 3:
        fails.append('حالة سالبة فشلت: رابط غير متاح يجب أن يُرجع رمز 3')


def check_reference_against_policy() -> None:
    """المرجع يوثّق نفس مفردات الاشتقاق الفعلية في المولّد — منع انحراف الوثيقة عن الشيفرة."""
    sys.path.insert(0, str(BRAIN / 'tools'))
    import closure_round as cr                                    # noqa: PLC0415
    ref = REF.read_text(encoding='utf-8')
    for k in policy_keys:
        if k not in cr.POLICY:
            fails.append(f'سياسة المولّد لا تحمل المفتاح: {k}')
        if k not in ref:
            fails.append(f'المرجع لا يوثّق مفتاح السياسة: {k}')
    for kw in ('بوابة', 'اختبار', 'حارس', 'قاعدة', 'check_', 'فحص', 'قياس'):
        if kw not in ref:
            fails.append(f'المرجع لا يذكر مفردة حاجز معلنة: {kw}')
    if 'rc=0' not in ref:
        fails.append('المرجع لا يوثّق نمط الدليل (rc=0)')


if __name__ == '__main__':
    import tempfile
    TMP = pathlib.Path(tempfile.mkdtemp(prefix='parity-skill-'))
    BRIAN_FIXTURE = TMP / 'page.html'
    BRIAN_FIXTURE.write_text('<html><body>صفحة قياس</body></html>\n', encoding='utf-8')
    check_surfaces()
    check_structure()
    check_tool()
    check_reference_against_policy()
    if fails:
        print('✘ عقد مهارة القياس الحي:')
        for f in fails:
            print(f'   - {f}')
        sys.exit(2)
    print('✔ عقد مهارة القياس الحي: الأسطح متطابقة · البنية معلنة · الأداة موجب وسالب · المرجع مطابق للسياسة')
