#!/usr/bin/env python3
"""Remove adjudicated copyright/watermark glyph runs from a map raster, then prove nothing
else moved. Mask = glyph strokes only (3 < highpass < 46), never a filled box.
Exit 0 = every preservation gate passed. Exit 2 = a gate failed or inputs are wrong."""
import argparse, json, os, sys
import numpy as np
import cv2


def hp_of(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return g - cv2.medianBlur(g.astype(np.uint8), 21).astype(np.float32)


def stroke_mask(hp, sites, tw, th, prot, halop):
    H, W = hp.shape
    mk = np.zeros((H, W), np.uint8)
    for x, y in sites:
        sub = hp[y:y + th, x:x + tw]
        sel = ((sub > 3.0) & (sub < 46)).astype(np.uint8) * 255
        sel = cv2.dilate(sel, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 7)))
        mk[y:y + th, x:x + tw] = np.maximum(mk[y:y + th, x:x + tw], sel)
    mk[prot > 0] = 0
    mk[halop > 0] = 0
    return mk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--sites", required=True, help="adjudicated mark origins: x,y;x,y;...")
    ap.add_argument("--template", required=True, help="x,y of one readable mark, for before/after scoring")
    ap.add_argument("--size", default="106x22")
    ap.add_argument("--passes", type=int, default=1, help="1 reproduces the accepted baseline; 2 lifts a little more glyph ink")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    tw, th = [int(v) for v in a.size.lower().split("x")]
    sites = [tuple(int(v) for v in s.split(",")) for s in a.sites.split(";") if s.strip()]
    tx, ty = [int(v) for v in a.template.split(",")]
    orig = cv2.imread(a.input)
    if orig is None:
        print(f"FAIL: cannot read {a.input}", file=sys.stderr); return 2
    if not sites:
        print("FAIL: no sites given", file=sys.stderr); return 2
    H, W = orig.shape[:2]
    for x, y in sites + [(tx, ty)]:
        if not (0 <= x and x + tw <= W and 0 <= y and y + th <= H):
            print(f"FAIL: box ({x},{y}) outside {W}x{H}", file=sys.stderr); return 2
    hp0 = hp_of(orig)
    prot = cv2.dilate((np.abs(hp0) > 55.0).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    halop = cv2.dilate((hp0 < -45.0).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    labelglyph = cv2.dilate(((orig[:, :, 0] > 150) & (halop > 0)).astype(np.uint8) * 255, np.ones((5, 5), np.uint8))
    tmpl = cv2.GaussianBlur(hp0, (0, 0), 2.0)[ty:ty + th, tx:tx + tw].copy()
    s_before = [float(cv2.matchTemplate(cv2.GaussianBlur(hp0, (0, 0), 2.0)[y:y + th, x:x + tw], tmpl, cv2.TM_CCOEFF_NORMED)[0, 0]) for x, y in sites]
    cur = orig.copy(); union = np.zeros((H, W), np.uint8)
    for p in range(a.passes):
        mk = stroke_mask(hp_of(cur), sites, tw, th, prot, halop)
        mk = cv2.bitwise_and(mk, cv2.bitwise_not(union))
        if int((mk > 0).sum()) == 0:
            break
        cur = cv2.inpaint(cur, mk, 4, cv2.INPAINT_NS)
        union = cv2.bitwise_or(union, mk)
    s_after = [float(cv2.matchTemplate(cv2.GaussianBlur(hp_of(cur), (0, 0), 2.0)[y:y + th, x:x + tw], tmpl, cv2.TM_CCOEFF_NORMED)[0, 0]) for x, y in sites]
    diff = (np.abs(cur.astype(np.int16) - orig.astype(np.int16)).max(axis=2) > 0)
    gates = []
    gates.append(("changed pixels outside mask", int((diff & (union == 0)).sum()), 0))
    gates.append(("changed pixels inside strong structure", int((diff & (prot > 0)).sum()), 0))
    gates.append(("changed pixels inside label halo", int((diff & (halop > 0)).sum()), 0))
    gates.append(("changed pixels over label glyph ink", int((diff & (labelglyph > 0)).sum()), 0))
    outm = union == 0
    shift = [float(np.abs(cur[:, :, i][outm].astype(np.float32) - orig[:, :, i][outm].astype(np.float32)).mean()) for i in range(3)]
    gates.append(("max channel mean shift outside mask (x1000)", int(round(max(shift) * 1000)), 0))
    print(f"sites {len(sites)}  footprint {int((union > 0).sum())} px ({100 * (union > 0).mean():.2f}%)  passes used {p + 1}")
    print("template score before -> after (first 5):")
    for i in range(min(5, len(sites))):
        print(f"   site {sites[i]}: {s_before[i]:.3f} -> {s_after[i]:.3f}")
    print(f"median score before {np.median(s_before):.3f} after {np.median(s_after):.3f}")
    if float(np.median(s_after)) >= float(np.median(s_before)):
        gates.append(("median template score must drop", 1, 0))
    failed = [g for g in gates if g[1] != g[2]]
    for name, val, want in gates:
        print(f"GATE {name}: {val} (want {want}) -> {'PASS' if val == want else 'FAIL'}")
    cv2.imwrite(f"{a.out_dir}/cleaned.png", cur)
    cv2.imwrite(f"{a.out_dir}/mask.png", union)
    json.dump(dict(sites=sites, scores_before=s_before, scores_after=s_after,
                   footprint_px=int((union > 0).sum()), gates=[[n, v, w] for n, v, w in gates]),
              open(f"{a.out_dir}/qa.json", "w"), indent=1)
    print(f"wrote {a.out_dir}/cleaned.png mask.png qa.json")
    if failed:
        print(f"RESULT: {len(failed)} gate(s) FAILED - the cleanup touched other content. Revert and narrow the mask.", file=sys.stderr)
        return 2
    print("RESULT: all preservation gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
