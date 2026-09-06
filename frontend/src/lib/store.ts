/**
 * 목업 단계용 임시 저장소 (PRD §3 v0.1 — "저장 없음, 브라우저 세션만").
 *
 * 7단계에서 Supabase 저장이 붙으면 이 파일은 사라지고
 * `GET /readings/{id}` 호출로 대체된다.
 * sessionStorage 를 쓰는 이유: 새로고침을 견디되 탭을 닫으면 남지 않게.
 */
import { readingSchema, type Reading } from '../schemas/reading'

const KEY = 'saju:readings'
const NAME_KEY = 'saju:names'

/**
 * 이름은 **브라우저에만** 둔다 (PRD §12.14).
 *
 * 서버는 이름을 암호화해 저장하고 응답에 담지 않는다. 그래서 화면에 이름을
 * 보이려고 응답에 넣으면, 주소만 아는 사람도 남의 이름을 보게 된다
 * (`GET /readings/{id}` 는 인증이 없다). 공유 링크에도 딸려 나간다.
 * 리포트를 만든 당사자의 브라우저에만 두면 그 두 경우가 모두 막힌다.
 * 탭을 닫으면 사라진다 — 그게 맞다.
 */
export function saveName(id: string, name: string): void {
  try {
    const all = JSON.parse(sessionStorage.getItem(NAME_KEY) ?? '{}')
    all[id] = name
    sessionStorage.setItem(NAME_KEY, JSON.stringify(all))
  } catch {
    /* 시크릿 창 등 */
  }
}

export function getName(id: string): string | null {
  try {
    const v = JSON.parse(sessionStorage.getItem(NAME_KEY) ?? '{}')[id]
    return typeof v === 'string' && v ? v : null
  } catch {
    return null
  }
}

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
