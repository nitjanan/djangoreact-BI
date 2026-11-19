import type { ReactNode } from 'react'
import { Truck } from 'lucide-react'

/** หน้าเข้าสู่ระบบ: แผงแบรนด์สีเหล็ก (จอใหญ่) + ฟอร์มบนพื้นขาว */
export function AuthShell({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <div className="grid min-h-svh grid-cols-1 bg-card lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="relative hidden overflow-hidden bg-plate text-plate-foreground lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:linear-gradient(135deg,currentColor_1px,transparent_1px),linear-gradient(45deg,currentColor_1px,transparent_1px)] [background-size:28px_28px]"
        />
        <Brand />
        <div className="relative max-w-md">
          <p className="font-heading text-4xl leading-tight font-semibold">
            ค่าซ่อม ชั่วโมงทำงาน และน้ำมัน ของรถทุกคันในที่เดียว
          </p>
          <p className="mt-4 text-plate-muted">
            ดูต้นทุนซ่อมต่อชั่วโมง ความพร้อมใช้งาน และรถที่เสียบ่อย แยกตามบริษัทและแผนก
          </p>
        </div>
        <div className="relative h-1.5 w-24 rounded-full bg-signal" aria-hidden />
      </aside>

      <main className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <Brand dark />
          </div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          {description && <p className="mt-1.5 text-sm text-muted-foreground">{description}</p>}
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  )
}

function Brand({ dark = false }: { dark?: boolean }) {
  return (
    <div className="relative flex items-center gap-3">
      <span className="flex size-10 items-center justify-center rounded-lg bg-signal text-signal-foreground">
        <Truck className="size-5" />
      </span>
      <span className="leading-tight">
        <span className={`block font-heading text-lg font-semibold ${dark ? 'text-foreground' : ''}`}>
          Fleet Dashboard
        </span>
        <span className={`block text-xs ${dark ? 'text-muted-foreground' : 'text-plate-muted'}`}>
          งานซ่อมบำรุงรถและเครื่องจักร
        </span>
      </span>
    </div>
  )
}
