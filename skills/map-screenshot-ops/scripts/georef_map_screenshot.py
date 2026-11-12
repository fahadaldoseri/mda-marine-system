#!/usr/bin/env python3
"""Georeference a map raster (satellite screenshot) by fitting it to a public-domain coastline.
Model fitted:  u = ux + ub*lon    v = vy + vm*M + vq*M^2   (M = Mercator latitude in degrees)
Usage: python3 georef_map_screenshot.py --input shot.png --out-dir geo --ref ne_10m_land.geojson
Stages: coast mask -> coarse scan -> coordinate descent -> ICP correspondences -> quadratic refit
        -> per-zone error table -> graticule.png + georef.json
Exit 0 = fit passed its gate. Exit 2 = missing input or fit not trustworthy."""
import argparse, json, math, os, sys, time
import numpy as np
import cv2

DEG = 180.0 / np.pi
NE_URL = "https://github.com/nvkelso/natural-earth-vector/raw/master/geojson/ne_10m_land.geojson"
Mv = lambda la: np.log(np.tan(np.pi / 4 + np.radians(np.asarray(la, dtype=np.float64)) / 2)) * DEG
M1 = lambda la: math.log(math.tan(math.pi / 4 + math.radians(float(la)) / 2)) * DEG


def ref_coast_points(path, bbox, dens=0.05):
    gj = json.load(open(path)); pts = []
    for ft in gj["features"]:
        g = ft.get("geometry") or {}
        rings = [g["coordinates"]] if g.get("type") == "Polygon" else (g["coordinates"] if g.get("type") == "MultiPolygon" else [])
        for poly in rings:
            for ring in poly:
                for j in range(len(ring) - 1):
                    p, q = ring[j], ring[j + 1]
                    n = max(1, int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) / dens))
                    for k in range(n):
                        t = k / n
                        lo = p[0] + t * (q[0] - p[0]); la = p[1] + t * (q[1] - p[1])
                        if bbox[0] <= lo <= bbox[1] and bbox[2] <= la <= bbox[3]:
                            pts.append((lo, la))
    return np.array(pts, float)


