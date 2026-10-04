# Frontend → Member 3: Geodata Request (MapLibre overlays)

**From:** Dinesh Kumar (Member 4 — Frontend UI/UX)
**To:** Harsith (Member 3 — Data/GIS & DevOps)
**Ref:** BIND Implementation Plan §1.1, §3.1, §5 Phase 1; FAI Task 2 resource list
**Why now:** Deliverable A needs cadastral GeoJSON in the browser. Until your export exists I develop against a clearly-labelled local fixture; I want the fixture to already match your real output so swapping is a one-file change.

---

## 1. Minimum viable hand-off (unblocks Deliverable A today)

1. **One** GeoJSON file containing the **target parcel 202/55** plus 5–20 neighbouring parcels — enough to prove selection + highlight logic.
2. The **same file** as `FeatureCollection` in **EPSG:4326 (WGS84)**.
3. Optional but valuable: one roads / water-body layer, and the admin boundary for context.

I can also accept a small export of the real cadastral sheet — one village extent is plenty for dev.

---

## 2. Format requirements (strict, or the map silently misrenders)

| Rule | Detail |
|---|---|
| Type | `FeatureCollection` → `Feature` → `Polygon`/`MultiPolygon` (Parks must be `LineString`, boundaries `Polygon`) |
| CRS | **EPSG:4326 only.** If you export UTM 44N / EPSG:32644 by accident, geometry lands off the coast of Africa. Please reproject before exporting. |
| Coordinate order | GeoJSON = `[longitude, latitude]`. Confirming explicitly because India coords are `lat ≈ 8–13°N`, `lon ≈ 77–80°E` — swaps are the most common geo bug. |
| Rings | Exterior ring closed (first vertex == last vertex), counter-clockwise; holes clockwise. |
| Geometry validity | No self-intersections / zero-area polygons — run `shapely` `is_valid` before export, or MapLibre may not fill them. |
| MultiPolygon | Preferred over a `GeometryCollection` when a survey number has disconnected parts. |
| Encoding | UTF-8, no BOM. Survey numbers like `202/55` must stay strings, never numbers. |

---

## 3. Property keys I will bind to (please confirm exact names)

| Key | Type | Used for |
|---|---|---|
| `survey_number` | string | **target-parcel matching** (e.g. `"202/55"`) |
| `parcel_id` / stable feature id | string | selection + React keys |
| `village`, `taluk`, `district` | string | detail pane / popup |
| `area_ha` (or `area_sqm`) | number | detail pane |
| `land_use` / classification | string | detail pane, styling |
| `layer` | string | if layers share one file: `parcel` \| `road` \| `water` \| `boundary` |
| `source` + `data_date` | string | provenance badge, "MOCK vs REAL" |

**Do not rename these later without a ping** — the map component reads exactly these keys through a single adapter (`mapAdapter.ts`), which is the only place I'd need to edit.

---

## 4. Delivery options — pick one

| Option | Frontend impact |
|---|---|
| **A. File in `public/fixtures/*.geojson`** (dev only) | simplest; no CORS, no network |
| **B. S3 presigned GET URL** | works with private buckets; needs expiry long enough for a session |
| **C. Public-read CORS-enabled S3 GET** | please do **not** make buckets public (AWS guide forbids it) |
| **D. PMTiles / vector tiles** | only if a layer exceeds ~5 MB; needs a different MapLibre source type — tell me and I'll build that adapter |

Minimum: **CORS must allow the frontend origin** (`http://localhost:5173` in dev, plus the deployed origin). Plan §5 Phase 3 assigns API Gateway CORS config to you; the same applies to any S3-hosted geodata.

---

## 5. Metadata alongside the data

Please include or tell me:

- `bbox` `[minLon, minLat, maxLon, maxLat]` and a sensible map centre + initial zoom
- feature count per layer
- CRS confirmation + export date + data source
- whether the geometry is **simplified** (tolerance used) — affects rendering performance

If there is no bbox I will compute it client-side, but a backend/tool-provided viewport avoids an empty-looking first paint.

---

## 6. Performance & size

Target ≤ 2–3 MB per layer (uncompressed JSON parsed on the main thread). If a real village sheet is far larger, we have two clean options: (a) you pre-simplify + deliver per-village chunks, or (b) tiles. Tell me the expected size for the 202/55 area and I'll size the architecture accordingly.

---

## 7. What the frontend does with it (so we agree on scope)

- Renders parcels as fill + line layers, target parcel visually distinct, selection state via feature-state (no re-download).
- Displays the vision GPS `Point` supplied by the backend exhibit and shows whether it falls inside the target polygon **as a reported result** — I do not run point-in-polygon logic; that's Member 3/Member 1 territory.
- Shows a `MOCK DATA` badge whenever the fixture is in use.

---

## 8. One-line answer needed

**Which delivery option (A–D) and which property-key names, and can I have the 202/55 + neighbours export as EPSG:4326 `FeatureCollection`?**
