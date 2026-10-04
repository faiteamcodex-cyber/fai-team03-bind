import { describe, expect, it } from 'vitest'

import {
  MOCK_DOCKET_IN_FLIGHT,
  MOCK_DOCKET_REJECTED,
  MOCK_DOCKET_STAMPED,
} from '@/data/mockDocket'
import type { Docket } from '@/types'

import {
  countClaimsByStatus,
  findParcelExhibit,
  isOverBaseline,
  toClaimView,
  toClaimViews,
  toCostView,
  toDocketView,
  toMapView,
} from './mappers'

/** Minimal docket builder so cost cases can be varied without new fixtures. */
function docketWithCosts(totalCost: number, baseline: number): Docket {
  return { ...MOCK_DOCKET_STAMPED, total_cost_usd: totalCost, always_vlm_estimate_usd: baseline }
}

describe('toClaimView', () => {
  it('resolves a claim\'s exhibits from the docket exhibit pool', () => {
    const claim = MOCK_DOCKET_STAMPED.claims[0]!
    const view = toClaimView(claim, MOCK_DOCKET_STAMPED)

    expect(view.exhibits).toHaveLength(1)
    expect(view.exhibits[0]?.kind).toBe('geometry')
  })

  it('attaches the routing decision and the actual cost rows', () => {
    const view = toClaimView(
      MOCK_DOCKET_STAMPED.claims.find((c) => c.id === 'clm-vis0a1')!,
      MOCK_DOCKET_STAMPED,
    )

    expect(view.route?.assigned_writer).toBe('apac.amazon.nova-lite-v1:0')
    expect(view.costUsd).toBeCloseTo(0.003, 6)
  })

  it('keeps a null confidence rather than defaulting it to zero', () => {
    const view = toClaimView(MOCK_DOCKET_STAMPED.claims[0]!, MOCK_DOCKET_STAMPED)

    expect(view.confidence).toBeNull()
  })

  it('surfaces the kernel\'s rejection reason verbatim', () => {
    const rejected = MOCK_DOCKET_REJECTED.claims.find((c) => c.status === 'REJECTED')!
    const view = toClaimView(rejected, MOCK_DOCKET_REJECTED)

    expect(view.status).toBe('REJECTED')
    expect(view.stampReason).toContain('outside the parcel polygon')
  })

  it('reports zero cost for a claim with no ledger row', () => {
    const abstained = MOCK_DOCKET_STAMPED.claims.find((c) => c.status === 'ABSTAINED')!
    const view = toClaimView(abstained, MOCK_DOCKET_STAMPED)

    expect(view.costUsd).toBe(0)
    expect(view.writer).toBeNull()
  })
})

describe('countClaimsByStatus', () => {
  it('counts each status present in the docket', () => {
    const counts = countClaimsByStatus(MOCK_DOCKET_STAMPED)

    expect(counts.STAMPED).toBe(5)
    expect(counts.ABSTAINED).toBe(1)
  })

  it('returns an empty object for a docket with no claims', () => {
    expect(countClaimsByStatus({ ...MOCK_DOCKET_STAMPED, claims: [] })).toEqual({})
  })
})

