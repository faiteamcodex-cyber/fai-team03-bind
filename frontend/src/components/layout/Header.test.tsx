import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Header } from './Header'

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('Header', () => {
  it('always identifies the application', () => {
    render(<Header />)

    expect(screen.getByText('BIND')).toBeInTheDocument()
  })

  it('shows an em dash when no docket is open rather than a fake id', () => {
    render(<Header docketId={null} />)

    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('shows the open docket id', () => {
    render(<Header docketId="202/55" />)

    expect(screen.getByText('202/55')).toBeInTheDocument()
  })

  it('labels data provenance so mock data is never mistaken for real output', () => {
    vi.stubEnv('VITE_USE_MOCK_API', 'true')
    render(<Header />)

    expect(screen.getByText(/mock data/i)).toBeInTheDocument()
  })
})
