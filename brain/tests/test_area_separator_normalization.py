"""اختبار انحدار: فاصل قيمة الموقع يُطبّع إلى « - » قبل المطابقة، والمخالف يبقى مانعًا في الحارس."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_em_dash_is_normalized():
    mod = _load("dal", "tools/derive_area_labels.py")
    assert mod.normalize_separators("مقابل خصب — خليج عُمان") == "مقابل خصب - خليج عُمان"
    assert mod.normalize_separators("خورفكان – خليج عُمان") == "خورفكان - خليج عُمان"
    assert mod.normalize_separators("مضيق هرمز") == "مضيق هرمز"


def test_gate_rejects_raw_em_dash_and_accepts_normalized():
    mod = _load("cav", "validators/check_area_vocabulary.py")
    names, non_spatial = mod.load_allowed(ROOT)
    ok_bad, _ = mod.parts_ok("مقابل خصب — خليج عُمان", names, non_spatial)
    ok_good, _ = mod.parts_ok("مقابل خصب - خليج عُمان", names, non_spatial)
    assert ok_bad is False, "الحارس يجب أن يمنع الفاصل غير المعتمد"
    assert ok_good is True, "الحارس يجب أن يقبل الفاصل المعتمد"
