import { CostBar } from './CostBar'
import { CostBreakdownTable } from './CostBreakdownTable'
import { formatPercent, formatUsd } from '@/lib/format'
import { isOverBaseline } from '@/services/mappers'
import type { CostView } from '@/services/mappers'
import type { CostEntry, RouteEntry } from '@/types'

export interface CostComparisonPanelProps {
  readonly cost: CostView
  readonly costs: readonly CostEntry[]
  readonly routes?: readonly RouteEntry[]
  readonly className?: string
}

export function CostComparisonPanel({
  cost,
  costs,
  className = '',
}: CostComparisonPanelProps) {
  const overBaseline = isOverBaseline(cost)
  const estimatorDrift = cost.routedTotalUsd - cost.estimatedTotalUsd

  return (
    <div className={['space-y-4', className].filter(Boolean).join(' ')}>
      {/* 4-Card Summary Metrics Header */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* Metric 1: Actual Routed Cost */}
        <div className="rounded-lg border border-line bg-surface-1 p-3">
          <div className="text-[11px] font-medium text-slate-400">Actual Routed Cost</div>
          <div
            className="mt-1 font-mono text-base font-bold text-slate-100"
            data-numeric
            data-testid="actual-routed-cost"
          >
            {formatUsd(cost.routedTotalUsd)}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-400">Ledger actuals</div>
        </div>

        {/* Metric 2: Router's Estimate (Honesty Rule 3: Estimator Drift) */}
        <div className="rounded-lg border border-line bg-surface-1 p-3">
          <div className="text-[11px] font-medium text-slate-400">Router's Estimate</div>
          <div
            className="mt-1 font-mono text-base font-bold text-slate-200"
            data-numeric
            data-testid="router-estimated-cost"
          >
            {formatUsd(cost.estimatedTotalUsd)}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-400 font-mono">
            {estimatorDrift === 0
              ? 'Drift: $0.0000'
              : estimatorDrift > 0
                ? `Drift: +${formatUsd(estimatorDrift)}`
                : `Drift: -${formatUsd(Math.abs(estimatorDrift))}`}
          </div>
        </div>

        {/* Metric 3: Always-VLM Baseline Estimate */}
        <div className="rounded-lg border border-line bg-surface-1 p-3">
          <div className="text-[11px] font-medium text-slate-400">Always-VLM Baseline</div>
          <div
            className="mt-1 font-mono text-base font-bold text-slate-200"
            data-numeric
            data-testid="baseline-cost"
          >
            {formatUsd(cost.baselineUsd)}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-400">Counterfactual</div>
        </div>

        {/* Metric 4: Savings / Over Baseline Status */}
        <div className="rounded-lg border border-line bg-surface-1 p-3">
          <div className="text-[11px] font-medium text-slate-400">Cost Savings</div>
          {cost.baselineUsd === null ? (
            <div
              className="mt-1 font-mono text-base font-bold text-slate-400"
              data-numeric
              data-testid="savings-usd"
            >
              —
            </div>
          ) : overBaseline ? (
            <div
              className="mt-1 font-mono text-base font-bold text-amber-400"
              data-numeric
              data-testid="savings-usd"
            >
              +{formatUsd(Math.abs(cost.savingsUsd ?? 0))}
            </div>
          ) : (
            <div
              className="mt-1 font-mono text-base font-bold text-emerald-400"
              data-numeric
              data-testid="savings-usd"
            >
              {formatUsd(cost.savingsUsd)}
            </div>
          )}
          <div className="mt-0.5 text-[10px] text-slate-400 font-mono" data-testid="savings-pct">
            {cost.baselineUsd === null
              ? '—'
              : overBaseline
                ? 'Routing cost more than baseline'
                : formatPercent(cost.savingsPct)}
          </div>
        </div>
      </div>

      {/* Visual Comparison Bar */}
      <CostBar cost={cost} />

      {/* Per-Operation Cost Breakdown Table */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Operation Cost Ledger
        </h4>
        <CostBreakdownTable costs={costs} />
      </div>
    </div>
  )
}
