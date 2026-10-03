import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { BindMap } from './BindMap'
import {
  PARCEL_FILL_LAYER_ID,
  PARCEL_LINE_LAYER_ID,
  PARCEL_SOURCE_ID,
  TARGET_PARCEL_FILL_LAYER_ID,
  TARGET_PARCEL_LINE_LAYER_ID,
} from './mapLayers'
import {
  mockAddLayer,
  mockAddSource,
  mockRemove,
} from '@/test/maplibreMock'

describe('BindMap', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('creates a map instance and adds parcel sources and fill/line layers on load', () => {
    const { unmount } = render(<BindMap targetSurveyNumber="202/55" />)

    expect(screen.getByTestId('bind-map-container')).toBeInTheDocument()

    // Verify parcel GeoJSON source added
    expect(mockAddSource).toHaveBeenCalledWith(
      PARCEL_SOURCE_ID,
      expect.objectContaining({ type: 'geojson' }),
    )

    // Verify fill and line layers added
    expect(mockAddLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: PARCEL_FILL_LAYER_ID }),
    )
    expect(mockAddLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: PARCEL_LINE_LAYER_ID }),
    )
    expect(mockAddLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: TARGET_PARCEL_FILL_LAYER_ID }),
    )
    expect(mockAddLayer).toHaveBeenCalledWith(
      expect.objectContaining({ id: TARGET_PARCEL_LINE_LAYER_ID }),
    )

    // Verify remove called on unmount
    unmount()
    expect(mockRemove).toHaveBeenCalled()
  })

  it('renders accessible text summary for screen readers', () => {
    render(<BindMap targetSurveyNumber="202/55" />)
    expect(
      screen.getByText(/Cadastral map showing target parcel 202\/55/i),
    ).toBeInTheDocument()
  })
})
