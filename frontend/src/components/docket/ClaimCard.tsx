import type { KeyboardEvent } from 'react'

import { StatusBadge } from '@/components/claims/StatusBadge'
import { formatConfidence, formatUsd, formatWriter } from '@/lib/format'
import { getStatusMeta } from '@/lib/status'
import type { ClaimView } from '@/services/mappers'

export interface ClaimCardProps {
  claim: ClaimView
  isSelected?: boolean
  onSelect?: (id: string) => void
  className?: string
}

export function ClaimCard({
  claim,
  isSelected = false,
  onSelect,
  className,
}: ClaimCardProps) {
  const meta = getStatusMeta(claim.status)

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if ((e.key === 'Enter' || e.key === ' ') && onSelect) {
      e.preventDefault()
      onSelect(claim.id)
    }
  }

  const isPending = claim.status === 'OPEN' || claim.status === 'BINDING'
  const displayCost = isPending ? '—' : formatUsd(claim.costUsd)
  const displayConfidence = formatConfidence(claim.confidence)

  // Tone-specific border & background styles
  const toneBorderClass =
    meta.tone === 'danger'
      ? 'border-red-500/40 bg-red-950/10 hover:border-red-500/60'
      : meta.tone === 'warning'
        ? 'border-amber-500/40 bg-amber-950/10 hover:border-amber-500/60'
        : meta.tone === 'success'
          ? 'border-emerald-500/30 bg-emerald-950/10 hover:border-emerald-500/50'
          : meta.tone === 'progress'
            ? 'border-blue-500/30 bg-blue-950/10 hover:border-blue-500/50'
            : 'border-line bg-surface-2 hover:border-slate-600'

  const selectedClass = isSelected
    ? 'ring-2 ring-sky-400 ring-offset-2 ring-offset-surface-0'
    : ''

  return (
    <div
      role="button"
      tabIndex={0}
      data-status={claim.status}
      data-tone={meta.tone}
      data-claim-id={claim.id}
      aria-pressed={isSelected}
      onClick={() => onSelect?.(claim.id)}
      onKeyDown={handleKeyDown}
      className={[
        'group flex cursor-pointer flex-col gap-2 rounded-lg border p-3 transition-all outline-none focus-visible:ring-2 focus-visible:ring-sky-400',
        toneBorderClass,
        selectedClass,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {/* Top row: Type, Harm, Status */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-slate-100">
            {claim.type}
          </span>
          <span
            className={[
              'rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase',
              claim.harm === 'critical'
                ? 'bg-red-500/20 text-red-300'
                : claim.harm === 'high'
                  ? 'bg-amber-500/20 text-amber-300'
                  : 'bg-slate-700 text-slate-300',
            ].join(' ')}
          >
            {claim.harm}
          </span>
        </div>
        <StatusBadge status={claim.status} size="sm" />
      </div>

      {/* Detail metadata row */}
      <div className="grid grid-cols-3 gap-2 border-t border-line/60 pt-2 text-[11px] text-slate-400">
        <div>
          <span className="block text-[10px] text-slate-500">Writer</span>
          <span className="truncate font-mono text-slate-300">
            {formatWriter(claim.writer)}
          </span>
        </div>

        <div>
          <span className="block text-[10px] text-slate-500">Confidence</span>
          <span className="font-mono text-slate-300">{displayConfidence}</span>
        </div>

        <div>
          <span className="block text-[10px] text-slate-500">Cost</span>
          <span className="font-mono text-slate-300">{displayCost}</span>
        </div>
      </div>

      {/* Stamp reason verbatim callout */}
      {claim.stampReason !== null && (
        <div
          className={[
            'mt-1 rounded p-2 text-xs leading-relaxed',
            meta.tone === 'danger'
              ? 'border border-red-500/30 bg-red-500/10 text-red-200'
              : meta.tone === 'warning'
                ? 'border border-amber-500/30 bg-amber-500/10 text-amber-200'
                : 'border border-line/40 bg-surface-1/60 text-slate-300',
          ].join(' ')}
        >
          <p className="font-medium text-[11px] tracking-wide text-slate-400 uppercase">
            Reason:
          </p>
          <p className="mt-0.5 text-xs text-slate-200">{claim.stampReason}</p>
        </div>
      )}
    </div>
  )
}
