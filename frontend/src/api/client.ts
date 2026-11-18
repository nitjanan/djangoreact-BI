import createClient, { type Middleware } from 'openapi-fetch'

import type { components, paths } from './schema'

export type Schemas = components['schemas']
export type Me = Schemas['Me']
export type Dashboard = Schemas['Dashboard']
export type CarRow = Schemas['CarRow']

// ต้องตรงกับ CSRF_COOKIE_NAME ใน backend/config/settings.py
const CSRF_COOKIE = 'fleet_csrftoken'
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

function readCookie(name: string) {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null
}

/** ขอ cookie CSRF จาก Django หนึ่งครั้ง (ก่อน POST แรก) */
let csrfReady: Promise<void> | null = null
export function ensureCsrf() {
  if (readCookie(CSRF_COOKIE)) return Promise.resolve()
  csrfReady ??= fetch('/api/auth/csrf/', { credentials: 'same-origin' }).then(() => undefined)
  return csrfReady
}

const csrfMiddleware: Middleware = {
  async onRequest({ request }) {
    if (SAFE_METHODS.has(request.method)) return request
    await ensureCsrf()
    const token = readCookie(CSRF_COOKIE)
    if (token) request.headers.set('X-CSRFToken', token)
    return request
  },
}

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, body: unknown) {
    super(errorMessage(body) ?? `เกิดข้อผิดพลาด (${status})`)
    this.status = status
    this.body = body
  }
}

/** ดึงข้อความ error จาก response ของ DRF: {detail} หรือ {field: [msg]} */
function errorMessage(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const record = body as Record<string, unknown>
  if (typeof record.detail === 'string') return record.detail
  for (const value of Object.values(record)) {
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
    if (typeof value === 'string') return value
  }
  return null
}

export const api = createClient<paths>({ baseUrl: '/', credentials: 'same-origin' })
api.use(csrfMiddleware)

/** แปลงผลลัพธ์ของ openapi-fetch: สำเร็จคืน data, ไม่สำเร็จ throw ApiError */
export async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await promise
  if (!response.ok) throw new ApiError(response.status, error)
  return data as T
}
