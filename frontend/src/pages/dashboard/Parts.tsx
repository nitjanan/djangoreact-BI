import { ChevronRight, FileSpreadsheet } from "lucide-react";

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
import { downloadExcel } from "@/lib/export-excel";
import { num } from "@/lib/format";

import { useExportFilters } from "./export-context";
import { Kpi, KpiStrip } from "./Kpi";

type Parts = Schemas["Parts"];
type Part = Schemas["Part"];

const TITLE = "อะไหล่ที่ใช้มากที่สุด";

const thaiDate = (iso: string) =>
  new Date(iso).toLocaleDateString("th-TH", {
    day: "numeric",
    month: "short",
    year: "2-digit",
  });

/** ชื่ออะไหล่ ถ้าไม่มีในรายการสินค้าของ webstock แสดงรหัสแทน */
function partName(p: { name: string; stkcod: string }) {
  return p.name || p.stkcod;
}

/** รายการอะไหล่ในใบแจ้งซ่อมหนึ่งใบ (ย่อไว้ กดเพื่อดู) */
export function PartsDetails({
  parts,
  amount,
}: {
  parts: Part[];
  amount: number;
}) {
  return (
    <details className="group text-sm">
      <summary className="inline-flex cursor-pointer list-none items-center gap-1 rounded text-xs text-primary hover:underline focus-visible:outline-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
        <ChevronRight
          className="size-3.5 transition-transform group-open:rotate-90"
          aria-hidden
        />
        อะไหล่ที่ใช้ {parts.length} รายการ · {num(amount, 0)} บาท
      </summary>
      <ul className="mt-1.5 grid gap-1 border-l-2 border-primary/25 pl-3">
        {parts.map((p, i) => (
          <li
            key={`${p.docnum}-${p.stkcod}-${i}`}
            className="flex flex-wrap items-baseline gap-x-2"
          >
            <span className="min-w-0 flex-1">
              {partName(p)}
              {p.name && p.stkcod && (
                <span className="ml-1 text-xs text-muted-foreground">
                  {p.stkcod}
                </span>
              )}
              <span className="ml-1 text-xs text-muted-foreground">
                {p.docnum}
              </span>
            </span>
            <span className="text-muted-foreground tabular-nums">
              {num(p.qty, p.qty % 1 ? 2 : 0)} {p.unit}
            </span>
            <span className="w-24 text-right tabular-nums">
              {num(p.amount, 2)}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

export function PartsSummary({
  data,
  carSelected,
}: {
  data: Parts;
  carSelected: boolean;
}) {
  const filters = useExportFilters();
  const coverage = data.job_count
    ? (data.jobs_with_parts / data.job_count) * 100
    : 0;

  if (data.jobs_with_parts === 0) {
    return (
      <p className="rounded-xl border bg-card px-4 py-6 text-center text-sm text-muted-foreground">
        ยังไม่มีข้อมูลอะไหล่ของใบแจ้งซ่อมในตัวกรองนี้
        <span className="mt-1 block text-xs">
          อะไหล่มาจากใบจ่ายสินค้าภายใน-อะไหล่ใน Express
          (คลังกรอกเลขที่ใบแจ้งซ่อมในช่อง note3)
        </span>
      </p>
    );
  }

  const exportExcel = () =>
    downloadExcel({
      title: TITLE,
      unit: "บาท",
      filters,
      rows: [
        [
          "รหัส",
          "ชื่ออะไหล่",
          "จำนวน",
          "หน่วย",
          "ใช้ในใบแจ้งซ่อม (ใบ)",
          "มูลค่า (บาท)",
        ],
        ...data.top.map((p) => [
          p.stkcod,
          p.name,
          p.qty,
          p.unit,
          p.jobs,
          p.amount,
        ]),
      ],
    });

  return (
    <div className="grid grid-cols-1 gap-4">
      <KpiStrip className="sm:grid-cols-3 xl:grid-cols-3">
        <Kpi
          label="ค่าอะไหล่รวม"
          value={num(data.amount, 0)}
          unit="บาท"
          note="จากใบจ่ายสินค้าภายใน (ของที่ซื้อมาเข้าคลังก่อนเสมอ)"
        />
        <Kpi
          label="ค่าอะไหล่เฉลี่ยต่อการซ่อม"
          value={num(data.amount_per_job, 0)}
          unit="บาท/ใบ"
        />
        <Kpi
          label="ใบแจ้งซ่อมที่มีข้อมูลอะไหล่"
          value={`${num(data.jobs_with_parts, 0)} / ${num(data.job_count, 0)}`}
          unit="ใบ"
          meter={coverage}
          note="นับเฉพาะใบจ่ายอะไหล่ที่คลังกรอกเลขที่ใบแจ้งซ่อม"
        />
      </KpiStrip>

      <div className="overflow-hidden rounded-xl border bg-card">
        <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
          <h3 className="text-sm font-semibold">{TITLE}</h3>
          <span className="text-sm text-muted-foreground">
            เรียงตามมูลค่า {data.top.length} อันดับแรก
          </span>
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
        <Table className="text-sm">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-10">#</TableHead>
              <TableHead>อะไหล่</TableHead>
              <TableHead className="text-right">จำนวน</TableHead>
              <TableHead className="text-right">ใช้ใน</TableHead>
              <TableHead className="text-right">
                มูลค่า
                <span className="block text-xs font-normal text-muted-foreground">
                  บาท
                </span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.top.map((p, i) => (
              <TableRow key={p.stkcod || p.name}>
                <TableCell className="text-muted-foreground tabular-nums">
                  {i + 1}
                </TableCell>
                <TableCell className="max-w-[28rem] whitespace-normal">
                  {partName(p)}
                  {p.name && p.stkcod && (
                    <span className="ml-1.5 text-xs text-muted-foreground">
                      {p.stkcod}
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right whitespace-nowrap tabular-nums">
                  {num(p.qty, p.qty % 1 ? 2 : 0)} {p.unit}
                </TableCell>
                <TableCell className="text-right whitespace-nowrap tabular-nums">
                  {p.jobs} ใบ
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {num(p.amount, 2)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {carSelected && data.jobs.length > 0 && (
        <div className="rounded-xl border bg-card">
          <h3 className="border-b px-4 py-2.5 text-sm font-semibold">
            ประวัติการซ่อมและอะไหล่ที่ใช้
          </h3>
          <ul className="divide-y">
            {data.jobs.map((j) => (
              <li key={j.ext_id} className="grid gap-1 px-4 py-3">
                <div className="flex flex-wrap items-baseline gap-x-3">
                  <span className="font-medium">{j.ref_no || "ไม่มีเลขที่"}</span>
                  <span className="text-sm text-muted-foreground">
                    {thaiDate(j.reported_at)}
                  </span>
                  {!j.closed && (
                    <span className="text-xs text-destructive">ยังไม่ปิดงาน</span>
                  )}
                  <span className="ml-auto text-sm font-medium tabular-nums">
                    {num(j.amount, 0)} บาท
                  </span>
                </div>
                {j.broke_reason && <p className="text-sm">{j.broke_reason}</p>}
                <PartsDetails parts={j.parts} amount={j.amount} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
