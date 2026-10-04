import { useDocket } from '@/hooks'
import { env } from '@/lib/env'
import {
  MOCK_DOCKET_IN_FLIGHT,
  MOCK_DOCKET_REJECTED,
  MOCK_DOCKET_STAMPED,
} from '@/data/mockDocket'
import { useDocketStore } from '@/store/docketStore'

const MOCK_OPTIONS = [
  { id: MOCK_DOCKET_STAMPED.id, label: '202/55 · stamped (closed)' },
  { id: MOCK_DOCKET_REJECTED.id, label: '202/54 · rejected (closed)' },
  { id: MOCK_DOCKET_IN_FLIGHT.id, label: '202/55 · executing (in flight)' },
] as const

/**
 * Development aid select control for toggling between mock docket fixtures.
 * Appears ONLY when VITE_USE_MOCK_API is enabled.
 */
export function MockDocketSwitcher() {
  const docket = useDocket()
  const loadDocket = useDocketStore((state) => state.loadDocket)

  if (!env.useMockApi) {
    return null
  }

  return (
    <div className="flex items-center gap-1.5 text-xs">
      <label
        htmlFor="mock-docket-select"
        className="text-xs font-medium text-slate-400 whitespace-nowrap"
      >
        Mock Docket:
      </label>
      <select
        id="mock-docket-select"
        aria-label="Select mock docket"
        value={docket?.id ?? MOCK_DOCKET_STAMPED.id}
        onChange={(e) => void loadDocket(e.target.value)}
        className="rounded border border-amber-500/40 bg-surface-2 px-2 py-1 font-mono text-xs text-amber-200 focus:outline-none focus:ring-1 focus:ring-amber-400"
        title="Development aid: switch between mock docket fixtures"
      >
        {MOCK_OPTIONS.map((opt) => (
          <option key={opt.id} value={opt.id} className="bg-surface-1 text-slate-200">
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
