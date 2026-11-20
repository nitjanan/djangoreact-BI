import { ChevronDown, FileSpreadsheet } from "lucide-react";
import { useState } from "react";

import type { Schemas } from "@/api/client";
import { Button } from "@/components/ui/button";
import { downloadExcel } from "@/lib/export-excel";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";

import { useExportFilters, useNoun } from "./export-context";
import { Kpi, KpiStrip } from "./Kpi";

type Jobs = Schemas["Jobs"];
type Department = Schemas["JobDepartment"];

const TITLE = "งานที่ทำ แยกตามแผนกค่าใช้จ่าย";

/**
 * งานจากบันทึกการใช้รถ: แผนกค่าใช้จ่ายไหนใช้รถกี่ชั่วโมง (กดเพื่อดูรายละเอียดงาน)
 * ชั่วโมง = เวลาเริ่ม-จบของแต่ละงาน, กม. = เลขไมล์ของงาน, ครั้ง = จำนวนงานที่บันทึก
 */
export function JobsSummary({ data }: { data: Jobs }) {
  const filters = useExportFilters();
  const noun = useNoun();
  const [open, setOpen] = useState<string | null>(null);

  if (data.departments.length === 0) {
    return (
      <p className="rounded-xl border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
        ยังไม่มีบันทึกการใช้{noun}ในช่วงนี้
      </p>
    );
  }

  const max = Math.max(...data.departments.map((d) => d.hours), 1e-9);
  const exportExcel = () =>
    downloadExcel({
      title: TITLE,
      unit: "ชั่วโมง, กม., ครั้ง",
      filters,
      rows: [
        [
          "แผนกค่าใช้จ่าย",
          "รายละเอียดงาน",
          "ชั่วโมงทำงาน",
          "ระยะทาง (กม.)",
          "จำนวนครั้ง",
          `จำนวน${noun} (คัน)`,
        ],
        ...data.departments.flatMap((d) =>
          d.jobs.map((j) => [
            d.name,
            j.job,
            round2(j.hours),
            round2(j.km),
            j.trips,
            j.cars,
          ]),
        ),
      ],
    });

  return (
    <div className="grid grid-cols-1 gap-4">
      <KpiStrip className="sm:grid-cols-3 xl:grid-cols-3">
        <Kpi label="ชั่วโมงทำงานรวม" value={num(data.hours, 0)} unit="ชม." />
        <Kpi
          label="ระยะทางรวม (ตามเลขไมล์ของงาน)"
          value={num(data.km, 0)}
          unit="กม."
        />
        <Kpi label="งานที่บันทึก" value={num(data.trips, 0)} unit="ครั้ง" />
      </KpiStrip>

      <div className="grid min-w-0 grid-cols-1 gap-1 rounded-xl border bg-card px-4 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-medium">
            ชั่วโมงทำงานตามแผนกค่าใช้จ่าย · กดเพื่อดูรายละเอียดงาน
          </h3>
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
          {data.departments.map((d) => (
            <DepartmentRow
              key={d.name}
              dept={d}
              share={data.hours > 0 ? (d.hours / data.hours) * 100 : 0}
              width={(d.hours / max) * 100}
              open={open === d.name}
              onToggle={() => setOpen(open === d.name ? null : d.name)}
              noun={noun}
            />
          ))}
        </ul>
      </div>
    </div>
  );
}

function DepartmentRow({
  dept: d,
  share,
  width,
  open,
  onToggle,
  noun,
}: {
  dept: Department;
  share: number;
  width: number;
  open: boolean;
  onToggle: () => void;
  noun: string;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1.5 px-1 py-2.5 text-left hover:bg-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring sm:grid-cols-[minmax(9rem,14rem)_minmax(0,1fr)_auto]"
      >
        <span className="min-w-0">
          <span
            className={cn(
              "block truncate font-medium",
              !d.assigned && "text-muted-foreground italic",
            )}
          >
            {d.name}
          </span>
          <span className="block truncate text-xs text-muted-foreground">
            {num(d.trips, 0)} ครั้ง · {num(d.cars, 0)} คัน
            {d.km > 0 && ` · ${num(d.km, 0)} กม.`}
          </span>
        </span>

        <span className="col-span-2 row-start-2 grid min-w-0 gap-1 sm:col-span-1 sm:row-start-auto">
          <span
            className="h-2 overflow-hidden rounded-full bg-muted"
            aria-hidden
          >
            <span
              className={cn(
                "block h-full rounded-full",
                d.assigned ? "bg-primary" : "bg-muted-foreground/40",
              )}
              style={{ width: `${Math.max(width, 1)}%` }}
            />
          </span>
        </span>

        <span className="col-start-2 row-start-1 inline-flex items-center gap-2 justify-self-end text-sm whitespace-nowrap tabular-nums sm:col-start-auto sm:row-start-auto">
          <span className="font-semibold">{num(d.hours, 0)} ชม.</span>
          <span className="w-10 text-right text-xs text-muted-foreground">
            {share.toFixed(0)}%
          </span>
          <ChevronDown
            className={cn(
              "size-4 text-muted-foreground transition-transform",
              open && "rotate-180",
            )}
            aria-hidden
          />
        </span>
      </button>

      {open && (
        <div className="overflow-x-auto pb-3 pl-1">
          <table className="w-full min-w-[32rem] text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th className="py-1.5 pr-3 font-normal">รายละเอียดงาน</th>
                <th className="py-1.5 pr-3 text-right font-normal">ชั่วโมง</th>
                <th className="py-1.5 pr-3 text-right font-normal">กม.</th>
                <th className="py-1.5 pr-3 text-right font-normal">ครั้ง</th>
                <th className="py-1.5 text-right font-normal">{noun} (คัน)</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {d.jobs.map((j) => (
                <tr key={j.job}>
                  <td className="py-1.5 pr-3">{j.job}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">
                    {num(j.hours, 1)}
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">
                    {j.km > 0 ? num(j.km, 0) : "-"}
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">
                    {num(j.trips, 0)}
                  </td>
                  <td className="py-1.5 text-right tabular-nums">
                    {num(j.cars, 0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </li>
  );
}

const round2 = (v: number) => Math.round(v * 100) / 100;
