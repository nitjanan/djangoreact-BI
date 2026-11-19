import { Check, ChevronDown } from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useDashboardParams } from '@/lib/dashboard-params'
import { cn } from '@/lib/utils'

import { useCurrentUser } from './RequireAuth'

/** ความกว้างที่กันไว้ให้ปุ่ม "เพิ่มเติม" */
const MORE_WIDTH = 120

const tabClass = (active: boolean) =>
  cn(
    // แท็บติดขอบล่างของแถบบน: บริษัทที่เลือกมีเส้นสีปะการังใต้ชื่อ
    'relative shrink-0 px-3 text-sm whitespace-nowrap text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:-outline-offset-2',
    'after:absolute after:inset-x-3 after:bottom-0 after:h-[3px] after:rounded-t-full after:bg-transparent',
    active && 'font-semibold text-foreground after:bg-signal',
  )

/**
 * แท็บบริษัทบนแถบบน: แสดงเท่าที่พอดีความกว้าง ที่เหลือเก็บในเมนู "เพิ่มเติม"
 * บริษัทที่เลือกอยู่แสดงเป็นแท็บเสมอ (ถ้าอยู่ในเมนู จะสลับมาแทนแท็บสุดท้าย)
 */
export function CompanyTabs() {
  const me = useCurrentUser()
  const { company, selectCompany } = useDashboardParams(me)
  const containerRef = useRef<HTMLElement>(null)
  const measureRef = useRef<HTMLDivElement>(null)
  const [fit, setFit] = useState(me.companies.length)

  // วัดความกว้างของทุกแท็บจากแถวที่ซ่อนไว้ แล้วนับว่าใส่ได้กี่แท็บ
  useLayoutEffect(() => {
    const container = containerRef.current
    const measure = measureRef.current
    if (!container || !measure) return
    const recount = () => {
      const widths = [...measure.children].map((el) => (el as HTMLElement).offsetWidth)
      const total = widths.reduce((a, b) => a + b, 0)
      const available = container.clientWidth
      if (total <= available) return setFit(widths.length)
      let used = MORE_WIDTH
      let n = 0
      while (n < widths.length && used + widths[n] <= available) used += widths[n++]
      // บริษัทที่เลือกอยู่ในเมนู -> จะถูกสลับมาแทนแท็บสุดท้าย ต้องเผื่อความกว้างของมันด้วย
      const selected = me.companies.findIndex((c) => c.code === company)
      if (selected >= n) {
        const sum = (k: number) => widths.slice(0, k).reduce((a, b) => a + b, 0)
        while (n > 1 && MORE_WIDTH + sum(n - 1) + widths[selected] > available) n--
      }
      setFit(Math.max(n, 1))
    }
    recount()
    const observer = new ResizeObserver(recount)
    observer.observe(container)
    return () => observer.disconnect()
  }, [me.companies, company])

  if (me.companies.length === 0) {
    return <span className="text-sm text-muted-foreground">ยังไม่ได้กำหนดบริษัทให้ผู้ใช้นี้</span>
  }

  const visible = me.companies.slice(0, fit)
  const hidden = me.companies.slice(fit)
  const selectedHidden = hidden.find((c) => c.code === company)
  if (selectedHidden) {
    // สลับบริษัทที่เลือกขึ้นมาเป็นแท็บสุดท้าย ส่วนแท็บที่ถูกแทนลงไปอยู่ต้นเมนู
    const bumped = visible.pop()
    visible.push(selectedHidden)
    hidden.splice(hidden.indexOf(selectedHidden), 1)
    if (bumped) hidden.unshift(bumped)
  }

  return (
    <nav
      ref={containerRef}
      aria-label="เลือกบริษัท"
      className="relative flex min-w-0 flex-1 self-stretch overflow-hidden"
    >
      {/* แถวสำหรับวัดความกว้าง มองไม่เห็นและกดไม่ได้ */}
      <div
        ref={measureRef}
        aria-hidden
        className="pointer-events-none invisible absolute flex h-0 overflow-hidden"
      >
        {me.companies.map((c) => (
          <span key={c.code} className={cn(tabClass(c.code === company), 'font-semibold')}>
            {c.name ?? c.code}
          </span>
        ))}
      </div>

      {visible.map((c) => (
        <button
          key={c.code}
          type="button"
          onClick={() => selectCompany(c.code)}
          aria-current={c.code === company ? 'page' : undefined}
          title={c.name ?? c.code}
          className={tabClass(c.code === company)}
        >
          {c.name ?? c.code}
        </button>
      ))}

      {hidden.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="ml-1 inline-flex shrink-0 items-center gap-1 self-center rounded-md border px-2.5 py-1 text-sm text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring data-[state=open]:bg-muted"
            >
              เพิ่มเติม
              <span className="rounded bg-muted px-1.5 text-xs tabular-nums">{hidden.length}</span>
              <ChevronDown className="size-3.5" aria-hidden />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="max-h-80 w-60">
            {hidden.map((c) => (
              <DropdownMenuItem key={c.code} onSelect={() => selectCompany(c.code)}>
                <span className="w-10 shrink-0 text-xs text-muted-foreground">{c.code}</span>
                <span className="min-w-0 flex-1 truncate">{c.name ?? c.code}</span>
                {c.code === company && <Check className="size-4 text-primary" aria-hidden />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </nav>
  )
}
