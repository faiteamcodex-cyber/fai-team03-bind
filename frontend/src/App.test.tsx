import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

/**
 * Step 2 smoke test — the three Member 4 deliverable regions must exist as
 * labelled landmarks before any data is wired in.
 */
describe('BIND dashboard shell', () => {
  it('renders the three deliverable regions', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Cadastral map' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Docket' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Cost comparison' })).toBeInTheDocument()
  })

  it('labels the application and its data source', () => {
    render(<App />)

    expect(screen.getByText('BIND')).toBeInTheDocument()
    expect(screen.getByText(/mock data/i)).toBeInTheDocument()
  })

  it('does not invent docket data before the contract layer exists', () => {
    render(<App />)

    // Docket id is unknown at this stage and must render as an em dash.
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
