import { useMemo } from 'react'

import { useDocketStore } from '@/store/docketStore'
import type { ApiError } from '@/services'
import type {
  ClaimStatusCounts,
  ClaimView,
  CostView,
  DocketView,
  MapView,
} from '@/services/mappers'
import type { DocketLoadState } from '@/types'

const EMPTY_CLAIMS: readonly ClaimView[] = []
const EMPTY_COUNTS: ClaimStatusCounts = {}

/** Returns the current active `DocketView` or `null`. */
export function useDocket(): DocketView | null {
  return useDocketStore((state) => state.docket)
}

/** Returns a readonly array of `ClaimView` for the current docket. */
export function useClaims(): readonly ClaimView[] {
  return useDocketStore((state) => state.docket?.claims ?? EMPTY_CLAIMS)
}

/** Returns the currently selected `ClaimView` or `null`. */
export function useSelectedClaim(): ClaimView | null {
  return useDocketStore((state) => {
    if (!state.docket || !state.selectedClaimId) return null
    return state.docket.claims.find((claim) => claim.id === state.selectedClaimId) ?? null
  })
}

/** Returns counts per claim status for the current docket. */
export function useClaimStatusCounts(): ClaimStatusCounts {
  const claims = useClaims()
  return useMemo(() => {
    if (claims.length === 0) return EMPTY_COUNTS
    const counts: Record<string, number> = {}
    for (const claim of claims) {
      counts[claim.status] = (counts[claim.status] ?? 0) + 1
    }
    return counts
  }, [claims])
}

/** Returns the `CostView` model for the current docket or `null`. */
export function useCostView(): CostView | null {
  return useDocketStore((state) => state.docket?.cost ?? null)
}

/** Returns the `MapView` model for the current docket or `null`. */
export function useMapView(): MapView | null {
  return useDocketStore((state) => state.docket?.map ?? null)
}

/** Returns the current docket fetch load state (`'idle' | 'loading' | 'ready' | 'error'`). */
export function useLoadState(): DocketLoadState {
  return useDocketStore((state) => state.loadState)
}

/** Returns the current API error or `null`. */
export function useError(): ApiError | null {
  return useDocketStore((state) => state.error)
}

/** Returns whether polling is currently active. */
export function useIsPolling(): boolean {
  return useDocketStore((state) => state.isPolling)
}

/** Returns the currently selected survey number or `null`. */
export function useSelectedSurveyNumber(): string | null {
  return useDocketStore((state) => state.selectedSurveyNumber)
}
