/**
 * ─────────────────────────────────────────────────────────────────────────────
 *  MIRRORED FROM MEMBER 1'S BACKEND SCHEMAS — DO NOT ADD FIELDS
 * ─────────────────────────────────────────────────────────────────────────────
 *  Source: `backend/app/schemas/models.py` → `Exhibit`, `AdvisoryForm`
 *
 *  `payload` is typed `dict[str, Any]` in Pydantic. In TypeScript that becomes
 *  `unknown` (never `any`), narrowed through the guards in `services/mappers.ts`.
 *  The payload interfaces below describe the *known* shapes produced by the
 *  kernel's connectors; they are read-only views, not the source of truth.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import type { ExhibitKind, ClaimType } from './enums'

/** GeoJSON geometry emitted by the GIS connector (geometry exhibit payload). */
export interface GeoJsonPolygonGeometry {
  readonly type: 'Polygon'
  readonly coordinates: number[][][]
}

export interface GeoJsonMultiPolygonGeometry {
  readonly type: 'MultiPolygon'
  readonly coordinates: number[][][][]
}

export interface GeoJsonPointGeometry {
  readonly type: 'Point'
  readonly coordinates: [number, number]
}

export type GeoJsonGeometry =
  | GeoJsonPolygonGeometry
  | GeoJsonMultiPolygonGeometry
  | GeoJsonPointGeometry

/**
 * `geometry` exhibit payload — a GeoJSON Feature produced by the GIS connector.
 * Properties observed in `backend/app/connectors/geography.py`.
 */
export interface ParcelFeatureProperties {
  readonly survey_number: string
  readonly village?: string
  readonly taluk?: string
  readonly district?: string
  readonly extent_acres?: number
  /** Permitted because the backend payload is open-ended; extra keys are ignored. */
  readonly [key: string]: unknown
}

export interface ParcelFeature {
  readonly type: 'Feature'
  readonly properties: ParcelFeatureProperties
  readonly geometry: GeoJsonGeometry
}

/** `image` exhibit payload — photo retrieval + bind status. */
export interface PhotoExhibitPayload {
  readonly image_uri: string
  readonly capture_time: string
  readonly gps_lat: number
  readonly gps_lon: number
  /** 'inside' = GPS falls within the target polygon. Anything else is unbound. */
  readonly bind_status: string
  readonly parcel_id: string
  readonly [key: string]: unknown
}

/** `registry_row` exhibit payload — mock land record. */
export interface RegistryRowPayload {
  readonly owner_name?: string
  readonly survey_number?: string
  readonly extent_acres?: number
  readonly [key: string]: unknown
}

/** `prediction` exhibit payload — vision model output. */
export interface VisionPredictionPayload {
  readonly crop?: string
  readonly stage?: string
  readonly condition?: string
  readonly label?: string
  readonly [key: string]: unknown
}

/** `advisory_rag` chunk exhibit payload. */
export interface AdvisoryChunkPayload {
  readonly text?: string
  readonly document?: string
  readonly page?: string
  readonly [key: string]: unknown
}

/**
 * `AdvisoryForm` — structured fertilizer/practice advisory.
 * Backend sets `extra: "forbid"`, so these are the only permitted keys.
 */
export interface AdvisoryForm {
  readonly crop: string
  readonly stage: string
  readonly product?: string | null
  readonly dose?: string | null
  readonly unit?: string | null
  readonly timing?: string | null
  readonly source_id: string
  readonly page?: string | null
}

/** `Exhibit` — a piece of evidence attached to a claim. */
export interface Exhibit {
  readonly id: string
  readonly kind: ExhibitKind
  /** Resolvable reference (registry row ID, S3 URI, cadastral source id). */
  readonly source_id: string
  /** Untyped in the contract; narrowed via the guards in mappers.ts. */
  readonly payload: Record<string, unknown>
  readonly created_ms: number
}

/** Narrowing helpers for the untyped payload bag. */
export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

export function isParcelFeature(value: unknown): value is ParcelFeature {
  if (!isRecord(value)) return false
  return value.type === 'Feature' && isRecord(value.geometry) && isRecord(value.properties)
}

export function isPhotoPayload(value: unknown): value is PhotoExhibitPayload {
  if (!isRecord(value)) return false
  return typeof value.gps_lat === 'number' && typeof value.gps_lon === 'number'
}

export function isVisionPrediction(value: unknown): value is VisionPredictionPayload {
  if (!isRecord(value)) return false
  return typeof value.crop === 'string' || typeof value.label === 'string'
}

export function isAdvisoryForm(value: unknown): value is AdvisoryForm {
  if (!isRecord(value)) return false
  return typeof value.crop === 'string' && typeof value.stage === 'string'
}

/** Convenience: which exhibit kind a claim type is expected to produce. */
export const EXPECTED_EXHIBIT_KIND: Readonly<Partial<Record<ClaimType, ExhibitKind>>> = {
  'GEO.PARCEL': 'geometry',
  'REG.OWNER': 'registry_row',
  'MEDIA.PHOTO': 'image',
  'VIS.CROP': 'prediction',
  'VIS.STAGE': 'prediction',
  'VIS.CONDITION': 'prediction',
  'ADV.FERTILIZER': 'form',
  'ADV.PRACTICE': 'form',
  'WX.CONTEXT': 'weather',
  'META.CLARIFY': 'chunk',
}
