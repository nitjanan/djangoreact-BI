import { ArrowDown, ArrowUp } from 'lucide-react'
import { useState } from 'react'

import type { Schemas } from '@/api/client'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { num } from '@/lib/format'
import { cn } from '@/lib/utils'

type Branch = Schemas['BranchCompare']
type Key = Exclude<keyof Branch, 'branch_company_id' | 'branch_company_name'>

/** better: ค่าน้อยดี (down) หรือมากดี (up) → ไฮไลต์สาขาที่ดีที่สุด/แย่ที่สุด */
const COLUMNS: {
  key: Key
  label: string
  unit?: string
  digits: number
  better?: 'up' | 'down'
}[] = [
  { key: 'car_count', label: 'จำนวน', unit: 'คัน', digits: 0 },
  { key: 'repair_total', label: 'ค่าซ่อมรวม', unit: 'บาท', digits: 0 },
  { key: 'repair_cost_per_hr', label: 'ต้นทุนซ่อม/ชม.', unit: 'บาท', digits: 2, better: 'down' },
  { key: 'percent_ma', label: '%MA เฉลี่ย', unit: '%', digits: 1, better: 'up' },
  { key: 'failure_count', label: 'ครั้งที่เสีย', unit: 'ครั้ง', digits: 0 },
  { key: 'mtbf', label: 'MTBF', unit: 'ชม.', digits: 1, better: 'up' },
  { key: 'downtime_hours', label: 'Downtime', unit: 'ชม.', digits: 0 },
]

export function BranchCompare({
  data,
  onSelectBranch,
}: {
  data: Branch[]
  onSelectBranch: (branchCompanyId: string) => void
}) {
  const [sort, setSort] = useState<{ key: Key; dir: 'asc' | 'desc' }>({
    key: 'repair_total',
    dir: 'desc',
  })

  // สาขาที่ดีที่สุด/แย่ที่สุดของคอลัมน์ที่มีทิศทางดี-แย่ (ต้องมีอย่างน้อย 2 สาขาที่มีค่า)
  const extremes = Object.fromEntries(
    COLUMNS.filter((c) => c.better).map((c) => {
      const values = data.map((b) => b[c.key]).filter((v): v is number => v !== null)
      if (values.length < 2) return [c.key, null]
      const lo = Math.min(...values)
      const hi = Math.max(...values)
      return [c.key, c.better === 'down' ? { best: lo, worst: hi } : { best: hi, worst: lo }]
    }),
  ) as Partial<Record<Key, { best: number; worst: number } | null>>

  const rows = [...data].sort((a, b) => {
    const x = a[sort.key] ?? -Infinity
    const y = b[sort.key] ?? -Infinity
    return sort.dir === 'asc' ? x - y : y - x
  })

  return (
    <div className="grid gap-2">
      <div className="scroll-thin overflow-x-auto rounded-xl border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-40">บริษัท</TableHead>
              {COLUMNS.map((c) => {
                const active = sort.key === c.key
                const Icon = sort.dir === 'asc' ? ArrowUp : ArrowDown
                return (
                  <TableHead key={c.key} className="text-right">
                    <button
                      type="button"
                      onClick={() =>
                        setSort((s) => ({
                          key: c.key,
                          dir: s.key === c.key && s.dir === 'desc' ? 'asc' : 'desc',
                        }))
                      }
                      className="inline-flex items-start gap-1 text-right hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <span>
                        {c.label}
                        {c.unit && (
                          <span className="block text-xs font-normal text-muted-foreground">
                            {c.unit}
                          </span>
                        )}
                      </span>
                      {active && <Icon className="mt-0.5 size-3.5 text-signal" aria-hidden />}
                    </button>
                  </TableHead>
                )
              })}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((b) => (
              <TableRow key={b.branch_company_id}>
                <TableCell>
                  <button
                    type="button"
                    onClick={() => onSelectBranch(b.branch_company_id)}
                    className="text-left font-medium text-primary underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
                    title="ดูเฉพาะบริษัทนี้"
                  >
                    {b.branch_company_name}
                  </button>
                </TableCell>
                {COLUMNS.map((c) => {
                  const v = b[c.key]
                  const ex = extremes[c.key]
                  const best = ex && v === ex.best
                  const worst = ex && v === ex.worst
                  return (
                    <TableCell
                      key={c.key}
                      className={cn(
                        'text-right tabular-nums',
                        best && 'font-semibold text-emerald-700',
                        worst && 'font-semibold text-red-700',
                      )}
                    >
                      {num(v, c.digits)}
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-muted-foreground">
        <span className="font-semibold text-emerald-700">สีเขียว</span> = ดีที่สุด ·{' '}
        <span className="font-semibold text-red-700">สีแดง</span> = ควรดูเป็นพิเศษ (ต้นทุนซ่อม/ชม. ต่ำดี, %MA
        และ MTBF สูงดี) · กดชื่อบริษัทเพื่อดูเฉพาะบริษัทนั้น
      </p>
    </div>
  )
}
