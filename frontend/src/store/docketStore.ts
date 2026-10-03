import { ApiError, bindApi } from '@/services'
import { toDocketView } from '@/services/mappers'
import type { DocketView } from '@/services/mappers'
import type { DocketLoadState } from '@/types'
import { DOCKET_STATUS } from '@/types'
import { create } from 'zustand'

export interface DocketState {
  readonly docket: DocketView | null
  readonly loadState: DocketLoadState
  readonly error: ApiError | null
  readonly selectedClaimId: string | null
  readonly selectedSurveyNumber: string | null
  readonly isPolling: boolean

  openDocket: (query: string) => Promise<void>
  loadDocket: (id: string) => Promise<void>
  refresh: () => Promise<void>
  selectClaim: (id: string | null) => void
  selectSurveyNumber: (surveyNumber: string | null) => void
  clearError: () => void
  startPolling: (intervalMs?: number) => void
  stopPolling: () => void
  reset: () => void
}

let pollingTimerId: ReturnType<typeof setInterval> | null = null

export const useDocketStore = create<DocketState>((set, get) => ({
  docket: null,
  loadState: 'idle',
  error: null,
  selectedClaimId: null,
  selectedSurveyNumber: null,
  isPolling: false,

  openDocket: async (query: string): Promise<void> => {
    set({ loadState: 'loading', error: null })
    try {
      const response = await bindApi.openDocket({ query })
      const docketView = toDocketView(response.docket)
      set({
        docket: docketView,
        loadState: 'ready',
        error: null,
      })
      if (
        docketView.status === DOCKET_STATUS.CLOSED ||
        docketView.status === DOCKET_STATUS.FAILED
      ) {
        get().stopPolling()
      }
    } catch (err) {
      const apiErr =
        err instanceof ApiError
          ? err
          : new ApiError(
              'server',
              err instanceof Error ? err.message : 'An unknown error occurred.',
            )
      set({ loadState: 'error', error: apiErr, docket: null })
    }
  },

  loadDocket: async (id: string): Promise<void> => {
    set({ loadState: 'loading', error: null })
    try {
      const response = await bindApi.getDocket(id)
      const docketView = toDocketView(response.docket)
      set({
        docket: docketView,
        loadState: 'ready',
        error: null,
      })
      if (
        docketView.status === DOCKET_STATUS.CLOSED ||
        docketView.status === DOCKET_STATUS.FAILED
      ) {
        get().stopPolling()
      }
    } catch (err) {
      const apiErr =
        err instanceof ApiError
          ? err
          : new ApiError(
              'server',
              err instanceof Error ? err.message : 'An unknown error occurred.',
            )
      set({ loadState: 'error', error: apiErr, docket: null })
    }
  },

  refresh: async (): Promise<void> => {
    const currentId = get().docket?.id
    if (currentId) {
      await get().loadDocket(currentId)
    }
  },

  selectClaim: (id: string | null): void => {
    set({ selectedClaimId: id })
  },

  selectSurveyNumber: (surveyNumber: string | null): void => {
    set({ selectedSurveyNumber: surveyNumber })
  },

  clearError: (): void => {
    set((state) => ({
      error: null,
      loadState: state.loadState === 'error' ? 'idle' : state.loadState,
    }))
  },

  startPolling: (intervalMs = 2000): void => {
    if (pollingTimerId !== null) {
      clearInterval(pollingTimerId)
      pollingTimerId = null
    }
    set({ isPolling: true })
    pollingTimerId = setInterval(() => {
      const currentId = get().docket?.id
      if (currentId) {
        void get().loadDocket(currentId)
      }
    }, intervalMs)
  },

  stopPolling: (): void => {
    if (pollingTimerId !== null) {
      clearInterval(pollingTimerId)
      pollingTimerId = null
    }
    set({ isPolling: false })
  },

  reset: (): void => {
    if (pollingTimerId !== null) {
      clearInterval(pollingTimerId)
      pollingTimerId = null
    }
    set({
      docket: null,
      loadState: 'idle',
      error: null,
      selectedClaimId: null,
      selectedSurveyNumber: null,
      isPolling: false,
    })
  },
}))
