import { ArrowDown, ArrowUp, ArrowUpDown, Search, X } from 'lucide-react'
import { useState } from 'react'

import type { CarRow, Schemas } from '@/api/client'
import { Input } from '@/components/ui/input'
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

type Metrics = CarRow | Schemas['CarTotals']

/** ตัดช่องว่าง/ขีดออก ให้พิมพ์ทะเบียน "1ตญ2871" แล้วเจอ "1ตญ-2871" */
const normalize = (s: string) => s.toLowerCase().replace(/[\s-]/g, '')

type SortValue = number | string | null | undefined

const COLUMNS: {
  label: string
  unit?: string
  value: (r: Metrics) => string
  sortBy: (r: CarRow) => SortValue
}[] = [
  { label: '%MA', value: (r) => `${num(r.percent_ma, 2)}%`, sortBy: (r) => r.percent_ma },
  {
    label: 'ทำงานเฉลี่ยต่อวัน',
    unit: 'ชม.',
    value: (r) => num(r.avg_work_per_day, 2),
    sortBy: (r) => r.avg_work_per_day,
  },
  {
    label: 'การทำงาน',
    unit: 'ชม.',
    value: (r) => num(r.work_total, 2),
    sortBy: (r) => r.work_total,
  },
  { label: 'น้ำมันดีเซล', unit: 'ลิตร', value: (r) => num(r.oil_total, 2), sortBy: (r) => r.oil_total },
  {
    label: 'อัตราเชื้อเพลิง',
    unit: 'ลิตร/ชม.',
    value: (r) => num(r.fuel_rate, 2),
    sortBy: (r) => r.fuel_rate,
  },
  {
    label: 'ค่าซ่อม',
    unit: 'บาท',
    value: (r) => num(r.repair_total, 2),
    sortBy: (r) => r.repair_total,
  },
  {
    label: 'ต้นทุนซ่อม',
    unit: 'บาท/ชม.',
    value: (r) => num(r.repair_cost_per_hr, 2),
    sortBy: (r) => r.repair_cost_per_hr,
  },
  { label: 'ครั้งที่เสีย', value: (r) => String(r.failure_count), sortBy: (r) => r.failure_count },
  { label: 'MTBF', unit: 'ชม.', value: (r) => num(r.mtbf, 1), sortBy: (r) => r.mtbf },
  { label: 'MTTR', unit: 'ชม.', value: (r) => num(r.mttr, 1), sortBy: (r) => r.mttr },
]

const TEXT_COLUMNS: { label: string; sortBy: (r: CarRow) => SortValue }[] = [
  { label: 'บริษัท', sortBy: (r) => r.branch_company_name },
  { label: 'รหัส', sortBy: (r) => r.code },
  { label: 'ชื่อรถ', sortBy: (r) => r.name },
]

const SORTERS: Record<string, (r: CarRow) => SortValue> = Object.fromEntries(
  [...TEXT_COLUMNS, ...COLUMNS].map((c) => [c.label, c.sortBy]),
)

type Sort = { key: string; dir: 'asc' | 'desc' } | null

/** ค่าว่างอยู่ท้ายเสมอ ไม่ว่าจะเรียงขึ้นหรือลง */
function compare(a: SortValue, b: SortValue, dir: 'asc' | 'desc') {
  const emptyA = a == null || a === ''
  const emptyB = b == null || b === ''
  if (emptyA || emptyB) return emptyA === emptyB ? 0 : emptyA ? 1 : -1
  const diff =
    typeof a === 'number' && typeof b === 'number'
      ? a - b
      : String(a).localeCompare(String(b), 'th', { numeric: true })
  return dir === 'asc' ? diff : -diff
}

/** หัวคอลัมน์ที่กดเรียงได้: ตัวเลขกดครั้งแรกเรียงมากไปน้อย ตัวหนังสือเรียง ก→ฮ กดซ้ำสลับทิศ */
function SortHead({
  label,
  unit,
  sort,
  numeric,
  onSort,
}: {
  label: string
  unit?: string
  sort: Sort
  numeric?: boolean
  onSort: (key: string) => void
}) {
  const active = sort?.key === label
  const Icon = !active ? ArrowUpDown : sort.dir === 'asc' ? ArrowUp : ArrowDown
  return (
    <TableHead
      className={cn('leading-tight', numeric && 'text-right align-bottom')}
      aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      <button
        type="button"
        onClick={() => onSort(label)}
        className={cn(
          'group inline-flex items-start gap-1 rounded font-medium hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring',
          numeric && 'flex-row-reverse text-right',
        )}
      >
        <span>
          {label}
          {unit && <span className="block text-xs font-normal text-muted-foreground">{unit}</span>}
        </span>
        <Icon
          aria-hidden
          className={cn(
            'mt-0.5 size-3.5 shrink-0',
            active ? 'text-signal' : 'text-muted-foreground/50 group-hover:text-muted-foreground',
          )}
        />
      </button>
    </TableHead>
  )
}

