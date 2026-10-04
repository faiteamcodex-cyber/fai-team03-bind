import { vi } from 'vitest'

export const mockAddSource = vi.fn()
export const mockAddLayer = vi.fn()
export const mockAddControl = vi.fn()
export const mockRemove = vi.fn()
export const mockResize = vi.fn()
export const mockFitBounds = vi.fn()
export const mockGetSource = vi.fn().mockReturnValue(undefined)
export const mockGetLayer = vi.fn().mockReturnValue(undefined)
export const mockSetFeatureState = vi.fn()
export const mockQueryRenderedFeatures = vi.fn().mockReturnValue([])

export const mockMapListeners: Record<string, ((...args: unknown[]) => void)[]> = {}
export const mockContainer = document.createElement('div')

export const mockMapInstance = {
  _container: mockContainer,
  getContainer: () => mockContainer,
  getCanvas: () => ({ style: { cursor: '' } }),
  on: vi.fn((event: string, cb: (...args: unknown[]) => void) => {
    if (!mockMapListeners[event]) {
      mockMapListeners[event] = []
    }
    mockMapListeners[event]!.push(cb)
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
  setFeatureState: mockSetFeatureState,
  queryRenderedFeatures: mockQueryRenderedFeatures,
}

export class MockMap {
  constructor() {
    return mockMapInstance
  }
}

export class MockMarker {
  element: HTMLElement

  constructor(options?: { element?: HTMLElement }) {
    this.element = options?.element ?? document.createElement('div')
  }

  setLngLat() {
    return this
  }

  addTo(map?: unknown) {
    if (map && typeof map === 'object' && 'getContainer' in map) {
      const container = (map as { getContainer: () => HTMLElement }).getContainer()
      container?.appendChild(this.element)
    } else {
      mockContainer.appendChild(this.element)
    }
    return this
  }

  remove() {
    if (this.element.parentNode) {
      this.element.parentNode.removeChild(this.element)
    }
    return this
  }

  getElement() {
    return this.element
  }
}

export class MockNavigationControl {}
