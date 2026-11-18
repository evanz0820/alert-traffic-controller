import type {
  AlertFilters,
  AlertPage,
  CustomerDetail,
  CustomerListItem,
  DayPoint,
  Flows,
  Replay,
  RulesConfig,
  RunInfo,
  Summary,
  Timeline,
} from './types'

const BASE = '/api'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

/** FastAPI errors are a string or a list of {loc, msg}; turn either into one readable line. */
function describeDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) =>
        [d.loc?.filter((l) => l !== 'body').join('.'), d.msg].filter(Boolean).join(': '),
      )
      .join('; ')
  }
  return null
}

export async function errorFrom(res: Response): Promise<ApiError> {
  let detail = res.statusText || `HTTP ${res.status}`
  try {
    detail = describeDetail(((await res.json()) as { detail?: unknown }).detail) ?? detail
  } catch {
    // body wasn't JSON; keep the status text
  }
  return new ApiError(res.status, detail)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    throw new ApiError(0, 'The ATC API is not reachable')
  }
  if (!res.ok) throw await errorFrom(res)
  return (await res.json()) as T
}

export function filterParams(filters: AlertFilters, extra: Record<string, string | number> = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === '') continue
    if (Array.isArray(value)) value.forEach((v) => params.append(key, String(v)))
    else params.set(key, String(value))
  }
  for (const [key, value] of Object.entries(extra)) params.set(key, String(value))
  return params
}

export const api = {
  runs: (limit = 10) => request<RunInfo[]>(`/runs?limit=${limit}`),
  summary: (runId: string) => request<Summary>(`/runs/${runId}/summary`),
  flows: (runId: string) => request<Flows>(`/runs/${runId}/flows`),
  timeseries: (runId: string) => request<DayPoint[]>(`/runs/${runId}/timeseries`),
  replay: (runId: string) => request<Replay>(`/runs/${runId}/replay`),
  alerts: (runId: string, filters: AlertFilters, page: number, pageSize: number, sort: string) =>
    request<AlertPage>(
      `/runs/${runId}/alerts?${filterParams(filters, { page, page_size: pageSize, sort })}`,
    ),
  alertsCsvUrl: (runId: string, filters: AlertFilters) =>
    `${BASE}/runs/${runId}/alerts.csv?${filterParams(filters)}`,
  customers: (runId: string, q = '') =>
    request<CustomerListItem[]>(`/customers?run=${runId}${q ? `&q=${encodeURIComponent(q)}` : ''}`),
  customer: (runId: string, id: number) => request<CustomerDetail>(`/customers/${id}?run=${runId}`),
  timeline: (runId: string, id: number) =>
    request<Timeline>(`/customers/${id}/timeline?run=${runId}`),
  config: () => request<RulesConfig>('/config'),
  saveConfig: (config: RulesConfig) =>
    request<RulesConfig>('/config', { method: 'PUT', body: JSON.stringify(config) }),
  simulate: (overrides: Partial<RulesConfig>, label?: string) =>
    request<{ run_id: string; baseline_run_id: string; duration_ms: number }>('/simulate', {
      method: 'POST',
      body: JSON.stringify({ overrides, label }),
    }),
}
