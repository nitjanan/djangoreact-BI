import type { ReactNode } from 'react'
import { FileSpreadsheet } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { downloadExcel, type ExportTable } from '@/lib/export-excel'

import { useExportFilters } from './export-context'

export function ChartCard({
  title,
  unit,
  rows,
  empty,
  className,
  children,
}: {
  title: string
  unit?: string
  /** ข้อมูลสำหรับปุ่ม Excel */
  rows?: ExportTable
  /** true = ไม่มีข้อมูล แสดงข้อความแทนกราฟ */
  empty?: boolean
  className?: string
  children: ReactNode
}) {
  const filters = useExportFilters()

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {unit && <CardDescription>{unit}</CardDescription>}
        {rows && !empty && (
          <CardAction>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadExcel({ title, unit, filters, rows })}
              aria-label={`ดาวน์โหลด Excel: ${title}`}
            >
              <FileSpreadsheet />
              Excel
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent>
        {empty ? (
          <div className="flex h-60 items-center justify-center text-sm text-muted-foreground">
            ไม่มีข้อมูล
          </div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  )
}
