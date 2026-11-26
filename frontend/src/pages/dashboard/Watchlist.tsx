import { ChevronDown, FileSpreadsheet } from "lucide-react";
import { useState } from "react";

import type { Schemas } from "@/api/client";
import { Button } from "@/components/ui/button";
import { downloadExcel } from "@/lib/export-excel";
import { num } from "@/lib/format";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

import { useExportFilters, useNoun } from "./export-context";

type Watchlist = Schemas["Watchlist"];
type WatchCar = Schemas["WatchCar"];
type ReasonCode = WatchCar["reasons"][number]["code"];

const PREVIEW_ROWS = 8;

// สีตามความรุนแรงของเหตุผล: แดง = ต้องจัดการ, เหลือง = ติดตาม
const REASON_TONE: Record<ReasonCode, string> = {
  stale: "bg-destructive/12 text-destructive",
  cost: "bg-destructive/12 text-destructive",
  replace: "bg-chart-4/20 text-[color-mix(in_oklab,var(--chart-4)_55%,black)]",
  repeat: "bg-chart-4/20 text-[color-mix(in_oklab,var(--chart-4)_55%,black)]",
  failure: "bg-chart-4/20 text-[color-mix(in_oklab,var(--chart-4)_55%,black)]",
  fuel: "bg-muted text-muted-foreground",
  fuel_spike: "bg-chart-4/20 text-[color-mix(in_oklab,var(--chart-4)_55%,black)]",
  low_use: "bg-chart-1/15 text-[color-mix(in_oklab,var(--chart-1)_55%,black)]",
};

// สีของสัญญาณ "ควรพิจารณาเปลี่ยน" ใช้ชุดสีเดียวกับป้ายเหตุผล
const SIGNAL_TONE: Record<string, string> = {
  rising: REASON_TONE.cost,
  costly: REASON_TONE.cost,
  downtime: REASON_TONE.failure,
  failure: REASON_TONE.failure,
  old: "bg-chart-1/15 text-[color-mix(in_oklab,var(--chart-1)_55%,black)]",
};

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
  const noun = useNoun();
  const TITLE = `${noun}ที่ต้องจับตา`;

  if (data.cars.length === 0) {
    return (
      <p className="rounded-xl border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
        ไม่มี{noun}ที่ผิดปกติในตัวกรองนี้
        {!data.compared && (
          <span className="mt-1 block text-xs">
            {noun}น้อยกว่า 5 คัน จึงไม่เทียบค่าซ่อม การเสีย และน้ำมันกับ{noun}ส่วนใหญ่
          </span>
        )}
      </p>
    );
  }

  // ตัวกรองเหตุผล: เรียงตามค่าหลักของเหตุผลนั้น (reason.sort มากไปน้อย)
  const sortKey = (c: WatchCar) =>
    c.reasons.find((r) => r.code === reason)?.sort ?? 0;
  const cars = reason
    ? data.cars
        .filter((c) => c.reasons.some((r) => r.code === reason))
        .sort((a, b) => sortKey(b) - sortKey(a))
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
          `รหัส${noun}`,
          `ชื่อ${noun}`,
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
          <h3 className="text-sm font-medium">{SORT_NOTE[reason ?? "all"]}</h3>
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

        <WatchTable
          cars={shown}
          months={data.months}
          reason={reason}
          onSelectCar={onSelectCar}
        />

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

// หัวคอลัมน์ค่าหลักของแต่ละตัวกรอง (ค่าและคำอธิบายมาจาก reason.value / reason.note)
const METRIC_HEAD: Record<ReasonCode, string> = {
  stale: "ค้างซ่อม",
  cost: "ค่าซ่อม/ชม.",
  replace: "ค่าซ่อม/ปี",
  repeat: "แจ้งซ่อมซ้ำ",
  failure: "เสีย",
  fuel: "อัตราน้ำมัน",
  fuel_spike: "น้ำมันเกินปกติ",
  low_use: "การใช้งาน",
};