describe('toCostView', () => {
  it('derives savings and percentage from backend-supplied figures', () => {
    const cost = toCostView(MOCK_DOCKET_STAMPED)

    expect(cost.routedTotalUsd).toBeCloseTo(0.014, 6)
    expect(cost.baselineUsd).toBeCloseTo(0.031, 6)
    expect(cost.savingsUsd).toBeCloseTo(0.017, 6)
    expect(cost.savingsPct).toBeCloseTo(54.84, 1)
  })

  it('handles a zero baseline without producing Infinity or NaN', () => {
    const cost = toCostView(docketWithCosts(0.014, 0))

    expect(cost.baselineUsd).toBeNull()
    expect(cost.savingsUsd).toBeNull()
    expect(cost.savingsPct).toBeNull()
  })

  it('handles a negative baseline defensively', () => {
    const cost = toCostView(docketWithCosts(0.014, -1))

    expect(cost.baselineUsd).toBeNull()
    expect(cost.savingsPct).toBeNull()
  })

  it('reports a negative saving when routing cost more than the baseline', () => {
    const cost = toCostView(docketWithCosts(0.05, 0.031))

    expect(cost.savingsUsd).toBeCloseTo(-0.019, 6)
    expect(isOverBaseline(cost)).toBe(true)
  })

  it('does not report over-baseline when the baseline is unknown', () => {
    expect(isOverBaseline(toCostView(docketWithCosts(0.05, 0)))).toBe(false)
  })

  it('sums the router estimates so estimator drift is visible', () => {
    const cost = toCostView(MOCK_DOCKET_STAMPED)

    expect(cost.estimatedTotalUsd).toBeCloseTo(0.004, 6)
  })
})

describe('toMapView', () => {
  it('marks the docket\'s survey number as the target parcel', () => {
    const map = toMapView(MOCK_DOCKET_STAMPED)

    expect(map.parcels).toHaveLength(1)
    expect(map.parcels[0]?.surveyNumber).toBe('202/55')
    expect(map.parcels[0]?.isTarget).toBe(true)
  })

  it('extracts the photo GPS point and the kernel\'s bind verdict', () => {
    const map = toMapView(MOCK_DOCKET_STAMPED)
    const photo = map.photos[0]

    expect(photo?.lat).toBeCloseTo(10.7895, 4)
    expect(photo?.lon).toBeCloseTo(79.325, 4)
    expect(photo?.isBound).toBe(true)
  })

  it('flags an unbound photo without recomputing point-in-polygon', () => {
    const map = toMapView(MOCK_DOCKET_REJECTED)
    const photo = map.photos[0]

    expect(photo?.bindStatus).toBe('unbound')
    expect(photo?.isBound).toBe(false)
  })

  it('returns an empty map view for a docket with no geometry yet', () => {
    const map = toMapView({
      ...MOCK_DOCKET_STAMPED,
      claims: [],
      exhibits: [],
    })

    expect(map.parcels).toHaveLength(0)
    expect(map.photos).toHaveLength(0)
  })

  it('finds a parcel exhibit on a claim', () => {
    const feature = findParcelExhibit(MOCK_DOCKET_STAMPED.claims[0]!, MOCK_DOCKET_STAMPED)

    expect(feature?.properties.survey_number).toBe('202/55')
  })
})

describe('toDocketView', () => {
  it('projects the full docket without inventing values', () => {
    const view = toDocketView(MOCK_DOCKET_IN_FLIGHT)

    expect(view.id).toBe(MOCK_DOCKET_IN_FLIGHT.id)
    expect(view.status).toBe('EXECUTING')
    expect(view.surveyNumber).toBe('202/55')
    expect(view.closedMs).toBeNull()
    expect(view.claims).toHaveLength(5)
  })

  it('exposes open and binding claims for the reactive UI', () => {
    const view = toDocketView(MOCK_DOCKET_IN_FLIGHT)
    const statuses = view.claims.map((c) => c.status)

    expect(statuses).toContain('OPEN')
    expect(statuses).toContain('BINDING')
    expect(statuses).toContain('STAMPED')
  })

  it('leaves undecided claims without a stamp reason', () => {
    const view = toDocketView(MOCK_DOCKET_IN_FLIGHT)
    const open = view.claims.find((c) => c.status === 'OPEN')

    expect(open?.stampReason).toBeNull()
  })

  it('maps every claim type in the rejected fixture to a view', () => {
    const views = toClaimViews(MOCK_DOCKET_REJECTED)
    const types = views.map((v) => v.type)

    expect(types).toContain('GEO.PARCEL')
    expect(types).toContain('MEDIA.PHOTO')
    expect(types).toContain('VIS.CROP')
    expect(types).toContain('ADV.FERTILIZER')
  })
})
