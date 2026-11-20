import {
  ArrowUp,
  Clock,
  Download,
  History,
  Loader2,
  RotateCcw,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import type { Dashboard, Schemas } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { carHistoryPath } from "@/lib/car-path";
import type { useDashboardParams } from "@/lib/dashboard-params";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";

import { ChangeNote } from "./Kpi";
import {
  compareLabel,
  PERIOD_OPTIONS,
  pctChange,
  periodKey,
  periodLabel,
} from "./period";

const THIS_YEAR = new Date().getFullYear();
const THIS_MONTH = new Date().getMonth() + 1;
const PERIOD_GROUPS = ["", "ครึ่งปี", "ไตรมาส", "เดือน"];

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
  companyName: string;
  data: Dashboard | undefined;
  departments: Schemas["CarDepartment"][] | undefined;
  params: ReturnType<typeof useDashboardParams>;
  canSync: boolean;
  syncing: boolean;
  onSync: () => void;
}) {
  // ป้าย "กำลังดูเฉพาะ" ในแผงหัว: เลื่อนพ้นจอแล้วแสดงป้ายลอยด้านล่างแทน
  const [chip, setChip] = useState<HTMLDivElement | null>(null);
  const chipVisible = useInView(chip);
  // ไม่ได้เลือกคัน: แผงหัวพ้นจอแล้วแสดงป้ายลอยสีเขียวบอกตัวกรองที่ดูอยู่
  const [hero, setHero] = useState<HTMLElement | null>(null);
  const heroVisible = useInView(hero);
  const selectedCar = data?.selected_car ?? null;
  // unmatched มีค่าเฉพาะแท็บ "อื่นๆ" (ค่าซ่อมที่จับคู่กับรถไม่ได้) แท็บอื่นเป็น 0
  const repairTotal =
    data && data.car_table.totals.repair_total + data.unmatched.repair_total;
  const year = data?.filters.year ?? params.year ?? THIS_YEAR;
  // ปีปัจจุบันมีข้อมูลถึงเดือนนี้ ช่วงที่เลยไปเลือกไม่ได้
  const lastMonth = year >= THIS_YEAR ? THIS_MONTH : 12;
  const wholeYear = params.monthFrom === null && params.monthTo === null;
  const range = data
    ? { from: data.filters.month_from, to: data.filters.month_to }
    : { from: 1, to: lastMonth };
  const selectedKey = periodKey(range, lastMonth, wholeYear);
  const years = data?.filters.years ?? [year];
  const compare = data?.compare;

  return (
    <section
      ref={setHero}
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
          <p className="text-sm text-plate-muted">
            ภาพรวมงานซ่อมบำรุง {periodLabel(year, range, wholeYear)}
          </p>
          <h1 className="text-3xl leading-tight font-semibold tracking-tight text-white md:text-4xl">
            {companyName}
          </h1>
          {selectedCar && (
            <div className="flex flex-wrap items-center gap-2">
              <div
                ref={setChip}
                className="flex w-fit items-center gap-1 rounded-full bg-signal py-1 pr-1 pl-3 text-sm font-medium text-signal-foreground"
              >
                กำลังดูเฉพาะ {selectedCar.code || selectedCar.name}
                {selectedCar.branch_company_name &&
                  ` · ${selectedCar.branch_company_name}`}
                <button
                  type="button"
                  onClick={params.clearCar}
                  aria-label="กลับไปดูทุกคัน"
                  className="flex size-6 items-center justify-center rounded-full hover:bg-black/10 focus-visible:outline-2 focus-visible:outline-signal-foreground"
                >
                  <X className="size-3.5" />
                </button>
              </div>
              <Link
                to={carHistoryPath(
                  selectedCar.car_id,
                  selectedCar.branch_company_id,
                )}
                className="inline-flex items-center gap-1.5 rounded-full border border-white/30 px-3 py-1 text-sm text-white hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-signal"
              >
                <History className="size-3.5" aria-hidden />
                ดูประวัติทั้งหมดของคันนี้
              </Link>
            </div>
          )}
          {selectedCar && !chipVisible && (
            <FloatingCarPill
              label={[
                [selectedCar.code, selectedCar.name].filter(Boolean).join(" "),
                selectedCar.branch_company_name,
              ]
                .filter(Boolean)
                .join(" · ")}
              onClear={params.clearCar}
              historyPath={carHistoryPath(
                selectedCar.car_id,
                selectedCar.branch_company_id,
              )}
            />
          )}
          {!selectedCar && data && !heroVisible && (
            <FloatingCarPill
              tone="filter"
              label={[
                companyName,
                departments?.find((d) => d.id === params.carDep)?.name,
                data.car_types.find((t) => t.id === data.filters.car_type)
                  ?.name ?? `ทุกประเภท${data.filters.unit_noun}`,
                periodLabel(year, range, wholeYear),
              ]
                .filter(Boolean)
                .join(" · ")}
            />
          )}
        </div>

        <div className="grid gap-2 lg:justify-items-end">
          <p className="text-sm text-plate-muted">ค่าซ่อมรวม</p>
          {repairTotal === undefined ? (
            <Skeleton className="h-12 w-56 bg-white/10" />
          ) : (
            <p className="font-heading text-5xl leading-none font-semibold tracking-tight text-white tabular-nums md:text-6xl">
              {num(repairTotal, 0)}
              <span className="ml-2 text-lg font-medium text-plate-muted">
                บาท
              </span>
            </p>
          )}
          {compare && repairTotal !== undefined && (
            <ChangeNote
              onDark
              pct={
                compare.has_data
                  ? pctChange(repairTotal, compare.repair_total)
                  : null
              }
              better="down"
              against={compareLabel(compare)}
            />
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
                const active = d.id === params.carDep;
                return (
                  <button
                    key={d.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => params.selectCarDep(d.id)}
                    className={cn(
                      "shrink-0 rounded-md px-3 py-1.5 text-sm whitespace-nowrap text-plate-muted transition-colors hover:text-white focus-visible:outline-2 focus-visible:outline-signal",
                      active &&
                        "bg-white font-semibold text-foreground hover:text-foreground",
                    )}
                  >
                    {d.name}
                  </button>
                );
              })
            : Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-8 w-24 bg-white/10" />
              ))}
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
          <div
            role="group"
            aria-label="ช่วงเวลา"
            className="flex flex-wrap items-center gap-2"
          >
            <Select
              value={String(year)}
              onValueChange={(v) => {
                const y = Number(v);
                // ปีใหม่ยังไม่ถึงช่วงที่เลือก -> กลับไปดูทั้งปี
                const last = y >= THIS_YEAR ? THIS_MONTH : 12;
                if (wholeYear || range.from > last)
                  params.selectPeriod(y, null, null);
                else params.selectPeriod(y, range.from, range.to);
              }}
            >
              <SelectTrigger
                className="w-28 border-white/20 bg-white/5 text-white hover:bg-white/10 [&_svg]:text-plate-muted"
                aria-label="ปี"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {years.map((y) => (
                  <SelectItem key={y} value={String(y)}>
                    ปี {y}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={selectedKey}
              onValueChange={(key) => {
                const o = PERIOD_OPTIONS.find((p) => p.key === key);
                if (!o) return;
                if (o.key === "all") params.selectPeriod(year, null, null);
                else
                  params.selectPeriod(year, o.from, Math.min(o.to, lastMonth));
              }}
            >
              <SelectTrigger
                className="w-52 border-white/20 bg-white/5 text-white hover:bg-white/10 [&_svg]:text-plate-muted"
                aria-label="ช่วงเดือน"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {selectedKey === "custom" && (
                  <SelectItem value="custom" disabled>
                    {periodLabel(year, range, false)}
                  </SelectItem>
                )}
                {PERIOD_GROUPS.map((group) => (
                  <SelectGroup key={group || "all"}>
                    {group && <SelectLabel>{group}</SelectLabel>}
                    {PERIOD_OPTIONS.filter((o) => o.group === group).map(
                      (o) => (
                        <SelectItem
                          key={o.key}
                          value={o.key}
                          disabled={o.from > lastMonth}
                        >
                          {o.label}
                        </SelectItem>
                      ),
                    )}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
          </div>
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
          <LastSynced at={data?.last_synced_at} />
        </div>
      </div>
    </section>
  );
}

/** element อยู่ในจอหรือไม่ (null = ยังไม่มี element ถือว่าอยู่ในจอ ไม่ต้องแสดงป้ายลอย) */
function useInView(el: Element | null) {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) =>
      setVisible(entry.isIntersecting),
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      setVisible(true);
    };
  }, [el]);
  return visible;
}

