import sys, json, pathlib, io, contextlib
root = pathlib.Path(sys.argv[1]); sys.path.insert(0, str(root / "tools"))
import classify_zones as cz
reg, scale, levels, ovr = cz.load_governed()
out = {}
for p in sorted((root / "cumulative-2026/daily").glob("2026-*.json")):
    d = p.stem
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = cz.classify_day(d, reg, scale, levels, ovr, carry=False)
        out[d] = {"overall": r["overall"]["level"], **{z["id"]: [z["level"], z["confirmed"]] for z in r["zones"]}}
    except Exception as e:
        out[d] = {"error": f"{type(e).__name__}: {e}"[:120]}
json.dump(out, sys.stdout, ensure_ascii=False, indent=0, sort_keys=True)
