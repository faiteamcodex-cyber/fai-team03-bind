/**
 * DTO → view-model boundary.
 *
 * This is the **only** module allowed to know backend field names. Components and
 * the store consume the view models below, so a backend rename lands here and
 * nowhere else.
 *
 * Mappers never invent values: anything the kernel did not report becomes `null`
 * and the component renders an em dash.
 */

import { isParcelFeature, isPhotoPayload } from '@/types'
import type {
  Claim,
  ClaimType,
  CostEntry,
  Docket,
  Exhibit,
  HarmClass,
  ParcelFeature,
  PhotoExhibitPayload,
  RouteEntry,
} from '@/types'

/* ── Claim view model ──────────────────────────────────────────────────── */

export interface ClaimView {
  readonly id: string
  readonly type: ClaimType
  readonly harm: HarmClass
  readonly status: string
  /** 0..1 or null — null means the writer reports no confidence. */
  readonly confidence: number | null
  readonly writer: string | null
  readonly stampReason: string | null
  readonly exhibitIds: readonly string[]
  readonly dependsOn: readonly string[]
  /** Exhibits resolved from the docket pool, in claim order. */
  readonly exhibits: readonly Exhibit[]
  /** Routing decision for this claim, if the ledger has one. */
  readonly route: RouteEntry | null
  /** Actual cost rows for this claim (may be empty while still executing). */
  readonly costs: readonly CostEntry[]
  readonly costUsd: number
}

export function toClaimView(claim: Claim, docket: Docket): ClaimView {
  const exhibits = claim.exhibit_ids
    .map((id) => docket.exhibits.find((e) => e.id === id))
    .filter((e): e is Exhibit => e !== undefined)

  const costs = docket.costs.filter((c) => c.claim_id === claim.id)
  const route = docket.routes.find((r) => r.claim_id === claim.id) ?? null

  return {
    id: claim.id,
    type: claim.type,
    harm: claim.harm,
    status: claim.status,
    confidence: claim.confidence,
    writer: claim.writer,
    stampReason: claim.stamp_reason,
    exhibitIds: claim.exhibit_ids,
    dependsOn: claim.depends_on,
    exhibits,
    route,
    costs,
    costUsd: costs.reduce((sum, entry) => sum + entry.cost_usd, 0),
  }
}

export function toClaimViews(docket: Docket): readonly ClaimView[] {
  return docket.claims.map((claim) => toClaimView(claim, docket))
}

/** Counts per status, for the docket header and filters. */
export type ClaimStatusCounts = Readonly<Record<string, number>>

export function countClaimsByStatus(docket: Docket): ClaimStatusCounts {
  const counts: Record<string, number> = {}
  for (const claim of docket.claims) {
    counts[claim.status] = (counts[claim.status] ?? 0) + 1
  }
  return counts
}

/* ── Cost view model (Cost Comparison Panel) ───────────────────────────── */

export interface CostView {
  readonly routedTotalUsd: number
  /** Backend-provided baseline. null when the kernel did not report one. */
  readonly baselineUsd: number | null
  /** routed − baseline, negative when routing cost more than the baseline. */
  readonly savingsUsd: number | null
  /** Percentage saved. null when the baseline is 0 or absent (never Infinity). */
  readonly savingsPct: number | null
  readonly perClaim: readonly {
    readonly claimId: string
    readonly writer: string
    readonly costUsd: number
  }[]
  /** Sum of route estimates — compare with actuals to spot estimator drift. */
  readonly estimatedTotalUsd: number
}

/**
 * Build the cost comparison. All values are presentation-level derivations of
 * numbers the backend already computed; no pricing logic lives here.
 */
export function toCostView(docket: Docket): CostView {
  const routedTotalUsd = docket.total_cost_usd
  const baseline = docket.always_vlm_estimate_usd

  // A missing or non-positive baseline makes percentage savings undefined —
  // the UI shows an em dash rather than Infinity or NaN.
  const baselineUsd = Number.isFinite(baseline) && baseline > 0 ? baseline : null
  const savingsUsd = baselineUsd === null ? null : baselineUsd - routedTotalUsd
  const savingsPct =
    baselineUsd === null || savingsUsd === null ? null : (savingsUsd / baselineUsd) * 100

  return {
    routedTotalUsd,
    baselineUsd,
    savingsUsd,
    savingsPct,
    perClaim: docket.costs.map((entry) => ({
      claimId: entry.claim_id,
      writer: entry.writer,
      costUsd: entry.cost_usd,
    })),
    estimatedTotalUsd: docket.routes.reduce((sum, r) => sum + r.estimated_cost_usd, 0),
  }
}

