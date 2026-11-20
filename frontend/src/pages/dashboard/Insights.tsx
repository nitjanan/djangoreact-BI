import {
  ArrowRight,
  ChevronRight,
  CircleAlert,
  Database,
  Lightbulb,
  TrendingDown,
  TriangleAlert,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { Schemas } from "@/api/client";
import { cn } from "@/lib/utils";

import { useNoun } from "./export-context";

type Item = Schemas["InsightItem"];
type SelectCar = (carId: number, branchCompanyId: string) => void;

const SEVERITY: Record<
  Item["severity"],
  { label: string; icon: LucideIcon; tone: string; accent: string; bar: string }
> = {
  high: {
    label: "ต้องดูด่วน",
    icon: CircleAlert,
    tone: "bg-signal/15 text-[#a33a1c]",
    accent: "shadow-[inset_3px_0_0_var(--color-signal)]",
    bar: "bg-signal",
  },
  medium: {
    label: "ควรตรวจสอบ",
    icon: TriangleAlert,
    tone: "bg-[#eda100]/15 text-[#7a5300]",
    accent: "shadow-[inset_3px_0_0_#eda100]",
    bar: "bg-[#eda100]",
  },
  good: {
    label: "ดีขึ้น",
    icon: TrendingDown,
    tone: "bg-primary/10 text-primary",
    accent: "shadow-[inset_3px_0_0_var(--color-primary)]",
    bar: "bg-primary",
  },
  info: {
    label: "คุณภาพข้อมูล",
    icon: Database,
    tone: "bg-muted text-muted-foreground",
    accent: "shadow-[inset_3px_0_0_var(--color-border)]",
    bar: "bg-muted-foreground",
  },
};

/**
 * สรุปและข้อสังเกตอัตโนมัติ (คำนวณตามกฎที่ backend: dbapp/services/insights.py)
 * การ์ดแต่ละใบ: เกิดอะไรขึ้น -> ตัวเลขเทียบเป็นแถบ -> รถที่เกี่ยวข้อง (กดดูได้) -> ควรทำอะไร
 */
export function Insights({
  data,
  onSelectCar,
}: {
  data: Schemas["Insights"];
  onSelectCar: SelectCar;
}) {
  return (
    <div className="grid gap-3">
      <ul className="grid grid-cols-[repeat(auto-fit,minmax(13rem,1fr))] gap-3">
        {data.overview.map((f) => (
          <FactTile key={f.label} fact={f} />
        ))}
      </ul>

      {data.items.length > 0 ? (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.items.map((item) => (
            <InsightCard
              key={item.title}
              item={item}
              onSelectCar={onSelectCar}
            />
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          ไม่พบจุดผิดปกติตามเกณฑ์ในตัวกรองนี้
        </p>
      )}
    </div>
  );
}

/** ตัวเลขสรุป 1 ช่อง: หัวข้อ -> ตัวเลขใหญ่ -> คำอธิบาย (+ แถบสัดส่วน) */
function FactTile({ fact: f }: { fact: Schemas["OverviewFact"] }) {
  return (
    <li className="grid min-w-0 content-start gap-1 rounded-xl border bg-card px-4 py-3.5">
      <span className="text-sm text-muted-foreground">{f.label}</span>
      <span
        className={cn(
          "font-sans text-xl leading-tight font-semibold tabular-nums",
          f.tone === "bad" && "text-[#a33a1c]",
          f.tone === "good" && "text-primary",
        )}
      >
        {f.value}
      </span>
      {f.share != null && (
        <span
          className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted"
          aria-hidden
        >
          <span
            className="block h-full rounded-full bg-primary"
            style={{ width: `${Math.min(Math.max(f.share, 2), 100)}%` }}
          />
        </span>
      )}
      {f.note && (
        <span className="text-sm leading-snug text-muted-foreground">
          {f.note}
        </span>
      )}
    </li>
  );
}

function InsightCard({
  item,
  onSelectCar,
}: {
  item: Item;
  onSelectCar: SelectCar;
}) {
  const s = SEVERITY[item.severity];
  const noun = useNoun();
  // มีตัวเลขเทียบ/รายการแล้ว ไม่ต้องแสดงข้อความยาวซ้ำ
  const showDetail = !item.compare && item.points.length === 0;

  return (
    <li
      className={cn(
        "flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-4",
        s.accent,
      )}
    >
      <div className="grid gap-1.5">
        <span
          className={cn(
            "inline-flex w-fit items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium",
            s.tone,
          )}
        >
          <s.icon className="size-3.5" aria-hidden />
          {s.label}
        </span>
        <h3 className="font-sans text-base leading-snug font-semibold">
          {item.title}
        </h3>
      </div>

      {item.compare && <CompareBars compare={item.compare} bar={s.bar} />}

      {showDetail && (
        <p className="text-sm leading-relaxed text-muted-foreground">
          {item.detail}
        </p>
      )}

      {item.points.length > 0 && (
        <ul className="grid gap-1 text-sm">
          {item.points.map((p) => (
            <li key={p} className="flex gap-2">
              <span
                aria-hidden
                className="mt-[0.55em] size-1 shrink-0 rounded-full bg-muted-foreground"
              />
              {p}
            </li>
          ))}
        </ul>
      )}

      {item.cars.length > 0 && (
        <div className="grid gap-1">
          <span className="text-xs text-muted-foreground">
            {item.kind === "anomaly" ? `มาจาก${noun}` : `${noun}ที่เข้าข่าย`}{" "}
            (กดเพื่อดูคันนั้น)
          </span>
          <ul className="divide-y rounded-lg border">
            {item.cars.map((c) => (
              <li key={`${c.name}-${c.company}`}>
                <button
                  type="button"
                  disabled={!c.target}
                  onClick={() =>
                    c.target &&
                    onSelectCar(c.target.car_id, c.target.branch_company_id)
                  }
                  className="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 px-2.5 py-1.5 text-left text-sm hover:bg-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring disabled:cursor-default disabled:hover:bg-transparent"
                >
                  <span className="grid min-w-0">
                    <span className="truncate">
                      {c.name}
                      {c.company && (
                        <span className="text-xs text-muted-foreground">
                          {" "}
                          · {c.company}
                        </span>
                      )}
                    </span>
                    <span className="truncate text-xs text-muted-foreground tabular-nums">
                      {c.value}
                    </span>
                  </span>
                  {c.target && (
                    <ChevronRight
                      className="size-3.5 text-primary transition-transform group-hover:translate-x-0.5"
                      aria-hidden
                    />
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {item.hint && (
        <p className="flex gap-1.5 text-sm text-muted-foreground">
          <Lightbulb
            className="mt-0.5 size-3.5 shrink-0 text-[#b07800]"
            aria-hidden
          />
          <span>
            <span className="sr-only">ควรทำ: </span>
            {item.hint}
          </span>
        </p>
      )}

      {item.target && item.cars.length === 0 && (
        <button
          type="button"
          onClick={() =>
            item.target &&
            onSelectCar(item.target.car_id, item.target.branch_company_id)
          }
          className="mt-auto inline-flex w-fit items-center gap-1 rounded text-sm font-medium text-primary hover:underline focus-visible:outline-2 focus-visible:outline-ring"
        >
          {item.action ?? "ดูคันนี้"}
          <ArrowRight className="size-3.5" aria-hidden />
        </button>
      )}
    </li>
  );
}

/** ตัวเลขที่ผิดปกติเทียบกับค่าปกติ เป็นแถบยาวตามสัดส่วน */
function CompareBars({
  compare: c,
  bar,
}: {
  compare: NonNullable<Item["compare"]>;
  bar: string;
}) {
  const max = Math.max(c.value, c.baseline, 1e-9);
  const rows = [
    {
      label: c.value_label,
      text: c.value_text,
      value: c.value,
      tone: bar,
      strong: true,
    },
    {
      label: c.baseline_label,
      text: c.baseline_text,
      value: c.baseline,
      tone: "bg-muted-foreground/30",
      strong: false,
    },
  ];
  return (
    <dl className="grid min-w-0 gap-2">
      {rows.map((r) => (
        <div key={r.label} className="grid min-w-0 gap-1">
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <dt className="min-w-0 truncate text-muted-foreground">
              {r.label}
            </dt>
            <dd
              className={cn(
                "whitespace-nowrap tabular-nums",
                r.strong && "font-semibold",
              )}
            >
              {r.text}
            </dd>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-muted"
            aria-hidden
          >
            <span
              className={cn("block h-full rounded-full", r.tone)}
              style={{ width: `${Math.max((r.value / max) * 100, 2)}%` }}
            />
          </div>
        </div>
      ))}
    </dl>
  );
}
