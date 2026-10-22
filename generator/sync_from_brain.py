#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تحديث الموقع الدائم من مخرجات Brain اليومية.

الاستخدام:
  python3 generator/sync_from_brain.py --date 2026-10-12 [--brain $BRAIN_DIR]

ما يفعله بالترتيب:
1. ينسخ تقرير اليوم وملف واجهته من مساحة Brain إلى مصادر الموقع.
2. يحدّث دفتر الأحداث التراكمي إن وُجد أحدث منه.
3. يعيد بناء الموقع كاملًا (dist/) عبر build_site.py.
4. يطبع ملخصًا للنتيجة وحالة الروابط الداخلية.

لا ينشر ولا يرفع: النشر يبقى خطوة منفصلة عبر مشروع الاستضافة.
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
BRAIN = _tree("BRAIN_DIR", _ROOT, "brain-marine-news", "brain")

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent



def copy_section_policy(src_brain, dst_sources):
    """نسخ سياسة الأقسام إلى بيانات الموقع: مصدر واحد يقرأه المولّد والبوابات."""
    f = Path(src_brain) / 'appendices' / 'report-sections-policy.json'
    if f.is_file():
        Path(dst_sources).mkdir(parents=True, exist_ok=True)
        (Path(dst_sources) / 'report-sections-policy.json').write_text(
            f.read_text(encoding='utf-8'), encoding='utf-8')
        return True
    return False


