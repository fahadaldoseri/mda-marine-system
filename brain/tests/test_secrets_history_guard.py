"""اختبارات حارس الأسرار: فلترة البدائل، استثناء المرجع العاري، وتزايد فحص التاريخ."""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "validators"))
import check_secrets as cs  # noqa: E402


def test_placeholder_is_not_a_secret():
    # يُبنى التوكن وقت التشغيل: لا يظهر أي نمط توكن حرفي في الشجرة (يحترم حارس التنقيح).
    fake = '1234567890' + ':' + 'A' * 35
    txt = f'TELEGRAM_BOT_TOKEN={fake}  # مثال بديل\n'
    assert cs.scan_text("x.env", txt, []) == [], "قيمة بديلة موسومة بـexample يجب ألا تُعدّ سرًّا"


def test_bare_internal_reference_in_doc_is_not_a_secret():
    txt = "علّق فقط للتعيين العاري مثل `token = _canonical_identifier_token`.\n"
    assert cs.scan_text("docs/plan.md", txt, []) == [], "المرجع الداخلي العاري ليس سرًّا في الوثائق"


def test_real_value_still_blocks():
    # القيمة تُبنى وقت التشغيل: لا تعيين حرفي في الشجرة (يحترم بوابة الأسرار).
    val = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"
    txt = 'API_KEY="' + val + '"\n'
    assert cs.scan_text("app.env", txt, []), "التعيين بقيمة فعلية يبقى مانعًا"


def test_history_scan_is_incremental_and_complete():
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
        (d / "a.txt").write_text("نص نظيف\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(d), "commit", "-qm", "نظيف"], check=True)
        (d / "b.txt").write_text('TOKEN="A1b2C3d4E5f6G7h8I9j0K1l2M3n4"\n', encoding="utf-8")
        subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(d), "commit", "-qm", "سرّ"], check=True)
        old_root, old_cur = cs.ROOT, cs.HISTORY_CURSOR
        try:
            cs.ROOT = d
            cs.HISTORY_CURSOR = "cursor.json"
            hits1, cov1, _ = cs.history_scan([], set(), 0.0, True)  # سقف صفر: يكتب المؤشر فقط
            assert hits1 == [], "بسقف صفر لا يُفحص التزام"
            assert (d / "cursor.json").is_file(), "المؤشر يُكتب دائمًا"
            hits2, cov2, _ = cs.history_scan([], set(), 60.0, False)
            assert hits2, "الفحص التزايدي يكتشف السرّ في الالتزام الثاني"
            assert cov2.split("/")[1] == "2", "عدد الالتزامات الكلي معروف"
        finally:
            cs.ROOT, cs.HISTORY_CURSOR = old_root, old_cur


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"   ✔ {name}")
    print("   كل اختبارات حارس الأسرار ناجحة")
