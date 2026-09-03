/**
 * 목업 단계용 임시 저장소 (PRD §3 v0.1 — "저장 없음, 브라우저 세션만").
 *
 * 7단계에서 Supabase 저장이 붙으면 이 파일은 사라지고
 * `GET /readings/{id}` 호출로 대체된다.
 * sessionStorage 를 쓰는 이유: 새로고침을 견디되 탭을 닫으면 남지 않게.
 */
import { readingSchema, type Reading } from '../schemas/reading'

const KEY = 'saju:readings'

function load(): Record<string, unknown> {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? '{}')
  } catch {
    return {}
  }
}

export function saveReading(reading: Reading): void {
  try {
    const all = load()
    all[reading.id] = reading
    sessionStorage.setItem(KEY, JSON.stringify(all))
  } catch {
    // 시크릿 창 등에서 저장이 막힐 수 있다 — 실패해도 화면은 동작해야 한다
  }
}

export function getReading(id: string): Reading | null {
  const raw = load()[id]
  if (!raw) return null
  const parsed = readingSchema.safeParse(raw)
  return parsed.success ? parsed.data : null
}
