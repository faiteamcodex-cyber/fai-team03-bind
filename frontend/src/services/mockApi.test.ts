import { afterEach, describe, expect, it } from 'vitest'

import { MOCK_DOCKET_STAMPED, DEFAULT_MOCK_DOCKET_ID } from '@/data/mockDocket'

import { ApiError } from './api'
import { configureMockApi, mockApi } from './mockApi'

// Keep tests instant; latency behaviour is asserted explicitly below.
afterEach(() => {
  configureMockApi({ latencyMs: 0, simulateFailure: false })
})

describe('mockApi', () => {
  it('returns a docket response shaped like the live endpoint', async () => {
    configureMockApi({ latencyMs: 0 })
    const response = await mockApi.getDocket(DEFAULT_MOCK_DOCKET_ID)

    expect(response.docket.id).toBe(DEFAULT_MOCK_DOCKET_ID)
    expect(response.docket.claims.length).toBeGreaterThan(0)
    expect(response.docket.exhibits.length).toBeGreaterThan(0)
    expect(typeof response.docket.total_cost_usd).toBe('number')
    expect(typeof response.docket.always_vlm_estimate_usd).toBe('number')
  })

  it('rejects an unknown docket with a 404 client error', async () => {
    configureMockApi({ latencyMs: 0 })

    await expect(mockApi.getDocket('dkt-does-not-exist')).rejects.toBeInstanceOf(ApiError)

    try {
      await mockApi.getDocket('dkt-does-not-exist')
    } catch (error) {
      expect((error as ApiError).kind).toBe('client')
      expect((error as ApiError).status).toBe(404)
      expect((error as ApiError).detail).toContain('not found')
    }
  })

  it('validates the minimum query length like the backend does', async () => {
    configureMockApi({ latencyMs: 0 })

    await expect(mockApi.openDocket({ query: 'hi' })).rejects.toMatchObject({
      kind: 'client',
      status: 422,
    })
  })

  it('accepts a query that satisfies the backend minimum', async () => {
    configureMockApi({ latencyMs: 0 })
    const response = await mockApi.openDocket({ query: 'Verify survey 202/55' })

    expect(response.docket.id).toBe(MOCK_DOCKET_STAMPED.id)
  })

  it('can simulate an unreachable backend for error-state testing', async () => {
    configureMockApi({ latencyMs: 0, simulateFailure: true })

    await expect(mockApi.getDocket(DEFAULT_MOCK_DOCKET_ID)).rejects.toMatchObject({
      kind: 'network',
    })
  })

  it('lists dockets with the fields the backend returns', async () => {
    configureMockApi({ latencyMs: 0 })
    const rows = await mockApi.listDockets()

    expect(rows.length).toBeGreaterThanOrEqual(3)
    expect(rows[0]).toHaveProperty('claims_count')
    expect(rows[0]).toHaveProperty('cost_usd')
  })

  it('reports a healthy status for the dev dashboard', async () => {
    configureMockApi({ latencyMs: 0 })
    const health = await mockApi.health()

    expect(health.status).toBe('healthy')
    expect(health.team).toBe('fai-tce-team03')
  })

  it('honours the configured latency', async () => {
    configureMockApi({ latencyMs: 40 })
    const started = Date.now()
    await mockApi.health()
    const elapsed = Date.now() - started

    expect(elapsed).toBeGreaterThanOrEqual(30)
  })
})
