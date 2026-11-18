import { Download, Loader2, RotateCcw, X } from 'lucide-react'
import { toast } from 'sonner'

import { useCarDepartments, useDashboard, useSyncAll } from '@/api/hooks'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useCurrentUser } from '@/layout/RequireAuth'
import { useDashboardParams } from '@/lib/dashboard-params'
import { num } from '@/lib/format'

import { CarTable } from './CarTable'
import {
  OilByMonthChart,
  RepairByCarChart,
  RepairByCarTypeChart,
  RepairByMonthChart,
  RepairByTypeChart,
  RepairVsWorkChart,
  WorkByMonthChart,
} from './Charts'
import { ExportFiltersContext } from './export-context'
import { Kpi, KpiGrid } from './Kpi'
import { Reliability } from './Reliability'

const ALL_TYPES = 'all'
const THIS_YEAR = new Date().getFullYear()

export default function DashboardPage() {
  const me = useCurrentUser()
  const params = useDashboardParams(me)
  const departments = useCarDepartments()
  const dashboard = useDashboard(params.query)
  const sync = useSyncAll()

  const data = dashboard.data
  const company = me.companies.find((c) => c.code === params.company)
  const department = departments.data?.find((d) => d.id === params.carDep)
  const carType = data?.car_types.find((t) => t.id === data.filters.car_type)
  const selectedCar = data?.selected_car ?? null
  const totals = data?.car_table.totals

  const exportFilters: [string, string][] = [
    ['บริษัท', company?.name ?? params.company ?? ''],
    ['แผนก', department?.name ?? ''],
    ['ประเภทรถ', carType?.name ?? 'ทุกประเภทรถ'],
    ['รถ', selectedCar ? selectedCar.code || selectedCar.name || '' : 'ทุกคัน'],
  ]

  const runSync = () =>
    toast.promise(sync.mutateAsync(), {
      loading: 'กำลังดึงข้อมูลจาก webstock…',
      success: 'อัปเดตข้อมูลเรียบร้อย',
      error: (err: Error) => `อัปเดตไม่สำเร็จ: ${err.message}`,
    })

  if (!params.query) {
    return (
      <main className="p-4 md:p-6">
        <Alert>
          <AlertDescription>บัญชีนี้ยังไม่ได้รับสิทธิ์ดูข้อมูลบริษัทใด กรุณาติดต่อผู้ดูแลระบบ</AlertDescription>
        </Alert>
      </main>
    )
  }

  return (
    <ExportFiltersContext.Provider value={exportFilters}>
      <main className="grid grid-cols-1 gap-4 p-4 md:p-6">
        {/* Page header */}
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              ภาพรวมงานซ่อมบำรุง ปี {data?.filters.year ?? THIS_YEAR}
            </h1>
            <p className="text-sm text-muted-foreground">
              {company?.affiliated_name_sh ?? company?.name ?? params.company}
            </p>
          </div>
          {selectedCar && (
            <Badge variant="secondary" className="h-8 gap-1 pr-1 pl-3 text-sm">
              กำลังดูข้อมูล {selectedCar.code || selectedCar.name}
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={params.clearCar}
                aria-label="ดูข้อมูลทั้งหมด"
              >
                <X />
              </Button>
            </Badge>
          )}
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-3">
          <div className="max-w-full overflow-x-auto overflow-y-hidden pb-1 [scrollbar-width:thin]">
            {departments.data ? (
              <Tabs
                value={String(params.carDep)}
                onValueChange={(v) => params.selectCarDep(Number(v))}
              >
                <TabsList>
                  {departments.data.map((d) => (
                    <TabsTrigger key={d.id} value={String(d.id)}>
                      {d.name}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
            ) : (
              <Skeleton className="h-9 w-96 max-w-full" />
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={params.carType === null ? ALL_TYPES : String(params.carType)}
              onValueChange={(v) => params.selectCarType(v === ALL_TYPES ? null : Number(v))}
            >
              <SelectTrigger className="w-48" aria-label="ประเภทรถ">
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
            <Button variant="ghost" onClick={params.resetFilters}>
              <RotateCcw />
              ล้างตัวกรอง
            </Button>
            {me.user.is_superuser && (
              <Button onClick={runSync} disabled={sync.isPending}>
                {sync.isPending ? <Loader2 className="animate-spin" /> : <Download />}
                อัปเดตข้อมูล
              </Button>
            )}
          </div>
        </div>

        {dashboard.isError && (
          <Alert variant="destructive">
            <AlertDescription>โหลดข้อมูลไม่สำเร็จ: {dashboard.error.message}</AlertDescription>
          </Alert>
        )}

        {!data ? (
          <DashboardSkeleton />
        ) : (
          <div
            className="grid grid-cols-1 gap-4 transition-opacity data-[stale=true]:opacity-60"
            data-stale={dashboard.isPlaceholderData}
            aria-busy={dashboard.isFetching}
          >
            {/* Summary */}
            <KpiGrid>
              <Kpi feature label="ค่าซ่อมรวม" value={num(totals!.repair_total, 0)} unit="บาท" />
              <Kpi label="ต้นทุนซ่อมต่อชั่วโมง" value={num(totals!.repair_cost_per_hr, 2)} unit="บาท/ชม." />
              <Kpi label="%MA เฉลี่ย" value={num(totals!.percent_ma, 1)} unit="%" meter={totals!.percent_ma} />
              <Kpi label="การทำงานรวม" value={num(totals!.work_total, 0)} unit="ชม." />
              <Kpi label="น้ำมันดีเซลรวม" value={num(totals!.oil_total, 0)} unit="ลิตร" />
              <Kpi label="อัตราการใช้เชื้อเพลิง" value={num(totals!.fuel_rate, 2)} unit="ลิตร/ชม." />
            </KpiGrid>

            <CarTable
              table={data.car_table}
              selected={selectedCar}
              onSelect={(row) => params.selectCar(row.car_id, row.branch_company_id)}
            />

            <Reliability data={data.reliability} />

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <RepairByMonthChart chart={data.charts.repair_by_month} />
              <OilByMonthChart chart={data.charts.oil_by_month} />
              <RepairByTypeChart chart={data.charts.repair_by_type} />
              <RepairByCarTypeChart chart={data.charts.repair_by_car_type} />
              <WorkByMonthChart chart={data.charts.work_by_month} />
              <RepairVsWorkChart chart={data.charts.repair_vs_work} />
            </div>

            <RepairByCarChart chart={data.charts.repair_by_car} />
          </div>
        )}
      </main>
    </ExportFiltersContext.Provider>
  )
}

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4" aria-label="กำลังโหลด">
      <Skeleton className="h-24 rounded-xl" />
      <Skeleton className="h-80 rounded-xl" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
    </div>
  )
}
