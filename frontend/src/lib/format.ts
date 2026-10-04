/**
 * Presentation-level formatting.
 *
 * Rules:
 *  - Missing / unusable values render as an em dash, never `NaN` or `Infinity`.
 *  - Money is presented in USD with enough precision to show sub-cent amounts
 *    (the kernel's cost table has entries at $0.001 and $0.003).
 *  - Timestamps arrive as epoch milliseconds (see `types/docket.ts`).
 *  - Nothing here computes business values — these are formatters only.
 */

/** Shown whenever a value is unavailable. */
export const EMPTY_VALUE = '—'

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)

/**
 * Format a USD amount.
 * Defaults to 4 decimals so sub-cent costs stay legible ($0.0030, not $0.00).
 */
export function formatUsd(value: number | null | undefined, decimals = 4): string {
  if (!isFiniteNumber(value)) return EMPTY_VALUE
  return `$${value.toFixed(decimals)}`
}

/** Percentage from a 0..100 input. Returns an em dash when not computable. */
export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (!isFiniteNumber(value)) return EMPTY_VALUE
  return `${value.toFixed(decimals)}%`
}

/** Confidence as a 0..1 ratio, shown to 2 decimals to match the 0.65 threshold. */
export function formatConfidence(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return EMPTY_VALUE
  return value.toFixed(2)
}

/** Epoch milliseconds → local time, e.g. "3 Oct 2026, 11:04". */
export function formatEpochMs(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return EMPTY_VALUE
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return EMPTY_VALUE

  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/** Epoch milliseconds → local time only, e.g. "11:04:22". */
export function formatEpochTime(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return EMPTY_VALUE
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return EMPTY_VALUE

  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

/** Duration in milliseconds → "820 ms" or "3.4 s". */
export function formatDuration(value: number | null | undefined): string {
  if (!isFiniteNumber(value) || value < 0) return EMPTY_VALUE
  if (value < 1000) return `${Math.round(value)} ms`
  return `${(value / 1000).toFixed(1)} s`
}

/** Integer token counts with thousands separators. */
export function formatCount(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) return EMPTY_VALUE
  return new Intl.NumberFormat().format(value)
}

/**
 * Human label for a writer / model identifier.
 * The kernel returns raw ids (`amazon.nova-lite-v1:0`, `gis_tool`); the UI shows
 * them verbatim when no friendly label is known, and NEVER invents one.
 */
export function formatWriter(writer: string | null | undefined): string {
  if (typeof writer !== 'string' || writer.trim() === '') return EMPTY_VALUE
  return writer.trim()
}
