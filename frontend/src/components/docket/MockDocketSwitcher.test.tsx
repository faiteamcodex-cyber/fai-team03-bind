import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  MOCK_DOCKET_REJECTED,
  MOCK_DOCKET_STAMPED,
} from '@/data/mockDocket'
import { configureMockApi } from '@/services'
import { useDocketStore } from '@/store/docketStore'

import { MockDocketSwitcher } from './MockDocketSwitcher'
import { DocketList } from './DocketList'

beforeEach(() => {
  configureMockApi({ latencyMs: 0, simulateFailure: false })
  useDocketStore.getState().reset()
  vi.unstubAllEnvs()
})

afterEach(() => {
  useDocketStore.getState().stopPolling()
  vi.unstubAllEnvs()
})

describe('MockDocketSwitcher', () => {
  it('renders only in mock mode and calls loadDocket on change', async () => {
    vi.stubEnv('VITE_USE_MOCK_API', 'true')
    await useDocketStore.getState().loadDocket(MOCK_DOCKET_STAMPED.id)

    render(<MockDocketSwitcher />)

    const select = screen.getByLabelText(/select mock docket/i)
    expect(select).toBeInTheDocument()
    expect(select).toHaveValue(MOCK_DOCKET_STAMPED.id)

    fireEvent.change(select, { target: { value: MOCK_DOCKET_REJECTED.id } })

    await waitFor(() => {
      expect(useDocketStore.getState().docket?.id).toBe(MOCK_DOCKET_REJECTED.id)
    })
  })

  it('does not render when VITE_USE_MOCK_API is false (live mode)', () => {
    vi.stubEnv('VITE_USE_MOCK_API', 'false')

    const { container } = render(<MockDocketSwitcher />)

    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByLabelText(/select mock docket/i)).not.toBeInTheDocument()
  })

  it('selecting the rejected fixture renders a REJECTED claim with its stamp_reason', async () => {
    vi.stubEnv('VITE_USE_MOCK_API', 'true')
    await useDocketStore.getState().loadDocket(MOCK_DOCKET_REJECTED.id)

    render(
      <div>
        <MockDocketSwitcher />
        <DocketList />
      </div>,
    )

    const rejectedClaim = useDocketStore
      .getState()
      .docket?.claims.find((c) => c.status === 'REJECTED')
    expect(rejectedClaim).toBeDefined()
    expect(rejectedClaim?.type).toBe('MEDIA.PHOTO')
    expect(rejectedClaim?.stampReason).toContain('outside the parcel polygon')

    expect(screen.getByText(/MEDIA.PHOTO/i)).toBeInTheDocument()
    expect(screen.getByText(/outside the parcel polygon/i)).toBeInTheDocument()
  })
})
