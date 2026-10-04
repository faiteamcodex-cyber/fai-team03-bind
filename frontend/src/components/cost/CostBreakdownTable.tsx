import { formatCount, formatDuration, formatUsd, formatWriter } from '@/lib/format'
import type { CostEntry } from '@/types'

export interface CostBreakdownTableProps {
  readonly costs: readonly CostEntry[]
}

export function CostBreakdownTable({ costs }: CostBreakdownTableProps) {
  const totalInputTokens = costs.reduce((sum, c) => sum + c.input_tokens, 0)
  const totalOutputTokens = costs.reduce((sum, c) => sum + c.output_tokens, 0)
  const totalLatencyMs = costs.reduce((sum, c) => sum + c.latency_ms, 0)
  const totalCostUsd = costs.reduce((sum, c) => sum + c.cost_usd, 0)

  if (costs.length === 0) {
    return (
      <div className="py-6 text-center text-xs text-slate-400">
        No execution costs recorded yet.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-surface-1">
      <table className="w-full text-left text-xs text-slate-300">
        <thead className="border-b border-line bg-surface-2/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          <tr>
            <th scope="col" className="px-3 py-2">Operation</th>
            <th scope="col" className="px-3 py-2">Writer</th>
            <th scope="col" className="px-3 py-2 text-right">Input Tokens</th>
            <th scope="col" className="px-3 py-2 text-right">Output Tokens</th>
            <th scope="col" className="px-3 py-2 text-right">Latency</th>
            <th scope="col" className="px-3 py-2 text-right">Cost</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line/50">
          {costs.map((entry, index) => (
            <tr
              key={`${entry.claim_id}-${entry.writer}-${index}`}
              className="hover:bg-surface-2/40 transition-colors"
              data-testid="cost-breakdown-row"
            >
              <td className="px-3 py-2 font-mono text-slate-200">
                {entry.claim_id}
              </td>
              <td className="px-3 py-2 font-mono text-slate-300">
                {formatWriter(entry.writer)}
              </td>
              <td className="px-3 py-2 text-right font-mono text-slate-400" data-numeric>
                {formatCount(entry.input_tokens)}
              </td>
              <td className="px-3 py-2 text-right font-mono text-slate-400" data-numeric>
                {formatCount(entry.output_tokens)}
              </td>
              <td className="px-3 py-2 text-right font-mono text-slate-300" data-numeric>
                {formatDuration(entry.latency_ms)}
              </td>
              <td className="px-3 py-2 text-right font-mono font-medium text-emerald-300" data-numeric>
                {formatUsd(entry.cost_usd)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot className="border-t-2 border-line bg-surface-2/80 font-semibold text-slate-200">
          <tr>
            <td className="px-3 py-2 font-sans" colSpan={2}>
              Total ({costs.length} operations)
            </td>
            <td className="px-3 py-2 text-right font-mono" data-numeric>
              {formatCount(totalInputTokens)}
            </td>
            <td className="px-3 py-2 text-right font-mono" data-numeric>
              {formatCount(totalOutputTokens)}
            </td>
            <td className="px-3 py-2 text-right font-mono" data-numeric>
              {formatDuration(totalLatencyMs)}
            </td>
            <td className="px-3 py-2 text-right font-mono text-emerald-400" data-numeric>
              {formatUsd(totalCostUsd)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
