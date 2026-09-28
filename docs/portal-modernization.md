# Sentinel Grid modernization report

Implemented in the existing Next.js portal. Authentication, permission gates, API endpoints, database records, stream transports and backend services retain their existing behavior.

## Theme and components

The shared CSS tokens now define layered navy surfaces, electric blue controls, cyan highlights, readable metadata, blue borders and distinct semantic status colors. Public/authentication palette aliases use the same tokens. Existing Inter/system font support is retained.

Updated the application shell, permission-aware navigation, workspace selector, global camera search, profile/context display, cards, tables, badges, form controls, map chrome, popups, video tiles, expanded video dialog, alerts and audit views. Mobile navigation traps/restores focus; mobile camera details use a bottom sheet. Focus indicators and reduced-motion handling are shared.

Video Wall retains bounded stream pagination and the existing WHEP/HLS hooks, with camera search, status filtering and registry-to-camera deep links. Audit Log retains chain verification and adds search, outcome and local-date filters over the latest 200 loaded records. Watchlist mutations, alert acknowledgement and streaming remain intact; priority colors now distinguish informational, warning and critical events. Vehicle Trace retains its data and evidence export, with themed map tiles, blue paths and data-driven bounds.

## Camera source and verified inventory

Authoritative application source: the existing jurisdiction/permission-scoped `GET /cameras` API. It reads the `cameras` table and serializes its PostGIS WGS84 `location` point through `services/api/api/cameras.py::_to_out`.

- Latitude: API `lat`, from geometry Y.
- Longitude: API `lon`, from geometry X.
- No frontend catalogue, invented coordinates, city-center fallback or geocoding was introduced.

Read-only checks against the running API service's configured database on 2026-09-28 found:

| Inventory | Total | Valid coordinates | Missing coordinates | Distinct locations |
| --- | ---: | ---: | ---: | ---: |
| Active cameras | 30 | 22 | 8 | 14 |
| Inactive cameras | 5 | 5 | 0 | 5 |
| Entire table | 35 | 27 | 8 | 18 |

All 22 located active records pass latitude/longitude range validation. The API excludes inactive records and applies the caller's jurisdiction scope, so an individual user's response may contain fewer than 30 cameras. These are verified database counts, not a claim that an authenticated user's `/cameras` response was fetched during this session.

The acceptance result for the full active inventory is **22 geographic entities plus 8 explicitly unavailable locations**. Mapping all 30 would require supplying actual coordinates for those eight records.

## Registry and map implementation

- Replaced `CircleMarker` overlays with actual Leaflet `Marker` entities inside the existing `leaflet.markercluster` integration.
- Each validated coordinate pair produces a marker. Numeric coordinate strings are normalized; null, empty, nonfinite and out-of-range values remain visible in the registry as unavailable locations.
- Bounds derive from filtered valid coordinates. Initialization and the Fit All Cameras control use those bounds. The empty viewport shows world bounds rather than assigning any camera a fallback position.
- Cluster labels use actual child counts. Coincident cameras expand through cluster spiderfying; this changes presentation only, never the source coordinates.
- Selection pans/zooms, opens the popup, highlights the marker/card and scrolls the registry. Stable record keys and a persistent map instance survive filtering and sorting.
- Search covers name, camera ID, department and known jurisdiction name. Department, status, location and sorting controls share one derived camera list with the map and counters.
- Location names use jurisdictions already available to the authenticated user. The camera schema has no city-name or thumbnail field; unavailable metadata is labeled rather than invented.
- Development diagnostics report API-record counts, valid/unavailable locations, duplicate IDs/coordinates and actual cluster-layer entity counts. Duplicate-ID records remain visible with an explicit warning.
- OpenStreetMap remains the provider. A CSS filter integrates its tiles with the theme; tile failures show a retry message while camera entities remain usable.
- Fixed a filtering race in the clustering plugin's asynchronous zoom helper by using synchronous focus and cluster expansion.

## Validation

- Production Next.js build and TypeScript checking.
- Six Playwright tests in the installed Chrome browser, using isolated test-only API responses; production code always uses the existing API.
- Coordinate edge cases: null, empty/string, invalid ranges, nonfinite values, zero coordinates, duplicate IDs and coincident locations.
- Thirty coincident test cameras represented by a cluster labeled 30; search, all three filters, sorting, fit, both selection directions and persistent map identity.
- Missing locations, unmatched search and API failure states.
- Desktop and mobile route/overflow checks for Video Wall, Registry Map, Vehicle Trace, Watchlist & Alerts and Audit Log; smoke checks for landing, login, forgot password, reset password and request access.
- Audit search/outcome/date filtering and chain-verification interaction.
- Mobile camera sheet dismissal and expanded video Escape dismissal.
- Captured browser exceptions and React/key/hydration warnings during the map and route suites.

Run from `apps/web`: `npm test`, `npm run build`, and `node node_modules/typescript/bin/tsc --noEmit`. Browser tests use port 3100 and an installed Chrome channel.

## Remaining limits

Eight active camera records lack coordinates. Registry statuses remain the backend's last-known values, not independent live health checks. The schema does not supply city names or thumbnails. External OSM tiles and the development Google Fonts request encountered network restrictions in the test environment; map retry and system-font fallback remain available. Live authenticated API workflows, real stream playback, real alert delivery and permission enforcement were not exercised end-to-end; those backend integrations were preserved. No deployment was performed.

## Files changed

- Theme: `apps/web/app/globals.css`, `apps/web/tailwind.config.ts`.
- Shell: `apps/web/app/(dashboard)/layout.tsx`, `apps/web/components/top-bar.tsx`, `apps/web/components/nav-sidebar.tsx`.
- Registry: `apps/web/app/(dashboard)/registry/page.tsx`, `apps/web/components/registry-map.tsx`, new `apps/web/lib/camera-registry.ts`, new `apps/web/components/map-base-layer.tsx`.
- Other views: `apps/web/app/(dashboard)/video-wall/page.tsx`, `apps/web/app/(dashboard)/watchlist/page.tsx`, `apps/web/app/(dashboard)/audit/page.tsx`, `apps/web/components/live-feed.tsx`, `apps/web/components/trace-map.tsx`, `apps/web/components/alert-card.tsx`.
- Shared UI: `apps/web/components/ui/card.tsx`, `apps/web/components/ui/table.tsx`, `apps/web/components/ui/badge.tsx`, new `apps/web/lib/use-dialog-focus.ts`.
- Verification: new `apps/web/playwright.config.ts`, new `apps/web/tests/portal.spec.ts`, `apps/web/package.json`, `apps/web/package-lock.json`, `.gitignore`, this report.

The pre-existing local change to `services/ingestion-config/generated/go2rtc.yaml` was not modified by this implementation.
