# Map redesign plan — 2026-10-31

## Scope
- Change only `generator/map_gulf.py`, add map source notes/data under `sources/map/`, and merge new generated UI strings into `sources/i18n/en/glossary.json`.
- Do not edit `generator/screen_layer.py`, `generator/build_report.py`, `validators/`, or the Brain tree.
- Preserve existing unrelated working-tree changes.

## Implementation
1. Keep the main map as last-24-hours context and keep incident markers empty because the daily ledger exposes no coordinates.
2. Make the Hormuz zoom panel unconditional for the screen hero map. Render the same local land geometry, >=3 labels, and schematic north/south/ Oman-side routes with a separation band.
3. Add explicit maritime-boundary and route layers. Use Marine Regions attribution for the boundary source; avoid claiming a formal delimitation. Use IMO FAQ facts for route options and label the drawn route geometry as schematic guidance.
4. Add a governed location lookup JSON with known place coordinates and document that no daily event was matched to it in this release.
5. Improve map colors using map-local SVG style overrides and add legend entries/source disclosure. Keep all Arabic UI strings in the English glossary.

## Acceptance measurements
- Build commands exit 0: sync from Brain, then site build.
- Hero zoom: non-empty SVG, positive viewBox dimensions, >=1 path, >=3 text elements.
- Daily event markers = 0; numbered incident legend rows = 0; no ungrounded event marker.
- Main map includes boundary, route, separation-band layers and legend labels.
- Contrast calculation from rendered CSS/computed colors for >=3 map text classes; small-text target >=4.5:1 where applicable.
- Playwright at 1440px and 390px for Arabic and English pages: no horizontal overflow at 390px, no Arabic leakage in English, zoom/marker/legend counts recorded.
- Save four screenshots under `/home/ubuntu/audit-2026-10-30/shots/` and inspect them visually before reporting.
