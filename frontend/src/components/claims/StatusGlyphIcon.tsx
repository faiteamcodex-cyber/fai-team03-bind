import type { StatusGlyph, StatusTone } from '@/lib/status'

import { GLYPH_CLASSES, GLYPH_PATHS } from './statusTone'

export interface StatusGlyphIconProps {
  glyph: StatusGlyph
  tone: StatusTone
  className?: string
}

/**
 * Decorative status icon — the accessible name lives on the surrounding badge's
 * text, so this SVG is always hidden from assistive technology.
 */
export function StatusGlyphIcon({ glyph, tone, className }: StatusGlyphIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={['h-3.5 w-3.5 shrink-0', GLYPH_CLASSES[tone], className]
        .filter(Boolean)
        .join(' ')}
    >
      <path d={GLYPH_PATHS[glyph] ?? GLYPH_PATHS.unknown} />
    </svg>
  )
}
