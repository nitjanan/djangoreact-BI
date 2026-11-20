import { Fragment } from 'react'

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

import { useFuel, useNoun } from './export-context'

type Comparison = Schemas['ModelComparison']
type Row = Schemas['ModelComparisonRow']

/** ต่างจากค่าของทั้งชนิดรถไม่ถึงเท่านี้ ถือว่าพอๆ กัน ไม่ใส่สี */
const SAME_BAND = 0.1

const dash = (v: number | null | undefined, digits: number) => (v == null ? '–' : num(v, digits))

function groupByType(rows: Row[]) {
  const groups: { name: string; typeCost: number | null; rows: Row[] }[] = []
  for (const r of rows) {
    const last = groups.at(-1)
    if (last && last.name === r.car_type_name) last.rows.push(r)
    else groups.push({ name: r.car_type_name, typeCost: r.type_repair_cost_per_hr, rows: [r] })
  }
  return groups
}

/** ต้นทุนซ่อม/ชม. เทียบกับทั้งชนิดรถ: ถูกกว่า = สีหลัก, แพงกว่า = แดง */
function VsType({ value }: { value: number | null }) {
  if (value == null) return <span className="text-muted-foreground">–</span>
  const pct = (value - 1) * 100
  const tone =
    value > 1 + SAME_BAND ? 'text-destructive' : value < 1 - SAME_BAND ? 'text-primary' : 'text-muted-foreground'
  return (
    <span className={cn('font-medium', tone)}>
      {Math.abs(pct) < 0.5 ? 'เท่ากัน' : `${pct > 0 ? '+' : '−'}${num(Math.abs(pct), 0)}%`}
    </span>
  )
}

