"""انحدار: معرّف الصف ذو اللاحقة لا يُنشئ مسارًا متداخلًا في سجل الدفعة."""
import importlib.util
import pathlib

BRAIN = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mbr', BRAIN / 'tools/measurement_batch_runner.py')
mbr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mbr)


def test_suffixed_id_has_no_separator():
    assert '/' not in mbr.safe_id('ك-93/ب')
    assert mbr.safe_id('ك-93/ب') == 'ك-93_ب'


def test_plain_id_unchanged():
    assert mbr.safe_id('ك-569') == 'ك-569'
