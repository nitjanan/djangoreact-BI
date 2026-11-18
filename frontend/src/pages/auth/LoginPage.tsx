import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { z } from 'zod'

import { useLogin, useMe } from '@/api/hooks'
import { FormField } from '@/components/form-field'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

import { AuthShell } from './AuthShell'

const schema = z.object({
  username: z.string().trim().min(1, 'กรุณากรอกชื่อผู้ใช้'),
  password: z.string().min(1, 'กรุณากรอกรหัสผ่าน'),
})
type Values = z.infer<typeof schema>

export function LoginPage() {
  const me = useMe()
  const login = useLogin()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { username: '', password: '' },
  })

  if (me.data) return <Navigate to={from} replace />

  const onSubmit = form.handleSubmit((values) =>
    login.mutate(values, { onSuccess: () => navigate(from, { replace: true }) }),
  )

  return (
    <AuthShell title="เข้าสู่ระบบ" description="ระบบติดตามงานซ่อมบำรุงรถและเครื่องจักร">
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        {login.error && (
          <Alert variant="destructive">
            <AlertDescription>{login.error.message}</AlertDescription>
          </Alert>
        )}
        <FormField
          label="ชื่อผู้ใช้"
          autoComplete="username"
          autoFocus
          error={form.formState.errors.username?.message}
          {...form.register('username')}
        />
        <FormField
          label="รหัสผ่าน"
          type="password"
          autoComplete="current-password"
          error={form.formState.errors.password?.message}
          hint={
            <Link to="/forgot-password" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
              ลืมรหัสผ่าน?
            </Link>
          }
          {...form.register('password')}
        />
        <Button type="submit" size="lg" disabled={login.isPending}>
          {login.isPending && <Loader2 className="animate-spin" />}
          เข้าสู่ระบบ
        </Button>
      </form>
    </AuthShell>
  )
}
