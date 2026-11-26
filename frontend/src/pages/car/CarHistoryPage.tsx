import { ArrowLeft, ChevronDown, ChevronRight, ChevronUp, CircleAlert } from 'lucide-react'
import { useState } from 'react'
import Chart from 'react-apexcharts'
import { useNavigate, useParams, useSearchParams } from 'react-router'

import type { Schemas } from '@/api/client'
import { useCarHistory } from '@/api/hooks'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { pieRows, seriesRows } from '@/lib/export-excel'
import { num } from '@/lib/format'
import { cn } from '@/lib/utils'
import { ChartCard } from '@/pages/dashboard/ChartCard'
import {
  CATEGORY_COLORS,
  COLOR,
  PALETTE,
  TEXT,
  baht,
  baseOptions,
  comboOptions,
  kilo,
} from '@/pages/dashboard/chart-theme'
import { ExportFiltersContext, NounContext } from '@/pages/dashboard/export-context'
import { JobsSummary } from '@/pages/dashboard/Jobs'
import { Kpi, KpiStrip } from '@/pages/dashboard/Kpi'
import { PartsDetails } from '@/pages/dashboard/Parts'
import { Section } from '@/pages/dashboard/Section'
import { MONTHS_SHORT } from '@/pages/dashboard/period'

type Ticket = Schemas['CarHistoryTicket']

const FILTERS = [
  { key: 'all', label: 'ทั้งหมด', match: () => true },
  { key: 'repair', label: 'ซ่อม', match: (t: Ticket) => t.ma_type === '02' },
  { key: 'pm', label: 'PM', match: (t: Ticket) => t.ma_type === '04' },
  { key: 'open', label: 'ยังไม่ปิดงาน', match: (t: Ticket) => t.is_open },
] as const

const TYPE_STYLE: Record<string, string> = {
  '02': 'bg-[#ffe6dd] text-[#a83a1c]',
  '04': 'bg-emerald-100 text-emerald-800',
}

function thDate(value: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('th-TH', {
    day: 'numeric',
    month: 'short',
    year: '2-digit',
  })
}

/** ระยะเวลาอ่านง่าย: ไม่ถึง 2 วันแสดงเป็นชั่วโมง */
function duration(hours: number) {
  return hours < 48 ? `${num(hours, 1)} ชม.` : `${num(hours / 24, 1)} วัน`
}

export default function CarHistoryPage() {
  const { carId } = useParams()
  const [search] = useSearchParams()
  const navigate = useNavigate()
  const company = search.get('company')
  const history = useCarHistory(Number(carId), company)
  const data = history.data

  const back = () => (window.history.length > 1 ? navigate(-1) : navigate('/'))

  return (
    <main className="mx-auto grid w-full max-w-[1400px] grid-cols-1 gap-8 p-4 md:p-6">
      <div>
        <Button variant="ghost" onClick={back} className="-ml-2">
          <ArrowLeft />
          กลับไป dashboard
        </Button>
      </div>

      {!company && (
        <Alert variant="destructive">
          <AlertDescription>ลิงก์ไม่ครบ: ไม่ได้ระบุบริษัทของรถคันนี้</AlertDescription>
        </Alert>
      )}
      {history.isError && (
        <Alert variant="destructive">
          <AlertDescription>โหลดข้อมูลไม่สำเร็จ: {history.error.message}</AlertDescription>
        </Alert>
      )}

      {!data ? (
        company && !history.isError && <Skeleton className="h-64 rounded-2xl" />
      ) : (
        <NounContext.Provider value={data.car.unit_noun}>
          <ExportFiltersContext.Provider
            value={[
              ['บริษัท', data.car.branch_company_name],
              [data.car.unit_noun, [data.car.code, data.car.name].filter(Boolean).join(' ')],
            ]}
          >
            <CarHeader data={data} />
            <Totals data={data} />
            {data.jobs.departments.length > 0 && (
              <Section
                title="งานที่ทำ แยกตามแผนกค่าใช้จ่าย"
                description={`จากบันทึกการใช้${data.car.unit_noun}ใน webstock ทุกช่วงที่มีข้อมูล · ชั่วโมง = เวลาเริ่ม-จบของแต่ละงาน`}
              >
                <JobsSummary data={data.jobs} singleCar />
              </Section>
            )}
            <Monthly data={data} />
            <RepairCosts items={data.repair_items} />
            <Timeline tickets={data.tickets} />
            {data.doc_jobs.length > 0 && <DocJobs jobs={data.doc_jobs} />}
          </ExportFiltersContext.Provider>
        </NounContext.Provider>
      )}
    </main>
  )
}

