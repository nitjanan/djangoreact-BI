import { ArrowDown, ArrowUp } from "lucide-react";
import type { ReactNode } from "react";

import { clampPercent, num } from "@/lib/format";
import { cn } from "@/lib/utils";

/** แถบตัวเลขสรุป: แผ่นเดียว แบ่งช่องด้วยเส้น ไม่ใช่การ์ดแยกกัน */
export function KpiStrip({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        // จอมือถือ 2 คอลัมน์: ช่องสุดท้ายที่เหลือเดี่ยวให้ยืดเต็มแถว ไม่ให้เห็นช่องว่างสีเทา
        "grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-3 xl:grid-cols-5",
        "[&>:last-child:nth-child(odd)]:col-span-2 sm:[&>:last-child:nth-child(odd)]:col-span-1",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Kpi({
  label,
  value,
  unit,
  meter,
  note,
  alert = false,
  change,
}: {
  label: string;
  value: string;
  unit?: string;
  /** แถบ 0–100 */
  meter?: number | null;
  note?: string;
  /** ช่องสีแดง: ตัวเลขที่ต้องรีบจัดการ */
  alert?: boolean;
  /** เทียบกับช่วงเดียวกันของปีก่อน */
  change?: Change;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-1.5 bg-card px-4 py-3.5",
        alert && "bg-[color-mix(in_oklab,var(--destructive)_9%,var(--card))]",
      )}
    >
      <span
        className={cn(
          "text-sm text-muted-foreground",
          alert && "text-destructive",
        )}
      >
        {label}
      </span>
      <span
        className={cn(
          "font-heading text-2xl leading-none font-semibold tracking-tight tabular-nums",
          alert && "text-destructive",
        )}
      >
        {value}
        {unit && (
          <small className="ml-1 font-sans text-xs font-normal text-muted-foreground">
            {unit}
          </small>
        )}
      </span>
      {meter !== undefined && (
        <div
          className="mt-0.5 h-1 overflow-hidden rounded-full bg-muted"
          aria-hidden
        >
          <span
            className="block h-full rounded-full bg-signal"
            style={{ width: `${clampPercent(meter)}%` }}
          />
        </div>
      )}
      {note && <span className="text-xs text-muted-foreground">{note}</span>}
      {change && <ChangeNote {...change} />}
    </div>
  );
}

export type Change = {
  /** % ที่เปลี่ยน (null = เทียบไม่ได้) */
  pct: number | null;
  /** ทิศที่ดี: ต้นทุนลดลงดี, ชั่วโมงทำงานเพิ่มขึ้นดี, null = ไม่ตัดสินว่าดีหรือแย่ */
  better: "up" | "down" | null;
  /** ช่วงที่เทียบ เช่น "ม.ค.–มี.ค. 2025" */
  against: string;
};

/** ▲ 12% จาก ม.ค.–มี.ค. 2025 — สีตามว่าดีขึ้นหรือแย่ลง */
export function ChangeNote({
  pct,
  better,
  against,
  onDark = false,
}: Change & { onDark?: boolean }) {
  if (pct === null) {
    return (
      <span
        className={cn(
          "text-xs",
          onDark ? "text-plate-muted" : "text-muted-foreground",
        )}
      >
        ไม่มีข้อมูล {against} ให้เทียบ
      </span>
    );
  }
  const flat = Math.abs(pct) < 0.5;
  const up = pct > 0;
  const good = flat || better === null ? null : (better === "up") === up;
  const Icon = up ? ArrowUp : ArrowDown;
  return (
    <span
      className={cn(
        "inline-flex flex-wrap items-center gap-x-1 text-xs",
        onDark ? "text-plate-muted" : "text-muted-foreground",
      )}
    >
      <span
        className={cn(
          "inline-flex items-center gap-0.5 font-medium tabular-nums",
          good === true && (onDark ? "text-[#7fe0d6]" : "text-chart-1"),
          good === false && (onDark ? "text-signal" : "text-destructive"),
        )}
      >
        {flat ? (
          "เท่าเดิม"
        ) : (
          <>
            <Icon className="size-3" aria-hidden />
            <span className="sr-only">{up ? "เพิ่มขึ้น" : "ลดลง"}</span>
            {num(Math.abs(pct), Math.abs(pct) < 10 ? 1 : 0)}%
          </>
        )}
      </span>
      จาก {against}
    </span>
  );
}
