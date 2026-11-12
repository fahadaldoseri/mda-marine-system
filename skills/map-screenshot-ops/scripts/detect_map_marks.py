#!/usr/bin/env python3
"""Detect semi-transparent copyright/watermark glyph runs on a map raster.
Emits candidates JSON + a high-amplification adjudication sheet for visual reading.
Exit 0 = candidates written, 2 = usage/detection failure (fails closed)."""
import argparse, json, os, sys
import numpy as np
import cv2

TW_TH_DEFAULT = (106, 22)


def hp_of(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return g - cv2.medianBlur(g.astype(np.uint8), 21).astype(np.float32)


def guards(hp):
    prot = cv2.dilate((np.abs(hp) > 55.0).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    halop = cv2.dilate((hp < -45.0).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    return prot, halop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--template", required=True, help="x,y of one readable mark (top-left of its glyph run)")
    ap.add_argument("--size", default="106x22", help="template glyph-run width x height")
    ap.add_argument("--water", default=None, help="optional 0/255 water mask png to restrict sites")
    ap.add_argument("--thresh", type=float, default=0.27)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    tx, ty = [int(v) for v in a.template.split(",")]
    tw, th = [int(v) for v in a.size.lower().split("x")]
    os.makedirs(a.out_dir, exist_ok=True)
    im = cv2.imread(a.input)
    if im is None:
        print(f"FAIL: cannot read {a.input}", file=sys.stderr); return 2
    H, W = im.shape[:2]
    if not (0 <= tx and tx + tw <= W and 0 <= ty and ty + th <= H):
        print("FAIL: template box outside image", file=sys.stderr); return 2
    hp = hp_of(im); sm = cv2.GaussianBlur(hp, (0, 0), 2.0)
    tmpl = sm[ty:ty + th, tx:tx + tw].copy()
    prot, halop = guards(hp)
    r = cv2.matchTemplate(sm, tmpl, cv2.TM_CCOEFF_NORMED).astype(np.float32)
    wm = None
    if a.water:
        wm = cv2.imread(a.water, cv2.IMREAD_GRAYSCALE)
        if wm is None or wm.shape[:2] != (H, W):
            print("FAIL: water mask shape mismatch", file=sys.stderr); return 2
    ys, xs = np.where(r >= a.thresh)
    out = []
    for x, y in zip(xs, ys):
        if r[y, x] < r[max(0, y - 30):y + 31, max(0, x - 55):x + 56].max():
            continue
        box = hp[y:y + th, x:x + tw]
        sel = (box > 3.0) & (box < 46)
        if int(sel.sum()) < 40 or int((box > 46).sum()) > 8:
            continue
        if float((halop[y:y + th, x:x + tw] > 0).mean()) > 0.02 or float((prot[y:y + th, x:x + tw] > 0).mean()) > 0.05:
            continue
        if wm is not None and float((wm[y:y + th, x:x + tw] > 100).mean()) < 0.85:
            continue
        out.append(dict(x=int(x), y=int(y), score=float(r[y, x]), strokes=int(sel.sum())))
    out.sort(key=lambda d: -d["score"])
    uniq = []
    for d in out:
        if any(abs(d["x"] - k["x"]) < 70 and abs(d["y"] - k["y"]) < 40 for k in uniq):
            continue
        uniq.append(d)
    if not uniq:
        print(f"FAIL: no candidate >= {a.thresh} (lower it, or the marks are not this template)", file=sys.stderr); return 2
    amp = np.clip(hp * 8.0 + 128, 0, 255).astype(np.uint8)
    Z, COLS = 3, 4
    tiles = []
    for i, d in enumerate(uniq[:24]):
        x, y = d["x"], d["y"]
        x0, x1 = max(0, x - 10), min(W, x + tw + 10); y0, y1 = max(0, y - 10), min(H, y + th + 10)
        t = cv2.resize(cv2.cvtColor(amp[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR), None, fx=Z, fy=Z, interpolation=cv2.INTER_NEAREST)
        bar = np.zeros((22, t.shape[1], 3), np.uint8)
        cv2.putText(bar, f"C{i:02d} ({x},{y}) s={d['score']:.2f} px={d['strokes']}", (3, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 255, 1, cv2.LINE_AA)
        tiles.append(np.vstack([bar, t]))
    cw = max(t.shape[1] for t in tiles); ch = max(t.shape[0] for t in tiles)
    rows = (len(tiles) + COLS - 1) // COLS
    sheet = np.zeros((rows * (ch + 6), COLS * (cw + 6), 3), np.uint8)
    for i, t in enumerate(tiles):
        rr, c = divmod(i, COLS)
        sheet[rr * (ch + 6):rr * (ch + 6) + t.shape[0], c * (cw + 6):c * (cw + 6) + t.shape[1]] = t
    json.dump(uniq, open(f"{a.out_dir}/candidates.json", "w"), indent=1)
    cv2.imwrite(f"{a.out_dir}/adjudication_sheet.png", sheet)
    print(f"candidates: {len(uniq)} (top 24 sheeted)  sheet={a.out_dir}/adjudication_sheet.png")
    print("NEXT: read the sheet at high amplification; keep ONLY sites whose glyphs spell the "
          "copyright phrase. Score alone does not separate marks from terrain relief or border lines. "
          "Then run apply_mark_cleanup.py --sites x,y;...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
