# AGENTS.md — BIND Frontend (Member 4)

Instructions for **any** AI coding tool working in this repository (Antigravity, Kiro,
Cursor, Claude Code, Copilot, ChatGPT, etc.).
Read this before writing code. It overrides generic "best practice" defaults.

---

## 1. Project

**BIND** — FarmwiseAI × TCE Product Challenge, team 03 (`fai-tce-team03-*`).
Event-driven, serverless orchestration kernel: **CLAIM → BIND → STAMP**.
This repository is **only the frontend** (React SPA).

### Repository layout — read first

The team repository is a **monorepo** and also contains the backend kernel
(Python/FastAPI, Lambda handlers, and `template.yaml` for AWS SAM).

```
<repo root>/
├── AGENTS.md              ← repo-wide rules (backend + frontend)
├── template.yaml          ← AWS SAM — Member 3 owns this
├── <backend code>/        ← Member 1 / Member 2 own this
└── frontend/              ← THIS app (Member 4). All npm commands run here.
    ├── AGENTS.md          ← you are reading the frontend copy
    ├── src/
    ├── docs/PROPOSED_frontend_contract.ts
    └── package.json
```

**Run every npm command from `frontend/`**, never from the repo root.

**Never edit, move or delete backend files** — not the Python packages, not
`template.yaml`, not the backend `.gitignore`. If a task seems to require a backend
change, stop and ask: the backend belongs to Members 1, 2 and 3.

Owner: **Dinesh Kumar — Member 4, Frontend UI/UX Developer**
Source of truth for architecture: `BIND_Implementation_Plan.pdf`.

| Deliverable | Scope |
|---|---|
| A | MapLibre GL integration + cadastral GeoJSON overlays |
| B | Reactive Docket UI (claims moving `OPEN → STAMPED`, plus `REJECTED`) |
| C | Cost Comparison Panel (routed execution vs always-Terra baseline) |

---

## 2. Hard rules — do not violate

1. **This is a frontend-only repository.** Never write Python, LangChain, Boto3,
   FastAPI, SQL, or infrastructure code here.
2. **Never implement backend business logic in React.** Routing decisions, Harm Class,
   pricing, model selection, vision fallback, point-in-polygon and cross-modal
   verification all happen in the kernel. The UI **displays** results; it does not
   compute them.
3. **Never call AWS Bedrock / Claude Platform / any model API from this app.** No AWS
   credentials may exist anywhere in this repo or in any `VITE_*` variable. Vite inlines
   every `VITE_*` value into the public JavaScript bundle.
4. **Never hardcode API URLs, model names (`luna`, `terra`, `nova-lite`), or prices.**
   Endpoints come from `import.meta.env`; model names and costs come from API payloads.
5. **`src/types/` mirrors the backend schemas — it is locked, and you must not extend
   it.** It was hand-mirrored from `backend/app/schemas/` (`enums.py`, `models.py`) at
   commit 71c6e80. `src/services/mappers.ts` is the only DTO → view-model translator.
   **Do not invent backend fields.** If a field is missing, render `—`. If the backend
   models change, regenerate `src/types/` from them — never guess, never add.
6. **Never use real land records.** All fixtures live in `src/data/` and must be
   labelled `MOCK DATA`. No real survey numbers, owners, or parcel geometry.
7. **Mock data must stay structurally compatible with the real API** — same field names,
   same nesting, same nullability.
8. **`any` is a bug.** `strict` + `noUncheckedIndexedAccess` are on. Use `unknown` and
   narrow it.
9. **Never claim something works unless you actually ran it.** Report build/test output.
10. **Do not commit** `.env.local`, credentials, `dist/`, or `node_modules/`.

---

## 3. Layer boundaries — where each kind of change belongs

```
components/  → presentation only. No fetch, no business rules.
store/       → Zustand: docket, claims, selection, map view, loading, error, cost.
hooks/       → selectors and effects.
services/    → the ONLY place that talks to the network.
  api.ts     → real transport (fetch), env-driven base URL
  mockApi.ts → same interface, returns fixtures
  mappers.ts → backend DTO → frontend view model (the only file that knows DTO field names)
types/       → MIRRORED from backend/app/schemas (locked; regenerate, never guess)
data/        → MOCK fixtures (docket + GeoJSON)
lib/         → pure helpers: formatting, status metadata, env access
components/map/ → MapLibre isolated here. mapAdapter.ts is the ONLY file that knows
                  GeoJSON property keys.
```

**If a task touches backend field names, stop and ask — do not guess.**

---

## 4. Conventions

- **React 18.3.1 (pinned)** — do not upgrade to React 19; the plan specifies 18.
- TypeScript strict; explicit return types on exported functions.
- Tailwind v4 (CSS-first `@theme` in `src/index.css`). **No `tailwind.config.js`.**
- Design language: dark, dense, technical operations dashboard. Neutral slate shell.
  **Colour is reserved for status** — no gradients, no decorative animation, no
  chatbot-style UI.
- **Status is never colour alone** — always icon + text + colour (`✓ STAMPED`,
  `⚠ REJECTED`, `● OPEN`). Use `src/lib/status.ts`; unknown statuses must render
  safely instead of crashing.
- Semantic HTML, keyboard reachable, visible focus ring, `aria-label` on icon-only
  controls, sufficient contrast.
- Prefer small pure functions in `lib/` that are unit-testable.

---

## 5. Toolchain constraints (already solved — don't "fix" these)

| Thing | Why it is the way it is |
|---|---|
| `.npmrc` sets `legacy-peer-deps=true` | npm 10.8.2 crashes resolving the React 18 peer set (`Cannot read properties of null (reading 'edgesOut')`) |
| `vitest` pinned to **4.x**, `jsdom` to **26.x** | vitest 5 needs Node ^22.12; jsdom 30 needs Node ^22.22.2 and crashes on Node 20 |
| `@testing-library/dom` is a direct dependency | `legacy-peer-deps` stops npm auto-installing peers |
| `VITE_ALLOWED_HOSTS` | dev-server host allow-list for container/tunnel URLs; no hostname is hardcoded |
| No `baseUrl` in tsconfig | deprecated in TypeScript 6; `paths` resolve relative to the tsconfig |

---

## 6. Verify before you say "done"

```bash
npm run typecheck   # tsc -b --noEmit
npm run lint        # oxlint
npm test            # vitest run
npm run build       # tsc -b && vite build
npm run dev         # http://localhost:5173
```

All four must pass. Then commit one concern at a time, e.g.
`feat: add cost comparison panel` — never a mixed-concern commit.

---

## 7. Escalate instead of guessing

Ask a human (Member 4 / Dinesh) when:

- a backend field, enum value or status transition is unknown → **ask, don't invent**
- a dependency upgrade would break the pins above
- a task requires AWS access, credentials, or a model call
- the team's GeoJSON is not yet available (use the labelled fixture, don't fabricate
  realistic-looking land records)