function CarHeader({ data }: { data: Schemas['CarHistory'] }) {
  const { car } = data
  const facts: [string, string | null][] = [
    ['บริษัท', car.branch_company_name],
    ['แผนก', car.car_dep_name],
    ['ชนิด', car.car_type_name],
    ['ยี่ห้อ/รุ่น', [car.brand, car.car_model].filter(Boolean).join(' ') || null],
    ['เริ่มใช้งาน', car.start_year ? `ปี ${car.start_year + 543} (อายุ ${num(car.age, 0)} ปี)` : null],
  ]
  return (
    <section className="rounded-2xl bg-hero p-5 text-plate-foreground md:p-7">
      <p className="text-sm text-plate-muted">ประวัติ{car.unit_noun}รายคัน</p>
      <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white md:text-4xl">
        {car.code || car.name}
        {car.code && car.name && (
          <span className="ml-3 text-xl font-medium text-plate-muted">{car.name}</span>
        )}
      </h1>
      <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
        {facts.map(([label, value]) => (
          <div key={label}>
            <dt className="text-plate-muted">{label}</dt>
            <dd className="font-medium text-white">{value || '-'}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function Totals({ data }: { data: Schemas['CarHistory'] }) {
  const t = data.totals
  return (
    <Section
      title="ยอดสะสม"
      description={
        t.data_from ? `ตั้งแต่ ${t.data_from} ถึงปัจจุบัน (ช่วงที่ดึงข้อมูลจาก webstock มา)` : undefined
      }
    >
      <KpiStrip className="xl:grid-cols-6">
        <Kpi label="ค่าซ่อมสะสม" value={num(t.repair_total, 0)} unit="บาท" />
        <Kpi label="ต้นทุนซ่อมต่อชั่วโมง" value={num(t.repair_cost_per_hr, 2)} unit="บาท/ชม." />
        <Kpi
          label="ใบแจ้งซ่อมทั้งหมด"
          value={num(t.ticket_count, 0)}
          unit="ใบ"
          note={
            t.doc_breakdown_count + t.doc_pm_count > 0
              ? `ไม่มีใบแจ้งซ่อม · จากใบจ่ายอะไหล่: ซ่อม ${t.doc_breakdown_count} · PM ${t.doc_pm_count} ครั้ง`
              : `ซ่อม ${t.breakdown_count} · PM ${t.pm_count}`
          }
        />
        <Kpi label="ยังไม่ปิดงาน" value={num(t.open_count, 0)} unit="ใบ" alert={t.open_count > 0} />
        <Kpi
          label="Downtime รวม"
          value={num(t.downtime_hours, 0)}
          unit="ชม."
          note={`≈ ${num(t.downtime_hours / 24, 0)} วัน · ใบซ่อมที่ปิดงานแล้ว`}
        />
        <Kpi
          label="ค่าอะไหล่จากใบจ่าย"
          value={num(t.parts_total, 0)}
          unit="บาท"
          note={
            data.doc_jobs.length > 0 ? 'ไม่มีใบแจ้งซ่อม · นับจากใบจ่ายอะไหล่ (เฉพาะอะไหล่/พัสดุ)' : undefined
          }
        />
      </KpiStrip>
    </Section>
  )
}

function Monthly({ data }: { data: Schemas['CarHistory'] }) {
  const m = data.monthly
  const costSeries = [
    { name: 'ค่าซ่อม (บาท)', type: 'column', data: m.repair },
    { name: 'ชั่วโมงทำงาน', type: 'line', data: m.work },
  ]
  const jobSeries = [
    { name: 'PM', data: m.pm },
    { name: 'ซ่อมเมื่อเสีย', data: m.breakdowns },
  ]
  return (
    <Section title="รายเดือน" description="ย้อนหลังไม่เกิน 24 เดือน">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard
          title="ค่าซ่อมและชั่วโมงทำงาน"
          unit="บาท, ชั่วโมง"
          empty={m.labels.length === 0}
          rows={seriesRows(m.labels, costSeries)}
        >
          <Chart
            type="line"
            height={280}
            series={costSeries}
            options={comboOptions({
              labels: m.labels,
              colors: [COLOR.repair, COLOR.work],
              leftTitle: 'บาท',
              rightTitle: 'ชั่วโมง',
              leftFormat: (v) => num(v, 0),
              rightFormat: (v) => num(v, 0),
            })}
          />
        </ChartCard>
        <ChartCard
          title="ใบแจ้งซ่อม: PM เทียบกับซ่อมเมื่อเสีย"
          description={
            data.totals.doc_breakdown_count + data.totals.doc_pm_count > 0
              ? 'คันนี้ไม่มีใบแจ้งซ่อม: นับครั้งที่เบิกอะไหล่แทน ประเภทการซ่อม "PM" = PM นอกนั้น = ซ่อมเมื่อเสีย (ใบจ่ายวันเดียวกันหรืออ้างใบแจ้งซ่อมเดียวกันนับ 1 ครั้ง)'
              : undefined
          }
          unit="ใบ"
          empty={m.labels.length === 0}
          rows={seriesRows(m.labels, jobSeries)}
        >
          <Chart
            type="bar"
            height={280}
            series={jobSeries}
            options={baseOptions({
              colors: [PALETTE[7], COLOR.failure],
              chart: { stacked: true },
              plotOptions: { bar: { borderRadius: 3, columnWidth: '55%' } },
              xaxis: { categories: m.labels },
              yaxis: { labels: { formatter: (v) => num(v, 0) } },
              dataLabels: { enabled: false },
              legend: { position: 'top', horizontalAlign: 'left' },
            })}
          />
        </ChartCard>
      </div>
    </Section>
  )
}

/** แสดงใบแจ้งซ่อมล่าสุดกี่ใบก่อนกด "แสดงเพิ่ม" */
const TIMELINE_PREVIEW = 5

function Timeline({ tickets }: { tickets: Ticket[] }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]['key']>('all')
  const [expanded, setExpanded] = useState(false)
  const active = FILTERS.find((f) => f.key === filter) ?? FILTERS[0]
  const rows = tickets.filter(active.match)
  const hidden = rows.length - TIMELINE_PREVIEW
  const shown = expanded ? rows : rows.slice(0, TIMELINE_PREVIEW)

  return (
    <Section title="ประวัติใบแจ้งซ่อม" description="ใหม่ → เก่า · เวลาซ่อม = แจ้งซ่อมจนหัวหน้าช่างปิดงาน">
      <div role="group" aria-label="กรองใบแจ้งซ่อม" className="flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const count = tickets.filter(f.match).length
          return (
            <button
              key={f.key}
              type="button"
              aria-pressed={filter === f.key}
              onClick={() => {
                setFilter(f.key)
                setExpanded(false)
              }}
              className={cn(
                'rounded-full border px-3 py-1 text-sm transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring',
                filter === f.key &&
                  'border-primary bg-primary text-primary-foreground hover:bg-primary',
              )}
            >
              {f.label} ({count})
            </button>
          )
        })}
      </div>

      {rows.length === 0 ? (
        <p className="rounded-xl border bg-card p-6 text-center text-sm text-muted-foreground">
          ไม่มีใบแจ้งซ่อมในกลุ่มนี้
        </p>
      ) : (
        <ol className="relative ml-3 border-l-2 border-border">
          {shown.map((t) => (
            <li key={t.ext_id} className="relative pb-5 pl-6 last:pb-0">
              <span
                aria-hidden
                className={cn(
                  'absolute top-1.5 -left-[7px] size-3 rounded-full border-2 border-background',
                  t.is_open ? 'bg-signal' : t.ma_type === '04' ? 'bg-emerald-600' : 'bg-primary',
                )}
              />
              <div className="rounded-xl border bg-card p-3 md:p-4">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <time dateTime={t.reported_at} className="font-semibold tabular-nums">
                    {thDate(t.reported_at)}
                  </time>
                  <span
                    className={cn(
                      'rounded-md px-2 py-0.5 text-xs font-medium',
                      TYPE_STYLE[t.ma_type] ?? 'bg-muted text-muted-foreground',
                    )}
                  >
                    {t.ma_type_name}
                  </span>
                  {t.ref_no && <span className="text-sm text-muted-foreground">{t.ref_no}</span>}
                  <span className="ml-auto text-sm">
                    {t.is_open ? (
                      <span className="inline-flex items-center gap-1 font-medium text-signal-foreground">
                        <CircleAlert className="size-4 text-signal" aria-hidden />
                        ยังไม่ปิดงาน{t.stage_label && ` · ${t.stage_label}`}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">
                        ปิดงาน {thDate(t.finished_at)}
                        {t.repair_hours !== null && ` · ${duration(t.repair_hours)}`}
                      </span>
                    )}
                  </span>
                </div>
                {(t.broke_reason || t.car_state) && (
                  <p className="mt-1.5 text-sm">
                    {t.broke_reason || '-'}
                    {t.car_state && <span className="text-muted-foreground"> · {t.car_state}</span>}
                  </p>
                )}
                {t.parts.length > 0 && (
                  <div className="mt-2">
                    <PartsDetails parts={t.parts} amount={t.parts_amount} defaultOpen />
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}

      {hidden > 0 && (
        <div className="flex justify-center">
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? (
              <>
                <ChevronUp aria-hidden />
                ย่อเหลือ {TIMELINE_PREVIEW} รายการล่าสุด
              </>
            ) : (
              <>
                <ChevronDown aria-hidden />
                แสดงอีก {num(hidden, 0)} รายการ
              </>
            )}
          </Button>
        </div>
      )}
    </Section>
  )
}

/** การซ่อมจากใบจ่ายอะไหล่ (รถที่ไม่มีใบแจ้งซ่อม) ย่อไว้ก่อน กดหัวข้อเพื่อดูรายการ */
function DocJobs({ jobs }: { jobs: Schemas['CarHistoryDocJob'][] }) {
  const total = jobs.reduce((sum, j) => sum + j.amount, 0)
  return (
    <Section
      title="ประวัติการซ่อมและอะไหล่ที่ใช้"
      description="จากใบจ่ายอะไหล่ใน Express (ไม่มีใบแจ้งซ่อม) · ใหม่ → เก่า · เฉพาะอะไหล่/พัสดุ"
    >
      <details className="group/history rounded-xl border bg-card">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 text-sm hover:bg-muted/40 focus-visible:outline-2 focus-visible:outline-ring group-open/history:border-b [&::-webkit-details-marker]:hidden">
          <ChevronRight
            className="size-4 text-muted-foreground transition-transform group-open/history:rotate-90"
            aria-hidden
          />
          <span className="font-medium">{num(jobs.length, 0)} ครั้ง</span>
          <span className="text-muted-foreground">· {num(total, 0)} บาท</span>
        </summary>
        <ul className="divide-y">
          {jobs.map((j) => (
            <li key={j.ref_no} className="grid gap-1 px-4 py-3">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <time dateTime={j.docdat} className="font-medium tabular-nums">
                  {thDate(j.docdat)}
                </time>
                <span
                  className={cn(
                    'rounded-md px-2 py-0.5 text-xs font-medium',
                    TYPE_STYLE[j.is_pm ? '04' : '02'],
                  )}
                >
                  {j.is_pm ? 'PM' : 'ซ่อม'}
                </span>
                <span className="text-sm text-muted-foreground">{j.ref_no}</span>
                <span className="ml-auto text-sm font-medium tabular-nums">
                  {num(j.amount, 0)} บาท
                </span>
              </div>
              <PartsDetails parts={j.parts} amount={j.amount} />
            </li>
          ))}
        </ul>
      </details>
    </Section>
  )
}

/** ค่าซ่อมรายเดือนแยกตามระบบ (จากใบเบิกค่าซ่อมใน webstock) ใหม่ -> เก่า */
/** ระบบที่แสดงแยกสี ที่เหลือรวมเป็น "อื่นๆ" (สีมากกว่านี้แยกกันไม่ออก) */
const TOP_SYSTEMS = 7
const OTHER_SYSTEMS = 'อื่นๆ'

function RepairCosts({ items }: { items: Schemas['CarHistoryRepairItem'][] }) {
  // รวมทั้งช่วง: ระบบที่ค่าซ่อมสูงสุดก่อน
  const totals = new Map<string, number>()
  for (const i of items) totals.set(i.repair_name, (totals.get(i.repair_name) ?? 0) + i.amount)
  const ranked = [...totals.entries()].sort((a, b) => b[1] - a[1])
  const shown = ranked.length > TOP_SYSTEMS + 1 ? ranked.slice(0, TOP_SYSTEMS) : ranked
  const shownNames = new Set(shown.map(([name]) => name))
  const rest = ranked.filter(([name]) => !shownNames.has(name))
  const systems = [...shown.map(([name]) => name), ...(rest.length ? [OTHER_SYSTEMS] : [])]
  const systemTotals = [
    ...shown.map(([, v]) => v),
    ...(rest.length ? [rest.reduce((sum, [, v]) => sum + v, 0)] : []),
  ]

  // เดือนเก่า -> ใหม่ ต่อเนื่อง (เดือนที่ไม่มีค่าซ่อมแสดงเป็น 0 ไม่ให้กราฟข้ามเดือน)
  const keys = items.map((i) => i.year * 12 + i.month - 1)
  const months: { key: number; label: string }[] = []
  for (let k = Math.min(...keys); k <= Math.max(...keys); k++) {
    const year = Math.floor(k / 12)
    const month = (k % 12) + 1
    months.push({
      key: year * 100 + month,
      label: `${MONTHS_SHORT[month - 1]} ${String((year + 543) % 100).padStart(2, '0')}`,
    })
  }
  const amount = (key: number, system: string) =>
    items
      .filter(
        (i) =>
          i.year * 100 + i.month === key &&
          (system === OTHER_SYSTEMS ? !shownNames.has(i.repair_name) : i.repair_name === system),
      )
      .reduce((sum, i) => sum + i.amount, 0)
  const monthSeries = systems.map((name) => ({
    name,
    data: months.map((m) => amount(m.key, name)),
  }))
  const labels = months.map((m) => m.label)
  const colors = systems.map((name, i) =>
    name === OTHER_SYSTEMS ? PALETTE[6] : CATEGORY_COLORS[i % CATEGORY_COLORS.length],
  )
  const grand = systemTotals.reduce((a, b) => a + b, 0)

  return (
    <Section
      title="ค่าซ่อมแยกตามระบบ"
      description="ยอดรายเดือนจากค่าซ่อมใน webstock (ไม่ได้ผูกกับใบแจ้งซ่อมรายใบ)"
    >
      {items.length === 0 ? (
        <p className="rounded-xl border bg-card p-6 text-center text-sm text-muted-foreground">
          ยังไม่มีค่าซ่อม
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <ChartCard
            title="ค่าซ่อมรายเดือน แยกตามระบบ"
            unit="บาท"
            rows={seriesRows(labels, monthSeries)}
          >
            <Chart
              type="bar"
              height={320}
              series={monthSeries}
              options={baseOptions({
                colors,
                chart: { stacked: true },
                plotOptions: { bar: { borderRadius: 2, columnWidth: '60%' } },
                xaxis: { categories: labels },
                yaxis: { labels: { formatter: kilo } },
                dataLabels: { enabled: false },
                legend: { position: 'top', horizontalAlign: 'left' },
                tooltip: {
                  shared: true,
                  intersect: false,
                  y: { formatter: (v) => baht(Number(v ?? 0)) },
                },
              })}
            />
          </ChartCard>
          <ChartCard
            title="รวมทั้งช่วง แยกตามระบบ"
            unit="บาท"
            description={`รวม ${num(grand, 0)} บาท`}
            rows={pieRows(systems, systemTotals)}
          >
            <Chart
              type="bar"
              height={320}
              series={[{ name: 'ค่าซ่อม', data: systemTotals }]}
              options={baseOptions({
                colors,
                plotOptions: {
                  bar: {
                    horizontal: true,
                    distributed: true,
                    borderRadius: 3,
                    barHeight: '65%',
                  },
                },
                xaxis: {
                  categories: systems,
                  labels: { formatter: (v) => kilo(Number(v)) },
                },
                dataLabels: {
                  enabled: true,
                  formatter: (v) => (grand ? `${((Number(v) / grand) * 100).toFixed(0)}%` : ''),
                  style: { fontSize: '11px', colors: [TEXT] },
                  offsetX: 4,
                },
                legend: { show: false },
                tooltip: { y: { formatter: (v) => baht(Number(v ?? 0)) } },
              })}
            />
          </ChartCard>
        </div>
      )}
    </Section>
  )
}
