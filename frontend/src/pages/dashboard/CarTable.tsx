import { ArrowDown, ArrowUp, ArrowUpDown, Search, X } from 'lucide-react'
import { useState } from 'react'

import type { CarRow, Schemas } from '@/api/client'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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

import { useFuel, useNoun, type Fuel } from './export-context'

type Metrics = CarRow | Schemas['CarTotals']

/** ตัดช่องว่าง/ขีดออก ให้พิมพ์ทะเบียน "1ตญ2871" แล้วเจอ "1ตญ-2871" */
const normalize = (s: string) => s.toLowerCase().replace(/[\s-]/g, '')

const ALL_BRANDS = '__all__'
const ALL_TYPES = 'all'
const NO_BRAND = '__none__'
/** กรอกต่างกันแค่ช่องว่าง/ขีด/วงเล็บ/ตัวพิมพ์ ถือเป็นยี่ห้อเดียวกัน (เหมือนตารางเทียบรุ่นฝั่ง server) */
const brandKey = (brand: string | null | undefined) =>
  (brand ?? '').toUpperCase().replace(/[^\p{L}\p{N}]+/gu, '') || NO_BRAND

/** ยี่ห้อที่มีในตาราง เรียงตามจำนวนคัน (ชื่อที่แสดงใช้แบบที่เจอก่อน) */
function brandOptions(rows: CarRow[]) {
  const map = new Map<string, { label: string; count: number }>()
  for (const r of rows) {
    const key = brandKey(r.brand)
    const item = map.get(key) ?? { label: r.brand?.trim() || 'ไม่ระบุยี่ห้อ', count: 0 }
    item.count += 1
    map.set(key, item)
  }
  return [...map.entries()]
    .map(([key, v]) => ({ key, ...v }))
    .sort((a, b) =>
      a.key === NO_BRAND
        ? 1
        : b.key === NO_BRAND
          ? -1
          : b.count - a.count || a.label.localeCompare(b.label, 'th'),
    )
}

type SortValue = number | string | null | undefined

type Column = {
  label: string
  unit?: string
  value: (r: Metrics) => string
  sortBy: (r: CarRow) => SortValue
}

