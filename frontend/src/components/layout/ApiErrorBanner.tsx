import type { ApiError } from '@/services/api'

export interface ApiErrorBannerProps {
  readonly error: ApiError
  readonly onRetry?: () => void
}

function getErrorTitle(error: ApiError): string {
  switch (error.kind) {
    case 'network':
      return 'API Unreachable (Network Error)'
    case 'timeout':
      return 'Request Timeout (Lambda Cold Start)'
    case 'client':
      return `Client Error ${error.status ? `(HTTP ${error.status})` : '(4xx)'}`
    case 'server':
      return `Server Error ${error.status ? `(HTTP ${error.status})` : '(5xx)'}`
    case 'config':
      return 'Configuration Error'
    case 'parse':
      return 'Invalid Response Format'
    default:
      return 'API Error'
  }
}

export function ApiErrorBanner({ error, onRetry }: ApiErrorBannerProps) {
  const title = getErrorTitle(error)
  const detailMessage = error.detail ?? error.message

  return (
    <div
      role="alert"
      data-testid="api-error-banner"
      data-error-kind={error.kind}
      className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-red-200"
    >
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-1 text-xs font-mono text-red-300">{detailMessage}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded bg-red-500/20 px-3 py-1.5 text-xs font-semibold text-red-100 hover:bg-red-500/30 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
        >
          Retry Request
        </button>
      )}
    </div>
  )
}
