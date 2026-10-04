import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CostComparisonPanel } from './CostComparisonPanel'
import { MOCK_DOCKET_STAMPED } from '@/data/mockDocket'
import { toCostView } from '@/services/mappers'
import type { Docket } from '@/types'

describe('CostComparisonPanel', () => {
  it('renders actual and baseline costs', () => {
    const costView = toCostView(MOCK_DOCKET_STAMPED)
    render(
      <CostComparisonPanel
        cost={costView}
        costs={MOCK_DOCKET_STAMPED.costs}
        routes={MOCK_DOCKET_STAMPED.routes}
      />,
    )

    // Actual routed cost: $0.0140
    expect(screen.getByTestId('actual-routed-cost')).toHaveTextContent('$0.0140')
    // Always-VLM Baseline: $0.0310
    expect(screen.getByTestId('baseline-cost')).toHaveTextContent('$0.0310')
  })

  it('renders savings and percentage for the stamped fixture', () => {
    const costView = toCostView(MOCK_DOCKET_STAMPED)
    render(
      <CostComparisonPanel
        cost={costView}
        costs={MOCK_DOCKET_STAMPED.costs}
        routes={MOCK_DOCKET_STAMPED.routes}
      />,
    )

    // savings = 0.0310 - 0.0140 = 0.0170
    // savingsPct = (0.0170 / 0.0310) * 100 = 54.838... -> 54.8%
    expect(screen.getByTestId('savings-usd')).toHaveTextContent('$0.0170')
    expect(screen.getByTestId('savings-pct')).toHaveTextContent('54.8%')
    expect(screen.getByTestId('savings-badge')).toHaveTextContent('Saved $0.0170 (54.8%)')
  })

  it('a zero baseline renders an em dash and never Infinity', () => {
    const zeroBaselineDocket: Docket = {
      ...MOCK_DOCKET_STAMPED,
      always_vlm_estimate_usd: 0,
    }
    const costView = toCostView(zeroBaselineDocket)

    render(
      <CostComparisonPanel
        cost={costView}
        costs={zeroBaselineDocket.costs}
        routes={zeroBaselineDocket.routes}
      />,
    )

    expect(screen.getByTestId('baseline-cost')).toHaveTextContent('—')
    expect(screen.getByTestId('savings-usd')).toHaveTextContent('—')
    expect(screen.getByTestId('savings-pct')).toHaveTextContent('—')
    expect(screen.queryByText(/Infinity/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/NaN/i)).not.toBeInTheDocument()
  })

  it('an over-baseline docket shows the "cost more than baseline" message', () => {
    const overBaselineDocket: Docket = {
      ...MOCK_DOCKET_STAMPED,
      total_cost_usd: 0.05,
      always_vlm_estimate_usd: 0.03,
    }
    const costView = toCostView(overBaselineDocket)

    render(
      <CostComparisonPanel
        cost={costView}
        costs={overBaselineDocket.costs}
        routes={overBaselineDocket.routes}
      />,
    )

    expect(screen.getByTestId('over-baseline-warning')).toHaveTextContent(
      'Routing cost more than baseline by $0.0200',
    )
    expect(screen.getByTestId('savings-pct')).toHaveTextContent(
      'Routing cost more than baseline',
    )
  })

  it('the table renders one row per cost entry', () => {
    const costView = toCostView(MOCK_DOCKET_STAMPED)
    render(
      <CostComparisonPanel
        cost={costView}
        costs={MOCK_DOCKET_STAMPED.costs}
        routes={MOCK_DOCKET_STAMPED.routes}
      />,
    )

    const rows = screen.getAllByTestId('cost-breakdown-row')
    expect(rows).toHaveLength(MOCK_DOCKET_STAMPED.costs.length)
  })

  it('renders router estimate next to actual total to expose estimator drift', () => {
    const costView = toCostView(MOCK_DOCKET_STAMPED)
    render(
      <CostComparisonPanel
        cost={costView}
        costs={MOCK_DOCKET_STAMPED.costs}
        routes={MOCK_DOCKET_STAMPED.routes}
      />,
    )

    expect(screen.getByTestId('router-estimated-cost')).toHaveTextContent('$0.0040')
  })
})
