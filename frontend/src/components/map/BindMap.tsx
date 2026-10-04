import { useEffect, useMemo, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'

import {
  createParcelFeatureCollection,
  createPhotoMarkerElement,
  extractParcelProperties,
  getParcelBounds,
} from './mapAdapter'
import {
  INLINE_BASEMAP_STYLE,
  PARCEL_FILL_LAYER,
  PARCEL_FILL_LAYER_ID,
  PARCEL_LINE_LAYER,
  PARCEL_SOURCE_ID,
  TARGET_PARCEL_FILL_LAYER,
  TARGET_PARCEL_FILL_LAYER_ID,
  TARGET_PARCEL_LINE_LAYER,
} from './mapLayers'
import { MOCK_DATASET_META, MOCK_PARCELS } from '@/data/mockGeoJSON'
import type { MapPhotoPoint, MapView } from '@/services/mappers'
import { useDocketStore } from '@/store/docketStore'

export interface BindMapProps {
  mapView?: MapView | null
  targetSurveyNumber?: string | null
  className?: string
}

interface HoverTooltipState {
  surveyNumber: string
  extentAcres: number
  village: string
  x: number
  y: number
}

const EMPTY_PHOTOS: readonly MapPhotoPoint[] = []

export function BindMap({
  mapView,
  targetSurveyNumber = '202/55',
  className,
}: BindMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<maplibregl.Marker[]>([])
  const hoveredFeatureIdRef = useRef<string | number | null>(null)

  const selectSurveyNumber = useDocketStore((s) => s.selectSurveyNumber)

  const [tooltip, setTooltip] = useState<HoverTooltipState | null>(null)

  const rawParcels = useMemo(() => {
    return mapView && mapView.parcels.length > 0
      ? mapView.parcels.map((p) => p.feature)
      : MOCK_PARCELS
  }, [mapView])

  const photos = useMemo(
    () => mapView?.photos ?? EMPTY_PHOTOS,
    [mapView?.photos],
  )

  const geoJsonData = useMemo(
    () => createParcelFeatureCollection(rawParcels, targetSurveyNumber),
    [rawParcels, targetSurveyNumber],
  )

  const initialParcelsRef = useRef(rawParcels)
  const initialTargetRef = useRef(targetSurveyNumber)
  const selectSurveyRef = useRef(selectSurveyNumber)
  selectSurveyRef.current = selectSurveyNumber

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!containerRef.current) return
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
        initialParcelsRef.current,
        initialTargetRef.current,
      )

      if (!map.getSource(PARCEL_SOURCE_ID)) {
        map.addSource(PARCEL_SOURCE_ID, {
          type: 'geojson',
          data: initialData,
        })
      }

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

      map.addControl(new maplibregl.NavigationControl(), 'top-right')

      // Parcel Click Handler
      const handleParcelClick = (
        e: maplibregl.MapMouseEvent & {
          features?: maplibregl.MapGeoJSONFeature[]
        },
      ) => {
        const feature = e.features?.[0]
        if (feature) {
          const props = extractParcelProperties(
            feature.properties as Record<string, unknown>,
          )
          selectSurveyRef.current(props.survey_number)
        }
      }

      map.on('click', PARCEL_FILL_LAYER.id, handleParcelClick)
      map.on('click', TARGET_PARCEL_FILL_LAYER.id, handleParcelClick)

      // Map Canvas Background Click Handler
      map.on('click', (e) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: [PARCEL_FILL_LAYER_ID, TARGET_PARCEL_FILL_LAYER_ID],
        })
        if (features.length === 0) {
          selectSurveyRef.current(null)
        }
      })

      // Hover Mousemove Handler
      const handleMouseMove = (
        e: maplibregl.MapMouseEvent & {
          features?: maplibregl.MapGeoJSONFeature[]
        },
      ) => {
        const feature = e.features?.[0]
        if (!feature) return

        map.getCanvas().style.cursor = 'pointer'

        const props = extractParcelProperties(
          feature.properties as Record<string, unknown>,
        )

        if (feature.id !== undefined && feature.id !== null) {
          if (
            hoveredFeatureIdRef.current !== null &&
            hoveredFeatureIdRef.current !== feature.id
          ) {
            map.setFeatureState(
              { source: PARCEL_SOURCE_ID, id: hoveredFeatureIdRef.current },
              { hover: false },
            )
          }
          hoveredFeatureIdRef.current = feature.id
          map.setFeatureState(
            { source: PARCEL_SOURCE_ID, id: feature.id },
            { hover: true },
          )
        }

        setTooltip({
          surveyNumber: props.survey_number,
          extentAcres: props.extent_acres,
          village: props.village,
          x: e.point.x,
          y: e.point.y,
        })
      }

      // Hover Mouseleave Handler
      const handleMouseLeave = () => {
        map.getCanvas().style.cursor = ''
        if (hoveredFeatureIdRef.current !== null) {
          map.setFeatureState(
            { source: PARCEL_SOURCE_ID, id: hoveredFeatureIdRef.current },
            { hover: false },
          )
          hoveredFeatureIdRef.current = null
        }
        setTooltip(null)
      }

      map.on('mousemove', PARCEL_FILL_LAYER.id, handleMouseMove)
      map.on('mousemove', TARGET_PARCEL_FILL_LAYER.id, handleMouseMove)
      map.on('mouseleave', PARCEL_FILL_LAYER.id, handleMouseLeave)
      map.on('mouseleave', TARGET_PARCEL_FILL_LAYER.id, handleMouseLeave)
    })

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
          // Ignore cleanup errors
        }
        mapRef.current = null
      }
    }
  }, [])

  // Sync GeoJSON data and fit bounds when target/parcels change
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const source = map.getSource(PARCEL_SOURCE_ID) as
      | maplibregl.GeoJSONSource
      | undefined
    if (source && typeof source.setData === 'function') {
      source.setData(geoJsonData)
    }

    if (targetSurveyNumber) {
      const targetFeature = rawParcels.find(
        (f) => f.properties.survey_number === targetSurveyNumber,
      )
      if (targetFeature) {
        const bounds = getParcelBounds(targetFeature)
        if (bounds && typeof map.fitBounds === 'function') {
          map.fitBounds(bounds, { padding: 40, maxZoom: 17 })
        }
      }
    }
  }, [geoJsonData, targetSurveyNumber, rawParcels])

  // Update Photo Markers
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = []

    photos.forEach((photo) => {
      const el = createPhotoMarkerElement(photo)
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([photo.lon, photo.lat])
        .addTo(map)
      markersRef.current.push(marker)
    })
  }, [photos])

  return (
    <div
      className={['relative h-full w-full min-h-[300px]', className]
        .filter(Boolean)
        .join(' ')}
    >
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

      {/* Hover Tooltip Popup */}
      {tooltip && (
        <div
          data-testid="map-hover-tooltip"
          style={{ left: `${tooltip.x + 12}px`, top: `${tooltip.y + 12}px` }}
          className="pointer-events-none absolute z-20 rounded border border-line bg-surface-1/95 px-2.5 py-1.5 text-xs text-slate-100 shadow-lg backdrop-blur"
        >
          <div className="font-mono font-semibold text-emerald-300">
            Survey {tooltip.surveyNumber}
          </div>
          <div className="text-[11px] text-slate-400">
            {tooltip.extentAcres} acres · {tooltip.village}
          </div>
        </div>
      )}

      {/* Place reserved for photo markers layer */}
      <div
        id="photo-markers-layer"
        className="pointer-events-none absolute inset-0"
      />
    </div>
  )
}

