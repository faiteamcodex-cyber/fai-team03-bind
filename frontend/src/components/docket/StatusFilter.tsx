import { StatusBadge } from '@/components/claims/StatusBadge'
import { CLAIM_STATUS_ORDER } from '@/lib/status'
import type { ClaimStatusCounts } from '@/services/mappers'

export interface StatusFilterProps {
  selectedStatus: string | null
  onSelectStatus: (status: string | null) => void
  counts: ClaimStatusCounts
  totalCount: number
  className?: string
}

export function StatusFilter({
  selectedStatus,
  onSelectStatus,
  counts,
  totalCount,
  className,
}: StatusFilterProps) {
  return (
    <div
      className={['flex flex-wrap items-center gap-1.5', className]
        .filter(Boolean)
        .join(' ')}
    >
      <button
        type="button"
        onClick={() => onSelectStatus(null)}
        className={[
          'inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-semibold tracking-wide transition-colors',
          selectedStatus === null
            ? 'border-slate-500 bg-slate-700 text-slate-100'
            : 'border-line bg-surface-2 text-slate-400 hover:text-slate-200',
        ].join(' ')}
      >
        <span>ALL</span>
        <span className="font-mono opacity-80">({totalCount})</span>
      </button>

      {CLAIM_STATUS_ORDER.map((status) => {
        const count = counts[status] ?? 0
        const isSelected = selectedStatus === status
        if (count === 0 && !isSelected) return null

        return (
          <button
            key={status}
            type="button"
            onClick={() => onSelectStatus(isSelected ? null : status)}
            className={[
              'inline-flex items-center gap-1.5 rounded transition-opacity',
              isSelected
                ? 'ring-2 ring-slate-400 ring-offset-1 ring-offset-surface-0'
                : 'opacity-80 hover:opacity-100',
            ].join(' ')}
          >
            <StatusBadge status={status} size="sm" />
            <span className="font-mono text-[11px] text-slate-400">({count})</span>
          </button>
        )
      })}
    </div>
  )
}
