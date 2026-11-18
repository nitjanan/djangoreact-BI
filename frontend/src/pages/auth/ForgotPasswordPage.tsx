import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, MailCheck } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { z } from 'zod'

import { usePasswordReset } from '@/api/hooks'
import { FormField } from '@/components/form-field'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

import { AuthShell } from './AuthShell'

const schema = z.object({ email: z.email('รูปแบบอีเมลไม่ถูกต้อง') })
type Values = z.infer<typeof schema>

export function ForgotPasswordPage() {
  const reset = usePasswordReset()
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: '' } })

  return (
    <AuthShell
      title="ลืมรหัสผ่าน"
      description="กรอกอีเมลของบัญชี ระบบจะส่งลิงก์สำหรับตั้งรหัสผ่านใหม่ให้"
    >
      {reset.isSuccess ? (
        <div className="grid gap-4">
          <Alert>
            <MailCheck />
            <AlertDescription>{reset.data.detail}</AlertDescription>
          </Alert>
          <Button variant="outline" asChild>
            <Link to="/login">กลับไปหน้าเข้าสู่ระบบ</Link>
          </Button>
        </div>
      ) : (
        <form
          onSubmit={form.handleSubmit((v) => reset.mutate(v))}
          className="grid gap-4"
          noValidate
        >
          {reset.error && (
            <Alert variant="destructive">
              <AlertDescription>{reset.error.message}</AlertDescription>
            </Alert>
          )}
          <FormField
            label="อีเมล"
            type="email"
            autoComplete="email"
            autoFocus
            error={form.formState.errors.email?.message}
            {...form.register('email')}
          />
          <Button type="submit" size="lg" disabled={reset.isPending}>
            {reset.isPending && <Loader2 className="animate-spin" />}
            ส่งลิงก์ตั้งรหัสผ่านใหม่
          </Button>
          <Link
            to="/login"
            className="text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
          >
            กลับไปหน้าเข้าสู่ระบบ
          </Link>
        </form>
      )}
    </AuthShell>
  )
}
