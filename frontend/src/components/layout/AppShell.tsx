import type { ReactNode } from 'react'

export interface AppShellProps {
  /** Usually `<Header />`. */
  header?: ReactNode
  children: ReactNode
}

/**
 * Top-level chrome. Deliberately thin: it owns page background, the vertical
 * rhythm, and the single `<main>` landmark. Panel composition happens in pages.
 */
export function AppShell({ header, children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-surface-0 text-slate-100">
      {header}
      <main className="min-h-0 flex-1 p-3 sm:p-4">{children}</main>
    </div>
  )
}
