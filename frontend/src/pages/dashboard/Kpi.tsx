import type { ReactNode } from 'react'

import { clampPercent } from '@/lib/format'
import { cn } from '@/lib/utils'

export function KpiGrid({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        'grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border md:grid-cols-3 xl:grid-cols-6',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function Kpi({
  label,
  value,
  unit,
  meter,
  note,
  feature,
}: {
  label: string
  value: string
  unit?: string
  /** แถบความคืบหน้า 0–100 */
  meter?: number | null
  note?: string
  /** ตัวเลขหลัก (พื้นเข้ม) */
  feature?: boolean
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-1 bg-card p-4',
        feature && 'bg-primary text-primary-foreground',
      )}
    >
      <span className={cn('text-xs text-muted-foreground', feature && 'text-primary-foreground/70')}>
        {label}
      </span>
      <span className="text-2xl font-semibold tracking-tight tabular-nums">
        {value}
        {unit && (
          <small
            className={cn(
              'ml-1 text-xs font-normal text-muted-foreground',
              feature && 'text-primary-foreground/70',
            )}
          >
            {unit}
          </small>
        )}
      </span>
      {meter !== undefined && (
        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden>
          <span
            className="block h-full rounded-full"
            style={{ width: `${clampPercent(meter)}%`, backgroundColor: '#1baf7a' }}
          />
        </div>
      )}
      {note && <span className="text-xs text-muted-foreground">{note}</span>}
    </div>
  )
}
