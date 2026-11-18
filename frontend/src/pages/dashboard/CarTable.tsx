import type { CarRow, Schemas } from '@/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { num } from '@/lib/format'
import { cn } from '@/lib/utils'

const COLUMNS: { label: string; value: (r: CarRow | Schemas['CarTotals']) => string }[] = [
  { label: '%MA', value: (r) => `${num(r.percent_ma, 2)}%` },
  { label: 'การทำงานเฉลี่ยต่อวัน', value: (r) => num(r.avg_work_per_day, 2) },
  { label: 'การทำงาน (hr)', value: (r) => num(r.work_total, 2) },
  { label: 'น้ำมันดีเซล (L)', value: (r) => num(r.oil_total, 2) },
  { label: 'อัตราการใช้เชื้อเพลิง (L/hr)', value: (r) => num(r.fuel_rate, 2) },
  { label: 'ค่าใช้จ่ายซ่อม (THB)', value: (r) => num(r.repair_total, 2) },
  { label: 'ต้นทุนซ่อม (บาท/ชั่วโมง)', value: (r) => num(r.repair_cost_per_hr, 2) },
  { label: 'จำนวนครั้งที่เสีย', value: (r) => String(r.failure_count) },
  { label: 'MTBF (ชม.)', value: (r) => num(r.mtbf, 1) },
  { label: 'MTTR (ชม.)', value: (r) => num(r.mttr, 1) },
]

export function CarTable({
  table,
  selected,
  onSelect,
}: {
  table: Schemas['CarTable']
  selected: CarRow | null
  onSelect: (row: CarRow) => void
}) {
  const isSelected = (r: CarRow) =>
    selected?.car_id === r.car_id && selected.branch_company_id === r.branch_company_id

  return (
    <Card>
      <CardHeader>
        <CardTitle>รายการรถ</CardTitle>
        <CardDescription>คลิกที่แถวเพื่อดูข้อมูลเฉพาะคันนั้น</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="max-h-[480px] overflow-auto rounded-lg border">
          <Table className="text-xs">
            <TableHeader className="sticky top-0 z-10 bg-muted">
              <TableRow>
                <TableHead className="w-10">No.</TableHead>
                <TableHead>บริษัท</TableHead>
                <TableHead>CODE</TableHead>
                <TableHead>NAME</TableHead>
                {COLUMNS.map((c) => (
                  <TableHead key={c.label} className="text-right whitespace-normal">
                    {c.label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {table.rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={COLUMNS.length + 4} className="h-24 text-center text-muted-foreground">
                    ไม่มีข้อมูล
                  </TableCell>
                </TableRow>
              )}
              {table.rows.map((row, i) => (
                <TableRow
                  key={`${row.car_id}-${row.branch_company_id}`}
                  data-state={isSelected(row) ? 'selected' : undefined}
                  className="cursor-pointer"
                  tabIndex={0}
                  aria-selected={isSelected(row)}
                  onClick={() => onSelect(row)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelect(row)
                    }
                  }}
                >
                  <TableCell>{i + 1}</TableCell>
                  <TableCell>{row.branch_company_name}</TableCell>
                  <TableCell className="font-medium">{row.code}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  {COLUMNS.map((c) => (
                    <TableCell key={c.label} className="text-right tabular-nums">
                      {c.value(row)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
            {table.rows.length > 0 && (
              <TableFooter className="sticky bottom-0 bg-muted">
                <TableRow>
                  <TableCell colSpan={4} className="text-right font-semibold">
                    รวมทั้งหมด
                  </TableCell>
                  {COLUMNS.map((c) => (
                    <TableCell key={c.label} className={cn('text-right font-semibold tabular-nums')}>
                      {c.value(table.totals)}
                    </TableCell>
                  ))}
                </TableRow>
              </TableFooter>
            )}
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
