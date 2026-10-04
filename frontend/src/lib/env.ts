/**
 * Typed access to build-time environment configuration.
 *
 * Rules honoured here:
 *  - No production URL is hardcoded anywhere in the source (BIND rule 17).
 *  - Every `VITE_*` value is inlined into the public bundle, so this module is the
 *    single place that reads them.
 */

export type DataSourceMode = 'mock' | 'live'

function readString(value: string | undefined): string {
  return (value ?? '').trim()
}

function readBoolean(value: string | undefined, fallback: boolean): boolean {
  const normalised = readString(value).toLowerCase()
  if (normalised === '') return fallback
  if (['1', 'true', 'yes', 'on'].includes(normalised)) return true
  if (['0', 'false', 'no', 'off'].includes(normalised)) return false
  return fallback
}

/** Remove a trailing slash so callers can safely concatenate paths. */
function stripTrailingSlash(url: string): string {
  return url.endsWith('/') ? url.slice(0, -1) : url
}

export const env = {
  /** BIND API Gateway base URL — never hardcoded, always from the environment. */
  apiBaseUrl: stripTrailingSlash(readString(import.meta.env.VITE_API_BASE_URL)),

  /** Defaults to mock: the app must be runnable with zero backend available. */
  get useMockApi(): boolean {
    return readBoolean(import.meta.env.VITE_USE_MOCK_API, true)
  },

  /** Optional GeoJSON endpoint; falls back to the labelled local fixture. */
  geojsonUrl: readString(import.meta.env.VITE_GEOJSON_URL),
}

/** Which data source the app is currently wired to. */
export const dataSourceMode: DataSourceMode = env.useMockApi ? 'mock' : 'live'

export const isMockMode = (): boolean => env.useMockApi

/**
 * Configuration problems that should be shown to the user rather than thrown.
 * Live mode without a base URL is a misconfiguration, not a crash.
 */
export function getEnvConfigIssues(): string[] {
  const issues: string[] = []

  if (!env.useMockApi && env.apiBaseUrl === '') {
    issues.push(
      'VITE_USE_MOCK_API is false but VITE_API_BASE_URL is empty — the app cannot reach the BIND backend.',
    )
  }

  if (env.useMockApi && env.apiBaseUrl !== '') {
    issues.push(
      'A VITE_API_BASE_URL is configured while VITE_USE_MOCK_API is true — mock data is being used and the endpoint is ignored.',
    )
  }

  return issues
}
