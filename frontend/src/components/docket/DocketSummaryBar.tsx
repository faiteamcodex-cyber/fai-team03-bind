import { StatusBadge } from '@/components/claims/StatusBadge'
import { formatDuration, formatUsd } from '@/lib/format'
import type { DocketView } from '@/services/mappers'

export interface DocketSummaryBarProps {
  docket: DocketView
  className?: string
}

export function DocketSummaryBar({ docket, className }: DocketSummaryBarProps) {
  return (
    <div
      className={[
        'flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface-2 px-4 py-2.5 text-xs',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="flex items-center gap-3">
        <StatusBadge status={docket.status} size="sm" />
        <span className="font-mono text-slate-300">{docket.id}</span>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-slate-400">
        <div>
          <span>Claims: </span>
          <strong className="font-mono text-slate-200">{docket.claims.length}</strong>
        </div>
        <div>
          <span>Total Cost: </span>
          <strong className="font-mono text-slate-200">
            {formatUsd(docket.cost.routedTotalUsd)}
          </strong>
        </div>
        <div>
          <span>Duration: </span>
          <strong className="font-mono text-slate-200">
            {formatDuration(docket.totalLatencyMs)}
          </strong>
        </div>
      </div>
    </div>
  )
}
