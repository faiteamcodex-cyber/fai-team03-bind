import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { ClaimCard } from './ClaimCard'
import { DocketList } from './DocketList'
import { MOCK_DOCKET_REJECTED, MOCK_DOCKET_STAMPED } from '@/data/mockDocket'
import { configureMockApi } from '@/services'
import type { ClaimView } from '@/services/mappers'
import { useDocketStore } from '@/store/docketStore'

const createMockClaim = (overrides: Partial<ClaimView> = {}): ClaimView => ({
  id: 'clm-test-1',
  type: 'GEO.PARCEL',
  harm: 'high',
  status: 'STAMPED',
  confidence: 0.95,
  writer: 'gis_tool',
  stampReason: 'Reason for testing',
  exhibitIds: ['exh-1'],
  dependsOn: [],
  exhibits: [],
  route: null,
  costs: [],
  costUsd: 0.003,
  ...overrides,
})

describe('ClaimCard and Docket UI components', () => {
  beforeEach(() => {
    configureMockApi({ latencyMs: 0, simulateFailure: false })
    useDocketStore.getState().reset()
  })

  afterEach(() => {
    useDocketStore.getState().stopPolling()
  })

  const statuses = [
    'OPEN',
    'BINDING',
    'STAMPED',
    'REJECTED',
    'ABSTAINED',
    'DISPUTE',
  ] as const

  statuses.forEach((status) => {
    it(`renders a card for status ${status}`, () => {
      const claim = createMockClaim({ id: `clm-${status}`, status })
      render(<ClaimCard claim={claim} />)

      expect(screen.getByText(status)).toBeInTheDocument()
      expect(screen.getByRole('button')).toHaveAttribute('data-status', status)
    })
  })

  it('renders an unknown status string without crashing', () => {
    const claim = createMockClaim({ status: 'FOO_UNKNOWN_STATUS' })
    render(<ClaimCard claim={claim} />)

    expect(screen.getByText('FOO_UNKNOWN_STATUS')).toBeInTheDocument()
  })

  it('visually distinguishes STAMPED and REJECTED cards by data-tone', () => {
    const stampedClaim = createMockClaim({ id: 'c1', status: 'STAMPED' })
    const rejectedClaim = createMockClaim({ id: 'c2', status: 'REJECTED' })

    const { rerender } = render(<ClaimCard claim={stampedClaim} />)
    const stampedCard = screen.getByRole('button')
    expect(stampedCard).toHaveAttribute('data-tone', 'success')

    rerender(<ClaimCard claim={rejectedClaim} />)
    const rejectedCard = screen.getByRole('button')
    expect(rejectedCard).toHaveAttribute('data-tone', 'danger')
  })

  it('renders an em dash when confidence is null', () => {
    const claim = createMockClaim({ confidence: null })
    render(<ClaimCard claim={claim} />)

    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('updates the store when a card is selected', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DOCKET_STAMPED.id)
    render(<DocketList />)

    const targetCard = document.querySelector('[data-claim-id="clm-geo0a1"]')
    expect(targetCard).not.toBeNull()
    fireEvent.click(targetCard!)

    expect(useDocketStore.getState().selectedClaimId).toBe('clm-geo0a1')
  })

  it('shows the real stamp_reason text for the rejected fixture', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DOCKET_REJECTED.id)
    render(<DocketList />)

    expect(
      screen.getByText(
        /falls outside the parcel polygon for survey 202\/54/i,
      ),
    ).toBeInTheDocument()
  })
})
