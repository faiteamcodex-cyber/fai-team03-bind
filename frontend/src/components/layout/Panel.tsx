import type { ReactNode } from 'react'

export interface PanelProps {
  /** Rendered as the panel's heading when present. */
  title?: ReactNode
  /** Small muted line under the title. */
  description?: ReactNode
  /** Right-aligned controls (filters, toggles, counts). */
  actions?: ReactNode
  children: ReactNode
  className?: string
  /** Optional id for the region, useful for `aria-labelledby` deep links. */
  id?: string
}

/**
 * The standard surface used by every dashboard region (map, docket, cost).
 * Keeps borders, spacing and heading levels consistent across the app.
 */
export function Panel({ title, description, actions, children, className, id }: PanelProps) {
  const headingId = id ? `${id}-heading` : undefined

  return (
    <section
      id={id}
      aria-labelledby={title ? headingId : undefined}
      className={[
        'flex min-h-0 flex-col overflow-hidden rounded-lg border border-line bg-surface-1',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            {title && (
              <h2
                id={headingId}
                className="truncate text-sm font-semibold text-slate-100"
              >
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-0.5 text-xs text-slate-400">{description}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}

      <div className="min-h-0 flex-1">{children}</div>
    </section>
  )
}
