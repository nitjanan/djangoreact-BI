import { Download, Loader2, RotateCcw, X } from 'lucide-react'

import type { Dashboard, Schemas } from '@/api/client'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import type { useDashboardParams } from '@/lib/dashboard-params'
import { num } from '@/lib/format'
import { cn } from '@/lib/utils'

const ALL_TYPES = 'all'
const THIS_YEAR = new Date().getFullYear()

/**
 * แผงหัวหน้าแบบแผงควบคุมเครื่องจักร: บริษัท/แผนกที่กำลังดู + ค่าซ่อมรวม + แท่งรายเดือน
 * เป็นจุดเด่นจุดเดียวของหน้า ส่วนอื่นของหน้าตั้งใจให้เรียบ
 */
export function HeroPanel({
  companyName,
  data,
  departments,
  params,
  canSync,
  syncing,
  onSync,
}: {
  companyName: string
  data: Dashboard | undefined
  departments: Schemas['CarDepartment'][] | undefined
  params: ReturnType<typeof useDashboardParams>
  canSync: boolean
  syncing: boolean
  onSync: () => void
}) {
  const selectedCar = data?.selected_car ?? null
  // unmatched มีค่าเฉพาะแท็บ "อื่นๆ" (ค่าซ่อมที่จับคู่กับรถไม่ได้) แท็บอื่นเป็น 0
  const repairTotal = data && data.car_table.totals.repair_total + data.unmatched.repair_total
  const year = data?.filters.year ?? THIS_YEAR

  return (
    <section
      aria-label="ภาพรวม"
      className="relative overflow-hidden rounded-2xl bg-hero text-plate-foreground"
    >
      {/* ลายเส้นตารางจาง ๆ แบบแผ่นเหล็กกันลื่น ให้แผงไม่แบน */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:linear-gradient(135deg,currentColor_1px,transparent_1px),linear-gradient(45deg,currentColor_1px,transparent_1px)] [background-size:22px_22px]"
      />

      <div className="relative grid gap-6 p-5 md:p-7 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div className="grid min-w-0 gap-3">
          <p className="text-sm text-plate-muted">ภาพรวมงานซ่อมบำรุง ปี {year}</p>
          <h1 className="text-3xl leading-tight font-semibold tracking-tight text-white md:text-4xl">
            {companyName}
          </h1>
          {selectedCar && (
            <div className="flex w-fit items-center gap-1 rounded-full bg-signal py-1 pr-1 pl-3 text-sm font-medium text-signal-foreground">
              กำลังดูเฉพาะ {selectedCar.code || selectedCar.name}
              <button
                type="button"
                onClick={params.clearCar}
                aria-label="กลับไปดูทุกคัน"
                className="flex size-6 items-center justify-center rounded-full hover:bg-black/10 focus-visible:outline-2 focus-visible:outline-signal-foreground"
              >
                <X className="size-3.5" />
              </button>
            </div>
          )}
        </div>

        <div className="grid gap-2 lg:justify-items-end">
          <p className="text-sm text-plate-muted">ค่าซ่อมรวม</p>
          {repairTotal === undefined ? (
            <Skeleton className="h-12 w-56 bg-white/10" />
          ) : (
            <p className="font-heading text-5xl leading-none font-semibold tracking-tight text-white tabular-nums md:text-6xl">
              {num(repairTotal, 0)}
              <span className="ml-2 text-lg font-medium text-plate-muted">บาท</span>
            </p>
          )}
          {data && <MonthBars chart={data.charts.repair_vs_work} />}
        </div>
      </div>

      {/* ตัวกรอง */}
      <div className="relative flex flex-wrap items-center gap-3 border-t border-white/10 bg-black/15 px-5 py-3 md:px-7">
        <div
          role="group"
          aria-label="แผนก"
          className="scroll-thin flex max-w-full gap-1 overflow-x-auto overflow-y-hidden rounded-lg bg-white/5 p-1"
        >
          {departments
            ? departments.map((d) => {
                const active = d.id === params.carDep
                return (
                  <button
                    key={d.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => params.selectCarDep(d.id)}
                    className={cn(
                      'shrink-0 rounded-md px-3 py-1.5 text-sm whitespace-nowrap text-plate-muted transition-colors hover:text-white focus-visible:outline-2 focus-visible:outline-signal',
                      active && 'bg-white font-semibold text-foreground hover:text-foreground',
                    )}
                  >
                    {d.name}
                  </button>
                )
              })
            : Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-8 w-24 bg-white/10" />
              ))}
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
          <Select
            value={params.carType === null ? ALL_TYPES : String(params.carType)}
            onValueChange={(v) => params.selectCarType(v === ALL_TYPES ? null : Number(v))}
          >
            <SelectTrigger
              className="w-48 border-white/20 bg-white/5 text-white hover:bg-white/10 data-[placeholder]:text-plate-muted [&_svg]:text-plate-muted"
              aria-label="ประเภทรถ"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_TYPES}>ทุกประเภทรถ</SelectItem>
              {data?.car_types.map((t) => (
                <SelectItem key={t.id} value={String(t.id)}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            onClick={params.resetFilters}
            className="text-plate-muted hover:bg-white/10 hover:text-white"
          >
            <RotateCcw />
            ล้างตัวกรอง
          </Button>
          {canSync && (
            <Button
              onClick={onSync}
              disabled={syncing}
              className="bg-signal text-signal-foreground hover:bg-signal/90"
            >
              {syncing ? <Loader2 className="animate-spin" /> : <Download />}
              อัปเดตข้อมูล
            </Button>
          )}
        </div>
      </div>
    </section>
  )
}

/** แท่งค่าซ่อมรายเดือนขนาดเล็ก — เดือนล่าสุดเป็นสีเหลืองอำพัน */
function MonthBars({ chart }: { chart: Schemas['RepairVsWorkChart'] }) {
  const max = Math.max(...chart.repair, 1)
  if (chart.repair.length === 0) return null
  return (
    <div className="flex h-10 items-end gap-1" role="img" aria-label="ค่าซ่อมรายเดือน">
      {chart.repair.map((v, i) => (
        <span
          key={chart.labels[i]}
          title={`${chart.labels[i]}: ${num(v, 0)} บาท`}
          className={cn(
            'w-3 rounded-t-sm bg-plate-muted/40',
            i === chart.repair.length - 1 && 'bg-signal',
          )}
          style={{ height: `${Math.max((v / max) * 100, 4)}%` }}
        />
      ))}
    </div>
  )
}
