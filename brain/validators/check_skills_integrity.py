#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مدقق سلامة المهارات — يمنع ضياع القواعد المعتمدة.

الأساس (عطل ك-48): أُعيدت ملفات المهارتين إلى نسخة أقدم ففُقدت قواعد اعتمدها
صاحب القرار، ثم نسخت أداة النسخ الاحتياطي النسخة الناقصة إلى المستودع، فانتشر
الفقد بصمت. القاعدة المانعة: كل قاعدة معتمدة تحمل شاهدًا نصيًا يُفحص قبل الدفع،
وما نقص يُستعاد من المستودع لا يُدفع فوقه.

الرمز: 0 سليم · 2 فقد قاعدة معتمدة
"""
from __future__ import annotations
import sys
from pathlib import Path

def _skills_dir(brain: Path) -> Path:
    """مجلد المهارات: SKILLS_DIR ← مسار الخادم إن وُجد ← skills/ في جذر المستودع (محمول)."""
    import os
    if os.environ.get("SKILLS_DIR"):
        return Path(os.environ["SKILLS_DIR"])
    if Path("/home/ubuntu/skills").is_dir():
        return Path("/home/ubuntu/skills")
    return brain.parent / "skills"

SK = _skills_dir(Path(__file__).resolve().parent.parent)
REPO = Path(__import__("os").environ.get("BACKUP_REPO_DIR") or Path(__file__).resolve().parent.parent.parent) / "skills"

# شواهد إلزامية: (المسار النسبي، نص الشاهد، وصف القاعدة)
REQUIRED = [
    ("marine-news-brain/SKILL.md", "appendices/libraries/", "إلزام قراءة مكتبات المراجع"),
    ("marine-news-brain/SKILL.md", "لا يُستخدم رمز جديد قبل تعريفه", "لا رمز بلا تعريف"),
    ("marine-news-brain/SKILL.md", "check_carryover", "فاحص النقل قبل التسليم"),
    ("marine-news-brain/SKILL.md", "كل نص ثابت يظهر للقارئ", "مدى بوابة الأسلوب"),
    ("marine-news-brain/SKILL.md", "قياس الوحدة يُعلن مع الرقم", "وحدة القياس"),
    ("marine-news-brain/references/terminology.md", "#", "ملف المعجم"),
    ("marine-news-brain/references/validation.md", "#", "قواعد التحقق"),
    ("marine-news-brain/references/source-policy.md", "#", "سياسة المصادر"),
    ("marine-news-brain/references/adaptive-learning.md", "#", "التعلم التكيفي"),
    ("military-arabic-editing/SKILL.md", "ambiguity-map.md", "خريطة الالتباس مرجع دائم"),
    ("military-arabic-editing/SKILL.md", "الكلمة ذات المعنيين", "قاعدة الالتباس"),
    ("military-arabic-editing/SKILL.md", "الرسم الموحّد", "قاعدة الرسم الموحّد"),
    ("military-arabic-editing/references/ambiguity-map.md", "#", "خريطة الالتباس"),
    ("military-arabic-editing/references/terminology-map.md", "#", "خريطة الاستبدالات"),
    ("military-arabic-editing/references/commander-style.md", "#", "أسلوب القائد"),
    ("military-arabic-editing/references/adaptive-learning.md", "#", "التعلم التكيفي"),
]


def main() -> int:
    missing = []
    for rel, marker, desc in REQUIRED:
        f = SK / rel
        if not f.exists():
            missing.append((rel, desc, "الملف غير موجود"))
            continue
        if marker != "#" and marker not in f.read_text(encoding="utf-8"):
            missing.append((rel, desc, f"الشاهد غائب: «{marker}»"))
    print(f"=== سلامة المهارات — {len(REQUIRED)} شاهدًا ===")
    if not missing:
        print("  ✔ كل القواعد المعتمدة مثبتة")
        return 0
    for rel, desc, why in missing:
        print(f"  ✘ {rel} — {desc} — {why}")
    print(f"  عدد الشواهد الغائبة: {len(missing)} — مانع")
    if REPO.exists():
        print("  الاستعادة من المستودع: bash tools/restore_skills.sh")
    return 2


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
