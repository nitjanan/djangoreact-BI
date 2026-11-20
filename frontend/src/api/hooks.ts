import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, api, unwrap } from './client'
import type { paths } from './schema'

export type DashboardQuery = NonNullable<paths['/api/dashboard/']['get']['parameters']['query']>

export const queryKeys = {
  me: ['me'] as const,
  dashboard: (q: DashboardQuery) => ['dashboard', q] as const,
  carDepartments: ['car-departments'] as const,
}

/** ข้อมูลผู้ใช้ที่ login อยู่ — null = ยังไม่ได้ login */
export function useMe() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: async () => {
      try {
        return await unwrap(api.GET('/api/me/'))
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) return null
        throw err
      }
    },
    staleTime: 5 * 60_000,
    retry: false,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { username: string; password: string }) =>
      unwrap(api.POST('/api/auth/login/', { body })),
    onSuccess: (me) => {
      qc.clear()
      qc.setQueryData(queryKeys.me, me)
    },
  })
}

/** เข้าสู่ระบบจากลิงก์ในอีเมลรายงาน (token ใช้ได้ครั้งเดียว) */
export function useReportLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (token: string) => unwrap(api.POST('/api/auth/report-login/', { body: { token } })),
    onSuccess: (me) => {
      qc.clear()
      qc.setQueryData(queryKeys.me, me)
    },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/auth/logout/')),
    onSettled: () => {
      qc.clear()
      qc.setQueryData(queryKeys.me, null)
    },
  })
}

export function usePasswordReset() {
  return useMutation({
    mutationFn: (body: { email: string }) =>
      unwrap(api.POST('/api/auth/password-reset/', { body })),
  })
}

export function usePasswordResetConfirm() {
  return useMutation({
    mutationFn: (body: { uid: string; token: string; new_password: string }) =>
      unwrap(api.POST('/api/auth/password-reset/confirm/', { body })),
  })
}

export function useCarDepartments() {
  return useQuery({
    queryKey: queryKeys.carDepartments,
    queryFn: () => unwrap(api.GET('/api/car-departments/')),
    staleTime: 60 * 60_000,
  })
}

export function useDashboard(query: DashboardQuery | null) {
  return useQuery({
    queryKey: queryKeys.dashboard(query ?? ({} as DashboardQuery)),
    queryFn: () => unwrap(api.GET('/api/dashboard/', { params: { query: query! } })),
    enabled: query !== null,
    // เปลี่ยนตัวกรองแล้วยังแสดงข้อมูลเดิมระหว่างโหลด (ไม่กระพริบเป็นหน้าว่าง)
    placeholderData: keepPreviousData,
  })
}

/** ประวัติรถรายคัน (หน้า /car/:carId?company=<branch_company_id>) */
export function useCarHistory(carId: number, branchCompanyId: string | null) {
  return useQuery({
    queryKey: ['car-history', carId, branchCompanyId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/car-history/{car_id}/', {
          params: { path: { car_id: carId }, query: { branch_company_id: branchCompanyId! } },
        }),
      ),
    enabled: Number.isFinite(carId) && branchCompanyId !== null,
  })
}

/** ปุ่ม "อัปเดตข้อมูล" (เฉพาะ superuser) — ดึงจาก webstock แล้วโหลด dashboard ใหม่ */
export function useSyncAll() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/sync/')),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboard'] }),
  })
}
