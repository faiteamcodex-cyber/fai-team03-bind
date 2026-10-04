/**
 * Status presentation metadata.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 *  VALUES MIRRORED FROM MEMBER 1'S BACKEND SCHEMAS — do not invent statuses
 * ─────────────────────────────────────────────────────────────────────────────
 *  Source: `backend/app/schemas/enums.py` (ClaimStatus, DocketStatus)
 *
 *  ClaimStatus : OPEN → BINDING → STAMPED | REJECTED | ABSTAINED | DISPUTE
 *  DocketStatus: PLANNING → EXECUTING → VERIFYING → CLOSED | FAILED
 *
 *  There is no PLANNED/ROUTED/EXECUTED/VERIFIED claim state — planning and
 *  routing are docket-level phases, and the kernel sets those on the docket.
 *
 *  Design rules:
 *   - Status is NEVER communicated by colour alone (icon + text + colour).
 *   - An unknown status must render safely rather than crash the dashboard.
 *   - This file only *labels* values it is given; it never decides them.
 * ─────────────────────────────────────────────────────────────────────────────
 */

/** Visual tone. Colour is additive information, never the only information. */
export type StatusTone = 'neutral' | 'progress' | 'success' | 'warning' | 'danger'

/** Glyph key rendered as an inline SVG by `StatusBadge`. */
export type StatusGlyph =
  | 'circle'
  | 'clock'
  | 'check'
  | 'alert'
  | 'dash'
  | 'conflict'
  | 'unknown'

export interface StatusMeta {
  /** Display label, exactly as the backend spells it. */
  readonly label: string
  readonly tone: StatusTone
  readonly glyph: StatusGlyph
  /** Spoken label for assistive technology. */
  readonly srLabel: string
  /** True when the kernel will not change this status again. */
  readonly terminal: boolean
}

/* ── ClaimStatus ───────────────────────────────────────────────────────── */

const CLAIM_STATUS_REGISTRY: Readonly<Record<string, StatusMeta>> = {
  OPEN: {
    label: 'OPEN',
    tone: 'neutral',
    glyph: 'circle',
    srLabel: 'Open, awaiting binding',
    terminal: false,
  },
  BINDING: {
    label: 'BINDING',
    tone: 'progress',
    glyph: 'clock',
    srLabel: 'Binding in progress',
    terminal: false,
  },
  STAMPED: {
    label: 'STAMPED',
    tone: 'success',
    glyph: 'check',
    srLabel: 'Stamped and accepted',
    terminal: true,
  },
  REJECTED: {
    label: 'REJECTED',
    tone: 'danger',
    glyph: 'alert',
    srLabel: 'Rejected',
    terminal: true,
  },
  ABSTAINED: {
    label: 'ABSTAINED',
    tone: 'warning',
    glyph: 'dash',
    srLabel: 'Abstained, no stamp issued',
    terminal: true,
  },
  DISPUTE: {
    label: 'DISPUTE',
    tone: 'warning',
    glyph: 'conflict',
    srLabel: 'In dispute, requires review',
    terminal: false,
  },
}

/* ── DocketStatus ──────────────────────────────────────────────────────── */

const DOCKET_STATUS_REGISTRY: Readonly<Record<string, StatusMeta>> = {
  PLANNING: {
    label: 'PLANNING',
    tone: 'progress',
    glyph: 'clock',
    srLabel: 'Planning claims',
    terminal: false,
  },
  EXECUTING: {
    label: 'EXECUTING',
    tone: 'progress',
    glyph: 'clock',
    srLabel: 'Executing claims',
    terminal: false,
  },
  VERIFYING: {
    label: 'VERIFYING',
    tone: 'progress',
    glyph: 'clock',
    srLabel: 'Verifying exhibits',
    terminal: false,
  },
  CLOSED: {
    label: 'CLOSED',
    tone: 'success',
    glyph: 'check',
    srLabel: 'Docket closed',
    terminal: true,
  },
  FAILED: {
    label: 'FAILED',
    tone: 'danger',
    glyph: 'alert',
    srLabel: 'Docket failed',
    terminal: true,
  },
}

function unknownStatusMeta(raw: string): StatusMeta {
  const label = raw.trim() === '' ? 'UNKNOWN' : raw.trim().toUpperCase()
  return {
    label,
    tone: 'neutral',
    glyph: 'unknown',
    srLabel: `${label} (unrecognised status)`,
    terminal: false,
  }
}

/** Resolve claim-status presentation. Unknown values render as-is, never hidden. */
export function getStatusMeta(status: string): StatusMeta {
  return CLAIM_STATUS_REGISTRY[status.trim().toUpperCase()] ?? unknownStatusMeta(status)
}

/** Resolve docket-status presentation. */
export function getDocketStatusMeta(status: string): StatusMeta {
  return DOCKET_STATUS_REGISTRY[status.trim().toUpperCase()] ?? unknownStatusMeta(status)
}

export function isKnownStatus(status: string): boolean {
  return status.trim().toUpperCase() in CLAIM_STATUS_REGISTRY
}

export function isKnownDocketStatus(status: string): boolean {
  return status.trim().toUpperCase() in DOCKET_STATUS_REGISTRY
}

/** Claim statuses ordered from untouched to decided, for filters and legends. */
export const CLAIM_STATUS_ORDER: readonly string[] = [
  'OPEN',
  'BINDING',
  'STAMPED',
  'REJECTED',
  'ABSTAINED',
  'DISPUTE',
] as const

/** Outcome statuses a closed docket reports. */
export const CLAIM_OUTCOME_STATUSES: readonly string[] = [
  'STAMPED',
  'REJECTED',
  'ABSTAINED',
  'DISPUTE',
] as const
