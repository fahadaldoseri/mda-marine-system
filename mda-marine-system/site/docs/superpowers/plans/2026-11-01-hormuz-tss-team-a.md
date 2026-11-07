# Hormuz TSS Team A Implementation Plan

> **For agentic workers:** Execute the tasks in order and keep the evidence commands and raw outputs.

**Goal:** Remove route graphics from the main map, render the official IMO 1968 Hormuz TSS only in the screen zoom panel, add a source-driven IMO reference line beside the sector strip, and prove geometry, label spacing, English parity, and responsive rendering.

**Architecture:** Keep all route geometry and screen-only route markup in `generator/map_gulf.py`; the main map receives no route SVG, while `_zoom_parts()` remains the sole route host. Use the saved IMO calibration and extracted lane coordinates from `/home/ubuntu/audit-2026-10-30/imo-tss/`, with a two-lane Lambda-shaped solid band, a separating line, and dashed inshore-traffic-zone boundaries. In `generator/build_report.py`, build the reference line from the governed IMO JSON at build time and fail closed with `BuildError` if required fields cannot be read. Avoid changing protected team-B files and put all newly introduced Arabic copy plus English meanings in `i18n-needed-A.json`.

**Tech Stack:** Python 3, Shapely/Natural Earth GeoJSON, inline SVG, HTML/CSS, existing `build_site.py`, Playwright screenshots, JSON source validation.

**Spec:** `/home/ubuntu/audit-2026-10-30/BRIEF-lanes-and-attacks-1101.md`, section `الفريق أ — مسارات المضيق في لوحة التكبير`.

## Global Constraints

- Modify only `seawatch/generator/map_gulf.py`, `seawatch/generator/build_report.py`, and `/home/ubuntu/audit-2026-10-30/i18n-needed-A.json` unless a test/evidence artifact is explicitly required.
- Do not modify `sources/i18n/en/glossary.json`, `generator/screen_layer.py`, `brain/appendices/card_registry.json`, or `brain/web/kpis-totals/2026-10-31.json`.
- Before editing, copy every file to be edited under `/home/ubuntu/audit-2026-10-30/backups-20261031/` and record SHA-256 hashes.
- Build command is exactly: `cd /home/ubuntu/seawatch && python3 generator/build_site.py --site-root .`.
- Do not push, publish, or run a runbook step.
- Preserve the existing sector strip and append the source-driven IMO line through `hero_map(..., extra_html=...)`.
- No unverified Arabic directional claim such as دخول/خروج; arrows must follow the saved `tss-band.png` orientation without textual entry/exit assertions.
- Every success statement in the final report must include command, raw output path or captured output, SHA-256 where applicable, and exit code.

---

### Task 1: Baseline, backups, and source contract

**Files:**
- Create: `/home/ubuntu/audit-2026-10-30/backups-20261031/map_gulf.py.team-a-20261101`
- Create: `/home/ubuntu/audit-2026-10-30/backups-20261031/build_report.py.team-a-20261101`
- Create: `/home/ubuntu/audit-2026-10-30/backups-20261031/i18n-needed-A.json.team-a-20261101` if an earlier file exists
- Create: `/home/ubuntu/audit-2026-10-30/backups-20261031/team-a-baseline.sha256`

**Interfaces:**
- Consumes: current source files and `/home/ubuntu/brain-marine-news/appendices/imo-incidents.json`.
- Produces: immutable rollback copies, governed values (`122`, `2026-10-30`), and a baseline record.

- [ ] Copy the two source files before modification; preserve any existing translation-needed file before replacing/updating it.
- [ ] Hash source and backup copies with `sha256sum` and confirm protected-file hashes are unchanged.
- [ ] Read `totals.confirmed_incidents` and `source.list_updated` from the IMO JSON; do not hard-code them in implementation.

### Task 2: Official TSS geometry and screen-only rendering

**Files:**
- Modify: `generator/map_gulf.py:183-219, 437-455, 546-565`
- Test/evidence: a Python measurement script under `/tmp` or captured command output only; do not add runtime code outside the owned file.

**Interfaces:**
- Consumes: `imo-tss-lanes.json` calibration and lane/centerline coordinates; Natural Earth polygons from `generator/data/ne_50m_land.geojson`.
- Produces: `ROUTES` with two official lane centerlines and official boundary data; `_routing_svg()` with exactly two routes, one separator, dashed inshore-zone boundaries, and arrows; `_panel()` emits route SVG only when `BBOX != MAIN_BBOX` / the zoom panel host is active.

- [ ] Replace the three old horizontal routes with two lane centerlines derived from the saved official geometry. Use the north/south lane data and centerline values as the authoritative trace; retain enough vertices to show the Lambda bend.
- [ ] Remove `ROUTE_LABELS` entries for `مسار دخول`, `مسار خروج`, `المسار الجديد من جهة عُمان`, and `منطقة الفصل`; do not add directional prose. Use neutral, source-grounded legend labels only.
- [ ] Remove the quadrilateral separation-zone fill. Render the solid Lambda band as two adjacent route strokes, a neutral separating stroke between them, and dashed inshore-traffic-zone boundary segments matching the official figure’s outer dashed shape.
- [ ] Draw two outline arrows in the orientation visible in `tss-band.png` (westward on the upper lane, eastward on the lower lane) without naming them entry/exit. Keep arrow geometry in SVG and make it non-operationally caveated in the legend.
- [ ] Make the route host condition screen-zoom-only: change the main panel condition from `BBOX == MAIN_BBOX` to a condition that is false for the main map and true only in `_zoom_parts()`; do not alter the existing map or print data layers.
- [ ] Replace the route key items for the Oman route and separation rectangle with a compact 2–3 line zoom key, using neutral labels and the IMO 1968 source. Ensure no old route wording remains in Arabic or English surfaces.
- [ ] Add a deterministic geometry measurement command that samples each rendered route/zone line against the same Natural Earth polygons, reports inside-point count, sampled length, inside length, and percentage. Target zero land intersection for both routes and report any residual explicitly.