def copy_sources(date_iso: str, brain: Path) -> list:
    log = []
    src_md = brain / "reports" / f"{date_iso}-sectioned.md"
    src_meta = brain / "web" / "meta" / f"{date_iso}.json"
    dst_md = SITE / "sources" / "reports" / f"{date_iso}-sectioned.md"
    dst_meta = SITE / "sources" / "meta" / f"{date_iso}.json"

    if src_md.exists():
        shutil.copy2(src_md, dst_md)
        log.append(f"نُسخ التقرير: {dst_md.name} ({dst_md.stat().st_size} بايت)")
    else:
        log.append(f"تحذير: تقرير اليوم غير موجود: {src_md}")

    if src_meta.exists():
        try:
            json.loads(src_meta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log.append(f"خطأ: ملف الواجهة ليس JSON صالحًا ({e}) — لم يُنسخ")
            return log
        shutil.copy2(src_meta, dst_meta)
        log.append(f"نُسخ ملف الواجهة: {dst_meta.name}")
    else:
        log.append(f"تحذير: ملف واجهة اليوم غير موجود: {src_meta}")

    ledger_candidates = sorted((brain / "cumulative-2026").glob("event-ledger*.json"))
    if ledger_candidates:
        newest = max(ledger_candidates, key=lambda p: p.stat().st_mtime)
        shutil.copy2(newest, SITE / "sources" / "ledger.json")
        log.append(f"حُدّث دفتر الأحداث: {newest.name}")

    cum_md = sorted((brain / "cumulative-2026").glob("*تراكمي*.md"))
    if cum_md:
        newest = max(cum_md, key=lambda p: p.stat().st_mtime)
        shutil.copy2(newest, SITE / "sources" / "reports" / "cumulative.md")
        log.append(f"حُدّث السجل التراكمي: {newest.name}")
    # صفحة «المصادر والمراجع»: سجل الموثوقية + أحدث فحص للتغذيات
    rel = brain / "appendices" / "source-reliability-40.md"
    if rel.exists():
        shutil.copy2(rel, SITE / "sources" / "source-reliability.md")
        _n = 0
        try:
            _n = int(json.loads((brain / "appendices" / "sources-manifest.json")
                                .read_text(encoding="utf-8"))["approved_source_count"])
        except Exception:
            _n = 0
        log.append(f"حُدّث سجل الموثوقية والمصداقية ({_n or '؟'} مصدرًا — من ملف المصدر الواحد)")

    # تشخيص المصادر (أداة tools/diagnose_sources.py) — أحدث ملف يُنسخ للموقع
    diag_files = sorted((brain / 'docs').glob('source-diagnosis-*.json'))
    if diag_files:
        shutil.copy2(diag_files[-1], SITE / 'sources' / 'source-diagnosis.json')
        log.append(f"حُدّث تشخيص المصادر ({diag_files[-1].name})")
    else:
        log.append("تحذير: سجل الموثوقية غير موجود")
    statuses = sorted((brain / "feeds").glob("feeds-*.status.json"))
    if statuses:
        newest = max(statuses, key=lambda x: x.stat().st_mtime)
        try:
            data = json.loads(newest.read_text(encoding="utf-8"))
            data.setdefault("date", newest.name.replace("feeds-", "").replace(".status.json", ""))
            (SITE / "sources" / "feeds-status.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            log.append(f"حُدّثت حالة التغذيات: {newest.name}")
        except Exception as e:
            log.append(f"تحذير: تعذّرت قراءة حالة التغذيات ({e})")
    else:
        log.append("تحذير: لا ملف حالة تغذيات")
    return log

# ---------------------------------------------------------------------------
# التقارير الخاصة: نسخ تلقائي + توليد بيانات واجهة عند غيابها
# ---------------------------------------------------------------------------
def auto_meta(md_path: Path) -> dict:
    """يستخرج بيانات الواجهة من ترويسة التقرير الخاص: العنوان، الرقم، التاريخ، التصنيف، الملخص."""
    text = md_path.read_text(encoding="utf-8")
    title = ""
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    if m:
        title = re.sub(r"^تقرير\s*[—\-:]\s*", "", m.group(1).strip())

    def field(name):
        mm = re.search(rf"\*\*{name}:\*\*\s*(.+?)\s*$", text, flags=re.M)
        return mm.group(1).strip() if mm else ""

    code = field("الرقم المرجعي")
    cls = field("التصنيف") or "عام"
    date_raw = field("التاريخ")
    iso = ""
    md_date = re.search(r"(\d{4}-\d{2}-\d{2})", md_path.name)
    if md_date:
        iso = md_date.group(1)
    elif date_raw:
        dm = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_raw)
        if dm:
            iso = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"

    body = re.sub(r"^#.*$", "", text, flags=re.M)
    paras = [p.strip() for p in body.split("\n")
             if p.strip() and not p.strip().startswith(("|", "#", "**جدول", "---"))]
    summary = ""
    for p in paras:
        if len(p) > 60:
            summary = re.sub(r"^\d+\.\s*", "", p)
            break

    return {
        "kind": "special",
        "title": title or md_path.stem,
        "headline": title or md_path.stem,
        "code": code,
        "date": iso,
        "classification": cls,
        "summary": summary,
        "lede": summary,
        "notice": "تقرير خاص مستقل عن الإصدار اليومي. يعتمد على المصادر المعلنة فقط، ولا يُنسب أي فعل إلى جهة إلا بسند رسمي معلن.",
        "footer_note": "تقرير خاص — مركز الوعي بالمجال البحري. التوقيت المعتمد مزدوج: UTC وتوقيت البحرين (UTC+3).",
    }


def sync_special(brain: Path) -> list:
    """ينسخ تقارير Brain الخاصة إلى مصادر الموقع تلقائيًا مع كل تشغيل."""
    log = []
    src_dir = brain / "reports"
    dst_dir = SITE / "sources" / "special"
    if not src_dir.exists():
        return log
    dst_dir.mkdir(parents=True, exist_ok=True)
    for md in sorted(src_dir.glob("special-*.md")):
        stem = re.sub(r"^special-", "", md.stem)
        stem = re.sub(r"-MACR$", "", stem)  # نسخة MACR هي المعتمدة للنشر
        dst_md = dst_dir / f"{stem}.md"
        if dst_md.exists() and dst_md.stat().st_mtime >= md.stat().st_mtime:
            continue
        shutil.copy2(md, dst_md)
        log.append(f"تقرير خاص نُسخ: {dst_md.name}")
        meta_path = dst_dir / f"{stem}.json"
        if not meta_path.exists():
            meta_path.write_text(
                json.dumps(auto_meta(md), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log.append(f"وُلّدت بيانات الواجهة تلقائيًا: {meta_path.name} (راجعها إن أردت تحسين الملخص)")
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="تاريخ التقرير YYYY-MM-DD")
    ap.add_argument("--brain", default=f"{BRAIN}")
    ap.add_argument("--skip-build", action="store_true")
    a = ap.parse_args()

    brain = Path(a.brain).resolve()
    copy_section_policy(brain, _ROOT / 'sources')
    for line in copy_sources(a.date, brain):
        print(line)
    for line in sync_special(brain):
        print(line)

    if a.skip_build:
        return 0
    r = subprocess.run([sys.executable, str(HERE / "build_site.py"), "--check"],
                       cwd=str(SITE), capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip(), file=sys.stderr)
        return r.returncode
    pages = sorted((SITE / "dist").rglob("*.html"))
    print(f"جاهز للنشر: {len(pages)} صفحة · " + " · ".join(p.name for p in pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
