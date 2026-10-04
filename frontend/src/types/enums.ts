/**
 * ─────────────────────────────────────────────────────────────────────────────
 *  MIRRORED FROM MEMBER 1'S BACKEND SCHEMAS — DO NOT ADD FIELDS
 * ─────────────────────────────────────────────────────────────────────────────
 *  Source of truth: `backend/app/schemas/enums.py`
 *  (faiteamcodex-cyber/fai-team03-bind, commit 71c6e80)
 *
 *  These are the real enumerations used by the BIND kernel. If the backend
 *  changes them, this file must be regenerated — never guessed at.
 *
 *  Naming: the backend uses `StrEnum`, so the *values* are the contract.
 *  Values are preserved exactly, including letter case.
 * ─────────────────────────────────────────────────────────────────────────────
 */

/** `ClaimType` — all claim types in the agriculture catalog. */
export const CLAIM_TYPE = {
  GEO_PARCEL: 'GEO.PARCEL',
  REG_OWNER: 'REG.OWNER',
  MEDIA_PHOTO: 'MEDIA.PHOTO',
  VIS_CROP: 'VIS.CROP',
  VIS_STAGE: 'VIS.STAGE',
  VIS_CONDITION: 'VIS.CONDITION',
  ADV_FERTILIZER: 'ADV.FERTILIZER',
  ADV_PRACTICE: 'ADV.PRACTICE',
  WX_CONTEXT: 'WX.CONTEXT',
  META_CLARIFY: 'META.CLARIFY',
} as const

export type ClaimType = (typeof CLAIM_TYPE)[keyof typeof CLAIM_TYPE]

/** `HarmClass` — harm-if-wrong classification. **Lower-case values.** */
export const HARM_CLASS = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const

export type HarmClass = (typeof HARM_CLASS)[keyof typeof HARM_CLASS]

/** `ClaimStatus` — lifecycle status of a claim within a docket. */
export const CLAIM_STATUS = {
  OPEN: 'OPEN',
  BINDING: 'BINDING',
  STAMPED: 'STAMPED',
  REJECTED: 'REJECTED',
  ABSTAINED: 'ABSTAINED',
  DISPUTE: 'DISPUTE',
} as const

export type ClaimStatus = (typeof CLAIM_STATUS)[keyof typeof CLAIM_STATUS]

/** `ExhibitKind` — type of evidence attached to a claim. **Lower-case values.** */
export const EXHIBIT_KIND = {
  GEOMETRY: 'geometry',
  REGISTRY_ROW: 'registry_row',
  IMAGE: 'image',
  PREDICTION: 'prediction',
  CHUNK: 'chunk',
  WEATHER: 'weather',
  FORM: 'form',
} as const

export type ExhibitKind = (typeof EXHIBIT_KIND)[keyof typeof EXHIBIT_KIND]

/** `DocketStatus` — overall docket lifecycle status. */
export const DOCKET_STATUS = {
  PLANNING: 'PLANNING',
  EXECUTING: 'EXECUTING',
  VERIFYING: 'VERIFYING',
  CLOSED: 'CLOSED',
  FAILED: 'FAILED',
} as const

export type DocketStatus = (typeof DOCKET_STATUS)[keyof typeof DOCKET_STATUS]

/** Runtime membership checks — useful when narrowing untyped API strings. */
const CLAIM_STATUS_VALUES: readonly string[] = Object.values(CLAIM_STATUS)
const CLAIM_TYPE_VALUES: readonly string[] = Object.values(CLAIM_TYPE)
const HARM_CLASS_VALUES: readonly string[] = Object.values(HARM_CLASS)
const EXHIBIT_KIND_VALUES: readonly string[] = Object.values(EXHIBIT_KIND)
const DOCKET_STATUS_VALUES: readonly string[] = Object.values(DOCKET_STATUS)

export const isClaimStatus = (value: string): value is ClaimStatus =>
  CLAIM_STATUS_VALUES.includes(value)
export const isClaimType = (value: string): value is ClaimType =>
  CLAIM_TYPE_VALUES.includes(value)
export const isHarmClass = (value: string): value is HarmClass =>
  HARM_CLASS_VALUES.includes(value)
export const isExhibitKind = (value: string): value is ExhibitKind =>
  EXHIBIT_KIND_VALUES.includes(value)
export const isDocketStatus = (value: string): value is DocketStatus =>
  DOCKET_STATUS_VALUES.includes(value)

/**
 * Default harm class per claim type — mirrored from `CLAIM_HARM_MAP` in
 * `backend/app/schemas/models.py`. Used **only** for display defaults and sorting
 * when the backend omits `harm`; the frontend never decides routing.
 */
export const CLAIM_HARM_MAP: Readonly<Record<ClaimType, HarmClass>> = {
  [CLAIM_TYPE.GEO_PARCEL]: HARM_CLASS.HIGH,
  [CLAIM_TYPE.REG_OWNER]: HARM_CLASS.HIGH,
  [CLAIM_TYPE.MEDIA_PHOTO]: HARM_CLASS.HIGH,
  [CLAIM_TYPE.VIS_CROP]: HARM_CLASS.MEDIUM,
  [CLAIM_TYPE.VIS_STAGE]: HARM_CLASS.MEDIUM,
  [CLAIM_TYPE.VIS_CONDITION]: HARM_CLASS.MEDIUM,
  [CLAIM_TYPE.ADV_FERTILIZER]: HARM_CLASS.CRITICAL,
  [CLAIM_TYPE.ADV_PRACTICE]: HARM_CLASS.HIGH,
  [CLAIM_TYPE.WX_CONTEXT]: HARM_CLASS.LOW,
  [CLAIM_TYPE.META_CLARIFY]: HARM_CLASS.LOW,
}
