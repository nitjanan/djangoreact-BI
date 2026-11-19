import { ArrowRight, CircleAlert, Database, TrendingDown, TriangleAlert } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import type { Schemas } from '@/api/client'
import { cn } from '@/lib/utils'

type Item = Schemas['InsightItem']

const SEVERITY: Record<
  Item['severity'],
  { label: string; icon: LucideIcon; tone: string; accent: string }
> = {
  high: {
    label: 'ต้องดูด่วน',
    icon: CircleAlert,
    tone: 'bg-signal/15 text-[#a33a1c]',
    accent: 'shadow-[inset_3px_0_0_var(--color-signal)]',
  },
  medium: {
    label: 'ควรตรวจสอบ',
    icon: TriangleAlert,
    tone: 'bg-[#eda100]/15 text-[#7a5300]',
    accent: 'shadow-[inset_3px_0_0_#eda100]',
  },
  good: {
    label: 'ดีขึ้น',
    icon: TrendingDown,
    tone: 'bg-primary/10 text-primary',
    accent: 'shadow-[inset_3px_0_0_var(--color-primary)]',
  },
  info: {
    label: 'คุณภาพข้อมูล',
    icon: Database,
    tone: 'bg-muted text-muted-foreground',
    accent: 'shadow-[inset_3px_0_0_var(--color-border)]',
  },
}

/**
 * สรุปและข้อสังเกตอัตโนมัติ (คำนวณตามกฎที่ backend: dbapp/services/insights.py)
 * ย่อหน้าภาพรวม + การ์ดข้อสังเกตเรียงตามความสำคัญ การ์ดที่ชี้รถกดไปดูรถคันนั้นได้
 */
export function Insights({
  data,
  onSelectCar,
}: {
  data: Schemas['Insights']
  onSelectCar: (carId: number, branchCompanyId: string) => void
}) {
  return (
    <div className="grid gap-3">
      <ul className="grid gap-1 rounded-xl border bg-card px-5 py-4 text-[0.95rem] leading-relaxed">
        {data.overview.map((line) => (
          <li key={line} className="flex gap-2">
            <span aria-hidden className="mt-[0.6em] size-1.5 shrink-0 rounded-full bg-primary" />
            {line}
          </li>
        ))}
      </ul>

      {data.items.length > 0 ? (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.items.map((item) => {
            const s = SEVERITY[item.severity]
            return (
              <li
                key={item.title}
                className={cn('flex flex-col gap-2 rounded-xl border bg-card p-4', s.accent)}
              >
                <span
                  className={cn(
                    'inline-flex w-fit items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium',
                    s.tone,
                  )}
                >
                  <s.icon className="size-3.5" aria-hidden />
                  {s.label}
                </span>
                <h3 className="font-sans text-base leading-snug font-semibold">{item.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{item.detail}</p>
                {item.target && (
                  <button
                    type="button"
                    onClick={() =>
                      item.target && onSelectCar(item.target.car_id, item.target.branch_company_id)
                    }
                    className="mt-auto inline-flex w-fit items-center gap-1 rounded text-sm font-medium text-primary hover:underline focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {item.action ?? 'ดูรถคันนี้'}
                    <ArrowRight className="size-3.5" aria-hidden />
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">ไม่พบจุดผิดปกติตามเกณฑ์ในตัวกรองนี้</p>
      )}
    </div>
  )
}
