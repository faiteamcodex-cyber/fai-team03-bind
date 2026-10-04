import { describe, expect, it } from 'vitest'

import {
  EMPTY_VALUE,
  formatConfidence,
  formatCount,
  formatDuration,
  formatEpochMs,
  formatPercent,
  formatUsd,
  formatWriter,
} from './format'

describe('formatUsd', () => {
  it('shows sub-cent costs at 4 decimals', () => {
    expect(formatUsd(0.003)).toBe('$0.0030')
    expect(formatUsd(0.001)).toBe('$0.0010')
  })

  it('shows a zero cost as $0.0000 rather than an empty value', () => {
    expect(formatUsd(0)).toBe('$0.0000')
  })

  it('renders an em dash for missing values', () => {
    expect(formatUsd(null)).toBe(EMPTY_VALUE)
    expect(formatUsd(undefined)).toBe(EMPTY_VALUE)
  })

  it('renders an em dash for non-finite values instead of NaN or Infinity', () => {
    expect(formatUsd(Number.NaN)).toBe(EMPTY_VALUE)
    expect(formatUsd(Number.POSITIVE_INFINITY)).toBe(EMPTY_VALUE)
  })
})

describe('formatPercent', () => {
  it('formats a percentage to one decimal', () => {
    expect(formatPercent(54.838)).toBe('54.8%')
  })

  it('renders an em dash when savings are not computable', () => {
    expect(formatPercent(null)).toBe(EMPTY_VALUE)
    expect(formatPercent(Number.NaN)).toBe(EMPTY_VALUE)
  })
})

describe('formatConfidence', () => {
  it('matches the precision the kernel uses for its threshold', () => {
    expect(formatConfidence(0.58)).toBe('0.58')
    expect(formatConfidence(0.72)).toBe('0.72')
  })

  it('renders an em dash when the writer reports no confidence', () => {
    expect(formatConfidence(null)).toBe(EMPTY_VALUE)
  })
})

describe('formatDuration', () => {
  it('uses ms below one second and seconds above', () => {
    expect(formatDuration(820)).toBe('820 ms')
    expect(formatDuration(7420)).toBe('7.4 s')
  })

  it('rejects negative durations', () => {
    expect(formatDuration(-5)).toBe(EMPTY_VALUE)
  })
})

describe('formatEpochMs', () => {
  it('formats epoch milliseconds into a readable local timestamp', () => {
    const formatted = formatEpochMs(1_791_009_600_000)  // 2026-10-03T06:40:00Z
    expect(formatted).not.toBe(EMPTY_VALUE)
    expect(formatted).toMatch(/2026/)
  })

  it('renders an em dash for a null closed timestamp', () => {
    expect(formatEpochMs(null)).toBe(EMPTY_VALUE)
  })
})

describe('formatWriter', () => {
  it('passes model ids through verbatim rather than prettifying them', () => {
    expect(formatWriter('apac.amazon.nova-lite-v1:0')).toBe('apac.amazon.nova-lite-v1:0')
  })

  it('renders an em dash when no writer ran', () => {
    expect(formatWriter(null)).toBe(EMPTY_VALUE)
    expect(formatWriter('   ')).toBe(EMPTY_VALUE)
  })
})

describe('formatCount', () => {
  it('adds thousands separators to token counts', () => {
    expect(formatCount(1240)).toBe('1,240')
  })
})