/**
 * True when routing spent more than the always-VLM baseline. Possible in principle
 * (many cheap calls can cost more than one expensive one) and the UI should say so
 * honestly rather than always claiming savings.
 */
export function isOverBaseline(cost: CostView): boolean {
  return cost.savingsUsd !== null && cost.savingsUsd < 0
}

/* ── Map view model ────────────────────────────────────────────────────── */

export interface MapParcel {
  readonly surveyNumber: string
  readonly isTarget: boolean
  readonly feature: ParcelFeature
}

export interface MapPhotoPoint {
  readonly claimId: string
  readonly surveyNumber: string
  readonly lat: number
  readonly lon: number
  /** 'inside' means the kernel verified the point lies within the polygon. */
  readonly bindStatus: string
  readonly isBound: boolean
  readonly imageUri: string
  readonly captureTime: string
}

export interface MapView {
  readonly parcels: readonly MapParcel[]
  readonly photos: readonly MapPhotoPoint[]
}

/** Extract a parcel geometry exhibit from a claim, if present. */
export function findParcelExhibit(claim: Claim, docket: Docket): ParcelFeature | null {
  for (const id of claim.exhibit_ids) {
    const exhibit = docket.exhibits.find((e) => e.id === id)
    if (exhibit?.kind === 'geometry' && isParcelFeature(exhibit.payload)) {
      // `payload` is Record<string, unknown>; the guard narrows it to a Feature.
      return exhibit.payload as unknown as ParcelFeature
    }
  }
  return null
}

function toPhotoPoint(exhibit: Exhibit): MapPhotoPoint | null {
  if (exhibit.kind !== 'image') return null
  if (!isPhotoPayload(exhibit.payload)) return null
  const payload: PhotoExhibitPayload = exhibit.payload

  return {
    claimId: exhibit.id,
    surveyNumber: payload.parcel_id,
    lat: payload.gps_lat,
    lon: payload.gps_lon,
    bindStatus: payload.bind_status,
    isBound: payload.bind_status === 'inside',
    imageUri: payload.image_uri,
    captureTime: payload.capture_time,
  }
}

/**
 * Build everything the map needs: the target parcel, its claimed geometry and the
 * photo GPS points. Point-in-polygon is **not** recomputed here — `bindStatus` is
 * the kernel's own verdict.
 */
export function toMapView(docket: Docket, targetSurveyNumber?: string | null): MapView {
  const parcels: MapParcel[] = []
  const effectiveTarget =
    targetSurveyNumber !== undefined ? targetSurveyNumber : docket.survey_number

  for (const claim of docket.claims) {
    if (claim.type !== 'GEO.PARCEL') continue
    const feature = findParcelExhibit(claim, docket)
    if (!feature) continue
    parcels.push({
      surveyNumber: feature.properties.survey_number,
      isTarget: feature.properties.survey_number === effectiveTarget,
      feature,
    })
  }

  const photos = docket.exhibits
    .map(toPhotoPoint)
    .filter((point): point is MapPhotoPoint => point !== null)

  return { parcels, photos }
}

/* ── Docket view model ─────────────────────────────────────────────────── */

export interface DocketView {
  readonly id: string
  readonly query: string
  readonly surveyNumber: string | null
  readonly villageId: string | null
  readonly status: string
  readonly imageProvided: boolean
  readonly claims: readonly ClaimView[]
  readonly cost: CostView
  readonly map: MapView
  readonly costs: readonly CostEntry[]
  readonly routes: readonly RouteEntry[]
  readonly createdMs: number
  readonly closedMs: number | null
  readonly totalLatencyMs: number
}

export function toDocketView(docket: Docket): DocketView {
  return {
    id: docket.id,
    query: docket.query,
    surveyNumber: docket.survey_number,
    villageId: docket.village_id,
    status: docket.status,
    imageProvided: docket.image_provided,
    claims: toClaimViews(docket),
    cost: toCostView(docket),
    map: toMapView(docket),
    costs: docket.costs,
    routes: docket.routes,
    createdMs: docket.created_ms,
    closedMs: docket.closed_ms,
    totalLatencyMs: docket.total_latency_ms,
  }
}
