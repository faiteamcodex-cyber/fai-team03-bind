import { StatusGlyphIcon } from './StatusGlyphIcon'
import { TONE_CLASSES } from './statusTone'

import { getStatusMeta } from '@/lib/status'

export interface StatusBadgeProps {
  /** Raw status value from the backend. Unknown values render safely. */
  status: string
  /** `sm` for claim rows, `md` for detail panes and the docket header. */
  size?: 'sm' | 'md'
  className?: string
}

/**
 * The single way claim status is displayed anywhere in BIND.
 *
 * Accessibility contract:
 *  - the visible label is always the status word (never colour alone)
 *  - `role="status"` + `aria-label` carry the plain-language meaning
 *  - the icon is decorative (`aria-hidden`) so screen readers do not repeat it
 */
export function StatusBadge({ status, size = 'sm', className }: StatusBadgeProps) {
  const meta = getStatusMeta(status)

  const sizeClasses =
    size === 'md'
      ? 'gap-1.5 px-2.5 py-1 text-xs tracking-wide'
      : 'gap-1.5 px-2 py-0.5 text-[11px] tracking-wide'

  return (
    <span
      role="status"
      aria-label={`Status: ${meta.srLabel}`}
      data-status={meta.label}
      data-tone={meta.tone}
      className={[
        'inline-flex items-center rounded border font-semibold uppercase',
        sizeClasses,
        TONE_CLASSES[meta.tone],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <StatusGlyphIcon glyph={meta.glyph} tone={meta.tone} />
      <span>{meta.label}</span>
    </span>
  )
}
