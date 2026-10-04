/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║  MOCK DATA — NOT REAL LAND RECORDS                                        ║
 * ║  Development fixture only. Mirrors the kernel's own mock parcels in        ║
 * ║  `backend/app/connectors/geography.py` so the frontend and backend agree   ║
 * ║  during the 202/55 demonstration, then is replaced by Member 3's real      ║
 * ║  cadastral GeoJSON (EPSG:4326 FeatureCollection).                          ║
 * ║  Never present these as production land records.                           ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 *
 * Property keys mirror the backend exactly and are read through a single adapter
 * (`components/map/mapAdapter.ts`) so swapping the source is a one-file change.
 */

import type { ParcelFeature } from '@/types'

export interface MockDatasetMeta {
  readonly label: string
  readonly source: string
  readonly isMock: boolean
  readonly crs: string
  readonly generatedAt: string
  readonly bbox: readonly [number, number, number, number]
  readonly centre: readonly [number, number]
  readonly initialZoom: number
}

export const MOCK_DATASET_META: MockDatasetMeta = {
  label: 'MOCK DATA',
  source: 'frontend fixture mirroring backend/app/connectors/geography.py',
  isMock: true,
  crs: 'EPSG:4326',
  generatedAt: '2026-10-03',
  bbox: [79.3235, 10.787, 79.3295, 10.792],
  centre: [79.3265, 10.7895],
  initialZoom: 15,
}

interface ParcelInput {
  readonly surveyNumber: string
  readonly extentAcres: number
  /** Closed exterior ring, [[lon, lat], …], first vertex repeated last. */
  readonly ring: ReadonlyArray<readonly [number, number]>
  readonly landUse?: string
}

function parcel({
  surveyNumber,
  extentAcres,
  ring,
  landUse = 'agricultural',
}: ParcelInput): ParcelFeature {
  return {
    type: 'Feature',
    properties: {
      survey_number: surveyNumber,
      village: 'Kadambur',
      taluk: 'Orathanadu',
      district: 'Thanjavur',
      extent_acres: extentAcres,
      land_use: landUse,
      data_source: 'MOCK',
    },
    geometry: {
      type: 'Polygon',
      coordinates: [ring.map(([lon, lat]) => [lon, lat])],
    },
  }
}

/**
 * Parcels 202/55, 202/54, 145/2 and 88/1B are copied from the kernel's mock
 * connector. 202/56, 145/1 and 88/1A are adjacent context parcels so the map has
 * surrounding fabric to render (a target parcel floating alone reads as a bug).
 */
export const MOCK_PARCELS: readonly ParcelFeature[] = [
  // ── From the kernel's mock connector ──
  parcel({
    surveyNumber: '202/55',
    extentAcres: 2.5,
    ring: [
      [79.3245, 10.789],
      [79.3255, 10.789],
      [79.3255, 10.79],
      [79.3245, 10.79],
      [79.3245, 10.789],
    ],
  }),
  parcel({
    surveyNumber: '202/54',
    extentAcres: 3.1,
    ring: [
      [79.3235, 10.789],
      [79.3245, 10.789],
      [79.3245, 10.79],
      [79.3235, 10.79],
      [79.3235, 10.789],
    ],
  }),
  parcel({
    surveyNumber: '145/2',
    extentAcres: 1.8,
    ring: [
      [79.326, 10.791],
      [79.327, 10.791],
      [79.327, 10.792],
      [79.326, 10.792],
      [79.326, 10.791],
    ],
  }),
  parcel({
    surveyNumber: '88/1B',
    extentAcres: 4.2,
    ring: [
      [79.328, 10.787],
      [79.3295, 10.787],
      [79.3295, 10.7885],
      [79.328, 10.7885],
      [79.328, 10.787],
    ],
  }),

  // ── Adjacent context parcels (frontend-only, same mock village) ──
  parcel({
    surveyNumber: '202/56',
    extentAcres: 2.2,
    ring: [
      [79.3255, 10.789],
      [79.3265, 10.789],
      [79.3265, 10.79],
      [79.3255, 10.79],
      [79.3255, 10.789],
    ],
  }),
  parcel({
    surveyNumber: '145/1',
    extentAcres: 2.0,
    ring: [
      [79.326, 10.79],
      [79.327, 10.79],
      [79.327, 10.791],
      [79.326, 10.791],
      [79.326, 10.79],
    ],
  }),
  parcel({
    surveyNumber: '88/1A',
    extentAcres: 3.6,
    ring: [
      [79.328, 10.7885],
      [79.3295, 10.7885],
      [79.3295, 10.79],
      [79.328, 10.79],
      [79.328, 10.7885],
    ],
  }),
]

/** GeoJSON FeatureCollection wrapper for MapLibre sources. */
export const MOCK_PARCEL_FEATURECOLLECTION = {
  type: 'FeatureCollection',
  features: MOCK_PARCELS,
} as const

/** Look up a parcel by survey number. Returns null rather than throwing. */
export function findMockParcel(surveyNumber: string | null | undefined): ParcelFeature | null {
  if (!surveyNumber) return null
  const normalised = surveyNumber.replace('-', '/').trim()
  return MOCK_PARCELS.find((f) => f.properties.survey_number === normalised) ?? null
}
