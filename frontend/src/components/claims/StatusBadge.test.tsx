import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusBadge } from './StatusBadge'
import { CLAIM_STATUS } from '@/types'

describe('StatusBadge', () => {
  it('shows the status word, not just a colour', () => {
    render(<StatusBadge status="STAMPED" />)

    expect(screen.getByText('STAMPED')).toBeInTheDocument()
  })

  it('exposes a plain-language accessible name with role status', () => {
    render(<StatusBadge status="REJECTED" />)

    expect(screen.getByRole('status')).toHaveAccessibleName('Status: Rejected')
  })

  it('renders all six claim statuses correctly (OPEN, BINDING, STAMPED, REJECTED, ABSTAINED, DISPUTE)', () => {
    const statuses = [
      CLAIM_STATUS.OPEN,
      CLAIM_STATUS.BINDING,
      CLAIM_STATUS.STAMPED,
      CLAIM_STATUS.REJECTED,
      CLAIM_STATUS.ABSTAINED,
      CLAIM_STATUS.DISPUTE,
    ]

    for (const status of statuses) {
      const { unmount } = render(<StatusBadge status={status} />)
      expect(screen.getByText(status)).toBeInTheDocument()
      expect(screen.getByRole('status')).toBeInTheDocument()
      unmount()
    }
  })

  it('marks the tone so rejected is distinguishable from open', () => {
    const { container: rejected } = render(<StatusBadge status="REJECTED" />)
    const { container: open } = render(<StatusBadge status="OPEN" />)

    expect(rejected.querySelector('[data-tone="danger"]')).not.toBeNull()
    expect(open.querySelector('[data-tone="neutral"]')).not.toBeNull()
  })

  it('renders an unrecognised backend status without crashing', () => {
    render(<StatusBadge status="DEFERRED_FOR_SURVEY" />)

    expect(screen.getByText('DEFERRED_FOR_SURVEY')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveAccessibleName(
      'Status: DEFERRED_FOR_SURVEY (unrecognised status)',
    )
  })

  it('hides the decorative icon from assistive technology', () => {
    const { container } = render(<StatusBadge status="STAMPED" />)

    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  })
})

