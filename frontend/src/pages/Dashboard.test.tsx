import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { MOCK_DOCKET_REJECTED, MOCK_DOCKET_STAMPED } from '@/data/mockDocket'
import { configureMockApi } from '@/services'
import { useDocketStore } from '@/store/docketStore'

import { Dashboard } from './Dashboard'

describe('Dashboard page', () => {
  beforeEach(() => {
    configureMockApi({ latencyMs: 0, simulateFailure: false })
    useDocketStore.getState().reset()
  })

  afterEach(() => {
    useDocketStore.getState().stopPolling()
  })

  it('renders the loading state', () => {
    useDocketStore.setState({ loadState: 'loading', docket: null, error: null })

    render(<Dashboard />)

    expect(screen.getByText(/loading docket data/i)).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Cadastral map' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Docket' })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Cost comparison' }),
    ).toBeInTheDocument()
  })

  it('renders the error state from the mock failure mode', async () => {
    configureMockApi({ latencyMs: 0, simulateFailure: true })
    useDocketStore.getState().reset()

    render(<Dashboard />)

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(
      screen.getByText(/unable to connect to the bind backend/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('renders the stamped docket outcome without crashing', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DOCKET_STAMPED.id)

    render(<Dashboard />)

    expect(screen.getAllByText(MOCK_DOCKET_STAMPED.id).length).toBeGreaterThan(0)
    expect(
      screen.getByRole('heading', { name: 'Cadastral map' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Docket' })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Cost comparison' }),
    ).toBeInTheDocument()
  })

  it('renders the rejected docket outcome without crashing', async () => {
    await useDocketStore.getState().loadDocket(MOCK_DOCKET_REJECTED.id)

    render(<Dashboard />)

    expect(screen.getAllByText(MOCK_DOCKET_REJECTED.id).length).toBeGreaterThan(0)
    expect(
      screen.getByRole('heading', { name: 'Cadastral map' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Docket' })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Cost comparison' }),
    ).toBeInTheDocument()
  })
})
