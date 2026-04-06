import type { ReactNode } from 'react'

type StatusPillProps = {
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  children: ReactNode
}

export function StatusPill({ tone = 'default', children }: StatusPillProps) {
  return <span className={`status-pill status-pill--${tone}`}>{children}</span>
}