const SORT_NOTE: Record<ReasonCode | "all", string> = {
  all: "เรียงตามจำนวนเรื่องที่ติด · กดแถวเพื่อดูคันนั้น",
  stale: "เรียงตามจำนวนวันที่ค้างซ่อม · กดแถวเพื่อดูคันนั้น",
  cost: "เรียงตามค่าซ่อม/ชม. เทียบกับคันส่วนใหญ่ · กดแถวเพื่อดูคันนั้น",
  replace:
    "เรียงตามค่าซ่อมต่อปี (ค่าซ่อมเฉลี่ยรายเดือนของเดือนที่จบแล้ว × 12 ใช้เทียบกับราคารถใหม่) · กดแถวเพื่อดูคันนั้น",
  repeat: "เรียงตามจำนวนครั้งที่แจ้งซ่อมซ้ำ · กดแถวเพื่อดูคันนั้น",
  failure: "เรียงตามความถี่ที่เสียเทียบกับคันส่วนใหญ่ · กดแถวเพื่อดูคันนั้น",
  fuel: "เรียงตามอัตราน้ำมันเทียบกับคันส่วนใหญ่ · กดแถวเพื่อดูคันนั้น",
  fuel_spike:
    "เดือนที่ใช้น้ำมันต่องานสูงกว่าปกติของคันนั้นเอง 1.3 เท่าขึ้นไป · เรียงตามลิตรที่เกิน (น้ำมันรั่ว เครื่องผิดปกติ หรือบันทึกไม่ครบ) · กดแถวเพื่อดูคันนั้น",
  low_use:
    "จอดนิ่ง (ไม่มีงานและไม่เติมน้ำมัน 2 เดือนล่าสุดขึ้นไป) อยู่บนสุด ตามด้วยคันที่ชั่วโมงต่ำกว่า 30% ของคันส่วนใหญ่ · กดแถวเพื่อดูคันนั้น",
};

const carName = (c: WatchCar) =>
  [c.code, c.name].filter(Boolean).join(" ") || "ไม่ระบุ";

const MONTH_SHORT: Record<string, string> = {
  มกราคม: "ม.ค.", กุมภาพันธ์: "ก.พ.", มีนาคม: "มี.ค.", เมษายน: "เม.ย.",
  พฤษภาคม: "พ.ค.", มิถุนายน: "มิ.ย.", กรกฎาคม: "ก.ค.", สิงหาคม: "ส.ค.",
  กันยายน: "ก.ย.", ตุลาคม: "ต.ค.", พฤศจิกายน: "พ.ย.", ธันวาคม: "ธ.ค.",
}; // prettier-ignore

/** กราฟแท่งค่าซ่อมรายเดือน: แท่งสีส้ม = เดือนที่สูงสุด */
function MonthlyBars({ values, months }: { values: number[]; months: string[] }) {
  const top = Math.max(...values, 0);
  if (top <= 0) return <span className="text-xs text-muted-foreground">ไม่มีค่าซ่อม</span>;
  const peak = values.indexOf(top);
  return (
    <div className="grid w-44 gap-0.5">
      <div
        className="flex h-8 items-end gap-px"
        role="img"
        aria-label={values.map((v, i) => `${months[i]} ${num(v, 0)} บาท`).join(", ")}
      >
        {values.map((v, i) => (
          <span
            key={i}
            title={`${months[i]}: ${num(v, 0)} บาท`}
            className={cn("min-w-0 flex-1 rounded-t-sm", i === peak ? "bg-signal" : "bg-chart-1/55")}
            style={{ height: v > 0 ? `${Math.max((v / top) * 100, 4)}%` : "1px" }}
          />
        ))}
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>{MONTH_SHORT[months[0]] ?? months[0]}</span>
        <span>
          สูงสุด {MONTH_SHORT[months[peak]] ?? months[peak]} {num(values[peak], 0)}
        </span>
        <span>{MONTH_SHORT[months[months.length - 1]] ?? months[months.length - 1]}</span>
      </div>
    </div>
  );
}

