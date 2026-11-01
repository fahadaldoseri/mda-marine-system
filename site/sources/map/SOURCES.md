# Map sources — 2026-10-31

## Maritime boundaries

The rendered layer is labelled **حدود بحرية**. Its geometry is a clipped and simplified extract of the Marine Regions `eez_boundaries` WFS layer, backed by the Flanders Marine Institute (VLIZ) Maritime Boundaries Geodatabase, version 12. The extract was retrieved on 2026-10-31 for the main Gulf/Arabian Sea extent and the Red Sea/Bab al-Mandab inset, then stored in `generator/data/marine_boundaries.geojson`. The selected records include treaty, court-ruling, median-line, and unsettled maritime lines returned by the service. The map does not infer a line where the source returned no geometry.

Source and service:

- Marine Regions EEZ documentation: <https://www.marineregions.org/eez.php>
- Marine Regions source/citation page: <https://www.marineregions.org/sources.php>
- Marine Regions WFS documentation: <https://www.marineregions.org/webservices.php>
- WFS endpoint: <https://geo.vliz.be/geoserver/MarineRegions/wfs>
- Dataset citation: Flanders Marine Institute (2023), *Maritime Boundaries Geodatabase: Maritime Boundaries and Exclusive Economic Zones (200NM), version 12*, DOI <https://doi.org/10.14284/632>
- License: CC BY 4.0, as stated by Marine Regions: <https://creativecommons.org/licenses/by/4.0/>

Marine Regions notes that its boundary database contains treaties and disputed or unsettled lines and that its EEZ construction differs from the strict UNCLOS EEZ definition in some respects. The layer is therefore a source-backed visualization of the dataset, not a legal opinion or a replacement for official nautical charts.

## Hormuz routing graphic

The rendered layer is labelled **مسارات إرشادية (تمثيل تخطيطي)**. The linework is deliberately schematic: three dashed paths represent an inbound route, an outbound route, and a newer southern/Oman-side route, with a translucent separation band between the first two. The geometry is not a navigational instruction and is not presented as the current IMO TSS.

The factual basis is the official IMO Operational FAQs for the Strait of Hormuz Evacuation Plan, retrieved 2026-10-31. The page identifies northern and southern routing options, assigns operational routing responsibility to Iran and Oman respectively, and states that the existing TSS should not be used because of reported mines. It does not provide a complete set of chart-ready coordinates for the schematic shown here.

- IMO source: <https://www.imo.org/en/mediacentre/hottopics/pages/faqs-strait-of-hormuz-evacuation-plan.aspx>
- Independent contextual source consulted: <https://maritime-executive.com/article/iran-publishes-redrawn-traffic-scheme-for-strait-of-hormuz>

## Land and coastline background

The existing land and land-border background remains Natural Earth 1:50m data. Natural Earth states that its vector and raster data are public domain and provides an optional attribution.

- Natural Earth terms: <https://www.naturalearthdata.com/about/terms-of-use/>
- Attribution used in the map: Made with Natural Earth.

## Daily incident coordinates

The 2026-10-31 daily ledger and web zone record were checked before rendering. They contain area names and zone labels but no latitude, longitude, or event-level coordinate fields. Consequently, the release renders **بلاغات آخر 24 ساعة فقط** as scope text, but draws zero numbered incident markers. The governed place anchors are kept in `sources/map/locations.json` for future matching; no event is matched to an anchor in this release.
