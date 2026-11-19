import { ChevronDown, FileSpreadsheet, Search, TriangleAlert } from 'lucide-react'
import { useId, useState } from 'react'

import type { Schemas } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { downloadExcel } from '@/lib/export-excel'
import { num } from '@/lib/format'
import { cn } from '@/lib/utils'

import { useExportFilters } from './export-context'

const TITLE = 'รายการที่ยังจับคู่ทะเบียนรถ/เครื่องจักร/หน่วยงานไม่ได้'

const normalize = (s: string) => s.toLowerCase().replace(/[\s-]/g, '')

/**
 * ค่าใช้จ่ายที่ remark ในเอกสารจับคู่กับรถใน webstock ไม่ได้ (ทั้งปี ทุกแผนก)
 * แผงสีปะการัง (--signal) แบบคำเตือน ย่อไว้เป็นค่าเริ่มต้น เห็นแค่จำนวนและยอดรวม กดขยายเพื่อดูรายการ
 */
export function UnmatchedTable({ data }: { data: Schemas['Unmatched'] }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const filters = useExportFilters()
  const bodyId = useId()

  const q = normalize(query)
  const rows = data.rows.filter((r) => !q || normalize(r.remark).includes(q))

  const exportExcel = () =>
    downloadExcel({
      title: TITLE,
      unit: 'บาท, ลิตร',
      filters,
      rows: [
        ['หมายเหตุในเอกสาร', 'บริษัท', 'ค่าซ่อม (บาท)', 'น้ำมันดีเซล (ลิตร)'],
        ...data.rows.map((r) => [r.remark, r.branch_company_name, r.repair_amount, r.oil_qty]),
        ['รวม', '', data.repair_total, data.oil_total],
      ],
    })

  return (
    <section
      aria-label={TITLE}
      className="rounded-xl border border-signal/40 bg-signal/10 text-foreground"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <TriangleAlert className="size-5 shrink-0 text-signal" aria-hidden />
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold">{TITLE}</h2>
          <p className="text-sm text-muted-foreground">
            ทั้งปี {data.rows.length} รายการ · ค่าซ่อม{' '}
            <span className="font-semibold tabular-nums">{num(data.repair_total, 0)}</span> บาท
            {data.oil_total > 0 && (
              <>
                {' '}
                · น้ำมัน <span className="font-semibold tabular-nums">
                  {num(data.oil_total, 0)}
                </span>{' '}
                ลิตร
              </>
            )}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls={bodyId}
          className="border-signal/50 bg-card hover:bg-signal/15"
        >
          {open ? 'ย่อ' : 'แสดงทั้งหมด'}
          <ChevronDown className={cn('transition-transform', open && 'rotate-180')} />
        </Button>
      </div>

      {open && (
        <div id={bodyId} className="grid gap-3 border-t border-signal/25 px-4 pt-3 pb-4">
          <p className="max-w-[80ch] text-sm text-muted-foreground">
            ข้อความในช่องหมายเหตุของเอกสารไม่ตรงกับชื่อหรือรหัสรถใน webstock จึงไม่นับในตัวเลขรายคัน ถ้าเป็นรถ
            ให้ตั้งค่าที่ webstock (หน้า admin ของทะเบียนรถ → รายการที่ยังจับคู่ทะเบียนรถ/เครื่องจักร/หน่วยงานไม่ได้)
            แล้วกดอัปเดตข้อมูล
          </p>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <div className="relative w-full sm:w-80">
              <Search
                className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Escape' && setQuery('')}
                placeholder="ค้นหาหมายเหตุ"
                aria-label={`ค้นหาหมายเหตุใน${TITLE}`}
                className="bg-card pl-8"
              />
            </div>
            {q && (
              <span className="text-sm text-muted-foreground" aria-live="polite">
                พบ {rows.length} จาก {data.rows.length} รายการ
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={exportExcel}
              className="text-muted-foreground sm:ml-auto"
              aria-label={`ดาวน์โหลด Excel: ${TITLE}`}
            >
              <FileSpreadsheet />
              Excel
            </Button>
          </div>

          <div className="scroll-thin max-h-[420px] overflow-auto rounded-lg border bg-card [&>[data-slot=table-container]]:overflow-visible">
            <Table className="text-sm">
              <TableHeader className="sticky top-0 z-10 bg-card shadow-[inset_0_-1px_0_var(--color-border)]">
                <TableRow className="hover:bg-transparent">
                  <TableHead>หมายเหตุในเอกสาร</TableHead>
                  <TableHead>บริษัท</TableHead>
                  <TableHead className="text-right">
                    ค่าซ่อม
                    <span className="block text-xs font-normal text-muted-foreground">บาท</span>
                  </TableHead>
                  <TableHead className="text-right">
                    น้ำมันดีเซล
                    <span className="block text-xs font-normal text-muted-foreground">ลิตร</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.length === 0 && (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={4} className="h-20 text-center text-muted-foreground">
                      ไม่พบหมายเหตุที่ตรงกับ "{query.trim()}"
                    </TableCell>
                  </TableRow>
                )}
                {rows.map((r) => (
                  <TableRow
                    key={`${r.branch_company_name}|${r.remark}`}
                    className="hover:bg-signal/5"
                  >
                    <TableCell className="max-w-[28rem] whitespace-normal">{r.remark}</TableCell>
                    <TableCell className="whitespace-nowrap">{r.branch_company_name}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {r.repair_amount ? num(r.repair_amount, 2) : '–'}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {r.oil_qty ? num(r.oil_qty, 2) : '–'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter className="sticky bottom-0 bg-[color-mix(in_oklab,var(--signal)_12%,var(--card))] font-semibold">
                <TableRow className="hover:bg-transparent">
                  <TableCell colSpan={2} className="text-right">
                    รวมทั้งหมด {data.rows.length} รายการ
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {num(data.repair_total, 2)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {num(data.oil_total, 2)}
                  </TableCell>
                </TableRow>
              </TableFooter>
            </Table>
          </div>
        </div>
      )}
    </section>
  )
}
