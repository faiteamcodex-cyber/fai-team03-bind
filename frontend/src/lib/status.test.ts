import { describe, expect, it } from 'vitest'

import {
  CLAIM_STATUS_ORDER,
  getDocketStatusMeta,
  getStatusMeta,
  isKnownStatus,
} from './status'

describe('status registry', () => {
  it('gives STAMPED a terminal success tone and a tick glyph', () => {
    const meta = getStatusMeta('STAMPED')

    expect(meta.label).toBe('STAMPED')
    expect(meta.tone).toBe('success')
    expect(meta.glyph).toBe('check')
    expect(meta.terminal).toBe(true)
  })

  it('gives REJECTED a danger tone so it is visibly distinct from OPEN', () => {
    const meta = getStatusMeta('REJECTED')

    expect(meta.tone).toBe('danger')
    expect(meta.terminal).toBe(true)
  })

  it('treats OPEN as a non-terminal neutral state', () => {
    const meta = getStatusMeta('OPEN')

    expect(meta.tone).toBe('neutral')
    expect(meta.terminal).toBe(false)
  })

  it('accepts lower-case and padded input from the API', () => {
    expect(getStatusMeta('  stamped ').label).toBe('STAMPED')
  })

  it('renders an unknown status safely instead of throwing', () => {
    const meta = getStatusMeta('ESCALATED_TO_TERRA')

    expect(meta.label).toBe('ESCALATED_TO_TERRA')
    expect(meta.glyph).toBe('unknown')
    expect(meta.srLabel).toContain('unrecognised')
  })

  it('falls back to UNKNOWN for an empty status', () => {
    expect(getStatusMeta('   ').label).toBe('UNKNOWN')
  })

  it('reports known and unknown statuses distinctly', () => {
    expect(isKnownStatus('BINDING')).toBe(true)
    expect(isKnownStatus('nope')).toBe(false)
  })

  it('orders the claim lifecycle starting at OPEN', () => {
    expect(CLAIM_STATUS_ORDER[0]).toBe('OPEN')
    expect(CLAIM_STATUS_ORDER).toContain('BINDING')
    expect(CLAIM_STATUS_ORDER).toContain('ABSTAINED')
    expect(CLAIM_STATUS_ORDER).toContain('DISPUTE')
  })

  it('does not invent pipeline states the kernel does not send', () => {
    // These were guessed before Member 1's schemas landed and do not exist.
    expect(CLAIM_STATUS_ORDER).not.toContain('PLANNED')
    expect(CLAIM_STATUS_ORDER).not.toContain('ROUTED')
    expect(CLAIM_STATUS_ORDER).not.toContain('EXECUTED')
    expect(CLAIM_STATUS_ORDER).not.toContain('VERIFIED')
  })

  it('gives ABSTAINED a warning tone, distinct from STAMPED and REJECTED', () => {
    const meta = getStatusMeta('ABSTAINED')
    expect(meta.tone).toBe('warning')
    expect(meta.terminal).toBe(true)
    expect(meta.srLabel).toContain('no stamp')
  })

  it('gives DISPUTE its own glyph', () => {
    expect(getStatusMeta('DISPUTE').glyph).toBe('conflict')
  })

  it('resolves docket statuses from the same module', () => {
    expect(getDocketStatusMeta('CLOSED').tone).toBe('success')
    expect(getDocketStatusMeta('FAILED').tone).toBe('danger')
    expect(getDocketStatusMeta('nonexistent').glyph).toBe('unknown')
  })
})