function Chip({ tone, label, value }: { tone: string; label: string; value?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-1 rounded px-1.5 py-px text-xs whitespace-nowrap",
        tone,
      )}
    >
      <span className="font-medium">{label}</span>
      {value && <span className="font-semibold tabular-nums">{value}</span>}
    </span>
  );
}

/** ตารางรถที่ต้องจับตา: ทุกตัวกรองใช้รูปแบบเดียวกัน ต่างกันที่คอลัมน์ค่าหลักและป้าย */
function WatchTable({
  cars,
  months,
  reason,
  onSelectCar,
}: {
  cars: WatchCar[];
  months: string[];
  reason: ReasonCode | null;
  onSelectCar: (carId: number, branchCompanyId: string) => void;
}) {
  const metricHead = reason ? METRIC_HEAD[reason] : "ค่าซ่อมรวม";
  const chipsHead =
    reason === null ? "เรื่องที่ติด" : reason === "replace" ? "สัญญาณ" : "เรื่องอื่นที่ติด";
  return (
    <div className="border-t">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>คัน</TableHead>
            <TableHead className="text-right">อายุ</TableHead>
            <TableHead className="text-right">{metricHead}</TableHead>
            <TableHead>{chipsHead}</TableHead>
            <TableHead>ค่าซ่อมรายเดือน</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {cars.map((c) => {
            const active = reason ? c.reasons.find((r) => r.code === reason) : undefined;
            const others = c.reasons.filter((r) => r.code !== reason);
            return (
              <TableRow
                key={`${c.car_id}-${c.branch_company_id}`}
                className="cursor-pointer"
                onClick={() => onSelectCar(c.car_id, c.branch_company_id)}
              >
                <TableCell className="max-w-56">
                  <button
                    type="button"
                    className="block max-w-full truncate text-left font-medium hover:underline focus-visible:outline-2 focus-visible:outline-ring"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectCar(c.car_id, c.branch_company_id);
                    }}
                  >
                    {carName(c)}
                  </button>
                  <div className="truncate text-xs text-muted-foreground">
                    {[c.branch_company_name, c.car_type_name].filter(Boolean).join(" · ")}
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {c.age != null ? `${c.age} ปี` : "-"}
                </TableCell>
                <TableCell className="w-44 min-w-36 text-right whitespace-normal">
                  <div className="font-semibold whitespace-nowrap tabular-nums">
                    {active ? active.value : `${num(c.repair_total, 0)} บาท`}
                  </div>
                  {active && reason !== "replace" && active.note && (
                    <div className="text-xs leading-snug text-muted-foreground">
                      {active.note}
                    </div>
                  )}
                </TableCell>
                <TableCell className="min-w-56 whitespace-normal">
                  <div className="flex max-w-80 flex-wrap gap-1">
                    {reason === "replace" && c.replace ? (
                      <>
                        {c.replace.signals.map((s) => (
                          <Chip
                            key={s.code}
                            tone={SIGNAL_TONE[s.code] ?? REASON_TONE.fuel}
                            label={s.label}
                            value={s.value}
                          />
                        ))}
                        {c.replace.covered.map((label) => {
                          const code = c.reasons.find((r) => r.label === label)?.code;
                          return (
                            <Chip
                              key={label}
                              tone={code ? REASON_TONE[code] : REASON_TONE.fuel}
                              label={label}
                            />
                          );
                        })}
                      </>
                    ) : others.length ? (
                      others.map((r) => (
                        <Chip
                          key={r.code}
                          tone={REASON_TONE[r.code]}
                          label={r.label}
                          value={r.value}
                        />
                      ))
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  {c.monthly.length > 1 ? (
                    <MonthlyBars values={c.monthly} months={months} />
                  ) : (
                    "-"
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
