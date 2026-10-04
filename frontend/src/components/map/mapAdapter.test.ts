import { describe, expect, it } from 'vitest'

import {
  createParcelFeatureCollection,
  createPhotoMarkerElement,
  extractParcelProperties,
  getParcelBounds,
} from './mapAdapter'
import { MOCK_PARCELS } from '@/data/mockGeoJSON'
import type { MapPhotoPoint } from '@/services/mappers'
import type { ParcelFeature } from '@/types'

describe('mapAdapter', () => {
  it('extracts parcel properties with fallback defaults', () => {
    const props = extractParcelProperties(
      {
        survey_number: '202/55',
        village: 'Kadambur',
        extent_acres: 2.5,
      },
      '202/55',
    )

    expect(props.survey_number).toBe('202/55')
    expect(props.village).toBe('Kadambur')
    expect(props.extent_acres).toBe(2.5)
    expect(props.is_target).toBe(true)
    expect(props.taluk).toBe('—')
    expect(props.district).toBe('—')
  })

  it('transforms raw parcel array into GeoJSON FeatureCollection with IDs', () => {
    const collection = createParcelFeatureCollection(MOCK_PARCELS, '202/55')

    expect(collection.type).toBe('FeatureCollection')
    expect(collection.features.length).toBe(MOCK_PARCELS.length)
    expect(collection.features[0]?.id).toBe(0)
    expect(collection.features[0]?.properties.is_target).toBe(true)
  })

  it('computes parcel bounding box accurately', () => {
    const feature = MOCK_PARCELS[0] as ParcelFeature
    const bounds = getParcelBounds(feature)

    expect(bounds).not.toBeNull()
    if (bounds) {
      const [[minLon, minLat], [maxLon, maxLat]] = bounds
      expect(minLon).toBeLessThanOrEqual(maxLon)
      expect(minLat).toBeLessThanOrEqual(maxLat)
    }
  })

  it('returns null bounds for invalid non-polygon geometry', () => {
    const invalidFeature = {
      type: 'Feature',
      properties: {},
      geometry: { type: 'Point', coordinates: [79.3, 10.7] },
    } as unknown as ParcelFeature

    expect(getParcelBounds(invalidFeature)).toBeNull()
  })

  it('renders photo marker element for bound vs unbound GPS photo point', () => {
    const boundPhoto: MapPhotoPoint = {
      claimId: 'clm-pho0a1',
      surveyNumber: '202/55',
      lat: 10.7895,
      lon: 79.325,
      bindStatus: 'inside',
      isBound: true,
      imageUri: 's3://test.jpg',
      captureTime: '2026-09-15T10:30:00Z',
    }

    const boundEl = createPhotoMarkerElement(boundPhoto)
    expect(boundEl.textContent).toContain('Photo (GPS inside)')

    const unboundPhoto: MapPhotoPoint = {
      claimId: 'clm-pho1b2',
      surveyNumber: '202/54',
      lat: 10.795,
      lon: 79.33,
      bindStatus: 'unbound',
      isBound: false,
      imageUri: 's3://test.jpg',
      captureTime: '2026-09-15T11:00:00Z',
    }

    const unboundEl = createPhotoMarkerElement(unboundPhoto)
    expect(unboundEl.textContent).toContain('GPS outside parcel')
    expect(
      unboundEl.querySelector('[data-testid="unbound-marker-callout"]'),
    ).not.toBeNull()
  })
})
