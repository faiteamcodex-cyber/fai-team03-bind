import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ApiErrorBanner } from './ApiErrorBanner'
import { ApiError } from '@/services/api'

describe('ApiErrorBanner', () => {
  it('handles network unreachable error kind', () => {
    const error = new ApiError(
      'network',
      'Unable to connect to the BIND backend.',
    )

    render(<ApiErrorBanner error={error} />)
    expect(
      screen.getByText(/API Unreachable \(Network Error\)/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Unable to connect to the BIND backend.'),
    ).toBeInTheDocument()
  })

  it('handles timeout error kind (30s cold start)', () => {
    const error = new ApiError(
      'timeout',
      'The BIND API did not respond within 30s.',
    )

    render(<ApiErrorBanner error={error} />)
    expect(
      screen.getByText(/Request Timeout \(Lambda Cold Start\)/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText('The BIND API did not respond within 30s.'),
    ).toBeInTheDocument()
  })

  it('handles 4xx client error kind with FastAPI detail string', () => {
    const error = new ApiError(
      'client',
      'Request failed with status 422.',
      { status: 422, detail: 'Invalid survey number format' },
    )

    render(<ApiErrorBanner error={error} />)
    expect(screen.getByText('Client Error (HTTP 422)')).toBeInTheDocument()
    expect(
      screen.getByText('Invalid survey number format'),
    ).toBeInTheDocument()
  })

  it('handles 5xx server error kind', () => {
    const error = new ApiError(
      'server',
      'Internal Server Error',
      { status: 500, detail: 'Kernel execution failed' },
    )

    render(<ApiErrorBanner error={error} />)
    expect(screen.getByText('Server Error (HTTP 500)')).toBeInTheDocument()
    expect(screen.getByText('Kernel execution failed')).toBeInTheDocument()
  })
})
