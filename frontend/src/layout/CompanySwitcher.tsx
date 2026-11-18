import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useDashboardParams } from '@/lib/dashboard-params'
import { cn } from '@/lib/utils'

import { useCurrentUser } from './RequireAuth'

/** แท็บบริษัท (จอใหญ่) / dropdown (มือถือ) — แทนแท็บบน navbar ของหน้าเดิม */
export function CompanySwitcher() {
  const me = useCurrentUser()
  const { company, selectCompany } = useDashboardParams(me)

  if (me.companies.length === 0) {
    return <span className="text-sm text-muted-foreground">ยังไม่ได้กำหนดบริษัทให้ผู้ใช้นี้</span>
  }

  return (
    <>
      <nav
        aria-label="เลือกบริษัท"
        className="hidden min-w-0 flex-1 gap-1 overflow-x-auto [scrollbar-width:thin] lg:flex"
      >
        {me.companies.map((c) => (
          <button
            key={c.code}
            type="button"
            onClick={() => selectCompany(c.code)}
            aria-current={c.code === company ? 'page' : undefined}
            title={c.name ?? c.code}
            className={cn(
              'shrink-0 rounded-md px-3 py-1.5 text-sm whitespace-nowrap text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
              c.code === company && 'bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground',
            )}
          >
            {c.name ?? c.code}
          </button>
        ))}
      </nav>

      <div className="min-w-0 flex-1 lg:hidden">
        <Select value={company ?? undefined} onValueChange={selectCompany}>
          <SelectTrigger className="w-full max-w-xs" aria-label="เลือกบริษัท">
            <SelectValue placeholder="เลือกบริษัท" />
          </SelectTrigger>
          <SelectContent>
            {me.companies.map((c) => (
              <SelectItem key={c.code} value={c.code}>
                {c.code} - {c.name ?? c.code}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  )
}
