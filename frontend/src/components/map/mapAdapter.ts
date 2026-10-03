import { MOCK_PARCELS } from '@/data/mockGeoJSON'
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
    features: parcels.map((feature) => {
      const props = extractParcelProperties(
        feature.properties as Record<string, unknown>,
        targetSurveyNumber,
      )
      return {
        ...feature,
        properties: props,
      }
    }),
  }
}
