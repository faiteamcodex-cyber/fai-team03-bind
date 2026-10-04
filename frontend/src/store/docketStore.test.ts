import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  useClaims,
  useClaimStatusCounts,
  useCostView,
  useDocket,
  useLoadState,
  useMapView,
  useSelectedClaim,
} from '@/hooks'
import { configureMockApi } from '@/services'
import { MOCK_DEFAULT_DOCKET_ID } from '@/services/mockApi'

import { useDocketStore } from './docketStore'

describe('docketStore', () => {
  beforeEach(() => {
    configureMockApi({ latencyMs: 0, simulateFailure: false })
    useDocketStore.getState().reset()
    vi.useRealTimers()
  })

  afterEach(() => {
    useDocketStore.getState().stopPolling()
    vi.useRealTimers()
  })

  it('starts with initial idle state', () => {
    const state = useDocketStore.getState()
    expect(state.docket).toBeNull()
    expect(state.loadState).toBe('idle')
    expect(state.error).toBeNull()
    expect(state.selectedClaimId).toBeNull()
    expect(state.selectedSurveyNumber).toBeNull()
    expect(state.isPolling).toBe(false)
  })

  it('sets ready and populates a DocketView on successful loadDocket', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)

    const state = useDocketStore.getState()
    expect(state.loadState).toBe('ready')
    expect(state.docket).not.toBeNull()
    expect(state.docket?.id).toBe(MOCK_DEFAULT_DOCKET_ID)
    expect(state.docket?.surveyNumber).toBe('202/55')
    expect(state.error).toBeNull()
  })

  it('sets ready and populates a DocketView on successful openDocket', async () => {
    await useDocketStore.getState().openDocket('Verify survey 202/55')

    const state = useDocketStore.getState()
    expect(state.loadState).toBe('ready')
    expect(state.docket).not.toBeNull()
    expect(state.error).toBeNull()
  })

  it('sets error with an ApiError and leaves docket null on failed load', async () => {
    configureMockApi({ latencyMs: 0, simulateFailure: true })

    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)

    const state = useDocketStore.getState()
    expect(state.loadState).toBe('error')
    expect(state.docket).toBeNull()
    expect(state.error).not.toBeNull()
    expect(state.error?.kind).toBe('network')
  })

  it('updates selectedClaimId and selectedSurveyNumber when a geometry claim is selected', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)
    useDocketStore.getState().selectClaim('clm-geo0a1')

    expect(useDocketStore.getState().selectedClaimId).toBe('clm-geo0a1')
    expect(useDocketStore.getState().selectedSurveyNumber).toBe('202/55')

    useDocketStore.getState().selectClaim(null)
    expect(useDocketStore.getState().selectedClaimId).toBeNull()
    expect(useDocketStore.getState().selectedSurveyNumber).toBeNull()
  })

  it('leaves selectedSurveyNumber unchanged when a non-geometry claim is selected', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)
    useDocketStore.getState().selectSurveyNumber('202/55')

    // clm-wxc0a1 is WX.CONTEXT (non-geometry)
    useDocketStore.getState().selectClaim('clm-wxc0a1')
    expect(useDocketStore.getState().selectedClaimId).toBe('clm-wxc0a1')
    expect(useDocketStore.getState().selectedSurveyNumber).toBe('202/55')
  })

  it('updates selectedClaimId when selectSurveyNumber is called', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)
    useDocketStore.getState().selectSurveyNumber('202/55')

    expect(useDocketStore.getState().selectedSurveyNumber).toBe('202/55')
    expect(useDocketStore.getState().selectedClaimId).toBe('clm-geo0a1')
  })

  it('clears error when clearError is called', async () => {
    configureMockApi({ latencyMs: 0, simulateFailure: true })
    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)
    expect(useDocketStore.getState().error).not.toBeNull()

    useDocketStore.getState().clearError()
    expect(useDocketStore.getState().error).toBeNull()
    expect(useDocketStore.getState().loadState).toBe('idle')
  })

  it('stops polling when the docket is CLOSED', async () => {
    vi.useFakeTimers()

    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)
    expect(useDocketStore.getState().docket?.status).toBe('CLOSED')

    useDocketStore.getState().startPolling(1000)
    expect(useDocketStore.getState().isPolling).toBe(true)

    await vi.advanceTimersByTimeAsync(1000)

    expect(useDocketStore.getState().isPolling).toBe(false)
  })

  it('can stop polling manually via stopPolling', () => {
    vi.useFakeTimers()
    useDocketStore.getState().startPolling(1000)
    expect(useDocketStore.getState().isPolling).toBe(true)

    useDocketStore.getState().stopPolling()
    expect(useDocketStore.getState().isPolling).toBe(false)
  })

  it('refreshes current docket when refresh is called', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)
    expect(useDocketStore.getState().docket?.id).toBe(MOCK_DEFAULT_DOCKET_ID)

    await useDocketStore.getState().refresh()
    expect(useDocketStore.getState().loadState).toBe('ready')
    expect(useDocketStore.getState().docket?.id).toBe(MOCK_DEFAULT_DOCKET_ID)
  })
})

describe('selector hooks', () => {
  beforeEach(() => {
    configureMockApi({ latencyMs: 0, simulateFailure: false })
    useDocketStore.getState().reset()
  })

  it('returns appropriate views via selector hooks', async () => {
    const { result: loadStateHook } = renderHook(() => useLoadState())
    expect(loadStateHook.current).toBe('idle')

    const { result: docketHook } = renderHook(() => useDocket())
    expect(docketHook.current).toBeNull()

    await useDocketStore.getState().loadDocket(MOCK_DEFAULT_DOCKET_ID)

    const { result: readyDocketHook } = renderHook(() => useDocket())
    expect(readyDocketHook.current?.id).toBe(MOCK_DEFAULT_DOCKET_ID)

    const { result: claimsHook } = renderHook(() => useClaims())
    expect(claimsHook.current.length).toBeGreaterThan(0)

    const { result: countsHook } = renderHook(() => useClaimStatusCounts())
    expect(countsHook.current['STAMPED']).toBeGreaterThan(0)

    const { result: costHook } = renderHook(() => useCostView())
    expect(costHook.current).not.toBeNull()

    const { result: mapHook } = renderHook(() => useMapView())
    expect(mapHook.current).not.toBeNull()
    expect(mapHook.current?.parcels.filter((p) => p.isTarget)).toHaveLength(1)

    const firstClaimId = claimsHook.current[0]?.id ?? null
    if (firstClaimId) {
      useDocketStore.getState().selectClaim(firstClaimId)
      const { result: selectedClaimHook } = renderHook(() => useSelectedClaim())
      expect(selectedClaimHook.current?.id).toBe(firstClaimId)
    }
  })
})
