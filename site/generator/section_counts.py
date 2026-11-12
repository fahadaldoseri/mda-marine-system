"""مصدر واحد لعدّ بنود الأقسام — يُقرأ من متن التقرير المعتمد (ك-251)."""
import re
from pathlib import Path

import os
_P = Path(__file__).resolve()
_CAND = [_P.parents[i] for i in range(1, min(5, len(_P.parents)))]
def _brain_root() -> Path:
    """الجذر القانوني: env ثم mda-marine-system/brain ثم brain — والأرشيف مرفوض (ك-571)."""
    import sys as _sys
    _sys.path.insert(0, str(_P.parent))
    try:
        from brain_root import brain_root as _br  # noqa: E402
        return _br()
    except SystemExit:
        raise
    except Exception:
        env = os.environ.get("BRAIN_DIR")
        if env and Path(env).is_dir():
            return Path(env)
        for r in _CAND:
            c = r / "mda-marine-system" / "brain"
            if (c / "reports").is_dir():
                return c
        for r in _CAND:
            c = r / "brain"
            if (c / "reports").is_dir():
                return c
        return _CAND[0] / "mda-marine-system" / "brain"


BRAIN = _brain_root()

def counts(date: str) -> dict:
    if not date:
        cands = sorted(BRAIN.glob("reports/*-sectioned.md"))
        if not cands:
            return {}
        p = cands[-1]
    else:
        p = BRAIN / "reports" / f"{date}-sectioned.md"
    if not p.exists():
        return {}
    out, cur = {}, None
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1).strip(); out.setdefault(cur, 0); continue
        if cur and re.match(r"^\s*(?:[-*]|\d+[.)])\s+\S", line):
            out[cur] += 1
    return out

def for_title(date: str, *titles: str, default: int = 0) -> int:
    data = counts(date)
    for t in titles:
        for k, v in data.items():
            if t and t in k:
                return v
    return default