### Task 3: Zoom labels and responsive key layout

**Files:**
- Modify: `generator/map_gulf.py:408-431, 437-455`
- Modify: `generator/build_report.py:417-426, 446-462` only if CSS is needed for the zoom key/labels.

**Interfaces:**
- Consumes: existing zoom place-label list, map SVG viewBox, and new compact route key markup.
- Produces: no-overlap zoom labels and a compact key under/inside the zoom panel that remains readable at desktop and 390px widths.

- [ ] Replace hard-coded zoom place labels with measured placements or a collision-free placement list that avoids route strokes, ports, and other text bounding boxes while preserving Iran, Oman, UAE, Strait, Arabian Gulf, Gulf of Oman, Khasab, and Fujairah where visible.
- [ ] Calculate text bounding rectangles from rendered SVG text lengths/known font sizes (or a deterministic approximation consistent with existing `_text_rect`) and report pairwise overlap count; target `0` overlaps in the zoom label set.
- [ ] Keep the key compact (2–3 rows/lines) and avoid duplicated “layer” keys in the narrow zoom panel; add CSS media behavior only as needed.
- [ ] Add only newly introduced Arabic labels to `i18n-needed-A.json` with concise English translations.

### Task 4: Source-driven IMO reference line

**Files:**
- Modify: `generator/build_report.py:1941-1956`
- Create/update: `/home/ubuntu/audit-2026-10-30/i18n-needed-A.json`

**Interfaces:**
- Consumes: `/home/ubuntu/brain-marine-news/appendices/imo-incidents.json`, specifically `totals.confirmed_incidents` and `source.list_updated`.
- Produces: an HTML reference line adjacent to the existing sector strip: `هجمات مؤكدة على سفن (IMO): <value> · آخر تحديث <localized date>` in Arabic and its translated English surface, or a closed build failure if either value is absent/invalid.

- [ ] Add a small loader/formatter in `build_report.py` that locates the governed IMO JSON relative to the repository (`Path(__file__).resolve().parents[2] / "brain-marine-news" / "appendices" / "imo-incidents.json"`) and validates integer `confirmed_incidents` plus ISO `source.list_updated`.
- [ ] Build the displayed Arabic date from the parsed ISO date, not a literal count/date. Preserve the existing zone-strip HTML and append the reference line in the same `extra_html` value.
- [ ] Raise `BuildError` (or propagate a clear build error) if the source cannot be read or required values are malformed; never render an unbacked numeric value.
- [ ] Provide English rendering for the new line through the project’s existing language/build path and record every Arabic string in `i18n-needed-A.json` without modifying `glossary.json`.

### Task 5: Fresh build and static contracts

**Files:**
- Create: `/home/ubuntu/audit-2026-10-30/evidence/team-a-build-20261101.log`
- Create: `/home/ubuntu/audit-2026-10-30/evidence/team-a-static-20261101.log`

**Interfaces:**
- Consumes: changed generator sources and governed source JSON.
- Produces: rebuilt Arabic/English outputs and literal command/exit evidence.

- [ ] Run the exact build command from the brief, capture stdout/stderr and exit code verbatim.
- [ ] Check generated Arabic and English HTML for: routes absent from the main map SVG, route SVG present only in the zoom SVG, old Oman/separation text absent, reference line present with source values, and no Arabic characters visible in English.
- [ ] Run applicable existing surface tests read from the repository; do not modify team-B tests or protected files.
- [ ] Record command, exit code, raw output path, and SHA-256 for each evidence log.

### Task 6: Playwright visual measurement at 1440px and 390px

**Files:**
- Create: `/home/ubuntu/audit-2026-10-30/evidence/team-a-screenshot-1440-20261101.png`
- Create: `/home/ubuntu/audit-2026-10-30/evidence/team-a-screenshot-390-20261101.png`
- Create: `/home/ubuntu/audit-2026-10-30/evidence/team-a-playwright-20261101.log`

**Interfaces:**
- Consumes: the freshly rebuilt local site/output.
- Produces: two Arabic screenshots, DOM/SVG measurements, and a visual description based on actually read screenshots.

- [ ] Discover the available Playwright MCP contract, install the configured browser if required, and open the local/generated Arabic report.
- [ ] Capture the full screen hero map at 1440px and 390px; ensure the zoom panel is visible in both captures.
- [ ] Measure SVG route count/host, label bounding-box intersections, and route-to-land intersections in the live DOM; save raw values.
- [ ] Read both screenshots visually and report only visible facts: route placement, arrow orientation, key wrapping, label overlap/cropping, and reference line presence.

### Task 7: Final integrity review

**Files:**
- Create/update: `/home/ubuntu/audit-2026-10-30/evidence/team-a-final-integrity-20261101.log`

- [ ] Verify the four protected files are byte-identical to their baseline hashes.
- [ ] Re-read the brief checklist line by line and map each requirement to command evidence.
- [ ] Print the complete `i18n-needed-A.json` and validate it with `python3 -m json.tool`.
- [ ] Report blockers or residual uncertainty explicitly; do not claim completion without fresh exit-code evidence.
