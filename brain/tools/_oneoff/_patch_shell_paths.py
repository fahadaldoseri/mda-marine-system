#!/usr/bin/env python3
"""تثبيت المسارات المحمولة في ملفات الشل الستة (تنفيذ دقيق، مع تحقق)."""
from pathlib import Path
import subprocess
import sys

T = Path('/home/ubuntu/brain-marine-news/tools')
PATCHES = {
    'daily_pipeline.sh': [
        ('B=/home/ubuntu/brain-marine-news\nSITE=/home/ubuntu/seawatch',
         'B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"\n'
         'SITE="${SITE_DIR:-$(dirname "$B")/seawatch}"'),
        ('"$S_LLM" "$NOTE_LLM" <<\'PY\'', '"$S_LLM" "$NOTE_LLM" "$B" <<\'PY\''),
        ('mark, d, f, o, a, l, no, na, nl, man, sl, nlm = sys.argv[1:13]\nB = Path(\'/home/ubuntu/brain-marine-news\')',
         'mark, d, f, o, a, l, no, na, nl, man, sl, nlm, b = sys.argv[1:14]\nB = Path(b)'),
    ],
    'final_gate.sh': [
        ('B=/home/ubuntu/brain-marine-news\nSITE=/home/ubuntu/seawatch',
         'B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"\n'
         'SITE="${SITE_DIR:-$(dirname "$B")/seawatch}"'),
        ('python3 - "$D" "$WORST" "$LOGDIR" <<\'PY\'', 'python3 - "$D" "$WORST" "$LOGDIR" "$B" <<\'PY\''),
        ("d, worst, logdir = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])\nB = Path('/home/ubuntu/brain-marine-news')",
         'd, worst, logdir = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])\nB = Path(sys.argv[4])'),
    ],
    'ensure_devserver.sh': [
        ('DIST=/home/ubuntu/seawatch/dist\nLOG=/home/ubuntu/brain-marine-news/logs/devserver-$P.log\nmkdir -p /home/ubuntu/brain-marine-news/logs',
         'B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"\n'
         'SITE="${SITE_DIR:-$(dirname "$B")/seawatch}"\n'
         'DIST="$SITE/dist"\nLOG="$B/logs/devserver-$P.log"\nmkdir -p "$B/logs"'),
    ],
    'sync_backup.sh': [
        ('SRC="${1:-/home/ubuntu/brain-marine-news}"\nDST="${2:-/home/ubuntu/seawatch/brain-backup}"',
         '_B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"\n'
         '_S="${SITE_DIR:-$(dirname "$_B")/seawatch}"\n'
         'SRC="${1:-$_B}"\nDST="${2:-$_S/brain-backup}"'),
    ],
    'github_backup.sh': [
        ('B="/home/ubuntu/brain-marine-news"\nREPO="/home/ubuntu/mda-marine-system"',
         'B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"\n'
         'REPO="${BACKUP_REPO_DIR:-$(dirname "$B")/mda-marine-system}"'),
    ],
    'install_macr_skill.sh': [
        ('KEEP=/home/ubuntu/brain-marine-news/skills/macr-system\nDEST=/home/ubuntu/skills/macr-system',
         'B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"\n'
         'SKILLS_HOME="${SKILLS_HOME:-$(dirname "$B")}"\n'
         'KEEP="$B/skills/macr-system"\nDEST="$SKILLS_HOME/skills/macr-system"'),
    ],
}

ok = True
for name, pairs in PATCHES.items():
    p = T / name
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if old not in s:
            print(f'  ✘ {name}: لم يُعثر على المقطع المطلوب')
            ok = False
            continue
        s = s.replace(old, new, 1)
    p.write_text(s, encoding='utf-8')
    r = subprocess.run(['bash', '-n', str(p)], capture_output=True, text=True)
    print(f'  {"✔" if r.returncode == 0 else "✘"} {name} — صياغة {"سليمة" if r.returncode == 0 else r.stderr.strip()[:60]}')
    if r.returncode:
        ok = False

print('\nالنتيجة:', 'كل ملفات الشل سليمة' if ok else 'توجد مشكلات')
sys.exit(0 if ok else 1)