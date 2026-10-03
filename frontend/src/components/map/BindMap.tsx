import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'

import { createParcelFeatureCollection } from './mapAdapter'
import {
  INLINE_BASEMAP_STYLE,
  PARCEL_FILL_LAYER,
  PARCEL_LINE_LAYER,
  PARCEL_SOURCE_ID,
  TARGET_PARCEL_FILL_LAYER,
  TARGET_PARCEL_LINE_LAYER,
} from './mapLayers'
import { MOCK_DATASET_META, MOCK_PARCELS } from '@/data/mockGeoJSON'
import type { MapView } from '@/services/mappers'

export interface BindMapProps {
  mapView?: MapView | null
  targetSurveyNumber?: string | null
  className?: string
}

export function BindMap({
  mapView,
  targetSurveyNumber = '202/55',
  className,
}: BindMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)

  // Determine parcels from props or fallback to mock fixture
  const rawParcels =
    mapView && mapView.parcels.length > 0
      ? mapView.parcels.map((p) => p.feature)
      : MOCK_PARCELS

  const geoJsonData = createParcelFeatureCollection(
    rawParcels,
    targetSurveyNumber,
  )

  useEffect(() => {
    if (!containerRef.current) return

    // Guard against React 18 StrictMode double-mount
    if (mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: INLINE_BASEMAP_STYLE,
      bounds: [
        MOCK_DATASET_META.bbox[0],
        MOCK_DATASET_META.bbox[1],
        MOCK_DATASET_META.bbox[2],
        MOCK_DATASET_META.bbox[3],
      ] as [number, number, number, number],
      fitBoundsOptions: { padding: 24 },
      attributionControl: false,
    })

    mapRef.current = map

    map.on('load', () => {
      const initialData = createParcelFeatureCollection(
        rawParcels,
        targetSurveyNumber,
      )

      // Add Cadastral GeoJSON Source
      if (!map.getSource(PARCEL_SOURCE_ID)) {
        map.addSource(PARCEL_SOURCE_ID, {
          type: 'geojson',
          data: initialData,
        })
      }

      // Add Layers
      if (!map.getLayer(PARCEL_FILL_LAYER.id)) {
        map.addLayer(PARCEL_FILL_LAYER)
      }
      if (!map.getLayer(PARCEL_LINE_LAYER.id)) {
        map.addLayer(PARCEL_LINE_LAYER)
      }
      if (!map.getLayer(TARGET_PARCEL_FILL_LAYER.id)) {
        map.addLayer(TARGET_PARCEL_FILL_LAYER)
      }
      if (!map.getLayer(TARGET_PARCEL_LINE_LAYER.id)) {
        map.addLayer(TARGET_PARCEL_LINE_LAYER)
      }

      // Add navigation controls
      map.addControl(new maplibregl.NavigationControl(), 'top-right')
    })

    // ResizeObserver with rAF for dynamic container resizes without loop warnings
    let resizeObserver: ResizeObserver | null = null
    if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
      resizeObserver = new ResizeObserver(() => {
        window.requestAnimationFrame(() => {
          map.resize()
        })
      })
      resizeObserver.observe(containerRef.current)
    }

    return () => {
      if (resizeObserver) {
        resizeObserver.disconnect()
      }
      if (mapRef.current) {
        try {
          mapRef.current.remove()
        } catch {
          // Ignore cleanup errors during unmount
        }
        mapRef.current = null
      }
    }
  }, [rawParcels, targetSurveyNumber])

  // Update source data when targetSurveyNumber or mapView changes
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const source = map.getSource(PARCEL_SOURCE_ID) as maplibregl.GeoJSONSource | undefined
    if (source && typeof source.setData === 'function') {
      source.setData(geoJsonData)
    }
  }, [geoJsonData])

  return (
    <div className={['relative h-full w-full min-h-[300px]', className].filter(Boolean).join(' ')}>
      {/* Accessible screen reader summary */}
      <div className="sr-only" aria-live="polite">
        Cadastral map showing target parcel {targetSurveyNumber ?? 'none'} and{' '}
        {rawParcels.length} total parcels in Kadambur village. Target parcel is
        highlighted in green with a distinct border.
      </div>

      {/* MapLibre Canvas Container */}
      <div
        ref={containerRef}
        data-testid="bind-map-container"
        className="h-full w-full rounded-b-lg overflow-hidden min-h-[300px]"
      />

      {/* Place reserved for photo markers in Step 8 */}
      <div id="photo-markers-layer" className="pointer-events-none absolute inset-0" />
    </div>
  )
}
