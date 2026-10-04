/**
 * Live BIND API client.
 *
 * Endpoints (from `backend/app/api/routes.py`, APIRouter prefix `/api/v1`):
 *   POST /api/v1/docket
 *   GET  /api/v1/docket/{docket_id}
 *   GET  /api/v1/dockets
 *   GET  /api/v1/health
 *
 * Rules honoured here:
 *  - The base URL comes from the environment, never hardcoded (rule 17).
 *  - Components never call this directly; they go through the store.
 *  - Failures become a typed `ApiError`, never a thrown string or an unhandled
 *    rejection, so the UI can render an honest error state.
 *  - No AWS credentials, model calls or backend logic live here.
 */

import { env } from '@/lib/env'
import type {
  BindApi,
  DocketListRow,
  DocketRequest,
  DocketResponse,
  HealthResponse,
} from '@/types'

/** Machine-readable failure kinds the UI can branch on. */
export type ApiErrorKind =
  | 'network' // could not reach the API at all
  | 'timeout' // exceeded the client-side timeout
  | 'client' // 4xx — the request was wrong
  | 'server' // 5xx — the kernel failed
  | 'parse' // 2xx but the body was not valid JSON / not the expected shape
  | 'config' // missing base URL, bad environment

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number | null
  /** FastAPI returns `{ "detail": "..." }` — surfaced verbatim for the UI. */
  readonly detail: string | null

  constructor(
    kind: ApiErrorKind,
    message: string,
    options: { status?: number | null; detail?: string | null } = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = options.status ?? null
    this.detail = options.detail ?? null
  }
}

/**
 * Cold starts: the first request after an idle Lambda can take several seconds.
 * This timeout is deliberately generous so a cold start is not reported as a
 * frontend bug.
 */
const REQUEST_TIMEOUT_MS = 30_000

function buildUrl(path: string): string {
  if (env.apiBaseUrl === '') {
    throw new ApiError(
      'config',
      'No API base URL is configured. Set VITE_API_BASE_URL or enable mock mode.',
    )
  }
  return `${env.apiBaseUrl}${path}`
}

/** Extract FastAPI's `detail` field from an error body, if present. */
async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
    }
    return null
  } catch {
    return null
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(buildUrl(path), {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(
        'timeout',
        `The BIND API did not respond within ${REQUEST_TIMEOUT_MS / 1000}s. The kernel may still be starting up.`,
      )
    }
    throw new ApiError(
      'network',
      'Unable to connect to the BIND backend. Check the API base URL and your connection.',
    )
  } finally {
    clearTimeout(timeoutId)
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    const kind: ApiErrorKind = response.status >= 500 ? 'server' : 'client'
    throw new ApiError(kind, detail ?? `Request failed with status ${response.status}.`, {
      status: response.status,
      detail,
    })
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError('parse', 'The BIND API returned a response that was not valid JSON.')
  }
}

/** Live implementation of the BIND API surface. */
export const liveApi: BindApi = {
  /** POST /api/v1/docket — open a new docket and run the kernel. */
  async openDocket(payload: DocketRequest): Promise<DocketResponse> {
    return request<DocketResponse>('/docket', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /** GET /api/v1/docket/{id} — fetch a previously processed docket. */
  async getDocket(docketId: string): Promise<DocketResponse> {
    return request<DocketResponse>(`/docket/${encodeURIComponent(docketId)}`)
  },

  /** GET /api/v1/dockets — list dockets (demo helper endpoint). */
  async listDockets(): Promise<DocketListRow[]> {
    return request<DocketListRow[]>('/dockets')
  },

  /** GET /api/v1/health — liveness probe. */
  async health(): Promise<HealthResponse> {
    return request<HealthResponse>('/health')
  },
}
