/**
 * Frontend service interface — NOT a backend DTO.
 *
 * This describes what the app needs from a transport, so `services/api.ts` (live)
 * and `services/mockApi.ts` (fixtures) are interchangeable. Keeping this narrow is
 * what makes the mock → live swap a one-line change.
 *
 * Every method returns a promise of the **backend's own response shapes** from
 * `types/docket.ts`; the interface adds no fields and invents no endpoints.
 */

import type { DocketListRow, DocketRequest, DocketResponse, HealthResponse } from './docket'

export interface BindApi {
  /** POST /api/v1/docket */
  openDocket(payload: DocketRequest): Promise<DocketResponse>
  /** GET /api/v1/docket/{docket_id} */
  getDocket(docketId: string): Promise<DocketResponse>
  /** GET /api/v1/dockets */
  listDockets(): Promise<DocketListRow[]>
  /** GET /api/v1/health */
  health(): Promise<HealthResponse>
}