def coast_edge(img, water_png):
    if water_png and os.path.exists(water_png):
        wm = (cv2.imread(water_png, cv2.IMREAD_GRAYSCALE) > 100).astype(np.uint8)
    else:
        b, g, r = cv2.split(img.astype(np.int16))
        wm = ((b > r + 10) & (b > 40)).astype(np.uint8)
        wm = cv2.morphologyEx(wm, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    edge = (wm ^ np.roll(wm, 1, 1)) | (wm ^ np.roll(wm, 1, 0))
    edge = cv2.dilate(edge, np.ones((3, 3), np.uint8)) > 0
    D = cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
    return D, (edge.astype(np.uint8) * 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--ref", default="ne_10m_land.geojson", help="Natural Earth land GeoJSON")
    ap.add_argument("--bbox", default="20,90,-10,45", help="reference clip window lonmin,lonmax,latmin,latmax")
    ap.add_argument("--water", default=None, help="water mask png (else auto blue-dominance)")
    ap.add_argument("--scan-limit", default="26,44,20,45,15,50", help="kx_from,kx_to,lon_from,lon_to,lat_from,lat_to for the coarse seed scan")
    ap.add_argument("--max-scan-seconds", type=float, default=45.0)
    ap.add_argument("--gate-median-px", type=float, default=12.0)
    ap.add_argument("--strict", action="store_true", help="fail (exit 2) if any zone is much worse than the global median")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    img = cv2.imread(a.input)
    if img is None:
        print(f"FAIL: cannot read {a.input}", file=sys.stderr); return 2
    H, W = img.shape[:2]
    if not os.path.exists(a.ref):
        print(f"FAIL: reference not found at {a.ref}\nFetch it first:  curl -sL '{NE_URL}' -o ne_10m_land.geojson", file=sys.stderr)
        return 2
    bx = [float(v) for v in a.bbox.split(",")]
    P = ref_coast_points(a.ref, bx)
    if len(P) < 5000:
        print(f"FAIL: only {len(P)} reference coast points in bbox {bx}; widen --bbox", file=sys.stderr); return 2
    LON, MR = P[:, 0], Mv(P[:, 1])
    D, edgepng = coast_edge(img, a.water)
    cv2.imwrite(f"{a.out_dir}/coast_edge.png", edgepng)
    E = np.argwhere(edgepng > 0); EX = E[:, 1].astype(np.float32); EY = E[:, 0].astype(np.float32)
    print(f"reference coast samples {len(P)} | image coast pixels {len(EX)}")

    DS = 4
    Ws, Hs = W // DS, H // DS
    sub = np.linspace(0, len(P) - 1, min(len(P), 2000)).astype(int)
    xs, ms = LON[sub], MR[sub]
    isub = np.linspace(0, len(EX) - 1, min(len(EX), 4000)).astype(int)
    IXs = (EX[isub] / DS).astype(np.int32); IYs = (EY[isub] / DS).astype(np.int32)
    goodI = (IXs >= 0) & (IXs < Ws) & (IYs >= 0) & (IYs < Hs)
    IXs, IYs = IXs[goodI], IYs[goodI]

    def chamfer(kx, lon0, lat0):
        """symmetric score: ref coast -> image coast AND image coast -> ref coast.
        Lower is better; returned as mean px (capped), so we minimise it."""
        u = (xs - lon0) * kx; v = (M1(lat0) - ms) * kx
        ok = (u >= 2) & (u < W - 2) & (v >= 2) & (v < H - 2)
        if ok.sum() < 300:
            return 1e9, 0
        ref = np.zeros((Hs, Ws), np.uint8)
        rx = np.clip((u[ok] / DS).astype(np.int32), 0, Ws - 1); ry = np.clip((v[ok] / DS).astype(np.int32), 0, Hs - 1)
        ref[ry, rx] = 1
        if ref.sum() < 30:
            return 1e9, 0
        Dr = cv2.distanceTransform((1 - ref).astype(np.uint8), cv2.DIST_L2, 3) * DS
        d_ref_to_img = D[np.clip(v[ok].astype(np.int32), 0, H - 1), np.clip(u[ok].astype(np.int32), 0, W - 1)]
        d_img_to_ref = Dr[IYs, IXs]
        return float(np.median(d_ref_to_img) + np.median(d_img_to_ref)), int(ok.sum())

    lo_kx, hi_kx, lo_lon, hi_lon, lo_lat, hi_lat = [float(v) for v in a.scan_limit.split(",")]
    t0 = time.time(); best = (1e9, None)
    for kx in np.arange(lo_kx, hi_kx, 1.0):
        for lon0 in np.arange(lo_lon, hi_lon, 1.0):
            for lat0 in np.arange(lo_lat, hi_lat, 1.0):
                sc, _n = chamfer(kx, lon0, lat0)
                if sc < best[0]:
                    best = (sc, (float(kx), float(lon0), float(lat0)))
        if time.time() - t0 > a.max_scan_seconds:
            break
    if best[1] is None or best[0] > 1e8:
        print("FAIL: coarse scan found no plausible seed; widen --scan-limit/--bbox", file=sys.stderr); return 2
    kx, lon0, lat0 = best[1]
    print(f"seed ({time.time()-t0:.1f}s): kx={kx:.2f} lon0={lon0:.2f} lat0={lat0:.2f} chamfer {best[0]:.1f}px")
    for step in (0.5, 0.2, 0.05):
        cur = chamfer(kx, lon0, lat0)[0]; improved = True
        while improved:
            improved = False
            for i in range(3):
                for sgn in (1, -1):
                    cand = [kx, lon0, lat0]; cand[i] += sgn * step
                    sc = chamfer(*cand)[0]
                    if sc < cur - 1e-4:
                        kx, lon0, lat0 = cand; cur = sc; improved = True
    print(f"seed refined: kx={kx:.3f} lon0={lon0:.3f} lat0={lat0:.3f} chamfer {cur:.1f}px")

    def nearest(u, v, win=40):
        bd = np.full(len(u), 1e9); nx = np.zeros(len(u)); ny = np.zeros(len(u)); C = 240
        ui = np.clip((u // C).astype(int), 0, (W + C) // C - 1); vi = np.clip((v // C).astype(int), 0, (H + C) // C - 1)
        cells = {}
        for i in range(len(u)):
            cells.setdefault((int(ui[i]), int(vi[i])), []).append(i)
        for (cx, cy), idx in cells.items():
            x0, x1 = max(0, cx * C - win), min(W, (cx + 1) * C + win); y0, y1 = max(0, cy * C - win), min(H, (cy + 1) * C + win)
            sel = (EX >= x0) & (EX < x1) & (EY >= y0) & (EY < y1)
            if not sel.any():
                continue
            sx, sy = EX[sel], EY[sel]; idx = np.array(idx)
            dd = (sx[None, :] - u[idx, None]) ** 2 + (sy[None, :] - v[idx, None]) ** 2
            j = dd.argmin(1); dm = np.sqrt(dd[np.arange(len(idx)), j]); g = dm <= win
            gi = idx[g]; upd = dm[g] < bd[gi]; gg = gi[upd]
            bd[gg] = dm[g][upd]; nx[gg] = sx[j[g][upd]]; ny[gg] = sy[j[g][upd]]
        return bd, nx, ny

    ux = ub = vy = vm = vq = None
    for it in range(4):
        u = kx * (LON - lon0); v = kx * (M1(lat0) - MR)
        ins = (u > 2) & (u < W - 3) & (v > 2) & (v < H - 3)
        bd, nx, ny = nearest(u[ins], v[ins]); ok = bd < 40
        X, Y, U, V = LON[ins][ok], MR[ins][ok], nx[ok], ny[ok]
        if len(X) < 3000:
            print("FAIL: too few ICP correspondences to trust the fit", file=sys.stderr); return 2
        solx = np.linalg.lstsq(np.stack([X, np.ones(len(X))], 1), U, rcond=None)[0]
        soly = np.linalg.lstsq(np.stack([np.ones(len(Y)), Y, Y * Y], 1), V, rcond=None)[0]
        ub, ux = float(solx[0]), float(solx[1]); vy, vm, vq = float(soly[0]), float(soly[1]), float(soly[2])
        u2 = ub * LON + ux; v2 = vy + vm * MR + vq * MR * MR
        bd2, _, _ = nearest(u2[(u2 > 2) & (u2 < W - 3) & (v2 > 2) & (v2 < H - 3)],
                           v2[(u2 > 2) & (u2 < W - 3) & (v2 > 2) & (v2 < H - 3)])
        print(f"  icp {it}: corr {int(ok.sum())} median {np.median(bd[ok]):.2f}px  new median {np.median(bd2):.2f}px")
    u = ub * LON + ux; v = vy + vm * MR + vq * MR * MR
    ins = (u > 2) & (u < W - 3) & (v > 2) & (v < H - 3)
    bd, nx, ny = nearest(u[ins], v[ins]); ok = bd < 40
    dd = bd[ok]; ui, vi = u[ins][ok], v[ins][ok]
    km_per_px = 111.32 * math.cos(math.radians(20)) / abs(ub)
    med = float(np.median(dd)); p90 = float(np.percentile(dd, 90)); w5 = float(100 * (dd <= 5).mean())
    print(f"FINAL u = {ux:.3f} + {ub:.4f}*lon ; v = {vy:.3f} + {vm:.4f}*M + {vq:.5f}*M^2 (vy,vm,vq order)")
    print(f"FINAL correspondences {int(ok.sum())} median {med:.2f}px ({med*km_per_px:.0f} km) p90 {p90:.2f}px within5px {w5:.1f}% scale {km_per_px:.2f} km/px")

    def px2lat(vv):
        t = vv - vy
        if abs(vq) < 1e-9:
            m = t / vm
        else:
            disc = vm * vm + 4 * vq * t
            if disc < 0:
                return float("nan")
            r1 = (-vm + math.sqrt(disc)) / (2 * vq); r2 = (-vm - math.sqrt(disc)) / (2 * vq)
            linm = t / vm
            m = r1 if abs(r1 - linm) <= abs(r2 - linm) else r2
        return math.degrees(2 * math.atan(math.exp(m / DEG)) - math.pi / 2)
    corners = {}
    for k, (pu, pv) in {"NW": (0, 0), "NE": (W - 1, 0), "SW": (0, H - 1), "SE": (W - 1, H - 1), "centre": (W / 2, H / 2)}.items():
        corners[k] = (float((pu - ux) / ub), px2lat(pv))
    for k in ("NW", "NE", "SW", "SE", "centre"):
        print(f"  corner {k}: {corners[k][1]:.3f}N {corners[k][0]:.3f}E")
    zones = {}
    for ry in range(3):
        for rx in range(4):
            s = dd[(ui >= rx * W / 4) & (ui < (rx + 1) * W / 4) & (vi >= ry * H / 3) & (vi < (ry + 1) * H / 3)]
            if len(s) >= 150:
                zones[f"row{ry+1}col{rx+1}"] = [int(len(s)), round(float(np.median(s)), 2), round(float(100 * (s <= 5).mean()), 1)]
    for k in sorted(zones):
        n_, m_, w_ = zones[k]
        print(f"  zone {k}: n {n_:5d} median {m_:5.2f}px ({m_*km_per_px:4.0f} km) within5px {w_:4.1f}%")
    ch_img = chamfer(kx, lon0, lat0)[0]
    zmed = [v[1] for v in zones.values() if v[0] >= 300]
    unif = (max(zmed) / max(1e-6, med)) if zmed else 99.0
    print(f"chamfer (both directions) {ch_img:.1f}px | zones used {len(zmed)} | worst-zone/global ratio {unif:.2f}")

    gr = img.copy(); fnt = cv2.FONT_HERSHEY_SIMPLEX
    for lon in range(int(math.floor(corners["NW"][0] / 5) * 5), int(math.ceil(corners["NE"][0] / 5) * 5) + 1, 5):
        pu = ux + ub * lon
        if 0 <= pu < W:
            cv2.line(gr, (int(round(pu)), 0), (int(round(pu)), H - 1), (0, 220, 255), 1, cv2.LINE_AA)
            for yy in (16, H - 6):
                cv2.putText(gr, f"{lon}E", (min(int(pu) + 3, W - 46), yy), fnt, 0.42, (0, 220, 255), 1, cv2.LINE_AA)
    for lat in range(int(math.floor(corners["SW"][1] / 5) * 5), int(math.ceil(corners["NW"][1] / 5) * 5) + 1, 5):
        pv = vy + vm * M1(lat) + vq * M1(lat) ** 2
        if 0 <= pv < H:
            cv2.line(gr, (0, int(round(pv))), (W - 1, int(round(pv))), (0, 220, 255), 1, cv2.LINE_AA)
            for xx in (4, W - 44):
                cv2.putText(gr, f"{lat}N", (xx, max(int(pv) - 4, 12)), fnt, 0.42, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.imwrite(f"{a.out_dir}/graticule.png", gr)
    st = dict(model=dict(ux=ux, ub=ub, vy=vy, vm=vm, vq=vq, form="v = vy + vm*M + vq*M^2"), corners=corners, zones=zones,
              km_per_px=km_per_px, median_px=med, p90_px=p90, within5px=w5, chamfer_px=ch_img,
              zone_ratio_worst=float(unif), correspondences=int(ok.sum()), reference=a.ref, source=a.input, status="")
    json.dump(st, open(f"{a.out_dir}/georef.json", "w"), indent=1)
    print(f"wrote {a.out_dir}/graticule.png georef.json coast_edge.png")
    if med > a.gate_median_px:
        print(f"RESULT: FAILED gate (median {med:.2f}px > {a.gate_median_px}px). Do not publish coordinates from this raster.", file=sys.stderr)
        return 2
    nonuniform = bool(zmed and max(zmed) > 3.0 * med)
    if nonuniform:
        msg = (f"worst zone {max(zmed):.1f}px = {unif:.1f}x global median {med:.1f}px: this view is not described by one "
               f"linear transform (typical of a wide tilted globe screenshot). Publish the per-zone table, not one number.")
        if a.strict:
            print("RESULT: FAILED uniformity gate (strict). " + msg, file=sys.stderr)
            st["status"] = "NONUNIFORM"; json.dump(st, open(f"{a.out_dir}/georef.json", "w"), indent=1)
            return 2
        print("WARNING (non-uniform, not strict): " + msg)
    print(f"status: {'NONUNIFORM' if nonuniform else 'UNIFORM'} | per-zone table in georef.json is the deliverable")
    print("RESULT: fit trustworthy near the centre band; always publish the per-zone table with it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
