/**
 * Mock BIND API — fixtures in the shape of Member 1's real responses.
 *
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║  MOCK DATA — the UI labels this as MOCK DATA wherever it is displayed.     ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 *
 * Implements the same `BindApi` interface as `services/api.ts`, so switching is a
 * one-line change in `services/index.ts` (or via VITE_USE_MOCK_API).
 *
 * Behaviour is deliberately faithful to the live client:
 *  - realistic latency, so loading states are exercised rather than instant
 *  - 404 for an unknown docket id, matching the FastAPI handler
 *  - an opt-in failure mode for testing error states without unplugging the API
 */

import {
  DEFAULT_MOCK_DOCKET_ID,
  MOCK_DOCKETS,
  MOCK_DOCKET_RESPONSES,
  MOCK_OPEN_DOCKET_RESPONSE,
} from '@/data/mockDocket'
import type {
  BindApi,
  DocketListRow,
  DocketRequest,
  DocketResponse,
  HealthResponse,
} from '@/types'

import { ApiError } from './api'

export interface MockApiOptions {
  /** Simulated round-trip latency in ms. Set 0 in tests to keep them fast. */
  latencyMs?: number
  /**
   * When true, every call rejects with a network error. Used by the UI's "API
   * unavailable" state and by tests. Toggle from the dashboard in mock mode.
   */
  simulateFailure?: boolean
}

let options: Required<MockApiOptions> = {
  latencyMs: 250,
  simulateFailure: false,
}

/** Adjust mock behaviour at runtime (tests and the dev failure toggle). */
export function configureMockApi(next: MockApiOptions): void {
  options = { ...options, ...next }
}

export function getMockApiOptions(): Required<MockApiOptions> {
  return { ...options }
}

function delay(ms: number): Promise<void> {
  if (ms <= 0) return Promise.resolve()
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function simulate<T>(produce: () => T): Promise<T> {
  await delay(options.latencyMs)

  if (options.simulateFailure) {
    throw new ApiError(
      'network',
      'Unable to connect to the BIND backend. (Mock failure mode is enabled.)',
    )
  }

  return produce()
}

export const mockApi: BindApi = {
  async openDocket(payload: DocketRequest): Promise<DocketResponse> {
    if (payload.query.trim().length < 5) {
      // Mirrors the backend's `min_length=5` validation on DocketRequest.
      await delay(options.latencyMs)
      throw new ApiError('client', 'Query must be at least 5 characters.', {
        status: 422,
        detail: 'Query must be at least 5 characters.',
      })
    }

    return simulate(() => MOCK_OPEN_DOCKET_RESPONSE)
  },

  async getDocket(docketId: string): Promise<DocketResponse> {
    return simulate(() => {
      const response = MOCK_DOCKET_RESPONSES[docketId]
      if (!response) {
        throw new ApiError('client', `Docket ${docketId} not found.`, {
          status: 404,
          detail: `Docket ${docketId} not found.`,
        })
      }
      return response
    })
  },

  async listDockets(): Promise<DocketListRow[]> {
    return simulate(() =>
      Object.values(MOCK_DOCKETS).map((docket) => ({
        id: docket.id,
        query: docket.query.slice(0, 80),
        status: docket.status,
        claims_count: docket.claims.length,
        cost_usd: docket.total_cost_usd,
      })),
    )
  },

  async health(): Promise<HealthResponse> {
    return simulate(() => ({
      status: 'healthy',
      service: 'bind-kernel (mock)',
      team: 'fai-tce-team03',
    }))
  },
}

/** Id used when the app opens with no docket selected. */
export const MOCK_DEFAULT_DOCKET_ID = DEFAULT_MOCK_DOCKET_ID
