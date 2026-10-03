import { vi } from 'vitest'

export const mockAddSource = vi.fn()
export const mockAddLayer = vi.fn()
export const mockAddControl = vi.fn()
export const mockRemove = vi.fn()
export const mockResize = vi.fn()
export const mockFitBounds = vi.fn()
export const mockGetSource = vi.fn().mockReturnValue(undefined)
export const mockGetLayer = vi.fn().mockReturnValue(undefined)

export const mockMapInstance = {
  on: vi.fn((event: string, cb: () => void) => {
    if (event === 'load') cb()
    return mockMapInstance
  }),
  off: vi.fn(),
  addSource: mockAddSource,
  getSource: mockGetSource,
  addLayer: mockAddLayer,
  getLayer: mockGetLayer,
  removeLayer: vi.fn(),
  removeSource: vi.fn(),
  addControl: mockAddControl,
  removeControl: vi.fn(),
  fitBounds: mockFitBounds,
  resize: mockResize,
  remove: mockRemove,
  setStyle: vi.fn(),
}

export class MockMap {
  constructor() {
    return mockMapInstance
  }
}

export class MockMarker {
  setLngLat() {
    return this
  }
  addTo() {
    return this
  }
  remove() {
    return this
  }
  getElement() {
    return document.createElement('div')
  }
}

export class MockNavigationControl {}
