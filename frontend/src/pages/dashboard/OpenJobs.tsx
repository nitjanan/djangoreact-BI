import { ChevronDown, FileSpreadsheet } from 'lucide-react'
import { useState } from 'react'

import type { Schemas } from '@/api/client'
import { Button } from '@/components/ui/button'
import { downloadExcel } from '@/lib/export-excel'
import { num } from '@/lib/format'
import { cn } from '@/lib/utils'

import { useExportFilters, useNoun } from './export-context'
import { Kpi, KpiStrip } from './Kpi'
import { PartsDetails } from './Parts'

type OpenJobs = Schemas['OpenJobs']
type OpenJob = Schemas['OpenJob']

const TITLE = 'ใบแจ้งซ่อมที่ยังไม่ปิดงาน'
const PREVIEW_ROWS = 8

// อายุงานค้าง: ใหม่ -> ค้างนาน (ตรงกับ AGE_BUCKETS ฝั่ง backend)
const BUCKET_TONES = [
  'bg-muted text-foreground',
  'bg-[color-mix(in_oklab,var(--chart-1)_30%,var(--card))] text-foreground',
  'bg-[color-mix(in_oklab,var(--chart-4)_45%,var(--card))] text-foreground',
  'bg-[color-mix(in_oklab,var(--destructive)_35%,var(--card))] text-foreground',
]

const thaiDate = (iso: string) =>
  new Date(iso).toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: '2-digit' })

const carName = (j: OpenJob) =>
  [j.code, j.name].filter(Boolean).join(' ') || 'ไม่ระบุ'

function daysTone(days: number, staleDays: number) {
  if (days > staleDays) return 'bg-destructive/12 text-destructive'
  if (days > 3) return 'bg-chart-4/20 text-[color-mix(in_oklab,var(--chart-4)_55%,black)]'
  return 'bg-muted text-muted-foreground'
}

