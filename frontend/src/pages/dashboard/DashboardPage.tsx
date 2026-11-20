import { toast } from "sonner";

import { useCarDepartments, useDashboard, useSyncAll } from "@/api/hooks";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/layout/RequireAuth";
import { useDashboardParams } from "@/lib/dashboard-params";
import { num } from "@/lib/format";

import { CarTable } from "./CarTable";
import {
  AgeCostChart,
  CarScatterChart,
  CostPerHourChart,
  OilByMonthChart,
  RepairByCarTypeChart,
  RepairByMonthChart,
  RepairByTypeChart,
  RepairHeatmapChart,
  RepairParetoChart,
  WorkByMonthChart,
} from "./Charts";
import {
  ExportFiltersContext,
  FuelContext,
  NounContext,
  type Fuel,
} from "./export-context";
import { HeroPanel } from "./HeroPanel";
import { Insights } from "./Insights";
import { JobsSummary } from "./Jobs";
import { Kpi, KpiStrip, type Change } from "./Kpi";
import { compareLabel, pctChange } from "./period";
import { OpenJobs } from "./OpenJobs";
import { PartsSummary } from "./Parts";
import { Reliability } from "./Reliability";
import { Section } from "./Section";
import { UnmatchedTable } from "./UnmatchedTable";
import { ModelBenchmark, ModelComparison } from "./ModelComparison";
import { Watchlist } from "./Watchlist";

