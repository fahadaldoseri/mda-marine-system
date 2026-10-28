#!/usr/bin/env bash
# يعيد تثبيت مهارة MACR المعتمدة (النسخة المرفقة 2026-10-15) بعد أي تزامن من المنصة.
set -e
B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SKILLS_HOME="${SKILLS_HOME:-$(dirname "$B")}"
KEEP="$B/skills/macr-system"
DEST="$SKILLS_HOME/skills/macr-system"
mkdir -p "$DEST"
cp -f "$KEEP/SKILL.md" "$DEST/SKILL.md"
cp -f "$KEEP"/fonts/*.ttf "$DEST/fonts/" 2>/dev/null || { mkdir -p "$DEST/fonts"; cp -f "$KEEP"/fonts/*.ttf "$DEST/fonts/"; }
mkdir -p ~/.fonts && cp -f "$KEEP"/fonts/*.ttf ~/.fonts/ && fc-cache -f >/dev/null 2>&1
echo "✔ أُعيد تثبيت مهارة MACR | $(wc -c < "$DEST/SKILL.md") بايت | خطوط: $(ls "$DEST/fonts" | tr '\n' ' ')"