/** ป้ายลอยกลางล่างจอ กดชื่อเพื่อกลับขึ้นไปด้านบน
 *
 * tone="car" (ส้ม): ดูรถคันเดียวอยู่ มีปุ่มดูประวัติ และ × เพื่อดูทุกคัน
 * tone="filter" (เขียว): ไม่ได้เลือกคัน แสดงตัวกรองที่ดูอยู่
 */
function FloatingCarPill({
  label,
  onClear,
  historyPath,
  tone = "car",
}: {
  label: string;
  onClear?: () => void;
  historyPath?: string;
  tone?: "car" | "filter";
}) {
  const isCar = tone === "car";
  return (
    <div
      role="status"
      className="fixed inset-x-0 bottom-5 z-40 flex justify-center px-4 animate-in fade-in slide-in-from-bottom-2"
    >
      <div
        className={cn(
          "flex max-w-full items-center gap-1 rounded-full border border-black/10 py-1 pr-1 pl-1 text-sm font-medium shadow-lg",
          isCar
            ? "bg-signal text-signal-foreground"
            : "bg-emerald-600 text-white",
        )}
      >
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          title="กลับขึ้นไปด้านบน"
          className="flex min-w-0 items-center gap-1.5 rounded-full py-1 pr-1 pl-2.5 hover:bg-black/10 focus-visible:outline-2 focus-visible:outline-signal-foreground"
        >
          <ArrowUp className="size-3.5 shrink-0" aria-hidden />
          <span className="truncate">
            {isCar ? `กำลังดูเฉพาะ ${label || "คันที่เลือก"}` : `กำลังดู ${label}`}
          </span>
        </button>
        {historyPath && (
          <Link
            to={historyPath}
            title="ดูประวัติทั้งหมดของคันนี้"
            aria-label="ดูประวัติทั้งหมดของคันนี้"
            className="flex size-7 shrink-0 items-center justify-center rounded-full hover:bg-black/10 focus-visible:outline-2 focus-visible:outline-signal-foreground"
          >
            <History className="size-3.5" />
          </Link>
        )}
        {onClear && (
          <button
            type="button"
            onClick={onClear}
            aria-label="กลับไปดูทุกคัน"
            className="flex size-7 shrink-0 items-center justify-center rounded-full hover:bg-black/10 focus-visible:outline-2 focus-visible:outline-signal-foreground"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

/** วันเวลาที่ดึงข้อมูลจาก webstock ครั้งล่าสุด (ทั้งจากปุ่มอัปเดตและงานอัปเดตอัตโนมัติ) */
function LastSynced({ at }: { at: string | null | undefined }) {
  if (at === undefined) return null;
  const date = at ? new Date(at) : null;
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-plate-muted">
      <Clock className="size-3.5" aria-hidden />
      อัปเดตข้อมูลล่าสุด{" "}
      {date ? (
        <time dateTime={at!} className="text-white tabular-nums">
          {date.toLocaleString("th-TH", {
            day: "numeric",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}{" "}
          น.
        </time>
      ) : (
        "ยังไม่เคยอัปเดต"
      )}
    </span>
  );
}

/** แท่งค่าซ่อมรายเดือนขนาดเล็ก — เดือนล่าสุดเป็นสีเหลืองอำพัน */
function MonthBars({ chart }: { chart: Schemas["RepairVsWorkChart"] }) {
  const max = Math.max(...chart.repair, 1);
  if (chart.repair.length === 0) return null;
  return (
    <div
      className="flex h-10 items-end gap-1"
      role="img"
      aria-label="ค่าซ่อมรายเดือน"
    >
      {chart.repair.map((v, i) => (
        <span
          key={chart.labels[i]}
          title={`${chart.labels[i]}: ${num(v, 0)} บาท`}
          className={cn(
            "w-3 rounded-t-sm bg-plate-muted/40",
            i === chart.repair.length - 1 && "bg-signal",
          )}
          style={{ height: `${Math.max((v / max) * 100, 4)}%` }}
        />
      ))}
    </div>
  );
}
