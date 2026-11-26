import { ChevronDown, CircleHelp, FileSpreadsheet } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { downloadExcel, type ExportTable } from '@/lib/export-excel'
import { cn } from '@/lib/utils'

import type { ChartHelp } from './chart-help'

import { useExportFilters, useNoun } from './export-context'

/** แผงกราฟ: ขอบบาง ไม่มีเงา ชื่อกราฟ + หน่วย + ปุ่ม Excel */
export function ChartCard({
  title,
  unit,
  description,
  help,
  rows,
  empty,
  className,
  actions,
  children,
}: {
  title: string
  unit?: string
  /** วิธีอ่านกราฟ / หมายเหตุข้อมูล */
  description?: string
  /** กราฟนี้หมายถึงอะไร + วิธีอ่าน (ซ่อนไว้ กดเปิดได้) */
  help?: ChartHelp
  /** ข้อมูลสำหรับปุ่ม Excel */
  rows?: ExportTable
  /** true = ไม่มีข้อมูล แสดงข้อความแทนกราฟ */
  empty?: boolean
  className?: string
  /** ปุ่มเพิ่มเติมที่หัวกราฟ เช่น ปุ่มสลับมุมมอง */
  actions?: ReactNode
  children: ReactNode
}) {
  const noun = useNoun()
  const filters = useExportFilters()
  const [helpOpen, setHelpOpen] = useState(false)
  const helpId = useId()

  return (
    <figure className={cn('m-0 flex min-w-0 flex-col rounded-xl border bg-card', className)}>
      <figcaption className="flex items-start justify-between gap-3 px-4 pt-4">
        <div className="min-w-0">
          <h3 className="font-sans text-base font-semibold">{title}</h3>
          {unit && <p className="text-sm text-muted-foreground">หน่วย: {unit}</p>}
          {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
          {help && (
            <button
              type="button"
              onClick={() => setHelpOpen((v) => !v)}
              aria-expanded={helpOpen}
              aria-controls={helpId}
              className="mt-1 inline-flex items-center gap-1 rounded text-sm font-medium text-primary hover:underline focus-visible:outline-2 focus-visible:outline-ring"
            >
              <CircleHelp className="size-3.5" aria-hidden />
              วิธีอ่านกราฟ
              <ChevronDown
                className={cn('size-3.5 transition-transform', helpOpen && 'rotate-180')}
                aria-hidden
              />
            </button>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
        {actions}
        {rows && !empty && (
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0 text-muted-foreground"
            onClick={() => downloadExcel({ title, unit, filters, rows })}
            aria-label={`ดาวน์โหลด Excel: ${title}`}
          >
            <FileSpreadsheet />
            Excel
          </Button>
        )}
        </div>
      </figcaption>
      {help && helpOpen && (
        <div
          id={helpId}
          className="mx-4 mt-3 grid max-w-[80ch] gap-1.5 rounded-lg bg-steel px-3 py-2.5 text-sm"
        >
          <p>
            <span className="font-semibold">กราฟนี้คือ </span>
            {help.meaning}
          </p>
          <ul className="grid list-disc gap-0.5 pl-5 text-muted-foreground marker:text-primary">
            {help.read.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="min-w-0 px-2 pb-2">
        {empty ? (
          <div className="flex h-56 flex-col items-center justify-center gap-1 text-center text-sm text-muted-foreground">
            <span className="font-medium text-foreground">ยังไม่มีข้อมูลในช่วงนี้</span>
            ลองเปลี่ยนแผนก ประเภท{noun} หรือบริษัท
          </div>
        ) : (
          children
        )}
      </div>
    </figure>
  )
}
