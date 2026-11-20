import Chart from 'react-apexcharts'

import type { CarRow, Schemas } from '@/api/client'
import { pieRows, seriesRows, type ExportTable } from '@/lib/export-excel'
import { num } from '@/lib/format'

import { ChartCard } from './ChartCard'
import { useChartHelp, type ChartHelp } from './chart-help'
import { useNoun } from './export-context'
import {
  CATEGORY_COLORS,
  COLOR,
  PALETTE,
  GRID,
  TEXT,
  TEXT_MUTED,
  baht,
  baseOptions,
  carLabel,
  comboOptions,
  kilo,
} from './chart-theme'

type Charts = Schemas['Charts']

const SIGNAL = COLOR.highlight
const round2 = (v: number) => Math.round(v * 100) / 100
const percent = (part: number, total: number) => (total ? (part / total) * 100 : 0)

const HTML_ESCAPES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
/** tooltip แบบ custom ของ ApexCharts เป็น HTML string: ชื่อรถ/ยี่ห้อ/รุ่นกรอกจาก webstock ต้อง escape ก่อน */
const esc = (v: unknown) => String(v ?? '').replace(/[&<>"']/g, (c) => HTML_ESCAPES[c])

/* ---------- ค่าซ่อมรายเดือน + เส้นค่าเฉลี่ย ---------- */

export function RepairByMonthChart({ chart }: { chart: Charts['repair_by_month'] }) {
  const CHART_HELP = useChartHelp()
  const name = 'ค่าใช้จ่ายซ่อมบำรุง'
  const avg = chart.series.length ? chart.series.reduce((a, b) => a + b, 0) / chart.series.length : 0
  return (
    <ChartCard
      title="ค่าใช้จ่ายซ่อมบำรุงรายเดือน"
      help={CHART_HELP.repairByMonth}
      unit="บาท"
      empty={chart.series.length === 0}
      rows={seriesRows(chart.labels, [{ name, data: chart.series }])}
    >
      <Chart
        type="bar"
        height={280}
        series={[{ name, data: chart.series }]}
        options={baseOptions({
          colors: [COLOR.repair],
          xaxis: { categories: chart.labels },
          plotOptions: { bar: { borderRadius: 6, columnWidth: '55%', dataLabels: { position: 'top' } } },
          dataLabels: { enabled: true, formatter: (v) => kilo(Number(v)), offsetY: -20, style: { fontSize: '11px', colors: [TEXT] } },
          yaxis: { labels: { formatter: kilo } },
          tooltip: { y: { formatter: baht } },
          annotations: {
            yaxis: [
              {
                y: avg,
                borderColor: TEXT_MUTED,
                strokeDashArray: 5,
                label: {
                  text: `เฉลี่ย ${kilo(avg)}`,
                  position: 'left',
                  textAnchor: 'start',
                  borderWidth: 0,
                  style: { background: '#fff', color: TEXT, fontSize: '11px' },
                },
              },
            ],
          },
        })}
      />
    </ChartCard>
  )
}

/* ---------- ต้นทุนซ่อมต่อชั่วโมงทำงาน (เส้นเดียว) ---------- */

export function CostPerHourChart({ chart }: { chart: Charts['repair_vs_work'] }) {
  const CHART_HELP = useChartHelp()
  // เดือนที่ชั่วโมงทำงาน ≤ 0 หารไม่ได้ -> เว้นช่องว่าง
  const cost = chart.labels.map((_, i) =>
    chart.work[i] > 0 ? round2(chart.repair[i] / chart.work[i]) : null,
  )
  const skipped = chart.labels.filter((_, i) => cost[i] === null && chart.repair[i] > 0)
  const name = 'ต้นทุนซ่อมต่อชั่วโมง'
  const rows = seriesRows(chart.labels, [
    { name: 'ค่าซ่อม (บาท)', data: chart.repair },
    { name: 'ชั่วโมงทำงาน', data: chart.work },
    { name: `${name} (บาท/ชม.)`, data: cost },
  ])
  return (
    <ChartCard
      title="ต้นทุนซ่อมต่อชั่วโมงทำงาน"
      help={CHART_HELP.costPerHour}
      unit="บาท/ชั่วโมง"
      description={
        skipped.length
          ? `ไม่แสดง ${skipped.join(', ')} เพราะชั่วโมงทำงานเป็น 0 หรือติดลบ`
          : 'ค่าซ่อมของเดือน หารด้วยชั่วโมงทำงานของเดือนเดียวกัน'
      }
      empty={cost.every((v) => v === null)}
      rows={rows}
    >
      <Chart
        type="line"
        height={280}
        series={[{ name, data: cost }]}
        options={baseOptions({
          colors: [COLOR.line],
          stroke: { width: 3, curve: 'straight' },
          markers: { size: 5 },
          xaxis: { categories: chart.labels },
          yaxis: { min: 0, labels: { formatter: (v) => num(v, 0) } },
          dataLabels: {
            enabled: true,
            formatter: (v) => (typeof v === 'number' ? num(v, 0) : ''),
            offsetY: -6,
            background: { enabled: false },
            style: { fontSize: '11px', colors: [TEXT] },
          },
          tooltip: { y: { formatter: (v) => (v == null ? 'ไม่มีข้อมูล' : `${num(v, 2)} บาท/ชม.`) } },
        })}
      />
    </ChartCard>
  )
}

/* ---------- แท่งแนวนอนเรียงมากไปน้อย (แทนกราฟวงกลม) ---------- */

function RankedBarCard({
  title,
  help,
  chart,
}: {
  title: string
  help: ChartHelp
  chart: Schemas['SeriesTotalChart']
}) {
  const name = 'ค่าใช้จ่ายซ่อมบำรุง'
  return (
    <ChartCard
      title={title}
      help={help}
      unit="บาท"
      empty={chart.series.length === 0}
      rows={pieRows(chart.labels, chart.series)}
    >
      <Chart
        type="bar"
        height={Math.max(220, chart.labels.length * 36 + 50)}
        series={[{ name, data: chart.series }]}
        options={baseOptions({
          // แต่ละหมวดคนละสี (ชื่อหมวดอยู่บนแกนแล้ว จึงไม่ต้องมีคำอธิบายสี)
          colors: CATEGORY_COLORS,
          legend: { show: false },
          plotOptions: {
            bar: {
              horizontal: true,
              distributed: true,
              borderRadius: 4,
              barHeight: '62%',
              dataLabels: { position: 'top' },
            },
          },
          // เผื่อที่ด้านขวาให้ตัวเลขท้ายแท่งที่ยาวที่สุดไม่ล้นกราฟ
          xaxis: {
            categories: chart.labels,
            min: 0,
            max: Math.max(...chart.series, 0) * 1.3 || undefined,
            tickAmount: 4,
            labels: { formatter: (v) => kilo(Number(v)) },
          },
          yaxis: { labels: { maxWidth: 160 } },
          grid: { yaxis: { lines: { show: false } }, xaxis: { lines: { show: true } } },
          dataLabels: {
            enabled: true,
            formatter: (v) => `${kilo(Number(v))} (${num(percent(Number(v), chart.total), 1)}%)`,
            offsetX: 8,
            textAnchor: 'start',
            style: { fontSize: '11px', fontWeight: 500, colors: [TEXT] },
          },
          tooltip: { y: { formatter: baht } },
        })}
      />
    </ChartCard>
  )
}

export function RepairByTypeChart({ chart }: { chart: Charts['repair_by_type'] }) {
  const CHART_HELP = useChartHelp()
  return <RankedBarCard title="ค่าซ่อมตามประเภทการซ่อม" help={CHART_HELP.repairByType} chart={chart} />
}

export function RepairByCarTypeChart({ chart }: { chart: Charts['repair_by_car_type'] }) {
  const CHART_HELP = useChartHelp()
  const noun = useNoun()
  return <RankedBarCard
      title={`ค่าใช้จ่ายแบ่งตามประเภท${noun}`}
      help={CHART_HELP.repairByCarType}
      chart={chart}
    />
}

/* ---------- Pareto ค่าซ่อมตามรถ ---------- */

const PARETO_TOP = 15

function cumulativePercent(values: number[], total: number) {
  const sums = values.reduce<number[]>((out, v) => [...out, (out.at(-1) ?? 0) + v], [])
  return sums.map((s) => round2(percent(s, total)))
}

export function RepairParetoChart({ chart }: { chart: Charts['repair_by_car'] }) {
  const CHART_HELP = useChartHelp()
  const noun = useNoun()
  // backend เรียงจากมากไปน้อยแล้ว
  const named = chart.labels.map((l, i) => carLabel(l, chart.companies[i]))
  const top = named.slice(0, PARETO_TOP)
  const values = chart.series.slice(0, PARETO_TOP)
  const rest = chart.series.slice(PARETO_TOP).reduce((a, b) => a + b, 0)
  const restCount = named.length - top.length
  // ไม่ใส่แท่ง "อื่น ๆ" เพราะยอดรวมของรถที่เหลือจะสูงจนแท่งของคันอื่นดูเล็ก -> บอกเป็นข้อความแทน
  const labels = top
  const bars = values

  // % สะสมของรถทุกคัน (เรียงแล้ว)
  const cumAll = cumulativePercent(chart.series, chart.total)
  const cumulative = cumulativePercent(bars, chart.total)

  // รถกี่คันแรกที่รวมกันถึง 80% ของค่าซ่อม
  const carsTo80 = cumAll.findIndex((p) => p >= 80) + 1

  const rows: ExportTable = [
    ['ลำดับ', noun, 'บริษัท', 'ค่าซ่อม (บาท)', 'สัดส่วน (%)', 'สะสม (%)'],
    ...chart.labels.map((label, i) => [
      i + 1,
      label,
      chart.companies[i],
      round2(chart.series[i]),
      round2(percent(chart.series[i], chart.total)),
      cumAll[i],
    ]),
  ]

  const series = [
    { name: 'ค่าซ่อม', type: 'column', data: bars },
    { name: 'สัดส่วนสะสม', type: 'line', data: cumulative },
  ]

  return (
    <ChartCard
      title={`${noun}ที่ใช้ค่าซ่อมมากที่สุด`}
      help={CHART_HELP.pareto}
      unit="บาท, % สะสม"
      description={[
        carsTo80 > 0 &&
          `${noun} ${carsTo80} จาก ${chart.labels.length} คัน ใช้ค่าซ่อมรวมกัน 80% ของทั้งหมด`,
        restCount > 0 && `ไม่แสดงอีก ${restCount} คัน (รวม ${kilo(rest)} บาท) ดูได้ในไฟล์ Excel`,
      ]
        .filter(Boolean)
        .join(' ')}
      empty={chart.series.length === 0}
      rows={rows}
    >
      <Chart
        type="line"
        height={360}
        series={series}
        options={baseOptions({
          chart: { type: 'line' },
          colors: [COLOR.repair, SIGNAL],
          labels,
          stroke: { width: [0, 3], curve: 'straight' },
          markers: { size: [0, 4] },
          plotOptions: { bar: { borderRadius: 4, columnWidth: '62%' } },
          dataLabels: { enabled: false },
          xaxis: { labels: { rotate: -45, rotateAlways: labels.length > 6, trim: true, maxHeight: 150 } },
          yaxis: [
            { title: { text: 'บาท' }, labels: { formatter: kilo } },
            { opposite: true, min: 0, max: 100, tickAmount: 5, title: { text: '% สะสม' }, labels: { formatter: (v) => `${num(v, 0)}%` } },
          ],
          annotations: {
            yaxis: [
              {
                y: 80,
                yAxisIndex: 1,
                borderColor: TEXT_MUTED,
                strokeDashArray: 5,
                label: { text: '80%', borderWidth: 0, style: { background: '#fff', color: TEXT, fontSize: '11px' } },
              },
            ],
          },
          tooltip: {
            shared: true,
            intersect: false,
            y: {
              formatter: (v, o) =>
                v == null ? '-' : o?.seriesIndex === 0 ? baht(v) : `${num(v, 1)}%`,
            },
          },
        })}
      />
    </ChartCard>
  )
}

/** ขอบบนของค่าปกติ: Q3 + 3×IQR (ข้อมูลน้อยกว่า 4 ค่าไม่ตัด) */
function outlierLimit(values: number[]) {
  if (values.length < 4) return Infinity
  const sorted = [...values].sort((a, b) => a - b)
  const q = (p: number) => sorted[Math.floor((sorted.length - 1) * p)]
  const iqr = q(0.75) - q(0.25)
  return iqr > 0 ? q(0.75) + 3 * iqr : Infinity
}

/* ---------- กราฟจุด: ชั่วโมงทำงาน vs ต้นทุนซ่อม/ชม. ---------- */

export function CarScatterChart({
  rows,
  selected,
  onSelect,
}: {
  rows: CarRow[]
  selected: CarRow | null
  onSelect: (row: CarRow) => void
}) {
  const CHART_HELP = useChartHelp()
  const noun = useNoun()
  // ตัดรถที่ไม่มีชั่วโมงทำงานหรือไม่มีค่าซ่อม (หาต้นทุนต่อชั่วโมงไม่ได้)
  const valid = rows.filter((r) => r.work_total > 0 && r.repair_total > 0 && r.repair_cost_per_hr != null)
  // ค่าที่สูงผิดปกติ (เกิน Q3 + 3×IQR) ทำให้จุดอื่นกองอยู่มุมเดียว -> ไม่แสดงบนกราฟ แต่บอกจำนวนไว้
  const xLimit = outlierLimit(valid.map((r) => r.work_total))
  const yLimit = outlierLimit(valid.map((r) => r.repair_cost_per_hr ?? 0))
  const cars = valid.filter((r) => r.work_total <= xLimit && (r.repair_cost_per_hr ?? 0) <= yLimit)
  const hidden = valid.length - cars.length
  const isSel = (r: CarRow) =>
    selected?.car_id === r.car_id && selected.branch_company_id === r.branch_company_id
  const point = (r: CarRow) => ({ x: round2(r.work_total), y: round2(r.repair_cost_per_hr ?? 0), z: r.failure_count + 1 })
  const groups = [cars.filter((r) => !isSel(r)), cars.filter(isSel)]
  const series = [
    { name: noun, data: groups[0].map(point) },
    { name: 'คันที่เลือก', data: groups[1].map(point) },
  ]
  const label = (r: CarRow) => carLabel([r.code, r.name].filter(Boolean).join(' '), r.branch_company_name)

  const exportRows: ExportTable = [
    [noun, 'ชั่วโมงทำงาน', 'ต้นทุนซ่อม (บาท/ชม.)', 'ค่าซ่อม (บาท)', 'ครั้งที่เสีย'],
    ...valid.map((r) => [label(r), round2(r.work_total), round2(r.repair_cost_per_hr ?? 0), round2(r.repair_total), r.failure_count]),
  ]

  return (
    <ChartCard
      title="ชั่วโมงทำงานเทียบต้นทุนซ่อมต่อชั่วโมง"
      help={CHART_HELP.scatter}
      unit="ชั่วโมง, บาท/ชั่วโมง"
      description={hidden ? `ไม่แสดง ${hidden} คันที่ค่าสูงผิดปกติ ดูได้ในตาราง` : undefined}
      empty={cars.length === 0}
      rows={exportRows}
    >
      <Chart
        type="bubble"
        height={380}
        series={series}
        options={baseOptions({
          chart: {
            type: 'bubble',
            zoom: { enabled: true, type: 'xy' },
            events: {
              dataPointSelection: (_e, _c, opts) => {
                const { seriesIndex, dataPointIndex } = opts as { seriesIndex: number; dataPointIndex: number }
                const row = groups[seriesIndex]?.[dataPointIndex]
                if (row) onSelect(row)
              },
            },
          },
          colors: [COLOR.repair, SIGNAL],
          fill: { opacity: [0.55, 0.95] },
          stroke: { width: 1, colors: ['#fff'] },
          plotOptions: { bubble: { minBubbleRadius: 5, maxBubbleRadius: 22 } },
          dataLabels: { enabled: false },
          legend: { show: groups[1].length > 0 },
          xaxis: {
            type: 'numeric',
            tickAmount: 6,
            title: { text: 'ชั่วโมงทำงานรวม' },
            labels: { formatter: (v) => kilo(Number(v)) },
          },
          yaxis: { min: 0, title: { text: 'บาท/ชม.' }, labels: { formatter: (v) => num(v, 0) } },
          tooltip: {
            custom: ({ seriesIndex, dataPointIndex }) => {
              const r = groups[seriesIndex]?.[dataPointIndex]
              if (!r) return ''
              return `<div style="padding:8px 10px;font-size:12px;line-height:1.6">
                <b>${esc(label(r))}</b><br/>
                ชั่วโมงทำงาน ${num(r.work_total, 0)} ชม.<br/>
                ต้นทุนซ่อม ${num(r.repair_cost_per_hr, 2)} บาท/ชม.<br/>
                ค่าซ่อม ${num(r.repair_total, 0)} บาท, เสีย ${r.failure_count} ครั้ง
              </div>`
            },
          },
        })}
      />
    </ChartCard>
  )
}

/* ---------- กราฟจุด: อายุ vs ต้นทุนซ่อม/ชม. แยกสีตามชนิดรถ ---------- */

// ผ่าน validate_palette (light): ไม่ใช้ปะการังเพราะสงวนไว้เป็นสีคันที่เลือก
const CAR_TYPE_COLORS = [PALETTE[2], PALETTE[3], PALETTE[4], PALETTE[7]]
const OTHER_TYPES = 'ชนิดอื่น'

export function AgeCostChart({
  rows,
  onSelect,
}: {
  rows: CarRow[]
  onSelect: (row: CarRow) => void
}) {
  const CHART_HELP = useChartHelp()
  const noun = useNoun()
  const valid = rows.filter(
    (r) => r.age != null && r.work_total > 0 && r.repair_total > 0 && r.repair_cost_per_hr != null,
  )
  const yLimit = outlierLimit(valid.map((r) => r.repair_cost_per_hr ?? 0))
  const cars = valid.filter((r) => (r.repair_cost_per_hr ?? 0) <= yLimit)
  const hidden = valid.length - cars.length
  const noAge = rows.filter((r) => r.age == null).length

  // ชนิดที่มีรถมากสุด 4 ชนิดได้สีของตัวเอง ที่เหลือรวมเป็นสีเทา (ไม่สร้างสีใหม่)
  const typeName = (r: CarRow) => r.car_type_name || 'ไม่ระบุชนิด'
  const counts = new Map<string, number>()
  for (const r of cars) counts.set(typeName(r), (counts.get(typeName(r)) ?? 0) + 1)
  const top = [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'th'))
    .slice(0, CAR_TYPE_COLORS.length)
    .map(([name]) => name)
    .sort((a, b) => a.localeCompare(b, 'th')) // สีผูกกับชื่อชนิด ไม่ใช่ลำดับจำนวน
  const groupOf = (r: CarRow) => (top.includes(typeName(r)) ? typeName(r) : OTHER_TYPES)
  const names = [...top, ...(cars.some((r) => groupOf(r) === OTHER_TYPES) ? [OTHER_TYPES] : [])]
  const groups = names.map((n) => cars.filter((r) => groupOf(r) === n))
  const series = names.map((n, i) => ({
    name: n,
    data: groups[i].map((r) => ({ x: r.age ?? 0, y: round2(r.repair_cost_per_hr ?? 0) })),
  }))
  const colors = names.map((n, i) => (n === OTHER_TYPES ? PALETTE[6] : CAR_TYPE_COLORS[i]))
  const label = (r: CarRow) => carLabel([r.code, r.name].filter(Boolean).join(' '), r.branch_company_name)

  const exportRows: ExportTable = [
    [noun, 'ชนิด', 'ยี่ห้อ', 'รุ่น', 'อายุ (ปี)', 'ต้นทุนซ่อม (บาท/ชม.)', 'ค่าซ่อม (บาท)', 'ชั่วโมงทำงาน'],
    ...valid.map((r) => [
      label(r),
      typeName(r),
      r.brand ?? '',
      r.car_model ?? '',
      r.age ?? '',
      round2(r.repair_cost_per_hr ?? 0),
      round2(r.repair_total),
      round2(r.work_total),
    ]),
  ]
  const notes = [
    hidden ? `ไม่แสดง ${hidden} คันที่ค่าสูงผิดปกติ` : '',
    noAge ? `${noAge} คันยังไม่ได้กรอกปีที่เริ่มใช้งาน` : '',
  ].filter(Boolean)

  return (
    <ChartCard
      title="อายุเทียบต้นทุนซ่อมต่อชั่วโมง"
      help={CHART_HELP.ageCost}
      unit="ปี, บาท/ชั่วโมง"
      description={notes.length ? notes.join(' · ') : undefined}
      empty={cars.length === 0}
      rows={exportRows}
    >
      <Chart
        type="scatter"
        height={380}
        series={series}
        options={baseOptions({
          chart: {
            type: 'scatter',
            zoom: { enabled: true, type: 'xy' },
            events: {
              dataPointSelection: (_e, _c, opts) => {
                const { seriesIndex, dataPointIndex } = opts as { seriesIndex: number; dataPointIndex: number }
                const row = groups[seriesIndex]?.[dataPointIndex]
                if (row) onSelect(row)
              },
            },
          },
          colors,
          markers: { size: 6, strokeWidth: 2, strokeColors: '#fff', hover: { sizeOffset: 2 } },
          fill: { opacity: 0.85 },
          dataLabels: { enabled: false },
          legend: { show: true },
          xaxis: {
            type: 'numeric',
            min: 0,
            tickAmount: 6,
            title: { text: 'อายุ (ปี)' },
            labels: { formatter: (v) => num(Number(v), 0) },
          },
          yaxis: { min: 0, title: { text: 'บาท/ชม.' }, labels: { formatter: (v) => num(v, 0) } },
          tooltip: {
            custom: ({ seriesIndex, dataPointIndex }) => {
              const r = groups[seriesIndex]?.[dataPointIndex]
              if (!r) return ''
              const model = [r.brand, r.car_model].filter(Boolean).join(' ')
              return `<div style="padding:8px 10px;font-size:12px;line-height:1.6">
                <b>${esc(label(r))}</b><br/>
                ${esc(typeName(r))}${model ? ` · ${esc(model)}` : ''}<br/>
                อายุ ${esc(r.age)} ปี (เริ่มใช้ ${esc(r.start_year)})<br/>
                ต้นทุนซ่อม ${num(r.repair_cost_per_hr, 2)} บาท/ชม.<br/>
                ค่าซ่อม ${num(r.repair_total, 0)} บาท, ทำงาน ${num(r.work_total, 0)} ชม.
              </div>`
            },
          },
        })}
      />
    </ChartCard>
  )
}

/* ---------- ตารางสี รถ x เดือน ---------- */

export function RepairHeatmapChart({ chart }: { chart: Charts['repair_heatmap'] }) {
  const CHART_HELP = useChartHelp()
  const noun = useNoun()
  const max = Math.max(0, ...chart.rows.flatMap((r) => r.data))
  // ApexCharts วาดแถวจากล่างขึ้นบน -> กลับลำดับให้คันที่ค่าซ่อมสูงสุดอยู่บนสุด
  const series = [...chart.rows].reverse().map((r) => ({
    name: carLabel(r.name, r.company),
    data: chart.labels.map((m, i) => ({ x: m, y: round2(r.data[i]) })),
  }))
  const steps = [0.25, 0.5, 0.75, 1]
  const shades = ['#cdeeed', '#8fd3d1', '#3fa9ab', '#0b6f74']

  return (
    <ChartCard
      title={`ค่าซ่อมรายเดือนของ${noun}แต่ละคัน`}
      help={CHART_HELP.heatmap}
      unit="บาท"
      description={`${noun} ${chart.rows.length} คันที่ค่าซ่อมสูงสุด`}
      empty={chart.rows.length === 0 || max === 0}
      rows={seriesRows(
        chart.labels,
        chart.rows.map((r) => ({ name: carLabel(r.name, r.company), data: r.data })),
      )}
    >
      <Chart
        type="heatmap"
        height={Math.max(220, chart.rows.length * 30 + 70)}
        series={series}
        options={baseOptions({
          dataLabels: { enabled: false },
          stroke: { width: 2, colors: ['#fff'] },
          legend: { show: true, position: 'bottom' },
          plotOptions: {
            heatmap: {
              radius: 3,
              enableShades: false,
              colorScale: {
                ranges: [
                  { from: 0, to: 0, color: GRID, name: 'ไม่มีค่าซ่อม' },
                  ...steps.map((s, i) => ({
                    from: i === 0 ? 0.01 : max * steps[i - 1],
                    to: max * s,
                    color: shades[i],
                    name: `ถึง ${kilo(max * s)}`,
                  })),
                ],
              },
            },
          },
          yaxis: { labels: { maxWidth: 230 } },
          tooltip: { y: { formatter: baht } },
        })}
      />
    </ChartCard>
  )
}

/* ---------- น้ำมัน / ชั่วโมงทำงาน (แท่ง + เส้น เพราะสองค่าเกี่ยวกันจริง) ---------- */

export function OilByMonthChart({ chart }: { chart: Charts['oil_by_month'] }) {
  const CHART_HELP = useChartHelp()
  const series = [
    { name: 'ปริมาณที่ใช้น้ำมัน (ลิตร)', type: 'column', data: chart.liters },
    { name: 'อัตราการใช้พลังงาน L/Km', type: 'line', data: chart.liter_per_km },
  ]
  return (
    <ChartCard
      title="ปริมาณที่ใช้น้ำมันเชื้อเพลิงรวม"
      help={CHART_HELP.oil}
      unit="ลิตร, ลิตร/กม."
      empty={chart.labels.length === 0}
      rows={seriesRows(chart.labels, series)}
    >
      <Chart
        type="line"
        height={280}
        series={series}
        options={comboOptions({
          labels: chart.labels,
          colors: [COLOR.oil, COLOR.line],
          leftTitle: 'ลิตร',
          rightTitle: 'L/Km',
          leftFormat: (v) => num(v, 0),
          rightFormat: (v) => num(v, 2),
        })}
      />
    </ChartCard>
  )
}

export function WorkByMonthChart({ chart }: { chart: Charts['work_by_month'] }) {
  const CHART_HELP = useChartHelp()
  const series = [
    { name: 'ชั่วโมงทำงาน', type: 'column', data: chart.hours },
    { name: '% อัตราการทำงานเฉลี่ย', type: 'line', data: chart.percent },
  ]
  return (
    <ChartCard
      title="มิเตอร์ทำงานรวม"
      help={CHART_HELP.work}
      unit="ชั่วโมง, %"
      empty={chart.labels.length === 0}
      rows={seriesRows(chart.labels, series)}
    >
      <Chart
        type="line"
        height={280}
        series={series}
        options={comboOptions({
          labels: chart.labels,
          colors: [COLOR.work, COLOR.line],
          leftTitle: 'ชั่วโมง',
          rightTitle: '%',
          leftFormat: (v) => num(v, 0),
          rightFormat: (v) => `${num(v, 2)}%`,
        })}
      />
    </ChartCard>
  )
}
