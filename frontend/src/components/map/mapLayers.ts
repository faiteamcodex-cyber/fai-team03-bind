import type { AddLayerObject, StyleSpecification } from 'maplibre-gl'

export const PARCEL_SOURCE_ID = 'cadastral-parcels-source'
export const PARCEL_FILL_LAYER_ID = 'parcels-fill-layer'
export const PARCEL_LINE_LAYER_ID = 'parcels-line-layer'
export const TARGET_PARCEL_FILL_LAYER_ID = 'target-parcel-fill-layer'
export const TARGET_PARCEL_LINE_LAYER_ID = 'target-parcel-line-layer'

export const PHOTO_POINT_SOURCE_ID = 'photo-points-source'
export const PHOTO_POINT_LAYER_ID = 'photo-points-layer'

/** Neutral dark operational background style (no external tile dependency). */
export const INLINE_BASEMAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: {
        'background-color': '#090d16',
      },
    },
  ],
}

/** Muted fill for neighbouring context parcels. */
export const PARCEL_FILL_LAYER: AddLayerObject = {
  id: PARCEL_FILL_LAYER_ID,
  type: 'fill',
  source: PARCEL_SOURCE_ID,
  filter: ['!=', ['get', 'is_target'], true],
  paint: {
    'fill-color': [
      'case',
      ['boolean', ['feature-state', 'hover'], false],
      '#334155',
      '#1e293b',
    ],
    'fill-opacity': [
      'case',
      ['boolean', ['feature-state', 'hover'], false],
      0.85,
      0.6,
    ],
  },
}

/** Muted boundary lines for neighbouring context parcels. */
export const PARCEL_LINE_LAYER: AddLayerObject = {
  id: PARCEL_LINE_LAYER_ID,
  type: 'line',
  source: PARCEL_SOURCE_ID,
  paint: {
    'line-color': '#475569',
    'line-width': 1.5,
  },
}

/** Highlighted fill for target survey parcel. */
export const TARGET_PARCEL_FILL_LAYER: AddLayerObject = {
  id: TARGET_PARCEL_FILL_LAYER_ID,
  type: 'fill',
  source: PARCEL_SOURCE_ID,
  filter: ['==', ['get', 'is_target'], true],
  paint: {
    'fill-color': [
      'case',
      ['boolean', ['feature-state', 'hover'], false],
      '#047857',
      '#065f46',
    ],
    'fill-opacity': [
      'case',
      ['boolean', ['feature-state', 'hover'], false],
      0.9,
      0.7,
    ],
  },
}

/** Distinct thick outline for target survey parcel. */
export const TARGET_PARCEL_LINE_LAYER: AddLayerObject = {
  id: TARGET_PARCEL_LINE_LAYER_ID,
  type: 'line',
  source: PARCEL_SOURCE_ID,
  filter: ['==', ['get', 'is_target'], true],
  paint: {
    'line-color': '#10b981',
    'line-width': 3,
  },
}
