import { Loader2 } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { useMe, useReportLogin } from '@/api/hooks'

import { AuthShell } from './AuthShell'

/** รับเฉพาะ path ภายในเว็บ (กันลิงก์พาไปเว็บอื่น) — ตรงกับ safe_next ฝั่ง backend */
function safeNext(value: string | null) {
  if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return '/'
  return value
}

/**
 * ลิงก์ในอีเมลรายงาน: /auto-login?token=...&next=/?company=...
 * login ด้วย POST จากหน้านี้ (ไม่ใช่ตอนเปิดลิงก์) ระบบสแกนลิงก์ของอีเมลจึงใช้ token ไม่ได้
 */
export function AutoLoginPage() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const next = safeNext(params.get('next'))
  const me = useMe()
  const login = useReportLogin()
  const navigate = useNavigate()
  const started = useRef(false)

  useEffect(() => {
    if (!token || me.isPending || started.current) return
    started.current = true // StrictMode เรียก effect สองครั้ง: token ใช้ได้ครั้งเดียว
    login.mutate(token, {
      onSuccess: () => navigate(next, { replace: true }),
      onError: (err) => {
        // login อยู่แล้ว (เช่นกดลิงก์ที่สองในอีเมลเดียวกัน) ก็ไปหน้าเดิมได้เลย
        if (me.data) return navigate(next, { replace: true })
        toast.error(err.message)
        navigate('/login', { replace: true, state: { from: next } })
      },
    })
  }, [token, me.isPending, me.data, next, login, navigate])

  if (!token) return <Navigate to={next} replace />

  return (
    <AuthShell title="กำลังเข้าสู่ระบบ" description="จากลิงก์ในอีเมลรายงาน">
      <div className="flex items-center gap-3 text-muted-foreground" role="status">
        <Loader2 className="size-5 animate-spin" aria-hidden />
        กำลังเปิด dashboard…
      </div>
    </AuthShell>
  )
}
