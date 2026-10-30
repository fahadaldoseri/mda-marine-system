#!/usr/bin/env python3
"""بوابة أمنية (ك-338): لا سرّ غير منقّح في شجرة المستودع.

السبب: أداة مزامنة يدوية نسخت ملفات تلغرام من الخادم إلى المرآة وأدخلت معرّفًا غير منقّح
إلى التاريخ. أدوات المشروع تستثني هذه المسارات (`tools/sync_to_repo.py`)، لكن لا شيء كان
يتحقق من المرآة بعد المزامنة. هذه البوابة تفحص الملفات المتتبَّعة في المرآة وتفشل مغلقًا
إذا وجدت نمط سرّ، بلا طباعة أي قيمة.

الاستعمال: python3 validators/check_repo_secrets.py [--repo /home/ubuntu/mda-marine-system]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

# مسارات يجب أن تبقى منقّحة في المستودع
GUARDED = (
    "brain/appendices/telegram-chat.json",
    "brain/appendices/telegram-targets.json",
    "brain/appendices/telegram-subscriptions.json",
)

PATTERNS = (
    ("توكن بوت", re.compile(r"\b\d{8,}:[A-Za-z0-9_-]{30,}\b")),
    ("مفتاح طويل", re.compile(r"\b(sk|pk|ghp|gho|xox[baprs])[-_][A-Za-z0-9_-]{20,}\b")),
    ("معرّف دردشة", re.compile(r'"?(chat_id|chatId|target)"?\s*[:=]\s*"?-?\d{8,}"?')),
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/home/ubuntu/mda-marine-system")
    a = ap.parse_args()
    repo = pathlib.Path(a.repo)
    if not (repo / ".git").exists():
        print(f"✗ ليس مستودعًا: {repo}")
        return 2
    try:
        tracked = subprocess.run(["git", "-C", str(repo), "ls-files"],
                                 capture_output=True, text=True, check=True).stdout.split()
    except Exception as exc:  # pragma: no cover
        print(f"✗ تعذّر سرد الملفات: {exc}")
        return 2
    bad: list[tuple[str, str]] = []
    for rel in tracked:
        if not rel.startswith("brain/"):
            continue
        # مخزن الأسرار المعتمد بقرار المالك (طلب الدمج #3): نصّ صريح في المستودع الخاص
        if rel.startswith("brain/secrets/"):
            continue
        p = repo / rel
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        guarded = any(rel.endswith(g.split("/", 1)[1]) for g in GUARDED)
        for label, rx in PATTERNS:
            if not rx.search(txt):
                continue
            # الملفات المحروسة: أي تطابق يعني قيمة غير منقّحة
            if guarded or label != "معرّف دردشة":
                bad.append((rel, label))
                break
    if bad:
        print("✗ منع: قيم غير منقّحة في شجرة المستودع")
        for rel, label in bad:
            print(f"   - {rel} · {label}")
        print("   الإصلاح: استعد النسخة المنقّحة ولا تنسخ مسارات الأسرار إلى المرآة.")
        return 2
    print(f"✔ لا قيم غير منقّحة في {len([r for r in tracked if r.startswith('brain/')])} ملفًا متتبَّعًا")
    return 0


if __name__ == "__main__":
    sys.exit(main())