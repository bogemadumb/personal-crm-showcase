// Тонкий клиент к /api/v2. Сессия — httpOnly-кука (из JS её не видно), поэтому 401 = «нужно войти».
export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(`${status}: ${detail}`)
    this.status = status
    this.detail = detail
  }
}

type Json = Record<string, unknown> | unknown[]

const onUnauthorized = new Set<() => void>()
export const whenUnauthorized = (fn: () => void) => {
  onUnauthorized.add(fn)
  return () => { onUnauthorized.delete(fn) }
}

export async function api<T>(path: string, init: { method?: string; body?: Json; params?: Record<string, string | number | undefined> } = {}): Promise<T> {
  const qs = init.params
    ? '?' + new URLSearchParams(Object.entries(init.params).filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => [k, String(v)])).toString()
    : ''
  const r = await fetch(`/api/v2${path}${qs}`, {
    method: init.method ?? (init.body ? 'POST' : 'GET'),
    credentials: 'same-origin',
    headers: init.body ? { 'Content-Type': 'application/json' } : undefined,
    body: init.body ? JSON.stringify(init.body) : undefined,
  })
  if (r.status === 204) return undefined as T
  const data = await r.json().catch(() => null)
  if (!r.ok) {
    if (r.status === 401 && path !== '/auth/login') onUnauthorized.forEach((fn) => fn())
    const d = data?.detail
    throw new ApiError(r.status, typeof d === 'string' ? d : d?.detail ?? r.statusText)
  }
  return data as T
}
