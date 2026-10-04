import { MOCK_PARCELS } from '@/data/mockGeoJSON'
import type { MapPhotoPoint } from '@/services/mappers'
import type { ParcelFeature } from '@/types'
import type { FeatureCollection, Geometry } from 'geojson'

export interface ParcelProperties {
  readonly survey_number: string
  readonly village: string
  readonly taluk: string
  readonly district: string
  readonly extent_acres: number
  readonly land_use?: string
  readonly is_target?: boolean
}

/**
 * Single source of truth for reading cadastral GeoJSON feature properties.
 * No component outside `components/map/` is allowed to access GeoJSON property keys directly.
 */
export function extractParcelProperties(
  properties: Record<string, unknown>,
  targetSurveyNumber?: string | null,
): ParcelProperties {
  const survey_number =
    typeof properties['survey_number'] === 'string'
      ? properties['survey_number']
      : '—'
  const village =
    typeof properties['village'] === 'string' ? properties['village'] : '—'
  const taluk =
    typeof properties['taluk'] === 'string' ? properties['taluk'] : '—'
  const district =
    typeof properties['district'] === 'string' ? properties['district'] : '—'
  const extent_acres =
    typeof properties['extent_acres'] === 'number'
      ? properties['extent_acres']
      : 0
  const land_use =
    typeof properties['land_use'] === 'string' ? properties['land_use'] : undefined

  const is_target =
    targetSurveyNumber !== null && targetSurveyNumber !== undefined
      ? survey_number === targetSurveyNumber
      : false

  return {
    survey_number,
    village,
    taluk,
    district,
    extent_acres,
    land_use,
    is_target,
  }
}

/**
 * Transform raw parcel features into an adapted GeoJSON FeatureCollection
 * suitable for MapLibre sources.
 */
export function createParcelFeatureCollection(
  parcels: readonly ParcelFeature[] = MOCK_PARCELS,
  targetSurveyNumber: string | null = '202/55',
): FeatureCollection<Geometry, ParcelProperties> {
  return {
    type: 'FeatureCollection',
    features: parcels.map((feature, index) => {
      const props = extractParcelProperties(
        feature.properties as Record<string, unknown>,
        targetSurveyNumber,
      )
      return {
        ...feature,
        id: index,
        properties: props,
      }
    }),
  }
}

/** Compute bounding box [[minLon, minLat], [maxLon, maxLat]] for a polygon feature. */
export function getParcelBounds(
  feature: ParcelFeature,
): [[number, number], [number, number]] | null {
  if (feature.geometry.type !== 'Polygon') return null
  const coords = feature.geometry.coordinates[0]
  if (!coords || coords.length === 0) return null

  let minLon = Infinity
  let maxLon = -Infinity
  let minLat = Infinity
  let maxLat = -Infinity

  for (const [lon, lat] of coords) {
    if (lon !== undefined && lat !== undefined) {
      minLon = Math.min(minLon, lon)
      maxLon = Math.max(maxLon, lon)
      minLat = Math.min(minLat, lat)
      maxLat = Math.max(maxLat, lat)
    }
  }

  if (!Number.isFinite(minLon)) return null
  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ]
}

/** Create HTML marker element for photo GPS points with kernel verdict badges. */
export function createPhotoMarkerElement(photo: MapPhotoPoint): HTMLElement {
  const container = document.createElement('div')
  container.className = 'group relative cursor-pointer'

  if (photo.isBound) {
    container.innerHTML = `
      <div class="flex items-center gap-1.5 rounded-full border border-emerald-400/60 bg-emerald-950/90 px-2.5 py-1 shadow-md backdrop-blur text-[11px] font-semibold text-emerald-200" title="Photo GPS inside parcel ${photo.surveyNumber}">
        <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>Photo (GPS inside)</span>
      </div>
    `
  } else {
    container.innerHTML = `
      <div class="flex items-center gap-1.5 rounded-md border border-red-500/80 bg-red-950/95 px-2.5 py-1 shadow-lg backdrop-blur text-[11px] font-bold text-red-200 ring-2 ring-red-500/40" title="Photo GPS outside parcel ${photo.surveyNumber}">
        <span class="h-2.5 w-2.5 rounded-full bg-red-500 animate-ping"></span>
        <span data-testid="unbound-marker-callout">GPS outside parcel</span>
      </div>
    `
  }

  return container
}

