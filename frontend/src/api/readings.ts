/**
 * 교체 지점 (PRD §7.1).
 *
 * 지금은 목업을 돌려주고, 4~5단계에서 백엔드가 붙으면 아래 fetch 쪽으로만 바뀐다.
 * 컴포넌트는 이 함수만 호출하므로 컴포넌트 코드를 고칠 일이 없다.
 */
import { mockReading } from './mockData'
import { readingSchema, type Reading, type ReadingRequest } from '../schemas/reading'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiFailure extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly field?: string,
    readonly traceId?: string,
  ) {
    super(message)
  }
}

/** 상태 코드 → 사용자에게 보일 문구 (PRD §10.6) */
export function messageFor(status: number, fallback?: string): string {
  switch (status) {
    case 400:
    case 422:
      return fallback ?? '입력값을 다시 확인해 주세요.'
    case 401:
      return '다시 로그인해 주세요.'
    case 403:
      return '권한이 없습니다.'
    case 404:
      return '링크가 만료되었거나 없는 페이지입니다.'
    case 429:
      return '요청이 많습니다. 잠시 후 다시 시도해 주세요.'
    default:
      return '잠시 후 다시 시도해 주세요.'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const traceId = res.headers.get('X-Trace-Id') ?? undefined
  if (!res.ok) {
    let detail: string | undefined
    let field: string | undefined
    try {
      const body = await res.json()
      detail = body?.error?.message
      field = body?.error?.field
    } catch {
      /* 본문이 JSON이 아닐 수 있다 */
    }
    throw new ApiFailure(res.status, messageFor(res.status, detail), field, traceId)
  }
  return (await res.json()) as T
}

export async function createReading(input: ReadingRequest): Promise<Reading> {
  if (USE_MOCK) {
    // 실제 호출과 비슷한 체감을 주기 위한 지연 (로딩 화면 확인용)
    await new Promise((r) => setTimeout(r, 1200))
    return readingSchema.parse(mockReading(input))
  }
  const data = await request<unknown>('/readings', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  return readingSchema.parse(data)
}

/** 저장된 리포트를 id 로 다시 불러온다 — 새로고침·링크 재방문 */
export async function fetchReading(id: string): Promise<Reading> {
  const data = await request<unknown>(`/readings/${encodeURIComponent(id)}`)
  return readingSchema.parse(data)
}

/** 읽기 전용 공유 링크를 만든다 (PRD §12.3) */
export async function createShareLink(id: string): Promise<string> {
  const data = await request<{ token: string }>(
    `/readings/${encodeURIComponent(id)}/share`,
    { method: 'POST' },
  )
  return `${location.origin}/share/${data.token}`
}

/** 공유 링크로 열람 — 생년월일시는 빠진 형태로 온다 */
export async function fetchShared(token: string): Promise<Reading> {
  const data = await request<{ id: string; payload: unknown }>(
    `/share/${encodeURIComponent(token)}`,
  )
  return readingSchema.parse({
    ...(data.payload as object),
    id: data.id,
    input_echo: {
      solar_datetime: '',
      ...((data.payload as { input_echo?: object }).input_echo ?? {}),
    },
  })
}

export async function getHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`)
    return res.ok
  } catch {
    return false
  }
}

export const usingMock = USE_MOCK
