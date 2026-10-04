import { formatPercent, formatUsd } from '@/lib/format'
import { isOverBaseline } from '@/services/mappers'
import type { CostView } from '@/services/mappers'

export interface CostBarProps {
  readonly cost: CostView
}

export function CostBar({ cost }: CostBarProps) {
  const { routedTotalUsd, baselineUsd, savingsUsd, savingsPct } = cost
  const overBaseline = isOverBaseline(cost)

  // Relative percentage calculation for bar width visualization
  const maxVal = Math.max(routedTotalUsd, baselineUsd ?? 0, 0.0001)
  const routedWidthPct = Math.min(
    100,
    Math.max(4, (routedTotalUsd / maxVal) * 100),
  )
  const baselineWidthPct =
    baselineUsd !== null
      ? Math.min(100, Math.max(4, (baselineUsd / maxVal) * 100))
      : 0

  return (
    <div className="space-y-3 rounded-lg border border-line bg-surface-1 p-4">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-slate-300">Cost Comparison</span>
        {baselineUsd === null ? (
          <span className="font-mono text-slate-400" data-testid="savings-badge">
            Savings: —
          </span>
        ) : overBaseline ? (
          <span
            className="font-mono font-medium text-amber-400"
            data-testid="over-baseline-warning"
          >
            Routing cost more than baseline by {formatUsd(Math.abs(savingsUsd ?? 0))}
          </span>
        ) : (
          <span
            className="font-mono font-semibold text-emerald-400"
            data-testid="savings-badge"
          >
            Saved {formatUsd(savingsUsd)} ({formatPercent(savingsPct)})
          </span>
        )}
      </div>

      <div className="space-y-2 text-xs">
        {/* Routed Cost Bar */}
        <div>
          <div className="mb-1 flex justify-between text-[11px] text-slate-400">
            <span>Routed Execution (Actual)</span>
            <span className="font-mono font-medium text-slate-200" data-numeric>
              {formatUsd(routedTotalUsd)}
            </span>
          </div>
          <div className="h-2.5 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                overBaseline ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${routedWidthPct}%` }}
              data-testid="routed-cost-bar"
            />
          </div>
        </div>

        {/* Baseline Cost Bar */}
        <div>
          <div className="mb-1 flex justify-between text-[11px] text-slate-400">
            <span>Always-VLM Baseline Estimate</span>
            <span className="font-mono font-medium text-slate-200" data-numeric>
              {formatUsd(baselineUsd)}
            </span>
          </div>
          <div className="h-2.5 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-sky-500/70 transition-all duration-300"
              style={{ width: `${baselineWidthPct}%` }}
              data-testid="baseline-cost-bar"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
