import type { ReactNode } from 'react'

/** หมวดของหน้า: หัวข้อวางนอกการ์ด เพื่อจัดกลุ่มกราฟที่ตอบคำถามเดียวกัน */
export function Section({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="grid grid-cols-1 gap-4" aria-label={title}>
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-foreground/15 pb-2">
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </header>
      {children}
    </section>
  )
}