export function CarTable({
  table,
  selected,
  onSelect,
}: {
  table: Schemas['CarTable']
  selected: CarRow | null
  onSelect: (row: CarRow) => void
}) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<Sort>(null)
  const onSort = (key: string) =>
    setSort((s) =>
      s?.key === key
        ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: TEXT_COLUMNS.some((c) => c.label === key) ? 'asc' : 'desc' },
    )
  const isSelected = (r: CarRow) =>
    selected?.car_id === r.car_id && selected.branch_company_id === r.branch_company_id

  const q = normalize(query)
  // เก็บลำดับเดิมไว้ ค้นหาแล้วยังเห็นว่าคันนี้อยู่ลำดับที่เท่าไรในตารางเต็ม
  const rows = table.rows
    .map((row, index) => ({ row, rank: index + 1 }))
    .filter(({ row }) => !q || normalize(`${row.code ?? ''} ${row.name ?? ''}`).includes(q))
  if (sort) {
    const by = SORTERS[sort.key]
    rows.sort((a, b) => compare(by(a.row), by(b.row), sort.dir) || a.rank - b.rank)
  }
  const filtering = q !== ''

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <div className="relative w-full sm:w-80">
          <Search
            className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && setQuery('')}
            placeholder="ค้นหาชื่อรถหรือรหัส"
            aria-label="ค้นหาชื่อรถหรือรหัส"
            className="bg-card pr-8 pl-8 [&::-webkit-search-cancel-button]:hidden"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute top-1/2 right-1.5 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
              aria-label="ล้างคำค้นหา"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>
        {filtering && (
          <span className="text-sm text-muted-foreground" aria-live="polite">
            พบ {rows.length} จาก {table.rows.length} คัน
          </span>
        )}
      </div>

      {/* ให้กล่องนี้เป็นตัวเลื่อนทั้งสองแกน เพื่อให้หัวตารางและแถวรวมติดขอบได้ */}
      <div className="scroll-thin max-h-[520px] overflow-auto rounded-xl border bg-card [&>[data-slot=table-container]]:overflow-visible">
        <Table className="text-sm">
          <TableHeader className="sticky top-0 z-10 bg-card shadow-[inset_0_-1px_0_var(--color-border)]">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-12" aria-sort={sort ? 'none' : 'ascending'}>
                <button
                  type="button"
                  onClick={() => setSort(null)}
                  title="กลับไปเรียงตามลำดับเดิม"
                  className={cn(
                    'rounded font-medium text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring',
                    !sort && 'text-foreground',
                  )}
                >
                  ลำดับ
                </button>
              </TableHead>
              {TEXT_COLUMNS.map((c) => (
                <SortHead key={c.label} label={c.label} sort={sort} onSort={onSort} />
              ))}
              {COLUMNS.map((c) => (
                <SortHead
                  key={c.label}
                  label={c.label}
                  unit={c.unit}
                  sort={sort}
                  numeric
                  onSort={onSort}
                />
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={COLUMNS.length + 4}
                  className="h-28 text-center text-muted-foreground"
                >
                  {filtering ? `ไม่พบรถที่ชื่อหรือรหัสตรงกับ "${query.trim()}"` : 'ยังไม่มีรถที่มีข้อมูลในตัวกรองนี้'}
                </TableCell>
              </TableRow>
            )}
            {rows.map(({ row, rank }) => (
              <TableRow
                key={`${row.car_id}-${row.branch_company_id}`}
                data-state={isSelected(row) ? 'selected' : undefined}
                className="cursor-pointer data-[state=selected]:bg-signal/15 data-[state=selected]:shadow-[inset_3px_0_0_var(--color-signal)] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
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
                <TableCell className="text-muted-foreground tabular-nums">{rank}</TableCell>
                <TableCell>{row.branch_company_name}</TableCell>
                <TableCell className="font-medium">{row.code || '–'}</TableCell>
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
            <TableFooter className="sticky bottom-0 bg-steel font-semibold">
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={4} className="text-right">
                  {/* ยอดรวมมาจาก server นับทุกคันเสมอ ไม่ใช่เฉพาะคันที่ค้นเจอ */}
                  {filtering ? 'รวมทั้งหมด' : 'รวม'} {table.rows.length} คัน
                </TableCell>
                {COLUMNS.map((c) => (
                  <TableCell key={c.label} className="text-right tabular-nums">
                    {c.value(table.totals)}
                  </TableCell>
                ))}
              </TableRow>
            </TableFooter>
          )}
        </Table>
      </div>
    </div>
  )
}
