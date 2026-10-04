/**
 * ─────────────────────────────────────────────────────────────────────────────
 *  PROPOSED FRONTEND CONTRACT — NOT THE FINAL SCHEMA
 * ─────────────────────────────────────────────────────────────────────────────
 *  Status: PROPOSAL for Member 1 (Sudharshanan) to confirm, correct, or replace.
 *  Marker: TEMPORARY — replace with Member 1 schemas (BIND plan §4, M1 Del. A).
 *
 *  Purpose: a concrete strawman so the schema lock conversation is about
 *  editing fields, not inventing them. Nothing here is authoritative.
 *
 *  Rules honoured:
 *   - No routing / pricing / fallback logic is encoded here. Values are
 *     received from the backend and rendered.
 *   - Every enum whose true values are unknown is typed as `string` with a
 *     TODO, to avoid inventing a false enum that TS would then enforce.
 * ─────────────────────────────────────────────────────────────────────────────
 */

/* ── Enums ──────────────────────────────────────────────────────────────── */

/** TEMPORARY — replace with Member 1 schemas. Plan names these 4; real list TBC. */
export type ClaimType =
  | 'GEO.PARCEL'
  | 'REG.OWNER'
  | 'VIS.CROP'
  | 'ADV.FERTILIZER'
  | (string & {}); // allows unknown future claim types without breaking the UI

/** TEMPORARY — replace with Member 1 schemas.
 *  OPEN is the entry state; the middle states are implied by plan §1.2 and need
 *  confirmation; STAMPED/REJECTED are terminal. */
export type ClaimStatus =
  | 'OPEN'
  | 'PLANNED'
  | 'ROUTED'
  | 'EXECUTED'
  | 'VERIFIED'
  | 'STAMPED'
  | 'REJECTED'
  | (string & {});

export type DocketStatus = 'OPEN' | 'PLANNING' | 'EXECUTING' | 'BINDING' | 'COMPLETE' | 'ERROR' | (string & {});

/** TEMPORARY — Member 2 owns Harm Class routing; values unknown. Do not hardcode logic. */
export type HarmClass = string;

/** TEMPORARY — engine identity comes from the Router (Member 2). */
export type EngineId = string;

export type VerificationResult = 'PASSED' | 'FAILED' | 'PARTIAL' | 'SKIPPED' | (string & {});

/* ── Exhibit ────────────────────────────────────────────────────────────── */

export type ExhibitGeometry =
  | { type: 'Point'; coordinates: [number, number] }
  | { type: 'Polygon'; coordinates: number[][][] }
  | { type: 'MultiPolygon'; coordinates: number[][][][] };

export interface Exhibit {
  exhibit_id: string;
  claim_id: string;
  /** TEMPORARY — e.g. 'geometry' | 'land_record' | 'vision' | 'advisory'. TBC by M1. */
  exhibit_type: string;
  /** Short human-readable line for the claim card, e.g. "Parcel boundary verified". */
  summary: string;
  /** Per-type payload. Typed as unknown on purpose: refined once M1 publishes shapes. */
  payload?: unknown;
  /** GPS point / polygon for map display. The frontend never parses EXIF. */
  geometry?: ExhibitGeometry | null;
  /** Model or tool that produced it — render as-is, never hardcode model names. */
  engine_label?: string | null;
  confidence?: number | null; // 0..1
  cost_usd?: number | null;
  latency_ms?: number | null;
  source_ref?: string | null; // S3 key / DB record id (display only)
  created_at?: string | null; // ISO-8601 UTC
}

/* ── Claim ──────────────────────────────────────────────────────────────── */

export interface ClaimStateTransition {
  status: ClaimStatus;
  at: string; // ISO-8601 UTC
  note?: string | null;
}

export interface ClaimVerification {
  result: VerificationResult;
  /** Machine identifier of the failed cross-modal predicate, if any. */
  predicate?: string | null;
  /** Human-readable reason — REQUIRED by the UI when status is REJECTED. */
  reason?: string | null;
}

/** Member 2's escalation record, e.g. nova-lite 0.58 → terra. Display only. */
export interface ClaimEscalation {
  from_engine: EngineId;
  to_engine: EngineId;
  threshold?: number | null;
  reason?: string | null;
}

export interface Claim {
  claim_id: string;
  docket_id: string;
  claim_type: ClaimType;
  harm_class: HarmClass;
  status: ClaimStatus;
  engine?: EngineId | null;
  confidence?: number | null; // 0..1
  cost_usd?: number | null;
  exhibit?: Exhibit | null;
  verification?: ClaimVerification | null;
  escalation?: ClaimEscalation | null;
  state_history?: ClaimStateTransition[] | null;
  created_at?: string | null;
  updated_at?: string | null;
}

/* ── Cost (Cost Comparison Panel input) ─────────────────────────────────── */

export interface ClaimCostLine {
  claim_id: string;
  engine?: EngineId | null;
  cost_usd: number;
}

export interface CostSummary {
  /** Sum of the actually routed execution path. */
  routed_total_usd: number;
  /** The always-Terra counterfactual. QUESTION for M1/M2:
   *  does the backend compute this? If yes, the frontend only renders it. */
  always_terra_total_usd?: number | null;
  currency: string; // e.g. 'USD'
  budget_cap_usd?: number | null; // plan: Max $0.08 per request
  budget_remaining_usd?: number | null;
  per_claim?: ClaimCostLine[];
}

/* ── Docket ─────────────────────────────────────────────────────────────── */

export interface PlannerMeta {
  model: string; // render as-is
  plan_version?: string | null;
  planned_at?: string | null;
}

export interface Docket {
  docket_id: string;
  /** Gazetteer target, e.g. "202/55". */
  survey_number: string;
  status: DocketStatus;
  claims: Claim[];
  cost?: CostSummary | null;
  planner?: PlannerMeta | null;
  /** Optional initial viewport for the map. */
  bbox?: [number, number, number, number] | null;
  created_at?: string | null;
  updated_at?: string | null;
}

/* ── API envelope & endpoints ───────────────────────────────────────────── */

export interface OpenDocketRequest {
  text_request: string;
  /** GeoJSON bounds of the area of interest. */
  bounds?: ExhibitGeometry | null;
  /** S3 key or upload reference for the optional image. */
  image_ref?: string | null;
}

export interface ApiError {
  error_code: string;
  message: string;
  details?: unknown;
}

/** TEMPORARY — replace with Member 1 schemas (or generated from OpenAPI). */
export interface BindApi {
  openDocket(req: OpenDocketRequest): Promise<Docket>;
  getDocket(docketId: string): Promise<Docket>;
}

/* ── Frontend-only view models (NOT backend contract) ───────────────────── */

/** Derived in services/mappers.ts for display; never persisted, never sent. */
export interface CostView {
  routedTotal: number;
  baselineTotal: number | null;
  savings: number | null;
  savingsPct: number | null; // null when baseline is 0/absent → UI shows "—"
  currency: string;
  budgetCap: number | null;
  budgetRemaining: number | null;
  withinBudget: boolean | null;
}
