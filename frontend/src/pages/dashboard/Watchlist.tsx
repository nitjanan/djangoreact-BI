import { ChevronDown, ChevronRight, FileSpreadsheet } from "lucide-react";
import { useState } from "react";

import type { Schemas } from "@/api/client";
import { Button } from "@/components/ui/button";
import { downloadExcel } from "@/lib/export-excel";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";

import { useExportFilters } from "./export-context";

type Watchlist = Schemas["Watchlist"];
type WatchCar = Schemas["WatchCar"];
type ReasonCode = WatchCar["reasons"][number]["code"];

const TITLE = "รถที่ต้องจับตา";
const PREVIEW_ROWS = 8;

// สีตามความรุนแรงของเหตุผล: แดง = ต้องจัดการ, เหลือง = ติดตาม
const REASON_TONE: Record<ReasonCode, string> = {
  stale: "bg-destructive/12 text-destructive",
  cost: "bg-destructive/12 text-destructive",
  repeat: "bg-chart-4/20 text-[color-mix(in_oklab,var(--chart-4)_55%,black)]",
  failure: "bg-chart-4/20 text-[color-mix(in_oklab,var(--chart-4)_55%,black)]",
  fuel: "bg-muted text-muted-foreground",
};

const carName = (c: WatchCar) =>
  [c.code, c.name].filter(Boolean).join(" ") || "ไม่ระบุ";

export function Watchlist({
  data,
  onSelectCar,
}: {
  data: Watchlist;
  onSelectCar: (carId: number, branchCompanyId: string) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const [reason, setReason] = useState<ReasonCode | null>(null);
  const filters = useExportFilters();

  if (data.cars.length === 0) {
    return (
      <p className="rounded-xl border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
        ไม่มีรถที่ผิดปกติในตัวกรองนี้
        {!data.compared && (
          <span className="mt-1 block text-xs">
            รถน้อยกว่า 5 คัน จึงไม่เทียบค่าซ่อม การเสีย และน้ำมันกับค่ากลาง
          </span>
        )}
      </p>
    );
  }

  const cars = reason
    ? data.cars.filter((c) => c.reasons.some((r) => r.code === reason))
    : data.cars;
  const shown = showAll ? cars : cars.slice(0, PREVIEW_ROWS);

  const exportExcel = () =>
    downloadExcel({
      title: TITLE,
      unit: "บาท",
      filters,
      rows: [
        [
          "บริษัท",
          "รหัสรถ",
          "ชื่อรถ",
          "จำนวนเรื่อง",
          "เรื่องที่ต้องจับตา",
          "รายละเอียด",
          "ค่าซ่อมรวม (บาท)",
          "เสีย (ครั้ง)",
        ],
        ...data.cars.map((c) => [
          c.branch_company_name,
          c.code,
          c.name ?? "",
          c.reasons.length,
          c.reasons.map((r) => r.label).join(", "),
          c.reasons.map((r) => `${r.label}: ${r.detail}`).join(" | "),
          c.repair_total,
          c.failure_count,
        ]),
      ],
    });

  const chip = (active: boolean) =>
    cn(
      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition-colors",
      active
        ? "border-primary bg-primary text-primary-foreground"
        : "bg-card hover:bg-muted",
    );

  return (
    <div className="grid gap-4 rounded-xl border bg-card px-4 py-4">
      <div className="grid gap-1.5">
        <h3 className="text-sm font-medium">
          {num(data.cars.length, 0)} จาก {num(data.car_count, 0)}{" "}
          คันติดเกณฑ์อย่างน้อย 1 เรื่อง
        </h3>
        <div
          className="flex flex-wrap gap-2"
          role="group"
          aria-label="กรองตามเรื่องที่ต้องจับตา"
        >
          <button
            type="button"
            className={chip(reason === null)}
            aria-pressed={reason === null}
            onClick={() => setReason(null)}
          >
            ทั้งหมด{" "}
            <span className="tabular-nums opacity-80">
              {num(data.cars.length, 0)}
            </span>
          </button>
          {data.reasons
            .filter((r) => r.count > 0)
            .map((r) => (
              <button
                key={r.code}
                type="button"
                className={chip(reason === r.code)}
                aria-pressed={reason === r.code}
                onClick={() => setReason(reason === r.code ? null : r.code)}
              >
                {r.label}{" "}
                <span className="font-semibold tabular-nums">
                  {num(r.count, 0)}
                </span>
              </button>
            ))}
        </div>
      </div>

      <div className="grid gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-medium">เรียงตามจำนวนเรื่องที่ติด</h3>
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
          {shown.map((c) => (
            <CarRow
              key={`${c.car_id}-${c.branch_company_id}`}
              car={c}
              onSelectCar={onSelectCar}
            />
          ))}
        </ul>

        {cars.length > PREVIEW_ROWS && (
          <Button
            variant="ghost"
            size="sm"
            className="justify-self-start"
            onClick={() => setShowAll((v) => !v)}
            aria-expanded={showAll}
          >
            {showAll
              ? `แสดงเฉพาะ ${PREVIEW_ROWS} คันแรก`
              : `แสดงทั้งหมด ${num(cars.length, 0)} คัน`}
            <ChevronDown
              className={cn("transition-transform", showAll && "rotate-180")}
            />
          </Button>
        )}
      </div>
    </div>
  );
}

function CarRow({
  car: c,
  onSelectCar,
}: {
  car: WatchCar;
  onSelectCar: (carId: number, branchCompanyId: string) => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelectCar(c.car_id, c.branch_company_id)}
        title="เลือกรถคันนี้"
        className="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-x-4 gap-y-1.5 px-1 py-2.5 text-left hover:bg-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring sm:grid-cols-[minmax(10rem,16rem)_minmax(0,1fr)_auto]"
      >
        <span className="min-w-0">
          <span className="block truncate font-medium">{carName(c)}</span>
          <span className="block truncate text-xs text-muted-foreground">
            {c.branch_company_name} · ค่าซ่อม {num(c.repair_total, 0)} บาท
          </span>
        </span>

        <ul className="col-span-2 row-start-2 grid min-w-0 gap-1 text-sm sm:col-span-1 sm:row-start-auto">
          {c.reasons.map((r) => (
            <li
              key={r.code}
              className="flex min-w-0 flex-wrap items-baseline gap-x-2"
            >
              <span
                className={cn(
                  "rounded px-1.5 py-px text-xs font-medium whitespace-nowrap",
                  REASON_TONE[r.code],
                )}
              >
                {r.label}
              </span>
              <span className="min-w-0 text-muted-foreground">{r.detail}</span>
            </li>
          ))}
        </ul>

        <span className="col-start-2 row-start-1 inline-flex items-center gap-0.5 justify-self-end text-xs text-primary sm:col-start-auto sm:row-start-auto">
          ดูรถ
          <ChevronRight
            className="size-3.5 transition-transform group-hover:translate-x-0.5"
            aria-hidden
          />
        </span>
      </button>
    </li>
  );
}
