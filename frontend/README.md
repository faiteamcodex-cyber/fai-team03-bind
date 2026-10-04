# BIND — Frontend (Member 4)

React single-page application for the BIND kernel: **CLAIM → BIND → STAMP**.
Owner: **Dinesh Kumar — Member 4, Frontend UI/UX Developer**.
Architecture source of truth: `BIND_Implementation_Plan.pdf` (repo root / team drive).

| Deliverable | Scope | Status |
|---|---|---|
| **A** | MapLibre GL integration + cadastral GeoJSON overlays | not started |
| **B** | Reactive Docket UI (claims moving `OPEN → STAMPED`, REJECTED handled) | not started |
| **C** | Cost Comparison Panel (routed vs always-Terra) | not started |

Until the backend is deployed this app runs against `services/mockApi.ts`, which returns
responses shaped like Member 1's schemas. Mock data is always labelled **MOCK DATA** in the UI.

---

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Build | Vite 8 | `npm run dev` / `build` / `preview` |
| UI | React **18.3.1** | pinned by plan §2.1 (template default is 19 — do not auto-upgrade) |
| Language | TypeScript 6 (`strict` + `noUncheckedIndexedAccess`) | `any` is treated as a bug |
| Styling | TailwindCSS 4 (CSS-first `@theme` tokens) | no `tailwind.config.js` in v4 |
| State | Zustand 5 | server state stays server-authoritative |
| Map | MapLibre GL 6 | isolated inside `src/components/map/` |
| Tests | Vitest 4 + React Testing Library + jsdom 26 | `npm test` |
| Lint | oxlint | `npm run lint` |

---

## Commands

```bash
npm install          # installs; .npmrc sets legacy-peer-deps (see Known constraints)
npm run dev          # dev server on http://localhost:5173
npm run build        # tsc -b && vite build
npm run preview      # serve the production build on :4173
npm test             # Vitest, single run
npm run test:watch   # Vitest, watch mode
npm run typecheck    # tsc -b --noEmit
npm run lint         # oxlint
```

---

## Environment

Copy `.env.example` → `.env.local` (git-ignored). Never hardcode endpoints.

| Variable | Meaning |
|---|---|
| `VITE_API_BASE_URL` | BIND API Gateway base URL (`ap-south-1`). Empty until SAM deploy. |
| `VITE_USE_MOCK_API` | `true` → mock layer; `false` → live API Gateway |
| `VITE_DEV_PORT` | dev port, used when allow-listing CORS on the API/S3 side |

---

## Structure

```
src/
├── components/
│   ├── layout/     AppShell, Header, Panel, StatusBadge
│   ├── docket/     DocketList, DocketSummary, status progression
│   ├── claims/     ClaimCard, ClaimDetail, ExhibitView
│   ├── map/        BindMap, layers, mapAdapter (only file that knows GeoJSON keys)
│   ├── cost/       CostComparisonPanel, CostBar
│   └── ...
├── pages/          Dashboard
├── store/          docketStore (Zustand)
├── services/       api.ts (transport) · mockApi.ts (fixtures) · mappers.ts (DTO → view model)
├── types/          MIRRORED from backend/app/schemas (enums/claim/exhibit/docket)
├── data/           mockDocket.ts · mockGeoJSON.ts    ← MOCK DATA, never real land records
├── hooks/          selector hooks
├── lib/            formatting, status metadata (icon + label + colour)
└── test/           setup.ts, shared render helpers
```

**Key boundary:** backend field names appear **only** in `types/` and `services/mappers.ts`.

**Contract status: LOCKED.** `src/types/` mirrors `backend/app/schemas/` in
`fai-team03-bind` (commit 71c6e80). The real statuses are
`OPEN → BINDING → STAMPED | REJECTED | ABSTAINED | DISPUTE`; endpoints are under
`/api/v1`. If Member 1 changes the models, regenerate `src/types/` — do not hand-edit.

---

## Known constraints (read before changing the toolchain)

1. **`.npmrc` sets `legacy-peer-deps=true`.** npm 10.8.2 aborts with
   `Cannot read properties of null (reading 'edgesOut')` when resolving the React 18 +
   `@types/react` 18 peer set. Remove the flag only after moving to Node 22 / npm 11.
2. **Node floor is 20.19.** Vite 8 requires `^20.19.0 || >=22.12.0`.
   `vitest` is pinned to **4.x** and `jsdom` to **26.x** deliberately: vitest 5 needs Node
   `^22.12` and jsdom 30 needs `^22.22.2`, so they fail on Node 20 (verified: jsdom 30
   crashes with `webidl.util.markAsUncloneable is not a function`).
3. **React 18 is intentional.** If a future dependency demands React 19, raise it with the
   team — the plan specifies React 18.
4. **`@testing-library/dom` is a direct devDependency** because `legacy-peer-deps` stops
   npm auto-installing peers; without it `screen` is not exported.
5. **Map basemap is undecided.** MapLibre requires a style; external tile providers add
   keys, licences and offline-preview failures. Development default: neutral background with
   GeoJSON layers only, basemap behind a toggle once the team picks a provider.
6. **Model names must never be hardcoded in React.** The plan names `gpt-5.6-luna/terra` and
   `nova-lite`, while the AWS Access Guide lists Ministral/Titan models. The UI renders
   `engine_label` / `model_id` exactly as the API returns them.
7. **The frontend never computes** routing, Harm Class, fallback decisions, pricing or
   point-in-polygon. It displays what the kernel returns; missing values render as `—`.

---

## Build order (one verified step at a time)

- [x] **1. Scaffold** — Vite + React 18 + TS strict + Tailwind + Vitest; build/test/lint green
- [x] 2. Design tokens + AppShell / Header / Panel / StatusBadge
- [x] 3. Contract layer — `types/` mirrored from the kernel, mock docket/GeoJSON, api + mockApi + mappers
- [ ] 4. Zustand `docketStore`
- [ ] 5. Dashboard layout
- [ ] 6. Docket UI + claim cards + status progression
- [ ] 7. MapLibre + GeoJSON overlays + claim↔map interaction
- [ ] 8. Cost Comparison Panel
- [ ] 9. API integration layer (swap mock → live)
- [ ] 10. Loading / error states, responsive polish, component tests, live integration

---

## Git workflow

Focused commits, one concern each. Example progression:

```
feat: initialize BIND frontend                     ← done
feat: add design tokens and app shell
feat: add docket contract layer and mock API
feat: add docket state management
feat: build docket dashboard
feat: add claim status components
feat: integrate MapLibre
feat: render cadastral GeoJSON
feat: add claim map interaction
feat: add cost comparison panel
feat: add API integration layer
test: add frontend component tests
feat: connect live BIND API
```
