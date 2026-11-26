import { toast } from "sonner";

import { useCarDepartments, useDashboard, useSyncAll } from "@/api/hooks";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/layout/RequireAuth";
import { useDashboardParams } from "@/lib/dashboard-params";
import { num } from "@/lib/format";

import { BranchCompare } from "./BranchCompare";
import { CarTable } from "./CarTable";
import {
  CarCostScatterChart,
  CostPerHourChart,
  OilByMonthChart,
  RepairBreakdownChart,
  RepairByMonthChart,
  RepairParetoChart,
  WorkByMonthChart,
} from "./Charts";
import {
  ExportFiltersContext,
  FuelContext,
  NounContext,
  type Fuel,
} from "./export-context";
import { DowntimeTimeline, PartPricesPanel } from "./FleetOps";
import { HeroPanel } from "./HeroPanel";
import { chartAnchorId, Insights } from "./Insights";
import { JobsSummary } from "./Jobs";
import { StatCard, type Change } from "./Kpi";
import { Clock, Droplets, Fuel as FuelIcon, Gauge, Wrench } from "lucide-react";
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
  const brand = data?.brands.find((b) => b.key === data.filters.brand);
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
    ["ยี่ห้อ", brand?.label ?? "ทุกยี่ห้อ"],
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
  // ไม่มีชั่วโมงทำงานใน webstock (เช่น เครื่องจักรโรงโม่ไม่ได้ลงบันทึกการใช้รถ)
  // ค่าที่หารด้วยชั่วโมงจึงเป็น 0 -> แสดง 0 ตามเดิมแต่บอกเหตุผลไว้ใต้ตัวเลข
  const noHoursNote =
    totals && totals.work_total === 0
      ? `ไม่มีชั่วโมงทำงานในบันทึกการใช้${noun}`
      : undefined;
  const fuelNote =
    fuel.field === "liter_per_km"
      ? totals && totals.km_total === 0
        ? "ไม่มีเลขไมล์ในบันทึกการเติมน้ำมัน"
        : undefined
      : noHoursNote;
  // เทียบกับช่วงเดียวกันของปีก่อน (ไม่มีข้อมูลปีก่อน -> แสดงว่าไม่มีให้เทียบ)
  // ไม่มีข้อมูลปีก่อน: ไม่แสดงการเทียบในแต่ละช่อง บอกครั้งเดียวใต้แถบตัวเลข
  type CompareKey =
    | "repair_cost_per_hr"
    | "percent_ma"
    | "work_total"
    | "oil_total"
    | "fuel_rate"
    | "liter_per_km";
  const compareTotals = data?.compare.has_data
    ? (data.compare.totals ?? null)
    : null;
  // ปีก่อนมีแถวแต่ค่าเป็น 0 ทุกช่อง (เทียบไม่ได้สักช่อง) -> ถือว่าไม่มีให้เทียบ
  const prev =
    totals &&
    compareTotals &&
    (
      [
        "repair_cost_per_hr",
        "percent_ma",
        "work_total",
        "oil_total",
        fuel.field,
      ] as CompareKey[]
    ).some((k) => pctChange(totals[k], compareTotals[k]) !== null)
      ? compareTotals
      : null;
  const change = (
    key: CompareKey,
    better: Change["better"],
  ): Change | undefined => {
    if (!data || !totals || !prev) return undefined;
    const pct = pctChange(totals[key], prev[key]);
    // เทียบไม่ได้เฉพาะช่องนี้: ไม่ต้องแสดงอะไร ไม่ให้ข้อความซ้ำทุกช่อง
    return pct === null
      ? undefined
      : { pct, better, against: compareLabel(data.compare) };
  };

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

              {/* ตัวเลขสรุปของทุกคันในตัวกรอง: ตัวหลัก 1 + ตัวรอง 4 */}
              {totals ? (
                <section className="grid gap-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <h2 className="font-heading text-lg font-semibold">
                      ภาพรวม{selectedCar ? `${noun}คันนี้` : `${noun}ทั้งหมด`}
                      {!selectedCar && (
                        <span className="ml-2 text-sm font-normal text-muted-foreground">
                          {num(data.car_table.rows.length, 0)} คันในตัวกรองนี้
                        </span>
                      )}
                    </h2>
                    {data && !prev && (
                      <span className="text-xs text-muted-foreground">
                        ไม่มีข้อมูล {compareLabel(data.compare)} ให้เทียบ
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3 xl:grid-cols-[minmax(0,1.6fr)_repeat(4,minmax(0,1fr))] [&>:first-child]:col-span-2 xl:[&>:first-child]:col-span-1">
                    <StatCard
                      headline
                      icon={Wrench}
                      tone="var(--signal)"
                      label="ต้นทุนซ่อมต่อชั่วโมง"
                      change={change("repair_cost_per_hr", "down")}
                      value={num(totals.repair_cost_per_hr, 2)}
                      unit="บาท/ชม."
                      note={
                        noHoursNote ?? (
                          <>
                            ค่าซ่อม{" "}
                            <b className="font-medium text-foreground tabular-nums">
                              {num(totals.repair_total, 0)}
                            </b>{" "}
                            บาท ÷ ทำงาน{" "}
                            <b className="font-medium text-foreground tabular-nums">
                              {num(totals.work_total, 0)}
                            </b>{" "}
                            ชม.
                          </>
                        )
                      }
                    />
                    <div className="contents">
                      <StatCard
                        icon={Gauge}
                        tone="var(--chart-1)"
                        label="%MA เฉลี่ย"
                        change={change("percent_ma", "up")}
                        value={num(totals.percent_ma, 1)}
                        unit="%"
                        meter={totals.percent_ma}
                        note={noHoursNote}
                      />
                      <StatCard
                        icon={Clock}
                        tone="var(--chart-3)"
                        label="การทำงานรวม"
                        change={change("work_total", "up")}
                        value={num(totals.work_total, 0)}
                        unit="ชม."
                        note={noHoursNote}
                      />
                      <StatCard
                        icon={FuelIcon}
                        tone="var(--chart-4)"
                        label="น้ำมันดีเซลรวม"
                        change={change("oil_total", null)}
                        value={num(totals.oil_total, 0)}
                        unit="ลิตร"
                      />
                      <StatCard
                        icon={Droplets}
                        tone="var(--chart-5)"
                        label="อัตราการใช้เชื้อเพลิง"
                        change={change(fuel.field, "down")}
                        value={num(totals[fuel.field], 2)}
                        unit={fuel.unit}
                        note={fuelNote}
                      />
                    </div>
                  </div>
                </section>
              ) : (
                <Skeleton className="h-56 rounded-xl" />
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
                {/* 0) ตารางรถทั้งหมด: ไว้ค้นหา/เลือกคัน (แสดง 7 แถว เลื่อนดูที่เหลือ) */}
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
                    brands={data.brands}
                    brand={data.filters.brand}
                    onSelectBrand={params.selectBrand}
                  />
                </Section>

                {/* 1) ภาพรวมสั้น ๆ: ตัวเลขสรุป เดือนที่พุ่ง แนวโน้ม คุณภาพข้อมูล */}
                <Section
                  title="สรุปและข้อสังเกต"
                  description={
                    selectedCar
                      ? `เทียบ${noun}คันนี้กับ${noun}คันอื่นในตัวกรองเดียวกัน`
                      : `คำนวณอัตโนมัติจากข้อมูลในตัวกรองนี้ · รายชื่อ${noun}ที่ผิดปกติอยู่ใน "${noun}ที่ต้องจับตา" ด้านล่าง`
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

                {/* 2) ต้องจัดการ: คันไหนก่อน และงานที่ค้าง */}
                {!selectedCar && (
                  <Section
                    title={`${noun}ที่ต้องจับตา`}
                    description={`${noun}ที่ติดเกณฑ์อย่างน้อย 1 เรื่อง เทียบกับ${noun}ส่วนใหญ่ในตัวกรองเดียวกัน (น้ำมันพุ่งเทียบกับเดือนปกติของคันนั้นเอง) · กดเพื่อดูคันนั้น`}
                  >
                    <Watchlist
                      data={data.watchlist}
                      onSelectCar={params.selectCar}
                    />
                  </Section>
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

                {/* 3) เงินไปไหน */}
                <Section title="ค่าใช้จ่ายซ่อมบำรุง">
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                    <div
                      id={chartAnchorId("repair_by_month")}
                      className="grid scroll-mt-20 rounded-xl"
                    >
                      <RepairByMonthChart
                        chart={data.charts.repair_by_month}
                        forecast={data.forecast}
                      />
                    </div>
                    <CostPerHourChart chart={data.charts.repair_vs_work} />
                  </div>
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                    <RepairBreakdownChart
                      byType={data.charts.repair_by_type}
                      byCarType={data.charts.repair_by_car_type}
                    />
                    <RepairParetoChart chart={data.charts.repair_by_car} />
                  </div>
                </Section>

                <Section
                  title="อะไหล่ที่ใช้ในการซ่อม"
                  description={
                    selectedCar
                      ? `อะไหล่ที่จ่ายให้ใบแจ้งซ่อมของ${noun}คันนี้ในช่วงที่เลือก`
                      : "จากใบจ่ายสินค้าภายใน-อะไหล่ ที่อ้างอิงเลขที่ใบแจ้งซ่อม"
                  }
                >
                  <PartsSummary data={data.parts} />
                  <PartPricesPanel data={data.part_prices} />
                </Section>

                {/* 4) การเสียและเวลาซ่อม */}
                <Section
                  title="การเสียและเวลาซ่อม"
                  description="นับจากใบแจ้งซ่อมประเภทซ่อม · PM = ใบแจ้งซ่อมประเภททำ PM · Downtime = เวลาตั้งแต่แจ้งซ่อมจนปิดงาน"
                >
                  <div
                    id={chartAnchorId("reliability")}
                    className="grid scroll-mt-20 rounded-xl"
                  >
                    <Reliability data={data.reliability} />
                  </div>
                  <DowntimeTimeline
                    data={data.downtime}
                    onSelectCar={params.selectCar}
                  />
                </Section>

                <Section title="น้ำมันและชั่วโมงทำงาน">
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                    <OilByMonthChart
                      chart={data.charts.oil_by_month}
                      forecast={data.forecast}
                    />
                    <WorkByMonthChart chart={data.charts.work_by_month} />
                  </div>
                </Section>

                {/* 5) เทียบและวิเคราะห์ */}
                {data.branch_compare.length > 1 && (
                  <Section
                    title="เทียบบริษัท/สาขา"
                    description={`${noun}ในตัวกรองนี้แยกตามบริษัท · ต้นทุนซ่อม/ชม. = ค่าซ่อมรวม ÷ ชั่วโมงทำงานรวมของบริษัท`}
                  >
                    <BranchCompare
                      data={data.branch_compare}
                      onSelectBranch={(id) => {
                        const c = me.companies.find((x) => x.id === id);
                        if (c) params.selectCompany(c.code);
                      }}
                    />
                  </Section>
                )}

                {selectedCar && (
                  <Section
                    title="เทียบกับรุ่นเดียวกัน"
                    description={`${noun}คันนี้เทียบกับคันอื่นยี่ห้อ/รุ่นเดียวกัน และคันอื่นในชนิดเดียวกัน (ไม่รวมคันนี้) ในตัวกรองนี้`}
                  >
                    <ModelBenchmark data={data.model_benchmark} />
                    <CarCostScatterChart
                      rows={data.car_table.rows}
                      selected={selectedCar}
                      onSelect={(row) =>
                        params.selectCar(row.car_id, row.branch_company_id)
                      }
                    />
                  </Section>
                )}

                {!selectedCar && (
                  <Section
                    title="เทียบยี่ห้อ/รุ่น และอายุ"
                    description={`ภายในชนิด${noun}เดียวกัน · ต้นทุนซ่อม/ชม. = ค่าซ่อมรวม ÷ ชั่วโมงรวมของรุ่น นับเฉพาะคันที่มีชั่วโมงทำงาน · อายุ ณ ปีที่เลือก`}
                  >
                    <ModelComparison data={data.model_comparison} />
                    <CarCostScatterChart
                      rows={data.car_table.rows}
                      selected={selectedCar}
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
