#!/usr/bin/env bash
# إثبات B010: جدول التوزيع يُختار، وجدول مستوى التهديد لا يُعامل كخريطة.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SITE="${SITE_DIR:-$ROOT/../seawatch}"
SITE_DIR="$SITE" python3 "$ROOT/tests/test_geo_table_selection.py"
