import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Panel } from './Panel'

describe('Panel', () => {
  it('renders its title as a level-2 heading', () => {
    render(
      <Panel title="Docket">
        <p>content</p>
      </Panel>,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'Docket' })).toBeInTheDocument()
  })

  it('associates the section with its heading when given an id', () => {
    const { container } = render(
      <Panel id="cost" title="Cost comparison">
        <p>content</p>
      </Panel>,
    )

    const section = container.querySelector('section#cost')

    expect(section).not.toBeNull()
    expect(section).toHaveAttribute('aria-labelledby', 'cost-heading')
  })

  it('renders without a title so it can wrap untitled regions', () => {
    render(
      <Panel>
        <p>bare content</p>
      </Panel>,
    )

    expect(screen.getByText('bare content')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 2 })).toBeNull()
  })

  it('renders action controls in the header', () => {
    render(
      <Panel title="Map" actions={<button type="button">Zoom to parcel</button>}>
        <p>content</p>
      </Panel>,
    )

    expect(screen.getByRole('button', { name: 'Zoom to parcel' })).toBeInTheDocument()
  })
})
