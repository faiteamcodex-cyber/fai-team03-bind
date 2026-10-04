import type { StatusGlyph, StatusTone } from '@/lib/status'

/**
 * Tone → Tailwind classes. Kept in a non-component module so the badge, the glyph
 * and future chart elements share one source of truth (and React Fast Refresh
 * stays happy).
 *
 * Classes are complete literal strings because Tailwind scans source text —
 * never build class names by concatenation.
 */
export const TONE_CLASSES: Readonly<Record<StatusTone, string>> = {
  neutral: 'border-slate-600/70 bg-slate-800/60 text-slate-200',
  progress: 'border-sky-500/40 bg-sky-500/10 text-sky-200',
  success: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  warning: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
  danger: 'border-red-500/40 bg-red-500/10 text-red-200',
}

/** Glyph stroke colour per tone. */
export const GLYPH_CLASSES: Readonly<Record<StatusTone, string>> = {
  neutral: 'text-slate-400',
  progress: 'text-sky-300',
  success: 'text-emerald-300',
  warning: 'text-amber-300',
  danger: 'text-red-300',
}

/** Inline SVG path data (24×24, stroke-based, no icon dependency). */
export const GLYPH_PATHS: Readonly<Record<StatusGlyph, string>> = {
  // ○ open / awaiting
  circle: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16z',
  // ◷ in progress
  clock: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zm0 4v4l3 2',
  // ✓ stamped
  check: 'M20 6 9 17l-5-5',
  // ⚠ rejected
  alert: 'M12 4 2 20h20L12 4zm0 6v5m0 3h.01',
  // — abstained (no stamp issued, but nothing was disproved)
  dash: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM8 12h8',
  // ⇄ dispute (conflicting evidence)
  conflict: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zm3 5-6 6m0-6 6 6',
  // ? unrecognised
  unknown: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zm0 4a3 3 0 0 1 0 6m0 3h.01',
}
