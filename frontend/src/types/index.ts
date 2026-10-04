/**
 * BIND frontend contract types.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 *  MIRRORED FROM MEMBER 1'S BACKEND SCHEMAS — DO NOT ADD FIELDS
 * ─────────────────────────────────────────────────────────────────────────────
 *  Source of truth: `backend/app/schemas/` in fai-team03-bind (commit 71c6e80).
 *
 *  When the backend changes, regenerate these files from the Pydantic models —
 *  do not hand-edit from memory, and do not add fields the backend does not send.
 *
 *  `api.ts` is the one exception: it is a frontend-owned service interface, not a
 *  backend contract, and is marked as such.
 * ─────────────────────────────────────────────────────────────────────────────
 */

export * from './enums'
export * from './exhibit'
export * from './claim'
export * from './docket'
export * from './api'
