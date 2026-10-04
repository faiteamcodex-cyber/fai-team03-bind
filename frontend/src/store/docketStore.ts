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
        selectedSurveyNumber: docketView.surveyNumber,
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
        selectedSurveyNumber: docketView.surveyNumber,
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
    if (id === null) {
      set({ selectedClaimId: null, selectedSurveyNumber: null })
      return
    }

    const currentDocket = get().docket
    if (!currentDocket) {
      set({ selectedClaimId: id })
      return
    }

    const claim = currentDocket.claims.find((c) => c.id === id)
    if (!claim) {
      set({ selectedClaimId: id })
      return
    }

    let targetSurvey: string | null = null

    // Check geometry exhibits
    for (const exhibit of claim.exhibits) {
      if (
        exhibit.kind === 'geometry' &&
        typeof exhibit.payload === 'object' &&
        exhibit.payload !== null
      ) {
        const payloadObj = exhibit.payload as Record<string, unknown>
        if (
          'properties' in payloadObj &&
          typeof payloadObj.properties === 'object' &&
          payloadObj.properties !== null
        ) {
          const props = payloadObj.properties as Record<string, unknown>
          if (typeof props.survey_number === 'string') {
            targetSurvey = props.survey_number
            break
          }
        }
      }
    }

    // Check image exhibit parcel_id
    if (targetSurvey === null && claim.type === 'MEDIA.PHOTO') {
      for (const exhibit of claim.exhibits) {
        if (
          exhibit.kind === 'image' &&
          typeof exhibit.payload === 'object' &&
          exhibit.payload !== null
        ) {
          const payloadObj = exhibit.payload as Record<string, unknown>
          if (typeof payloadObj.parcel_id === 'string') {
            targetSurvey = payloadObj.parcel_id
            break
          }
        }
      }
    }

    // Fallback for GEO.PARCEL
    if (targetSurvey === null && claim.type === 'GEO.PARCEL') {
      targetSurvey = currentDocket.surveyNumber
    }

    if (targetSurvey !== null) {
      set({ selectedClaimId: id, selectedSurveyNumber: targetSurvey })
    } else {
      // Non-geometry claim: leave selectedSurveyNumber unchanged
      set({ selectedClaimId: id })
    }
  },

  selectSurveyNumber: (surveyNumber: string | null): void => {
    if (surveyNumber === null) {
      set({ selectedSurveyNumber: null, selectedClaimId: null })
      return
    }

    const currentDocket = get().docket
    if (!currentDocket) {
      set({ selectedSurveyNumber: surveyNumber })
      return
    }

    let matchingClaimId: string | null = null
    for (const claim of currentDocket.claims) {
      for (const exhibit of claim.exhibits) {
        if (
          exhibit.kind === 'geometry' &&
          typeof exhibit.payload === 'object' &&
          exhibit.payload !== null
        ) {
          const payloadObj = exhibit.payload as Record<string, unknown>
          if (
            'properties' in payloadObj &&
            typeof payloadObj.properties === 'object' &&
            payloadObj.properties !== null
          ) {
            const props = payloadObj.properties as Record<string, unknown>
            if (props.survey_number === surveyNumber) {
              matchingClaimId = claim.id
              break
            }
          }
        }
      }
      if (matchingClaimId) break
    }

    if (!matchingClaimId) {
      const geoClaim = currentDocket.claims.find((c) => c.type === 'GEO.PARCEL')
      if (geoClaim) matchingClaimId = geoClaim.id
    }

    set({
      selectedSurveyNumber: surveyNumber,
      selectedClaimId: matchingClaimId ?? get().selectedClaimId,
    })
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
