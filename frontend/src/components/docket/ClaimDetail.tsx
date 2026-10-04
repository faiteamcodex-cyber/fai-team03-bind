import { StatusBadge } from '@/components/claims/StatusBadge'
import { formatConfidence, formatDuration, formatUsd, formatWriter } from '@/lib/format'
import { getStatusMeta } from '@/lib/status'
import type { ClaimView } from '@/services/mappers'

export interface ClaimDetailProps {
  claim: ClaimView | null
  onClose?: () => void
  className?: string
}

export function ClaimDetail({ claim, onClose, className }: ClaimDetailProps) {
  if (!claim) {
    return (
      <div className="flex h-full min-h-[180px] items-center justify-center p-6 text-center text-xs text-slate-500">
        Select a claim card to view detailed exhibits and routing logs.
      </div>
    )
  }

  const meta = getStatusMeta(claim.status)

  return (
    <div
      className={['flex flex-col gap-4 p-4 text-xs text-slate-300', className]
        .filter(Boolean)
        .join(' ')}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 border-b border-line pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-mono text-sm font-semibold text-slate-100">
              {claim.type}
            </h3>
            <StatusBadge status={claim.status} size="sm" />
          </div>
          <p className="mt-0.5 font-mono text-[11px] text-slate-500">ID: {claim.id}</p>
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close detail view"
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          >
            ✕
          </button>
        )}
      </div>

      {/* Reason verbatim callout */}
      {claim.stampReason !== null && (
        <div
          className={[
            'rounded-lg border p-3 text-xs leading-relaxed',
            meta.tone === 'danger'
              ? 'border-red-500/40 bg-red-950/20 text-red-200'
              : meta.tone === 'warning'
                ? 'border-amber-500/40 bg-amber-950/20 text-amber-200'
                : 'border-emerald-500/30 bg-emerald-950/20 text-emerald-200',
          ].join(' ')}
        >
          <span className="block text-[11px] font-semibold tracking-wide text-slate-400 uppercase">
            Kernel Reason
          </span>
          <p className="mt-1 text-slate-100">{claim.stampReason}</p>
        </div>
      )}

      {/* Metadata Grid */}
      <div className="grid grid-cols-2 gap-3 rounded-lg border border-line bg-surface-2 p-3">
        <div>
          <span className="block text-[10px] text-slate-500">Harm Class</span>
          <span className="font-semibold text-slate-200 uppercase">{claim.harm}</span>
        </div>
        <div>
          <span className="block text-[10px] text-slate-500">Confidence</span>
          <span className="font-mono text-slate-200">
            {formatConfidence(claim.confidence)}
          </span>
        </div>
        <div>
          <span className="block text-[10px] text-slate-500">Writer / Engine</span>
          <span className="font-mono text-slate-200">
            {formatWriter(claim.writer)}
          </span>
        </div>
        <div>
          <span className="block text-[10px] text-slate-500">Actual Cost</span>
          <span className="font-mono text-slate-200">{formatUsd(claim.costUsd)}</span>
        </div>
      </div>

      {/* Route Info */}
      {claim.route && (
        <div className="space-y-1 rounded-lg border border-line bg-surface-2 p-3">
          <span className="block text-[10px] font-semibold tracking-wide text-slate-400 uppercase">
            Routing Decision
          </span>
          <p className="text-slate-200">{claim.route.reason}</p>
          <div className="flex gap-4 font-mono text-[11px] text-slate-400 pt-1">
            <span>Est. Cost: {formatUsd(claim.route.estimated_cost_usd)}</span>
            <span>Est. Latency: {formatDuration(claim.route.estimated_latency_ms)}</span>
          </div>
        </div>
      )}

      {/* Exhibits list */}
      <div>
        <h4 className="mb-2 text-[11px] font-semibold tracking-wide text-slate-400 uppercase">
          Attached Exhibits ({claim.exhibits.length})
        </h4>
        {claim.exhibits.length === 0 ? (
          <p className="text-slate-500 italic">No exhibits attached.</p>
        ) : (
          <ul className="space-y-2">
            {claim.exhibits.map((exhibit) => (
              <li
                key={exhibit.id}
                className="space-y-1 rounded border border-line bg-surface-1 p-2.5"
              >
                <div className="flex items-center justify-between font-mono text-[11px]">
                  <span className="font-semibold text-slate-200">{exhibit.kind}</span>
                  <span className="text-slate-500">{exhibit.id}</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  <span>Source: </span>
                  <code className="text-slate-300">{exhibit.source_id}</code>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
