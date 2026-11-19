import type { ReactNode } from 'react'

import { clampPercent } from '@/lib/format'
import { cn } from '@/lib/utils'

/** แถบตัวเลขสรุป: แผ่นเดียว แบ่งช่องด้วยเส้น ไม่ใช่การ์ดแยกกัน */
export function KpiStrip({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        // จอมือถือ 2 คอลัมน์: ช่องสุดท้ายที่เหลือเดี่ยวให้ยืดเต็มแถว ไม่ให้เห็นช่องว่างสีเทา
        'grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-3 xl:grid-cols-5',
        '[&>:last-child:nth-child(odd)]:col-span-2 sm:[&>:last-child:nth-child(odd)]:col-span-1',
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
}: {
  label: string
  value: string
  unit?: string
  /** แถบ 0–100 */
  meter?: number | null
  note?: string
}) {
  return (
    <div className="flex flex-col gap-1.5 bg-card px-4 py-3.5">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-heading text-2xl leading-none font-semibold tracking-tight tabular-nums">
        {value}
        {unit && (
          <small className="ml-1 font-sans text-xs font-normal text-muted-foreground">{unit}</small>
        )}
      </span>
      {meter !== undefined && (
        <div className="mt-0.5 h-1 overflow-hidden rounded-full bg-muted" aria-hidden>
          <span
            className="block h-full rounded-full bg-signal"
            style={{ width: `${clampPercent(meter)}%` }}
          />
        </div>
      )}
      {note && <span className="text-xs text-muted-foreground">{note}</span>}
    </div>
  )
}
