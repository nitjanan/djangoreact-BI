import { ArrowDown, ArrowUp, type LucideIcon } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import { clampPercent, num } from "@/lib/format";
import { cn } from "@/lib/utils";

/** แถบตัวเลขสรุป: แผ่นเดียว แบ่งช่องด้วยเส้น ไม่ใช่การ์ดแยกกัน */
export function KpiStrip({
  className,
  onDark = false,
  children,
}: {
  className?: string;
  /** วางบนแผงหัวสีเข้ม: ไม่มีกรอบ ตัวเลขสีขาว */
  onDark?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        onDark
          ? "grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 xl:grid-cols-5"
          : // จอมือถือ 2 คอลัมน์: ช่องสุดท้ายที่เหลือเดี่ยวให้ยืดเต็มแถว ไม่ให้เห็นช่องว่างสีเทา
            "grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-3 xl:grid-cols-5 [&>:last-child:nth-child(odd)]:col-span-2 sm:[&>:last-child:nth-child(odd)]:col-span-1",
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
  onDark = false,
  headline = false,
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
  /** วางบนแผงหัวสีเข้ม (ใช้คู่กับ KpiStrip onDark) */
  onDark?: boolean;
  /** ตัวเลขหลักของแถบ: ตัวใหญ่ มีขีดสีด้านซ้าย */
  headline?: boolean;
}) {
  const muted = onDark ? "text-plate-muted" : "text-muted-foreground";
  return (
    <div
      className={cn(
        "flex min-w-0 flex-col gap-1.5",
        !onDark && "bg-card px-4 py-3.5",
        headline && "justify-center border-l-4 border-signal pl-4",
        alert && "bg-[color-mix(in_oklab,var(--destructive)_9%,var(--card))]",
      )}
    >
      <span className={cn("text-sm", muted, alert && "text-destructive")}>
        {label}
      </span>
      <span
        className={cn(
          "font-heading leading-none font-semibold tracking-tight tabular-nums",
          headline ? "text-5xl md:text-6xl" : "text-2xl",
          onDark && "text-white",
          alert && "text-destructive",
        )}
      >
        {value}
        {unit && (
          <small className={cn("ml-1 font-sans text-xs font-normal", muted)}>
            {unit}
          </small>
        )}
      </span>
      {meter !== undefined && (
        <div
          className={cn(
            "mt-0.5 h-1 overflow-hidden rounded-full",
            onDark ? "bg-white/15" : "bg-muted",
          )}
          aria-hidden
        >
          <span
            className="block h-full rounded-full bg-signal"
            style={{ width: `${clampPercent(meter)}%` }}
          />
        </div>
      )}
      {note && <span className={cn("text-xs", muted)}>{note}</span>}
      {change && <ChangeNote {...change} onDark={onDark} />}
    </div>
  );
}

/** การ์ดตัวเลขสรุป: ไอคอน + ชื่อ + ตัวเลข + บรรทัดเทียบ
 *  headline = ตัวเลขหลัก (ตัวเลขโต มีแถบสีด้านบน) */
export function StatCard({
  icon: Icon,
  tone = "var(--chart-1)",
  label,
  value,
  unit,
  meter,
  note,
  change,
  headline = false,
  className,
}: {
  icon: LucideIcon;
  /** สีของไอคอน/แถบ (ค่า CSS) */
  tone?: string;
  label: string;
  value: string;
  unit?: string;
  meter?: number | null;
  note?: ReactNode;
  change?: Change;
  headline?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative flex min-w-0 flex-col gap-2 overflow-hidden rounded-xl border bg-card p-4 shadow-xs",
        className,
      )}
      style={{ "--tone": tone } as CSSProperties}
    >
      {headline && (
        <span
          className="absolute inset-x-0 top-0 h-1 bg-(--tone)"
          aria-hidden
        />
      )}
      <div className="flex items-center gap-2.5">
        <span
          className="grid size-8 shrink-0 place-items-center rounded-lg bg-[color-mix(in_oklab,var(--tone)_14%,transparent)] text-(--tone)"
          aria-hidden
        >
          <Icon className="size-4" />
        </span>
        <span
          className={cn(
            "text-sm leading-tight",
            headline ? "font-medium text-foreground" : "text-muted-foreground",
          )}
        >
          {label}
        </span>
      </div>
      <div
        className={cn(
          "mt-1 font-heading leading-none font-semibold tracking-tight tabular-nums",
          headline ? "text-4xl" : "text-[1.75rem]",
        )}
      >
        {value}
        {unit && (
          <small
            className={cn(
              "ml-1.5 font-sans font-normal text-muted-foreground",
              headline ? "text-base" : "text-xs",
            )}
          >
            {unit}
          </small>
        )}
      </div>
      {meter !== undefined && (
        <div
          className="h-1.5 overflow-hidden rounded-full bg-muted"
          aria-hidden
        >
          <span
            className="block h-full rounded-full bg-(--tone)"
            style={{ width: `${clampPercent(meter)}%` }}
          />
        </div>
      )}
      {note && (
        <span
          className={cn(
            "text-muted-foreground",
            headline ? "text-sm" : "text-xs",
          )}
        >
          {note}
        </span>
      )}
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
