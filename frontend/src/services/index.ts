/**
 * The single place that decides which transport the app talks to.
 *
 * Components and the store import `bindApi` from here and never know whether the
 * data is live or mocked. Flipping VITE_USE_MOCK_API is the whole switch.
 */

import { env } from '@/lib/env'
import type { BindApi } from '@/types'

import { liveApi } from './api'
import { mockApi } from './mockApi'

export const bindApi: BindApi = env.useMockApi ? mockApi : liveApi

export { ApiError } from './api'
export type { ApiErrorKind } from './api'
export { configureMockApi, getMockApiOptions } from './mockApi'
