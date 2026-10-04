import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

import {
  MockMap,
  MockMarker,
  MockNavigationControl,
} from './maplibreMock'

// Polyfill ResizeObserver for jsdom
if (typeof globalThis.ResizeObserver === 'undefined') {
  class MockResizeObserver {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  globalThis.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver
}

// Global mock for maplibre-gl in jsdom tests
vi.mock('maplibre-gl', () => ({
  Map: MockMap,
  Marker: MockMarker,
  NavigationControl: MockNavigationControl,
}))

// Vitest does not auto-clean the DOM between tests unless globals are enabled.
afterEach(() => {
  cleanup()
})
