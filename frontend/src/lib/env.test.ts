import { afterEach, describe, expect, it, vi } from 'vitest'

/**
 * `env` is computed at module load, so each case stubs `import.meta.env`
 * (via `vi.stubEnv`), resets the module registry, then re-imports. This mirrors
 * how the module behaves under different `.env.local` configurations.
 */
async function loadEnvModule(values: Record<string, string>) {
  vi.resetModules()
  for (const [key, value] of Object.entries(values)) {
    vi.stubEnv(key, value)
  }
  return import('./env')
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe('env', () => {
  it('defaults to mock mode so the app runs with no backend', async () => {
    const mod = await loadEnvModule({})

    expect(mod.dataSourceMode).toBe('mock')
    expect(mod.isMockMode()).toBe(true)
  })

  it('treats VITE_USE_MOCK_API=false as live mode', async () => {
    const mod = await loadEnvModule({ VITE_USE_MOCK_API: 'false' })

    expect(mod.dataSourceMode).toBe('live')
  })

  it('strips a trailing slash from the API base URL', async () => {
    const mod = await loadEnvModule({
      VITE_API_BASE_URL: 'https://example.execute-api.ap-south-1.amazonaws.com/prod/',
    })

    expect(mod.env.apiBaseUrl).toBe(
      'https://example.execute-api.ap-south-1.amazonaws.com/prod',
    )
  })
})

describe('env configuration issues', () => {
  it('flags live mode without a base URL', async () => {
    const mod = await loadEnvModule({ VITE_USE_MOCK_API: 'false' })

    expect(mod.getEnvConfigIssues().join(' ')).toContain('VITE_API_BASE_URL is empty')
  })

  it('flags a base URL that is ignored because mock mode is on', async () => {
    const mod = await loadEnvModule({
      VITE_USE_MOCK_API: 'true',
      VITE_API_BASE_URL: 'https://example.execute-api.ap-south-1.amazonaws.com/prod',
    })

    expect(mod.getEnvConfigIssues().join(' ')).toContain('ignored')
  })

  it('reports no issues for a consistent live configuration', async () => {
    const mod = await loadEnvModule({
      VITE_USE_MOCK_API: 'false',
      VITE_API_BASE_URL: 'https://example.execute-api.ap-south-1.amazonaws.com/prod',
    })

    expect(mod.getEnvConfigIssues()).toEqual([])
  })
})
