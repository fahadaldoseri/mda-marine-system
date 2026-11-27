"""_name_en يحفظ أرقام الاسم العربي غير المسجّل كي لا يختل تطابق الأرقام في الأصل الإنجليزي."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import source_counts as sc  # noqa: E402


def test_unknown_arabic_name_keeps_digits():
    assert sc._name_en("مصدر مجهول 2026") == "Arabic-language source (2026)"


def test_unknown_arabic_name_without_digits_unchanged():
    assert sc._name_en("مصدر مجهول") == "Arabic-language source"


def test_known_name_mapped():
    assert sc._name_en("قناة العربية") == "Al Arabiya channel"