/** คอลัมน์ตัวเลข: รถบรรทุกเทียบน้ำมันเป็น ลิตร/กม. และมีคอลัมน์ระยะทาง */
const columnsFor = (fuel: Fuel): Column[] => [
  {
    label: '%MA',
    value: (r) => `${num(r.percent_ma, 2)}%`,
    sortBy: (r) => r.percent_ma,
  },
  {
    label: 'ทำงานเฉลี่ยต่อวัน',
    unit: 'ชม.',
    value: (r) => num(r.avg_work_per_day, 2),
    sortBy: (r) => r.avg_work_per_day,
  },
  {
    label: 'การทำงานรวม',
    unit: 'ชม.',
    value: (r) => num(r.work_total, 2),
    sortBy: (r) => r.work_total,
  },
  {
    label: 'น้ำมันดีเซล',
    unit: 'ลิตร',
    value: (r) => num(r.oil_total, 2),
    sortBy: (r) => r.oil_total,
  },
  ...(fuel.field === 'liter_per_km'
    ? [
        {
          label: 'ระยะทาง',
          unit: 'กม.',
          value: (r: Metrics) => num(r.km_total, 0),
          sortBy: (r: CarRow) => r.km_total,
        },
      ]
    : []),
  {
    label: 'อัตราเชื้อเพลิง',
    unit: fuel.unit,
    value: (r) => num(r[fuel.field], 2),
    sortBy: (r) => r[fuel.field],
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
  {
    label: 'ครั้งที่เสีย',
    value: (r) => String(r.failure_count),
    sortBy: (r) => r.failure_count,
  },
  {
    label: 'MTBF',
    unit: 'ชม.',
    value: (r) => num(r.mtbf, 1),
    sortBy: (r) => r.mtbf,
  },
  {
    label: 'MTTR',
    unit: 'ชม.',
    value: (r) => num(r.mttr, 1),
    sortBy: (r) => r.mttr,
  },
]

type TextColumn = {
  label: string
  sortBy: (r: CarRow) => SortValue
  cell: (r: CarRow) => string
  className?: string
}

const TEXT_COLUMNS: TextColumn[] = [
  { label: 'บริษัท', sortBy: (r) => r.branch_company_name, cell: (r) => r.branch_company_name },
  { label: 'รหัส', sortBy: (r) => r.code, cell: (r) => r.code || '–', className: 'font-medium' },
  { label: 'ชื่อ', sortBy: (r) => r.name, cell: (r) => r.name ?? '' },
  { label: 'ยี่ห้อ', sortBy: (r) => r.brand, cell: (r) => r.brand || '–' },
  { label: 'รุ่น', sortBy: (r) => r.car_model, cell: (r) => r.car_model || '–' },
  {
    label: 'ปีที่เริ่มใช้งาน',
    sortBy: (r) => r.start_year,
    cell: (r) => (r.start_year ? String(r.start_year) : '–'),
    className: 'tabular-nums',
  },
  {
    label: 'อายุ (ปี)',
    sortBy: (r) => r.age,
    cell: (r) => (r.age == null ? '–' : String(r.age)),
    className: 'tabular-nums',
  },
]

/** ลำดับ + คอลัมน์ตัวหนังสือ (ใช้กับ colSpan ของแถวว่าง/แถวรวม) */
const LEADING_COLUMNS = TEXT_COLUMNS.length + 1

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
  carTypes,
  carType,
  onSelectCarType,
}: {
  table: Schemas['CarTable']
  selected: CarRow | null
  onSelect: (row: CarRow) => void
  /** ประเภทรถ: กรองทั้งหน้า (ฝั่ง server) ไม่ใช่แค่ตารางนี้ */
  carTypes: { id: number; name: string }[]
  carType: number | null
  onSelectCarType: (id: number | null) => void
}) {
  const noun = useNoun()
  const COLUMNS = columnsFor(useFuel())
  const SORTERS: Record<string, (r: CarRow) => SortValue> = Object.fromEntries(
    [...TEXT_COLUMNS, ...COLUMNS].map((c) => [c.label, c.sortBy]),
  )
  const [query, setQuery] = useState('')
  const [brand, setBrand] = useState(ALL_BRANDS)
  const brands = brandOptions(table.rows)
  // แผนก/ตัวกรองเปลี่ยนแล้วยี่ห้อที่เลือกไว้ไม่มีในตาราง -> กลับไปทุกยี่ห้อ
  const activeBrand = brands.some((b) => b.key === brand) ? brand : ALL_BRANDS
  const [sort, setSort] = useState<Sort>(null)
  const onSort = (key: string) =>
    setSort((s) =>
      s?.key === key
        ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' }
        : {
            key,
            dir: TEXT_COLUMNS.some((c) => c.label === key) ? 'asc' : 'desc',
          },
    )
  const isSelected = (r: CarRow) =>
    selected?.car_id === r.car_id && selected.branch_company_id === r.branch_company_id

  const q = normalize(query)
  // เก็บลำดับเดิมไว้ ค้นหาแล้วยังเห็นว่าคันนี้อยู่ลำดับที่เท่าไรในตารางเต็ม
  const rows = table.rows
    .map((row, index) => ({ row, rank: index + 1 }))
    .filter(({ row }) => activeBrand === ALL_BRANDS || brandKey(row.brand) === activeBrand)
    .filter(
      ({ row }) =>
        !q ||
        normalize(
          `${row.code ?? ''} ${row.name ?? ''} ${row.brand ?? ''} ${row.car_model ?? ''}`,
        ).includes(q),
    )
  // คอลัมน์เปลี่ยนตามแผนก (เช่น ลิตร/ชม. ↔ ลิตร/กม.) ถ้าคอลัมน์ที่เรียงอยู่หายไปก็ไม่ต้องเรียง
  const by = sort ? SORTERS[sort.key] : undefined
  if (sort && by) {
    rows.sort((a, b) => compare(by(a.row), by(b.row), sort.dir) || a.rank - b.rank)
  }
  const filtering = q !== '' || activeBrand !== ALL_BRANDS

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
            placeholder={`ค้นหาชื่อ${noun} รหัส ยี่ห้อ หรือรุ่น`}
            aria-label={`ค้นหาชื่อ${noun} รหัส ยี่ห้อ หรือรุ่น`}
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
        <Select
          value={carType === null ? ALL_TYPES : String(carType)}
          onValueChange={(v) => onSelectCarType(v === ALL_TYPES ? null : Number(v))}
        >
          <SelectTrigger className="w-full bg-card sm:w-56" aria-label={`ประเภท${noun}`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_TYPES}>ทุกประเภท{noun}</SelectItem>
            {carTypes.map((t) => (
              <SelectItem key={t.id} value={String(t.id)}>
                {t.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {brands.length > 1 && (
          <Select value={activeBrand} onValueChange={setBrand}>
            <SelectTrigger className="w-full bg-card sm:w-56" aria-label="กรองตามยี่ห้อ">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_BRANDS}>ทุกยี่ห้อ ({table.rows.length})</SelectItem>
              {brands.map((b) => (
                <SelectItem key={b.key} value={b.key}>
                  {b.label} ({b.count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
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
                  colSpan={COLUMNS.length + LEADING_COLUMNS}
                  className="h-28 text-center text-muted-foreground"
                >
                  {q
                    ? `ไม่พบ${noun}ที่ชื่อ รหัส ยี่ห้อ หรือรุ่นตรงกับ "${query.trim()}"`
                    : filtering
                      ? `ไม่มี${noun}ยี่ห้อนี้`
                      : `ยังไม่มี${noun}ที่มีข้อมูลในตัวกรองนี้`}
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
                {TEXT_COLUMNS.map((c) => (
                  <TableCell key={c.label} className={c.className}>
                    {c.cell(row)}
                  </TableCell>
                ))}
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
                <TableCell colSpan={LEADING_COLUMNS} className="text-right">
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
