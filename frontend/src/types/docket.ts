/**
 * ─────────────────────────────────────────────────────────────────────────────
 *  MIRRORED FROM MEMBER 1'S BACKEND SCHEMAS — DO NOT ADD FIELDS
 * ─────────────────────────────────────────────────────────────────────────────
 *  Source: `backend/app/schemas/models.py` → `Docket`, `DocketRequest`,
 *          `DocketResponse`
 *  Endpoints: `backend/app/api/routes.py` (prefix `/api/v1`)
 *
 *  Timestamps are **epoch milliseconds** (`created_ms`, `closed_ms`), not ISO
 *  strings. Format them through `lib/format.ts`.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import type { DocketStatus } from './enums'
import type { Claim, CostEntry, RouteEntry } from './claim'
import type { Exhibit } from './exhibit'

/** `Docket` — the top-level object that drives the whole BIND lifecycle. */
export interface Docket {
  readonly id: string
  readonly query: string
  readonly village_id: string | null
  /** Gazetteer target extracted from the query, e.g. "202/55". */
  readonly survey_number: string | null
  readonly image_provided: boolean
  readonly status: DocketStatus

  readonly claims: readonly Claim[]
  /** Flat exhibit pool; claims reference these by id. */
  readonly exhibits: readonly Exhibit[]
  /** Routing ledger — one entry per claim, in planning order. */
  readonly routes: readonly RouteEntry[]
  /** Actual cost ledger — one entry per executed operation. */
  readonly costs: readonly CostEntry[]

  /** Sum of `costs[].cost_usd`. */
  readonly total_cost_usd: number
  /** Wall-clock duration of the full kernel run. */
  readonly total_latency_ms: number
  /**
   * Counterfactual baseline: what this docket would have cost if the teacher
   * vision model ("VLM B") had been used for everything. This is the number the
   * Cost Comparison Panel compares against — the frontend does not compute it.
   */
  readonly always_vlm_estimate_usd: number

  readonly created_ms: number
  readonly closed_ms: number | null
}

/** `DocketRequest` — POST /api/v1/docket */
export interface DocketRequest {
  /** The user's natural language request. Minimum length 5 (backend-validated). */
  readonly query: string
  readonly village_filter?: string | null
  /** Optional attached photo, base64 encoded. */
  readonly image_base64?: string | null
}

/** `DocketResponse` — the full docket returned to the client. */
export interface DocketResponse {
  readonly docket: Docket
  /** Officer-facing one-paragraph note. Absent on GET by id (backend sends null). */
  readonly summary: string | null
}

/** `GET /api/v1/dockets` list row. */
export interface DocketListRow {
  readonly id: string
  readonly query: string
  readonly status: DocketStatus
  readonly claims_count: number
  readonly cost_usd: number
}

/** `GET /api/v1/health` */
export interface HealthResponse {
  readonly status: string
  readonly service: string
  readonly team: string
}

/** Client-side state of the docket fetch. */
export type DocketLoadState = 'idle' | 'loading' | 'ready' | 'error'
