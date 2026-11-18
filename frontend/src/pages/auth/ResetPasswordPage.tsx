import { zodResolver } from '@hookform/resolvers/zod'
import { CircleCheck, Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useParams } from 'react-router'
import { z } from 'zod'

import { usePasswordResetConfirm } from '@/api/hooks'
import { FormField } from '@/components/form-field'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

import { AuthShell } from './AuthShell'

const schema = z
  .object({
    password: z.string().min(8, 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร'),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    message: 'รหัสผ่านทั้งสองช่องไม่ตรงกัน',
    path: ['confirm'],
  })
type Values = z.infer<typeof schema>

export function ResetPasswordPage() {
  const { uid = '', token = '' } = useParams()
  const confirm = usePasswordResetConfirm()
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { password: '', confirm: '' },
  })

  return (
    <AuthShell title="ตั้งรหัสผ่านใหม่">
      {confirm.isSuccess ? (
        <div className="grid gap-4">
          <Alert>
            <CircleCheck />
            <AlertDescription>{confirm.data.detail}</AlertDescription>
          </Alert>
          <Button asChild>
            <Link to="/login">เข้าสู่ระบบ</Link>
          </Button>
        </div>
      ) : (
        <form
          onSubmit={form.handleSubmit((v) =>
            confirm.mutate({ uid, token, new_password: v.password }),
          )}
          className="grid gap-4"
          noValidate
        >
          {confirm.error && (
            <Alert variant="destructive">
              <AlertDescription>{confirm.error.message}</AlertDescription>
            </Alert>
          )}
          <FormField
            label="รหัสผ่านใหม่"
            type="password"
            autoComplete="new-password"
            autoFocus
            error={form.formState.errors.password?.message}
            {...form.register('password')}
          />
          <FormField
            label="ยืนยันรหัสผ่านใหม่"
            type="password"
            autoComplete="new-password"
            error={form.formState.errors.confirm?.message}
            {...form.register('confirm')}
          />
          <Button type="submit" size="lg" disabled={confirm.isPending}>
            {confirm.isPending && <Loader2 className="animate-spin" />}
            บันทึกรหัสผ่านใหม่
          </Button>
        </form>
      )}
    </AuthShell>
  )
}
