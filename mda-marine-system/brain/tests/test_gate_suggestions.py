"""حاجز: لا تقترح بوابة اقتراحات تخصها ألفاظًا تحظرها قوائم المالك.
السبب الجذري (ك-XXX): بوابة الفهم اقترحت «لم يُحسم بعد» وهو لفظ ممنوع في السجل
الحاكم، فصار كل إصلاح أسلوبي يولّد مانعًا في بوابة العيوب.
"""
import json, sys
from pathlib import Path
B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B / "validators"))
import importlib.util
spec = importlib.util.spec_from_file_location("comp", B / "validators" / "check_comprehension.py")
comp = importlib.util.module_from_spec(spec); spec.loader.exec_module(comp)
banned = {e.get("term") for e in json.loads((B / "appendices" / "forbidden-coinages.json").read_text(encoding="utf-8")).get("entries", [])}
bad = [(t, r) for t, r in comp.AMBIGUOUS.items() if r in banned]
print(f"  اقتراحات بوابة الفهم: {len(comp.AMBIGUOUS)} · متعارضة مع الممنوع: {len(bad)}")
for t, r in bad:
    print(f"    ✘ «{t}» → «{r}» (ممنوع)")
raise SystemExit(1 if bad else 0)
