import type { ReactNode } from 'react'

import { dataSourceMode, getEnvConfigIssues } from '@/lib/env'

export interface HeaderProps {
  /** Docket currently open, e.g. "202/55". `null` before a docket is loaded. */
  docketId?: string | null
  /** Optional status node (a StatusBadge) for the docket itself. */
  statusSlot?: ReactNode
  /** Optional slot for dev/mock docket switcher control. */
  docketSwitcherSlot?: ReactNode
}

/**
 * Application header: identity on the left, docket context on the right.
 *
 * The mock/live badge is deliberate — BIND rule 11/19 requires that data provenance
 * is never ambiguous, especially while Member 1's backend is not yet deployed.
 */
export function Header({ docketId, statusSlot, docketSwitcherSlot }: HeaderProps) {
  const configIssues = getEnvConfigIssues()

  return (
    <header className="border-b border-line bg-surface-1">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3">
        <div className="flex items-baseline gap-3">
          <span className="text-lg font-semibold tracking-tight text-slate-50">
            BIND
          </span>
          <span className="hidden text-xs text-slate-500 sm:inline">
            Claim · Bind · Stamp
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {docketSwitcherSlot}
          {statusSlot}

          <dl className="flex items-baseline gap-2 text-xs">
            <dt className="text-slate-500">Docket</dt>
            <dd
              className="font-mono text-sm text-slate-100"
              aria-live="polite"
              aria-atomic="true"
            >
              {docketId ?? '—'}
            </dd>
          </dl>

          <DataSourceBadge />
        </div>
      </div>

      {configIssues.length > 0 && (
        <p
          role="alert"
          className="border-t border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-200"
        >
          Configuration: {configIssues.join(' ')}
        </p>
      )}
    </header>
  )
}

/** Shows whether the UI is reading fixtures or the live kernel. */
function DataSourceBadge() {
  const isMock = dataSourceMode === 'mock'

  return (
    <span
      data-source={dataSourceMode}
      title={
        isMock
          ? 'Reading mock API fixtures. Backend integration is pending.'
          : 'Reading the live BIND API Gateway.'
      }
      className={[
        'inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase',
        isMock
          ? 'border-amber-500/40 bg-amber-500/10 text-amber-200'
          : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
      ].join(' ')}
    >
      <span
        aria-hidden="true"
        className={[
          'h-1.5 w-1.5 rounded-full',
          isMock ? 'bg-amber-300' : 'bg-emerald-300',
        ].join(' ')}
      />
      {isMock ? 'Mock data' : 'Live API'}
    </span>
  )
}