export default function DashboardPage() {
  const me = useCurrentUser();
  const params = useDashboardParams(me);
  const departments = useCarDepartments();
  const dashboard = useDashboard(params.query);
  const sync = useSyncAll();

  const data = dashboard.data;
  const company = me.companies.find((c) => c.code === params.company);
  const department = departments.data?.find((d) => d.id === params.carDep);
  const carType = data?.car_types.find((t) => t.id === data.filters.car_type);
  const selectedCar = data?.selected_car ?? null;
  // แท็บ "อื่นๆ" (car_dep = 0): รถที่ไม่มีแผนก + รายการที่จับคู่กับรถไม่ได้
  const isOther = params.carDep === 0;
  // คำเรียกรถ = ชื่อแผนกที่เลือก (backend ส่งมา แท็บอื่นๆ = รถ/เครื่องจักร)
  const noun = data?.filters.unit_noun ?? "รถ";
  // อัตราการใช้น้ำมันของแผนกนี้ (รถบรรทุก = ลิตร/กม.)
  const fuel: Fuel = data
    ? { field: data.filters.fuel_field, unit: data.filters.fuel_unit }
    : { field: "fuel_rate", unit: "ลิตร/ชม." };

  const exportFilters: [string, string][] = [
    ["บริษัท", company?.name ?? params.company ?? ""],
    ["แผนก", department?.name ?? ""],
    [`ประเภท${noun}`, carType?.name ?? `ทุกประเภท${noun}`],
    [noun, selectedCar ? selectedCar.code || selectedCar.name || "" : "ทุกคัน"],
  ];

  const runSync = () =>
    toast.promise(sync.mutateAsync(), {
      loading: "กำลังดึงข้อมูลจาก webstock…",
      success: (res) => {
        // ขั้นที่ได้ false = ดึงไม่ได้หรือไม่มีข้อมูล ขั้นอื่นยังอัปเดตตามปกติ
        const summary =
          (res.result as { summary?: Record<string, boolean> }).summary ?? {};
        const missing = Object.entries(summary)
          .filter(([, ok]) => !ok)
          .map(([step]) => SYNC_STEP_NAMES[step] ?? step);
        return missing.length
          ? `อัปเดตข้อมูลแล้ว ยกเว้น${missing.join(", ")} (webstock ไม่ส่งข้อมูลมา)`
          : "อัปเดตข้อมูลแล้ว";
      },
      error: (err: Error) => `อัปเดตข้อมูลไม่สำเร็จ: ${err.message}`,
    });

  if (!params.query) {
    return (
      <main className="p-4 md:p-6">
        <Alert>
          <AlertDescription>
            บัญชีนี้ยังไม่ได้รับสิทธิ์ดูข้อมูลบริษัทใด ให้ผู้ดูแลระบบเพิ่มบริษัทในหน้า Admin
          </AlertDescription>
        </Alert>
      </main>
    );
  }

  const totals = data?.car_table.totals;
  // เทียบกับช่วงเดียวกันของปีก่อน (ไม่มีข้อมูลปีก่อน -> แสดงว่าไม่มีให้เทียบ)
  const prev = data?.compare.totals ?? null;
  const change = (
    key:
      | "repair_cost_per_hr"
      | "percent_ma"
      | "work_total"
      | "oil_total"
      | "fuel_rate"
      | "liter_per_km",
    better: Change["better"],
  ): Change | undefined =>
    data && totals
      ? {
          pct: prev ? pctChange(totals[key], prev[key]) : null,
          better,
          against: compareLabel(data.compare),
        }
      : undefined;

  return (
    <NounContext.Provider value={noun}>
      <FuelContext.Provider value={fuel}>
        <ExportFiltersContext.Provider value={exportFilters}>
          <main className="mx-auto grid w-full max-w-[1600px] grid-cols-1 gap-8 p-4 md:p-6">
            <div className="grid grid-cols-1 gap-3">
              <HeroPanel
                companyName={
                  company?.affiliated_name_sh ??
                  company?.name ??
                  params.company ??
                  ""
                }
                data={data}
                departments={departments.data}
                params={params}
                canSync={Boolean(me.user.is_superuser)}
                syncing={sync.isPending}
                onSync={runSync}
              />

              {totals ? (
                <KpiStrip>
                  <Kpi
                    label="ต้นทุนซ่อมต่อชั่วโมง"
                    change={change("repair_cost_per_hr", "down")}
                    value={num(totals.repair_cost_per_hr, 2)}
                    unit="บาท/ชม."
                  />
                  <Kpi
                    label="%MA เฉลี่ย"
                    change={change("percent_ma", "up")}
                    value={num(totals.percent_ma, 1)}
                    unit="%"
                    meter={totals.percent_ma}
                  />
                  <Kpi
                    label="การทำงานรวม"
                    change={change("work_total", "up")}
                    value={num(totals.work_total, 0)}
                    unit="ชม."
                  />
                  <Kpi
                    label="น้ำมันดีเซลรวม"
                    change={change("oil_total", null)}
                    value={num(totals.oil_total, 0)}
                    unit="ลิตร"
                  />
                  <Kpi
                    label="อัตราการใช้เชื้อเพลิง"
                    change={change(fuel.field, "down")}
                    value={num(totals[fuel.field], 2)}
                    unit={fuel.unit}
                  />
                </KpiStrip>
              ) : (
                <Skeleton className="h-20 rounded-xl" />
              )}
            </div>

            {dashboard.isError && (
              <Alert variant="destructive">
                <AlertDescription>
                  โหลดข้อมูลไม่สำเร็จ: {dashboard.error.message}
                </AlertDescription>
              </Alert>
            )}

            {!data ? (
              <DashboardSkeleton />
            ) : (
              <div
                className="grid grid-cols-1 gap-10 transition-opacity data-[stale=true]:opacity-60"
                data-stale={dashboard.isPlaceholderData}
                aria-busy={dashboard.isFetching}
              >
                <Section
                  title={`รายการ${noun}`}
                  description={
                    isOther
                      ? "รถ/เครื่องจักรที่ยังไม่ได้ตั้งแผนกใน webstock เลือกแถวเพื่อดูกราฟเฉพาะคันนั้น"
                      : "เลือกแถวเพื่อดูกราฟทั้งหมดเฉพาะคันนั้น"
                  }
                >
                  <CarTable
                    table={data.car_table}
                    selected={selectedCar}
                    onSelect={(row) =>
                      params.selectCar(row.car_id, row.branch_company_id)
                    }
                    carTypes={data.car_types}
                    carType={params.carType}
                    onSelectCarType={params.selectCarType}
                  />
                </Section>

                <Section
                  title="สรุปและข้อสังเกต"
                  description={
                    selectedCar
                      ? `เทียบ${noun}คันนี้กับ${noun}คันอื่นในตัวกรองเดียวกัน`
                      : `คำนวณอัตโนมัติจากข้อมูลในตัวกรองนี้ เทียบ${noun}แต่ละคันกับ${noun}ส่วนใหญ่ในกลุ่มเดียวกัน`
                  }
                >
                  <Insights
                    data={data.insights}
                    onSelectCar={params.selectCar}
                  />
                </Section>

                {data.unmatched.rows.length > 0 && (
                  <UnmatchedTable data={data.unmatched} />
                )}

                <Section
                  title="ใบแจ้งซ่อมที่ยังไม่ปิดงาน"
                  description="สถานะ ณ ตอนนี้ ไม่ขึ้นกับปีที่เลือก · นับใบที่หัวหน้าช่างยังไม่ปิดงานใน webstock"
                >
                  <OpenJobs
                    data={data.open_jobs}
                    onSelectCar={params.selectCar}
                  />
                </Section>

                {!selectedCar && (
                  <Section
                    title={`${noun}ที่ต้องจับตา`}
                    description={`${noun}ที่ติดเกณฑ์อย่างน้อย 1 เรื่อง เทียบกับ${noun}ส่วนใหญ่ในตัวกรองเดียวกัน · กดเพื่อดูคันนั้น`}
                  >
                    <Watchlist
                      data={data.watchlist}
                      onSelectCar={params.selectCar}
                    />
                  </Section>
                )}

                {selectedCar && (
                  <Section
                    title="เทียบกับรุ่นเดียวกัน"
                    description={`${noun}คันนี้เทียบกับคันอื่นยี่ห้อ/รุ่นเดียวกัน และคันอื่นในชนิดเดียวกัน (ไม่รวมคันนี้) ในตัวกรองนี้`}
                  >
                    <ModelBenchmark data={data.model_benchmark} />
                  </Section>
                )}

                {!selectedCar && (
                  <Section
                    title="เทียบยี่ห้อ/รุ่น และอายุ"
                    description={`ภายในชนิด${noun}เดียวกัน · ต้นทุนซ่อม/ชม. = ค่าซ่อมรวม ÷ ชั่วโมงรวมของรุ่น นับเฉพาะคันที่มีชั่วโมงทำงาน · อายุ ณ ปีที่เลือก`}
                  >
                    <ModelComparison data={data.model_comparison} />
                    <AgeCostChart
                      rows={data.car_table.rows}
                      onSelect={(row) =>
                        params.selectCar(row.car_id, row.branch_company_id)
                      }
                    />
                  </Section>
                )}

                <Section
                  title="งานที่ทำ แยกตามแผนกค่าใช้จ่าย"
                  description={`จากบันทึกการใช้${noun}ใน webstock · ชั่วโมง = เวลาเริ่ม-จบของแต่ละงาน${
                    selectedCar ? ` · เฉพาะ${noun}คันนี้` : ""
                  }`}
                >
                  <JobsSummary data={data.jobs} />
                  <CarScatterChart
                    rows={data.car_table.rows}
                    selected={selectedCar}
                    onSelect={(row) =>
                      params.selectCar(row.car_id, row.branch_company_id)
                    }
                  />
                </Section>

                <Section
                  title="การเสียและเวลาซ่อม"
                  description="นับจากใบแจ้งซ่อมประเภทซ่อม"
                >
                  <Reliability data={data.reliability} />
                </Section>

                <Section
                  title="อะไหล่ที่ใช้ในการซ่อม"
                  description={
                    selectedCar
                      ? `อะไหล่ที่จ่ายให้ใบแจ้งซ่อมของ${noun}คันนี้ในช่วงที่เลือก`
                      : "จากใบจ่ายสินค้าภายใน-อะไหล่ ที่อ้างอิงเลขที่ใบแจ้งซ่อม"
                  }
                >
                  <PartsSummary
                    data={data.parts}
                    carSelected={Boolean(selectedCar)}
                  />
                </Section>

                <Section title="ค่าใช้จ่ายซ่อมบำรุง">
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                    <RepairByMonthChart chart={data.charts.repair_by_month} />
                    <CostPerHourChart chart={data.charts.repair_vs_work} />
                    <RepairByTypeChart chart={data.charts.repair_by_type} />
                    <RepairByCarTypeChart
                      chart={data.charts.repair_by_car_type}
                    />
                  </div>
                  <RepairParetoChart chart={data.charts.repair_by_car} />
                  <RepairHeatmapChart chart={data.charts.repair_heatmap} />
                </Section>

                <Section title="น้ำมันและชั่วโมงทำงาน">
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                    <OilByMonthChart chart={data.charts.oil_by_month} />
                    <WorkByMonthChart chart={data.charts.work_by_month} />
                  </div>
                </Section>
              </div>
            )}
          </main>
        </ExportFiltersContext.Provider>
      </FuelContext.Provider>
    </NounContext.Provider>
  );
}

const SYNC_STEP_NAMES: Record<string, string> = {
  car_dep: "ข้อมูลแผนก",
  repair: "ค่าซ่อม",
  oil: "น้ำมัน",
  work: "ชั่วโมงทำงาน",
  maintenance: "ใบแจ้งซ่อม",
  unmatched: "รายการที่ยังจับคู่ทะเบียนรถ/เครื่องจักร/หน่วยงานไม่ได้",
};

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4" aria-label="กำลังโหลด">
      <Skeleton className="h-80 rounded-xl" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
    </div>
  );
}
