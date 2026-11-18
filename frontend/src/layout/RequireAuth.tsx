import { Loader2 } from 'lucide-react'
import { Navigate, Outlet, useLocation } from 'react-router'

import type { Me } from '@/api/client'
import { useMe } from '@/api/hooks'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function RequireAuth() {
  const me = useMe()
  const location = useLocation()

  if (me.isPending) {
    return (
      <div className="flex min-h-svh items-center justify-center text-muted-foreground">
        <Loader2 className="size-6 animate-spin" aria-label="กำลังโหลด" />
      </div>
    )
  }
  if (me.isError) {
    return (
      <div className="flex min-h-svh items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertDescription>เชื่อมต่อเซิร์ฟเวอร์ไม่ได้: {me.error.message}</AlertDescription>
        </Alert>
      </div>
    )
  }
  if (!me.data) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <Outlet />
}

/** ใช้ได้เฉพาะใต้ <RequireAuth> (ข้อมูลผู้ใช้โหลดแล้วแน่นอน) */
export function useCurrentUser(): Me {
  const me = useMe()
  if (!me.data) throw new Error('useCurrentUser must be used under <RequireAuth>')
  return me.data
}
