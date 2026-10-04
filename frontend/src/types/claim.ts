/**
 * ─────────────────────────────────────────────────────────────────────────────
 *  MIRRORED FROM MEMBER 1'S BACKEND SCHEMAS — DO NOT ADD FIELDS
 * ─────────────────────────────────────────────────────────────────────────────
 *  Source: `backend/app/schemas/models.py` → `Claim`, `RouteEntry`, `CostEntry`
 *
 *  Field names are exactly as Pydantic serialises them (`id`, not `claim_id` for
 *  the claim itself; `claim_id` only on the routing/cost ledger rows).
 * ─────────────────────────────────────────────────────────────────────────────
 */

import type { ClaimStatus, ClaimType, HarmClass } from './enums'

/**
 * `Claim` — a single claim within a docket.
 *
 * `value` and the written fields are null until the claim has been executed and
 * verified, which is why the UI must handle "not yet known" without inventing a
 * placeholder number.
 */
export interface Claim {
  readonly id: string
  readonly type: ClaimType
  readonly harm: HarmClass
  readonly status: ClaimStatus
  /** The resolved value (crop name, owner, advisory form, …). Opaque by contract. */
  readonly value: Record<string, unknown> | null
  /** 0..1, or null when the writer reports no confidence (e.g. deterministic tools). */
  readonly confidence: number | null
  /** Which model/tool wrote this claim, e.g. 'gis_tool', 'amazon.nova-lite-v1:0'. */
  readonly writer: string | null
  /** References into `Docket.exhibits`. */
  readonly exhibit_ids: readonly string[]
  /** Why the Binder stamped / rejected / abstained — shown verbatim in the UI. */
  readonly stamp_reason: string | null
  /** Claim IDs this claim depends on; execution resolves in dependency order. */
  readonly depends_on: readonly string[]
}

/** `RouteEntry` — a routing decision logged in the ledger. */
export interface RouteEntry {
  readonly claim_id: string
  /** Writer chosen by the Budget Compiler. 'ABSTAIN'/'NONE' are sentinel values. */
  readonly assigned_writer: string
  readonly reason: string
  readonly estimated_cost_usd: number
  readonly estimated_latency_ms: number
  readonly fallback_used: boolean
  readonly fallback_from: string | null
}

/** `CostEntry` — actual cost tracking for a single operation. */
export interface CostEntry {
  readonly claim_id: string
  readonly writer: string
  readonly input_tokens: number
  readonly output_tokens: number
  readonly cost_usd: number
  readonly latency_ms: number
}

/** Sentinel writers that mean "nothing was executed". */
export const ROUTE_SENTINEL_ABSTAIN = 'ABSTAIN'
export const ROUTE_SENTINEL_NONE = 'NONE'

/** True when a route assigned no real writer (budget exhaustion or no capability). */
export function isRouteSentinel(assignedWriter: string): boolean {
  const normalised = assignedWriter.trim().toUpperCase()
  return normalised === ROUTE_SENTINEL_ABSTAIN || normalised === ROUTE_SENTINEL_NONE
}
