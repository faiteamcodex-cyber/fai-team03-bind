import type { ReactNode } from 'react'

export interface EmptyStateProps {
  title?: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
  className?: string
}

/**
  Neutral empty state display for when no docket is active or available.
 */
export function EmptyState({
  title = 'No docket loaded',
  description = 'Open a docket or select one to view claims, map geometry, and cost analysis.',
  action,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={[
        'flex h-full min-h-[200px] flex-col items-center justify-center p-6 text-center',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {icon && <div className="mb-3 text-slate-500">{icon}</div>}
      <h3 className="text-sm font-medium text-slate-200">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-xs leading-relaxed text-slate-400">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
