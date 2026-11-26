import { ChevronDown, CircleHelp, FileSpreadsheet } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

import type { Schemas } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { downloadExcel, type ExportTable } from "@/lib/export-excel";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";

import { useChartHelp, type ChartHelp } from "./chart-help";
import { useExportFilters, useNoun } from "./export-context";
import { Kpi, KpiStrip } from "./Kpi";

type Downtime = Schemas["Downtime"];
type PartPrices = Schemas["PartPrices"];
type PartPrice = Schemas["PartPrice"];
type SelectCar = (carId: number, branchCompanyId: string) => void;

const PREVIEW_ROWS = 8;
const DAY_MS = 86_400_000;
const MONTHS_SHORT = [
  "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
  "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]; // prettier-ignore

const thaiDate = (iso: string) =>
  new Date(iso).toLocaleDateString("th-TH", {
    day: "numeric",
    month: "short",
    year: "2-digit",
  });

/* ---------- ส่วนประกอบร่วม ---------- */

function Panel({
  title,
  note,
  help,
  rows,
  unit,
  children,
}: {
  title: string;
  note?: ReactNode;
  /** วิธีอ่าน (ซ่อนไว้ กดเปิดได้) แบบเดียวกับ ChartCard */
  help?: ChartHelp;
  rows?: ExportTable;
  unit?: string;
  children: ReactNode;
}) {
  const filters = useExportFilters();
  const [helpOpen, setHelpOpen] = useState(false);
  const helpId = useId();
  return (
    <div className="grid min-w-0 gap-3 rounded-xl border bg-card px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-semibold">{title}</h3>
          {note && <p className="text-sm text-muted-foreground">{note}</p>}
          {help && (
            <button
              type="button"
              onClick={() => setHelpOpen((v) => !v)}
              aria-expanded={helpOpen}
              aria-controls={helpId}
              className="mt-1 inline-flex items-center gap-1 rounded text-sm font-medium text-primary hover:underline focus-visible:outline-2 focus-visible:outline-ring"
            >
              <CircleHelp className="size-3.5" aria-hidden />
              วิธีอ่านกราฟ
              <ChevronDown className={cn("size-3.5 transition-transform", helpOpen && "rotate-180")} aria-hidden />
            </button>
          )}
          {help && helpOpen && (
            <div id={helpId} className="mt-3 grid max-w-[80ch] gap-1.5 rounded-lg bg-steel px-3 py-2.5 text-sm">
              <p>
                <span className="font-semibold">กราฟนี้คือ </span>
                {help.meaning}
              </p>
              <ul className="grid list-disc gap-0.5 pl-5 text-muted-foreground marker:text-primary">
                {help.read.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        {rows && rows.length > 1 && (
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0 text-muted-foreground"
            onClick={() => downloadExcel({ title, unit, filters, rows })}
            aria-label={`ดาวน์โหลด Excel: ${title}`}
          >
            <FileSpreadsheet />
            Excel
          </Button>
        )}
      </div>
      {children}
    </div>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg bg-muted/50 px-4 py-6 text-center text-sm text-muted-foreground">
      {children}
    </p>
  );
}

function ShowMore({
  total,
  showAll,
  onToggle,
}: {
  total: number;
  showAll: boolean;
  onToggle: () => void;
}) {
  if (total <= PREVIEW_ROWS) return null;
  return (
    <Button variant="outline" size="sm" className="justify-self-start" onClick={onToggle}>
      {showAll ? "แสดงน้อยลง" : `แสดงทั้งหมด ${num(total, 0)} รายการ`}
    </Button>
  );
}

function CarButton({
  label,
  company,
  onClick,
}: {
  label: string;
  company: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="grid min-w-0 text-left hover:underline focus-visible:outline-2 focus-visible:outline-ring"
      title="ดูเฉพาะคันนี้"
    >
      <span className="truncate font-medium">{label}</span>
      {company && <span className="truncate text-xs text-muted-foreground">{company}</span>}
    </button>
  );
}

/** เส้นเล็กแสดงแนวโน้ม: ค่า null = ไม่มีข้อมูล (เส้นขาด) · baseline = เส้นประ · จุดเน้น = highlight */
export function Sparkline({
  values,
  baseline,
  highlight,
  label,
}: {
  values: (number | null)[];
  baseline?: number;
  highlight?: (v: number, i: number) => boolean;
  label: string;
}) {
  const W = 120;
  const H = 32;
  const P = 3;
  const nums = values.filter((v): v is number => v != null);
  if (nums.length === 0) return <span className="text-muted-foreground">-</span>;
  const lo = Math.min(...nums, baseline ?? Infinity);
  const hi = Math.max(...nums, baseline ?? -Infinity);
  const x = (i: number) => P + (values.length > 1 ? (i / (values.length - 1)) * (W - 2 * P) : (W - 2 * P) / 2);
  const y = (v: number) => (hi === lo ? H / 2 : H - P - ((v - lo) / (hi - lo)) * (H - 2 * P));
  let d = "";
  values.forEach((v, i) => {
    if (v == null) return;
    d += `${i > 0 && values[i - 1] != null ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
  });
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="block">
      {baseline != null && (
        <line x1={P} x2={W - P} y1={y(baseline)} y2={y(baseline)} stroke="var(--muted-foreground)" strokeDasharray="3 3" strokeWidth={1} opacity={0.6} />
      )}
      <path d={d} fill="none" stroke="var(--chart-1)" strokeWidth={1.75} strokeLinejoin="round" />
      {values.map((v, i) =>
        v == null ? null : (
          <circle
            key={i}
            cx={x(i)}
            cy={y(v)}
            r={highlight?.(v, i) ? 3.25 : 1.75}
            fill={highlight?.(v, i) ? "var(--signal)" : "var(--chart-1)"}
          />
        ),
      )}
    </svg>
  );
}

/* ---------- ⑤ ไทม์ไลน์รถหยุดซ่อม ---------- */

export function DowntimeTimeline({ data, onSelectCar }: { data: Downtime; onSelectCar: SelectCar }) {
  const HELP = useChartHelp();
  const noun = useNoun();
  const [showAll, setShowAll] = useState(false);
  const start = new Date(data.start).getTime();
  const end = new Date(data.end).getTime();
  const span = Math.max(end - start, 1);
  const pct = (t: number) => ((Math.min(Math.max(t, start), end) - start) / span) * 100;

  // เส้นแบ่งเดือน
  const ticks: { label: string; left: number }[] = [];
  const s = new Date(data.start);
  for (let d = new Date(s.getFullYear(), s.getMonth(), 1); d.getTime() < end; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) {
    ticks.push({ label: MONTHS_SHORT[d.getMonth()], left: pct(d.getTime()) });
  }

  const cars = showAll ? data.cars : data.cars.slice(0, PREVIEW_ROWS);
  const peak = Math.max(data.peak, 1);
  const rows: ExportTable = [
    ["บริษัท", noun, "เลขที่ใบแจ้งซ่อม", "อาการเสีย", "เริ่มหยุด", "กลับมาใช้งาน", "ชั่วโมง", "สถานะ"],
    ...data.cars.flatMap((c) =>
      c.spans.map((sp) => [
        c.company,
        c.label,
        sp.ref_no,
        sp.broke_reason,
        sp.start,
        sp.open ? "" : sp.end,
        (new Date(sp.end).getTime() - new Date(sp.start).getTime()) / 3_600_000,
        sp.open ? "ยังไม่ปิดงาน" : "ปิดงานแล้ว",
      ]),
    ),
  ];

  return (
    <Panel
      help={HELP.downtimeTimeline}
      title={`ไทม์ไลน์${noun}หยุดซ่อม`}
      note={`แต่ละแถบ = ช่วงที่หยุด (แจ้งซ่อม → ปิดงาน) · แถบลาย = ยังไม่ปิดงาน นับถึงตอนนี้ · แสดง ${num(data.cars.length, 0)} คันที่หยุดนานสุด`}
      rows={rows}
      unit="ชั่วโมง"
    >
      <KpiStrip className="sm:grid-cols-3 xl:grid-cols-3">
        <Kpi label={`${noun}ที่หยุดซ่อมในช่วงนี้`} value={num(data.car_count, 0)} unit="คัน" note={data.open_car_count ? `ยังหยุดอยู่ ${num(data.open_car_count, 0)} คัน` : undefined} />
        <Kpi label="ชั่วโมงหยุดรวม" value={num(data.hours, 0)} unit="ชม." />
        <Kpi
          label="หยุดพร้อมกันมากสุด"
          value={num(data.peak, 0)}
          unit="คัน"
          note={data.peak_date ? `วันที่ ${thaiDate(data.peak_date)}` : undefined}
          alert={data.peak >= 5}
        />
      </KpiStrip>

      {data.cars.length === 0 ? (
        <Empty>ไม่มี{noun}หยุดซ่อมในช่วงนี้</Empty>
      ) : (
        <div className="grid gap-1.5 overflow-x-auto">
          <div className="grid min-w-[640px] grid-cols-[minmax(9rem,14rem)_1fr] gap-x-3 gap-y-1.5 text-sm">
            {/* แถวบน: จำนวนรถที่หยุดในแต่ละวัน */}
            <div className="self-end text-xs text-muted-foreground">
              {noun}ที่หยุดต่อวัน (สูงสุด {num(data.peak, 0)})
            </div>
            <div className="relative h-10 border-b" aria-label="จำนวนรถที่หยุดในแต่ละวัน" role="img">
              {data.daily.map((n, i) =>
                n > 0 ? (
                  <div
                    key={i}
                    className="absolute bottom-0 bg-chart-1/60"
                    style={{
                      left: `${pct(start + i * DAY_MS)}%`,
                      width: `${Math.max(pct(start + (i + 1) * DAY_MS) - pct(start + i * DAY_MS), 0.15)}%`,
                      height: `${(n / peak) * 100}%`,
                    }}
                    title={`${thaiDate(new Date(start + i * DAY_MS).toISOString())}: ${n} คัน`}
                  />
                ) : null,
              )}
            </div>

            <div />
            <div className="relative h-4 text-xs text-muted-foreground">
              {ticks.map((t) => (
                <span key={t.left} className="absolute -translate-x-0 pl-1" style={{ left: `${t.left}%` }}>
                  {t.label}
                </span>
              ))}
            </div>

            {cars.map((c) => (
              <div key={`${c.car_id}-${c.branch_company_id}`} className="contents">
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <CarButton label={c.label} company={c.company} onClick={() => onSelectCar(c.car_id, c.branch_company_id)} />
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{num(c.hours, 0)} ชม.</span>
                </div>
                <div className="relative h-7 rounded bg-muted/50">
                  {ticks.map((t) => (
                    <div key={t.left} className="absolute inset-y-0 border-l border-dashed border-foreground/10" style={{ left: `${t.left}%` }} />
                  ))}
                  {c.spans.map((sp, i) => {
                    const left = pct(new Date(sp.start).getTime());
                    const width = Math.max(pct(new Date(sp.end).getTime()) - left, 0.4);
                    return (
                      <div
                        key={i}
                        className={cn(
                          "absolute inset-y-1 rounded-sm",
                          sp.open
                            ? "bg-[repeating-linear-gradient(45deg,var(--signal)_0_4px,color-mix(in_oklab,var(--signal)_45%,var(--card))_4px_8px)]"
                            : "bg-destructive/70",
                        )}
                        style={{ left: `${left}%`, width: `${width}%` }}
                        title={[
                          sp.ref_no || "ใบแจ้งซ่อม",
                          sp.broke_reason,
                          `${thaiDate(sp.start)} → ${sp.open ? "ยังไม่ปิดงาน" : thaiDate(sp.end)}`,
                        ]
                          .filter(Boolean)
                          .join("\n")}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
          <ShowMore total={data.cars.length} showAll={showAll} onToggle={() => setShowAll((v) => !v)} />
        </div>
      )}
    </Panel>
  );
}

/* ---------- ⑧ ราคาอะไหล่ที่เปลี่ยนไป ---------- */

export function PartPricesPanel({ data }: { data: PartPrices }) {
  const HELP = useChartHelp();
  const [dir, setDir] = useState<"up" | "down">("up");
  const [showAll, setShowAll] = useState(false);
  const list = data[dir];
  const parts = showAll ? list : list.slice(0, PREVIEW_ROWS);
  const exportRow = (p: PartPrice) => [
    p.stkcod, p.name, p.unit, p.first_date, p.first_price, p.last_date, p.last_price, p.change, p.period_qty, p.impact,
  ]; // prettier-ignore
  const rows: ExportTable = [
    ["รหัส", "ชื่ออะไหล่", "หน่วย", "จ่ายครั้งแรก", "ราคาเดิม/หน่วย", "จ่ายล่าสุด", "ราคาล่าสุด/หน่วย", "เปลี่ยน (%)", "จำนวนที่ใช้ในช่วงนี้", "จ่ายเพิ่ม/ลด (บาท)"],
    ...data.up.map(exportRow),
    ...data.down.map(exportRow),
  ];
  const chip = (active: boolean) =>
    cn(
      "rounded-full border px-3 py-1 text-sm transition-colors",
      active ? "border-primary bg-primary text-primary-foreground" : "bg-card hover:bg-muted",
    );

  return (
    <Panel
      help={HELP.partPrices}
      title="ราคาอะไหล่ที่เปลี่ยนไป"
      note={`ราคาต่อหน่วยจากใบจ่ายสินค้าภายใน · ราคาเดิม/ล่าสุด = ค่ากลางของการจ่าย 3 ครั้งแรก/ล่าสุด (ย้อนไปถึงปีก่อน) · ไม่นับรายการราคาตามงาน (ค่าแรง จ้างทำ) และที่เปลี่ยนไม่ถึง ${num(data.min_change, 0)}%`}
      rows={rows}
      unit="บาท"
    >
      {data.up.length + data.down.length === 0 ? (
        <Empty>ไม่พบอะไหล่ที่ราคาเปลี่ยนในช่วงนี้ (เทียบได้ {num(data.compared, 0)} รายการ)</Empty>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className={chip(dir === "up")} aria-pressed={dir === "up"} onClick={() => { setDir("up"); setShowAll(false); }}>
              ราคาขึ้น <span className="tabular-nums opacity-80">{num(data.up_count, 0)}</span>
            </button>
            <button type="button" className={chip(dir === "down")} aria-pressed={dir === "down"} onClick={() => { setDir("down"); setShowAll(false); }}>
              ราคาลง <span className="tabular-nums opacity-80">{num(data.down_count, 0)}</span>
            </button>
            <span className="text-sm text-muted-foreground">
              จาก {num(data.compared, 0)} รายการที่เทียบได้ · ผลต่อค่าใช้จ่ายในช่วงนี้สุทธิ{" "}
              <span className={cn("font-semibold tabular-nums", data.impact > 0 ? "text-destructive" : "text-foreground")}>
                {data.impact > 0 ? "+" : ""}
                {num(data.impact, 0)} บาท
              </span>
            </span>
          </div>
          {list.length === 0 ? (
            <Empty>ไม่มีรายการ</Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>อะไหล่</TableHead>
                  <TableHead className="text-right">ราคาเดิม</TableHead>
                  <TableHead className="text-right">ล่าสุด</TableHead>
                  <TableHead className="text-right">เปลี่ยน</TableHead>
                  <TableHead>ราคาแต่ละครั้ง</TableHead>
                  <TableHead className="text-right">ใช้ในช่วงนี้</TableHead>
                  <TableHead className="text-right">จ่ายเพิ่ม/ลด</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {parts.map((p) => (
                  <TableRow key={p.stkcod}>
                    <TableCell className="max-w-64">
                      <div className="truncate font-medium" title={p.name}>{p.name || p.stkcod}</div>
                      <div className="text-xs text-muted-foreground">{p.stkcod}</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {num(p.first_price, 2)}
                      <div className="text-xs text-muted-foreground">{thaiDate(p.first_date)}</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {num(p.last_price, 2)}
                      <div className="text-xs text-muted-foreground">{thaiDate(p.last_date)}</div>
                    </TableCell>
                    <TableCell className={cn("text-right font-medium tabular-nums", p.change > 0 ? "text-destructive" : "text-chart-1")}>
                      {p.change > 0 ? "+" : ""}
                      {num(p.change, 1)}%
                    </TableCell>
                    <TableCell>
                      <Sparkline values={p.prices} label={`ราคาต่อหน่วยแต่ละครั้งของ ${p.name}`} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {num(p.period_qty, 0)} {p.unit}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {p.impact > 0 ? "+" : ""}
                      {num(p.impact, 0)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <ShowMore total={list.length} showAll={showAll} onToggle={() => setShowAll((v) => !v)} />
        </>
      )}
    </Panel>
  );
}