export function OpenJobs({
  data,
  onSelectCar,
}: {
  data: OpenJobs
  onSelectCar: (carId: number, branchCompanyId: string) => void
}) {
  const noun = useNoun()
  const [showAll, setShowAll] = useState(false)
  const [stage, setStage] = useState<string | null>(null)
  const filters = useExportFilters()

  if (data.total === 0) {
    return (
      <p className="rounded-xl border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
        ไม่มีใบแจ้งซ่อมค้างในตัวกรองนี้
      </p>
    )
  }

  const jobs = stage ? data.jobs.filter((j) => j.stage === stage) : data.jobs
  const shown = showAll ? jobs : jobs.slice(0, PREVIEW_ROWS)

  const exportExcel = () =>
    downloadExcel({
      title: TITLE,
      unit: 'วัน',
      filters,
      rows: [
        [
          'เลขที่ใบแจ้งซ่อม', 'บริษัท', `รหัส${noun}`, `ชื่อ${noun}`, 'อาการเสีย', 'วันที่แจ้ง', 'ค้างมา (วัน)',
          `สภาพ${noun}`, 'ขั้นที่ค้าง', 'อยู่ขั้นนี้ (วัน)', 'กำหนดรับของ', 'เอกสาร',
        ],
        ...data.jobs.map((j) => [
          j.ref_no,
          j.branch_company_name,
          j.code,
          j.name ?? '',
          j.broke_reason,
          thaiDate(j.reported_at),
          j.days,
          j.immobile ? 'เคลื่อนย้ายไม่ได้' : 'เคลื่อนย้ายได้',
          j.stage_label,
          j.stage_days ?? '',
          j.po_due ? thaiDate(j.po_due) : '',
          j.documents.map((d) => d.ref_no).join(', '),
        ]),
      ],
    })

  return (
    <div className="grid grid-cols-1 gap-4">
      <KpiStrip className="sm:grid-cols-3 xl:grid-cols-3">
        <Kpi label="ใบงานที่ยังไม่ปิด" value={num(data.total, 0)} unit="ใบ" />
        <Kpi
          label={`${noun}จอดซ่อมอยู่ตอนนี้`}
          value={num(data.car_count, 0)}
          unit="คัน"
          note={data.immobile_car_count ? `เคลื่อนย้ายไม่ได้ ${num(data.immobile_car_count, 0)} คัน` : undefined}
        />
        <Kpi
          label={`ค้างเกิน ${data.stale_days} วัน`}
          value={num(data.stale_count, 0)}
          unit="ใบ"
          alert={data.stale_count > 0}
        />
      </KpiStrip>

      <div className="grid gap-4 rounded-xl border bg-card px-4 py-4">
        <AgeBar buckets={data.buckets} total={data.total} />

        {data.has_process && (
          <StageFilter stages={data.stages} value={stage} onChange={setStage} total={data.total} />
        )}

        <div className="grid gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-medium">
              ค้างนานที่สุด
              {stage && (
                <span className="font-normal text-muted-foreground">
                  {' '}
                  · {data.stages.find((s) => s.code === stage)?.label}
                </span>
              )}
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={exportExcel}
              className="ml-auto text-muted-foreground"
              aria-label={`ดาวน์โหลด Excel: ${TITLE}`}
            >
              <FileSpreadsheet />
              Excel
            </Button>
          </div>

          <ul className="divide-y border-t">
            {shown.map((j) => (
              <JobRow key={j.ext_id} job={j} staleDays={data.stale_days} onSelectCar={onSelectCar} />
            ))}
          </ul>

          {jobs.length > PREVIEW_ROWS && (
            <Button
              variant="ghost"
              size="sm"
              className="justify-self-start"
              onClick={() => setShowAll((v) => !v)}
              aria-expanded={showAll}
            >
              {showAll ? `แสดงเฉพาะ ${PREVIEW_ROWS} ใบแรก` : `แสดงทั้งหมด ${num(jobs.length, 0)} ใบ`}
              <ChevronDown className={cn('transition-transform', showAll && 'rotate-180')} />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

function JobRow({
  job: j,
  staleDays,
  onSelectCar,
}: {
  job: OpenJob
  staleDays: number
  onSelectCar: (carId: number, branchCompanyId: string) => void
}) {
  const select = j.car_id != null ? () => onSelectCar(j.car_id!, j.branch_company_id) : undefined
  const detail = [j.stage !== 'unknown' ? j.stage_label : null, j.broke_reason || null]
    .filter(Boolean)
    .join(' · ')
  const docs = j.documents.map((d) => d.ref_no).filter(Boolean)

  return (
    <li>
      <button
        type="button"
        disabled={!select}
        onClick={select}
        className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-0.5 px-1 py-2.5 text-left hover:bg-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring disabled:cursor-default sm:grid-cols-[minmax(10rem,16rem)_minmax(0,1fr)_auto]"
        title={select ? 'เลือกคันนี้' : undefined}
      >
        <span className="min-w-0">
          <span className="block truncate font-medium">{carName(j)}</span>
          <span className="block truncate text-xs text-muted-foreground">
            {j.ref_no || 'ไม่มีเลขที่'} · {j.branch_company_name}
            {j.immobile && <span className="text-destructive"> · เคลื่อนย้ายไม่ได้</span>}
          </span>
        </span>

        <span className="col-span-2 row-start-2 min-w-0 text-sm sm:col-span-1 sm:row-start-auto">
          <span className="block truncate">{detail || <span className="text-muted-foreground">–</span>}</span>
          {(j.po_due || docs.length > 0 || j.stage_days != null) && (
            <span className="block truncate text-xs text-muted-foreground">
              {j.stage_days != null && j.stage !== 'unknown' && `อยู่ขั้นนี้ ${num(j.stage_days, 0)} วัน`}
              {j.po_due && (
                <span className={cn(j.po_overdue && 'font-medium text-destructive')}>
                  {' '}
                  · {j.po_overdue ? 'เลยกำหนดรับของ' : 'กำหนดรับของ'} {thaiDate(j.po_due)}
                </span>
              )}
              {docs.length > 0 && ` · ${docs.join(', ')}`}
            </span>
          )}
        </span>

        <span
          className={cn(
            'col-start-2 row-start-1 justify-self-end rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap tabular-nums sm:col-start-auto sm:row-start-auto',
            daysTone(j.days, staleDays),
          )}
        >
          {num(j.days, 0)} วัน
        </span>
      </button>
      {j.parts.length > 0 && (
        <div className="px-1 pb-2.5 sm:pl-[calc(min(16rem,max(10rem,25%))+1.25rem)]">
          <PartsDetails parts={j.parts} amount={j.parts_amount} />
        </div>
      )}
    </li>
  )
}

/** แถบสัดส่วนอายุของใบค้าง (ตัวเลขอยู่ในแถบ + รายการสำหรับ screen reader) */
function AgeBar({ buckets, total }: { buckets: OpenJobs['buckets']; total: number }) {
  return (
    <div className="grid gap-1.5">
      <h3 className="text-sm font-medium">อายุงานค้าง</h3>
      <div className="flex h-7 overflow-hidden rounded-md text-xs" aria-hidden>
        {buckets.map((b, i) =>
          b.count > 0 ? (
            <span
              key={b.label}
              title={`${b.label}: ${b.count} ใบ`}
              className={cn(
                'flex min-w-0 items-center truncate border-r-2 border-card px-2 last:border-r-0',
                BUCKET_TONES[i],
              )}
              style={{ width: `${(b.count / total) * 100}%` }}
            >
              <span className="truncate">
                {b.label} · <span className="font-semibold tabular-nums">{b.count}</span>
              </span>
            </span>
          ) : null,
        )}
      </div>
      <ul className="sr-only">
        {buckets.map((b) => (
          <li key={b.label}>
            {b.label}: {b.count} ใบ
          </li>
        ))}
      </ul>
    </div>
  )
}

/** จำนวนใบในแต่ละขั้น กดเพื่อกรองรายการด้านล่าง */
function StageFilter({
  stages,
  value,
  onChange,
  total,
}: {
  stages: OpenJobs['stages']
  value: string | null
  onChange: (stage: string | null) => void
  total: number
}) {
  const chip = (active: boolean) =>
    cn(
      'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition-colors',
      active ? 'border-primary bg-primary text-primary-foreground' : 'bg-card hover:bg-muted',
    )

  return (
    <div className="grid gap-1.5">
      <h3 className="text-sm font-medium">ค้างอยู่ขั้นไหน</h3>
      <div className="flex flex-wrap gap-2" role="group" aria-label="กรองตามขั้นที่ค้าง">
        <button type="button" className={chip(value === null)} aria-pressed={value === null} onClick={() => onChange(null)}>
          ทั้งหมด <span className="tabular-nums opacity-80">{num(total, 0)}</span>
        </button>
        {stages.map((s) => (
          <button
            key={s.code}
            type="button"
            className={chip(value === s.code)}
            aria-pressed={value === s.code}
            onClick={() => onChange(value === s.code ? null : s.code)}
          >
            {s.label} <span className="font-semibold tabular-nums">{num(s.count, 0)}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