export function ModelComparison({ data }: { data: Comparison }) {
  const noun = useNoun()
  const fuel = useFuel()
  const groups = groupByType(data.rows)

  const missingNote = data.missing_cars > 0 && (
    <p className="text-sm text-muted-foreground">
      ยังไม่ได้กรอกยี่ห้อ{' '}
      <span className="font-medium text-foreground">
        {num(data.missing_cars, 0)} จาก {num(data.total_cars, 0)} คัน
      </span>{' '}
      ใน webstock (หน้า admin ทะเบียนรถ) คันเหล่านี้ไม่อยู่ในตารางนี้ แต่ยังนับรวมในค่าของทั้งชนิดรถ
    </p>
  )

  if (data.rows.length === 0) {
    return (
      <div className="grid gap-2 rounded-xl border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
        <p>ยังไม่มี{noun}ที่กรอกยี่ห้อในตัวกรองนี้</p>
        {missingNote}
      </div>
    )
  }

  return (
    <div className="grid gap-3">
      {missingNote}
      <div className="scroll-thin max-h-[560px] overflow-auto rounded-xl border bg-card [&>[data-slot=table-container]]:overflow-visible">
        <Table className="text-sm">
          <TableHeader className="sticky top-0 z-10 bg-card shadow-[inset_0_-1px_0_var(--color-border)]">
            <TableRow className="hover:bg-transparent [&>th]:leading-tight">
              <TableHead>ยี่ห้อ / รุ่น</TableHead>
              <TableHead className="text-right align-bottom">จำนวน</TableHead>
              <TableHead className="text-right align-bottom">
                อายุเฉลี่ย
                <span className="block text-xs font-normal text-muted-foreground">ปี</span>
              </TableHead>
              <TableHead className="text-right align-bottom">
                ชั่วโมงทำงาน
                <span className="block text-xs font-normal text-muted-foreground">ชม.</span>
              </TableHead>
              <TableHead className="text-right align-bottom">
                ต้นทุนซ่อม
                <span className="block text-xs font-normal text-muted-foreground">บาท/ชม.</span>
              </TableHead>
              <TableHead className="text-right align-bottom">
                เทียบทั้งชนิด
                <span className="block text-xs font-normal text-muted-foreground">ต้นทุนซ่อม</span>
              </TableHead>
              <TableHead className="text-right align-bottom">
                อัตราเชื้อเพลิง
                <span className="block text-xs font-normal text-muted-foreground">{fuel.unit}</span>
              </TableHead>
              <TableHead className="text-right align-bottom">ครั้งที่เสีย</TableHead>
              <TableHead className="text-right align-bottom">
                MTBF
                <span className="block text-xs font-normal text-muted-foreground">ชม.</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groups.map((g) => (
              <Fragment key={g.name}>
                <TableRow className="bg-steel hover:bg-steel">
                  <TableCell colSpan={9} className="py-1.5 font-semibold">
                    {g.name}
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      ทั้งชนิด {dash(g.typeCost, 2)} บาท/ชม.
                      {g.rows.length === 1 && ' · มีรุ่นเดียว ยังไม่มีรุ่นอื่นให้เทียบ'}
                    </span>
                  </TableCell>
                </TableRow>
                {g.rows.map((r) => {
                  const few = r.cars < data.min_cars
                  return (
                    <TableRow key={`${g.name}|${r.brand}|${r.car_model ?? ''}`}>
                      <TableCell>
                        <span className="font-medium">{r.brand}</span>{' '}
                        <span className="text-muted-foreground">{r.car_model ?? 'ไม่ระบุรุ่น'}</span>
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap tabular-nums">
                        {r.cars} คัน
                        {few && (
                          <span
                            className="ml-1.5 rounded bg-muted px-1.5 py-px text-xs text-muted-foreground"
                            title={`น้อยกว่า ${data.min_cars} คัน ค่าของรุ่นนี้อาจมาจากคันใดคันหนึ่ง ยังสรุปเป็นรุ่นไม่ได้`}
                          >
                            ตัวอย่างน้อย
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{dash(r.avg_age, 1)}</TableCell>
                      <TableCell className="text-right tabular-nums">{num(r.work_total, 0)}</TableCell>
                      <TableCell className="text-right font-medium tabular-nums">
                        {dash(r.repair_cost_per_hr, 2)}
                      </TableCell>
                      <TableCell className={cn('text-right tabular-nums', few && 'opacity-60')}>
                        <VsType value={r.vs_type} />
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{dash(r.fuel, 2)}</TableCell>
                      <TableCell className="text-right tabular-nums">{r.failure_count}</TableCell>
                      <TableCell className="text-right tabular-nums">{dash(r.mtbf, 1)}</TableCell>
                    </TableRow>
                  )
                })}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

type Benchmark = Schemas['ModelBenchmark']
type Metrics = Schemas['BenchmarkMetrics']

/** better: ค่าน้อยดี (down) / มากดี (up) / ไม่มีดีไม่ดี (null เช่น อายุ) */
const BENCH_ROWS: {
  label: string
  unit?: string
  value: (m: Metrics) => number | null | undefined
  digits: number
  better: 'down' | 'up' | null
}[] = [
  { label: 'ต้นทุนซ่อม', unit: 'บาท/ชม.', value: (m) => m.repair_cost_per_hr, digits: 2, better: 'down' },
  { label: 'อัตราเชื้อเพลิง', value: (m) => m.fuel, digits: 2, better: 'down' },
  { label: 'MTBF', unit: 'ชม.', value: (m) => m.mtbf, digits: 1, better: 'up' },
  { label: '%MA', unit: '%', value: (m) => m.percent_ma, digits: 1, better: 'up' },
  { label: 'อายุ', unit: 'ปี', value: (m) => m.avg_age, digits: 1, better: null },
]

/** คันนี้ต่างจากค่าเทียบกี่ % พร้อมสีว่าดีหรือแย่ */
function Diff({
  mine,
  base,
  better,
}: {
  mine: number | null | undefined
  base: number | null | undefined
  better: 'down' | 'up' | null
}) {
  if (mine == null || base == null || base === 0) return null
  const ratio = mine / base
  const pct = (ratio - 1) * 100
  if (Math.abs(pct) < 0.5) return <span className="ml-1.5 text-xs text-muted-foreground">เท่ากัน</span>
  const worse = better === 'down' ? ratio > 1 + SAME_BAND : better === 'up' ? ratio < 1 - SAME_BAND : false
  const nicer = better === 'down' ? ratio < 1 - SAME_BAND : better === 'up' ? ratio > 1 + SAME_BAND : false
  return (
    <span
      className={cn(
        'ml-1.5 text-xs font-medium',
        worse ? 'text-destructive' : nicer ? 'text-primary' : 'text-muted-foreground',
      )}
    >
      คันนี้ {pct > 0 ? '+' : '−'}
      {num(Math.abs(pct), 0)}%
    </span>
  )
}

const modelName = (b: Benchmark) => [b.brand, b.car_model].filter(Boolean).join(' ')

export function ModelBenchmark({ data }: { data: Benchmark | null }) {
  const noun = useNoun()
  const fuel = useFuel()

  if (!data) {
    return (
      <p className="rounded-xl border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
        {noun}คันนี้ยังไม่ได้กรอกยี่ห้อ/รุ่นใน webstock จึงยังเทียบกับรุ่นเดียวกันไม่ได้
      </p>
    )
  }

  const name = modelName(data)
  const mine = data.car.repair_cost_per_hr
  const base = data.model?.repair_cost_per_hr
  const ratio = mine != null && base ? mine / base : null
  const headline =
    ratio == null
      ? null
      : Math.abs(ratio - 1) < 0.005
        ? `ต้นทุนซ่อมเท่ากับค่าเฉลี่ยของ ${name} คันอื่น`
        : `ต้นทุนซ่อม${ratio > 1 ? 'สูง' : 'ต่ำ'}กว่าค่าเฉลี่ยของ ${name} คันอื่น ${num(Math.abs(ratio - 1) * 100, 0)}%`

  const columns: { title: string; sub: string; metrics: Metrics | null | undefined }[] = [
    { title: 'คันนี้', sub: name, metrics: data.car },
    {
      title: `${name} คันอื่น`,
      sub: data.model ? `${data.model.cars} คัน` : 'ไม่มีคันอื่นรุ่นนี้',
      metrics: data.model,
    },
    {
      title: `${data.car_type_name} คันอื่น`,
      sub: data.type ? `${data.type.cars} คัน ทุกยี่ห้อ` : 'ไม่มีคันอื่นชนิดนี้',
      metrics: data.type,
    },
  ]

  return (
    <div className="grid gap-3">
      {headline && <p className="text-base font-medium">{headline}</p>}
      {data.model && data.model.cars < 3 && (
        <p className="text-sm text-muted-foreground">
          รุ่นนี้มีคันอื่นแค่ {data.model.cars} คัน ค่าเฉลี่ยของรุ่นอาจมาจากคันใดคันหนึ่ง
        </p>
      )}
      <div className="overflow-x-auto rounded-xl border bg-card">
        <Table className="text-sm">
          <TableHeader>
            <TableRow className="hover:bg-transparent [&>th]:leading-tight">
              <TableHead />
              {columns.map((c) => (
                <TableHead key={c.title} className="text-right align-bottom">
                  {c.title}
                  <span className="block text-xs font-normal text-muted-foreground">{c.sub}</span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {BENCH_ROWS.map((r) => (
              <TableRow key={r.label}>
                <TableCell className="font-medium">
                  {r.label}
                  <span className="ml-1 text-xs font-normal text-muted-foreground">
                    {r.unit ?? fuel.unit}
                  </span>
                </TableCell>
                {columns.map((c, i) => (
                  <TableCell
                    key={c.title}
                    className={cn('text-right whitespace-nowrap tabular-nums', i === 0 && 'font-semibold')}
                  >
                    {c.metrics ? dash(r.value(c.metrics), r.digits) : '–'}
                    {i > 0 && c.metrics && (
                      <Diff mine={r.value(data.car)} base={r.value(c.metrics)} better={r.better} />
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
