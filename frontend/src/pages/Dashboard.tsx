import { useEffect } from 'react'

import { StatusBadge } from '@/components/claims/StatusBadge'
import { AppShell } from '@/components/layout/AppShell'
import { EmptyState } from '@/components/layout/EmptyState'
import { Header } from '@/components/layout/Header'
import { Panel } from '@/components/layout/Panel'
import { useDocket, useError, useLoadState } from '@/hooks'
import { CLAIM_STATUS_ORDER } from '@/lib/status'
import { MOCK_DEFAULT_DOCKET_ID } from '@/services/mockApi'
import { useDocketStore } from '@/store/docketStore'
import { DOCKET_STATUS } from '@/types'

export function Dashboard() {
  const docket = useDocket()
  const loadState = useLoadState()
  const error = useError()
  const loadDocket = useDocketStore((state) => state.loadDocket)
  const refresh = useDocketStore((state) => state.refresh)

  useEffect(() => {
    if (loadState === 'idle') {
      void loadDocket(MOCK_DEFAULT_DOCKET_ID)
    }
  }, [loadState, loadDocket])

  const isInProgress =
    docket &&
    (docket.status === DOCKET_STATUS.PLANNING ||
      docket.status === DOCKET_STATUS.EXECUTING ||
      docket.status === DOCKET_STATUS.VERIFYING)

  return (
    <AppShell
      header={
        <Header
          docketId={docket?.id ?? null}
          statusSlot={
            docket ? <StatusBadge status={docket.status} size="md" /> : null
          }
        />
      }
    >
      {loadState === 'error' && error ? (
        <div
          role="alert"
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-red-200"
        >
          <div>
            <h3 className="text-sm font-semibold">API Error</h3>
            <p className="mt-1 text-xs">{error.detail ?? error.message}</p>
          </div>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded bg-red-500/20 px-3 py-1.5 text-xs font-semibold text-red-100 hover:bg-red-500/30"
          >
            Retry
          </button>
        </div>
      ) : null}

      {isInProgress && (
        <div
          role="status"
          className="mb-4 flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-200"
        >
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
            <span>
              Docket processing in progress:{' '}
              <strong className="font-semibold uppercase">{docket.status}</strong>
            </span>
          </div>
          <StatusBadge status={docket.status} size="sm" />
        </div>
      )}

      {loadState === 'loading' && !docket ? (
        <div className="grid h-full grid-cols-1 gap-3 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <Panel
            id="map"
            title="Cadastral map"
            description="Survey parcels, target parcel and vision GPS point."
            className="min-h-[320px]"
          >
            <div className="flex h-full min-h-[280px] items-center justify-center p-6 text-center">
              <p className="text-xs text-slate-400">Loading docket data...</p>
            </div>
          </Panel>

          <div className="grid min-h-0 grid-rows-[minmax(0,2fr)_minmax(0,1fr)] gap-3">
            <Panel
              id="docket"
              title="Docket"
              description="Claims moving OPEN → STAMPED; rejected claims show the kernel's reason."
            >
              <div className="flex h-full min-h-[160px] items-center justify-center p-6">
                <p className="text-xs text-slate-400">Loading docket claims...</p>
              </div>
            </Panel>

            <Panel
              id="cost"
              title="Cost comparison"
              description="Routed execution vs. always-Terra baseline."
            >
              <div className="flex h-full min-h-[100px] items-center justify-center p-4">
                <p className="text-xs text-slate-400">Loading cost estimates...</p>
              </div>
            </Panel>
          </div>
        </div>
      ) : !docket && loadState !== 'loading' ? (
        <EmptyState
          action={
            <button
              type="button"
              onClick={() => void loadDocket(MOCK_DEFAULT_DOCKET_ID)}
              className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700"
            >
              Load Default Docket
            </button>
          }
        />
      ) : (
        <div className="grid h-full grid-cols-1 gap-3 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          {/* Deliverable A — MapLibre + cadastral GeoJSON */}
          <Panel
            id="map"
            title="Cadastral map"
            description="Survey parcels, target parcel and vision GPS point."
            actions={<StatusBadge status="OPEN" />}
            className="min-h-[320px]"
          >
            <div className="flex h-full min-h-[280px] items-center justify-center p-6 text-center">
              <p className="max-w-sm text-xs leading-relaxed text-slate-500">
                Map region. MapLibre GL and the cadastral GeoJSON fixture are added in
                Steps 7–8 of the frontend build order.
              </p>
            </div>
          </Panel>

          <div className="grid min-h-0 grid-rows-[minmax(0,2fr)_minmax(0,1fr)] gap-3">
            {/* Deliverable B — Reactive Docket UI */}
            <Panel
              id="docket"
              title="Docket"
              description="Claims moving OPEN → STAMPED; rejected claims show the kernel's reason."
              actions={
                docket ? (
                  <span className="font-mono text-xs text-slate-400">
                    {docket.claims.length} claims
                  </span>
                ) : undefined
              }
            >
              <div className="space-y-3 p-4">
                <p className="text-xs text-slate-500">
                  Docket region. Claim cards arrive in Step 6 once the contract layer
                  exists (Step 3).
                </p>

                <div className="border-t border-line pt-3">
                  <p className="mb-2 text-[11px] font-medium tracking-wide text-slate-500 uppercase">
                    Status vocabulary currently supported
                  </p>
                  <ul className="flex flex-wrap gap-1.5">
                    {CLAIM_STATUS_ORDER.map((status) => (
                      <li key={status}>
                        <StatusBadge status={status} />
                      </li>
                    ))}
                    <li>
                      <StatusBadge status="REJECTED" />
                    </li>
                  </ul>
                  <p className="mt-2 text-[11px] text-slate-500">
                    Mirrored from Member 1&apos;s <code>backend/app/schemas/enums.py</code>{' '}
                    (ClaimStatus). Unknown values from the backend still render safely
                    instead of breaking the dashboard.
                  </p>
                </div>
              </div>
            </Panel>

            {/* Deliverable C — Cost Comparison Panel */}
            <Panel
              id="cost"
              title="Cost comparison"
              description="Routed execution vs. always-Terra baseline."
            >
              <div className="p-4">
                <p className="text-xs text-slate-500">
                  Cost region. Figures come from the backend's cost summary — the
                  frontend never prices anything itself (Step 8).
                </p>
              </div>
            </Panel>
          </div>
        </div>
      )}
    </AppShell>
  )
}
