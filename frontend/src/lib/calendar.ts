/**
 * 달력 유틸 — 폼 UX 용 (PRD §6.1 필드 3·4·5·6).
 *
 * 음↔양 변환과 음력 월 정보는 3단계에서 **백엔드로 옮겼다**
 * (`api/calendar.ts` + `hooks/useCalendar.ts`).
 * 여기 남은 것은 서버가 필요 없는 순수 표시용 값뿐이다.
 */

/** 12지시 — 2시간 단위 (PRD §8.2) */
export const JIJI_HOURS = [
  { ji: '자시', label: '자시 (23:00~00:59)', time: '23:30' },
  { ji: '축시', label: '축시 (01:00~02:59)', time: '01:30' },
  { ji: '인시', label: '인시 (03:00~04:59)', time: '03:30' },
  { ji: '묘시', label: '묘시 (05:00~06:59)', time: '05:30' },
  { ji: '진시', label: '진시 (07:00~08:59)', time: '07:30' },
  { ji: '사시', label: '사시 (09:00~10:59)', time: '09:30' },
  { ji: '오시', label: '오시 (11:00~12:59)', time: '11:30' },
  { ji: '미시', label: '미시 (13:00~14:59)', time: '13:30' },
  { ji: '신시', label: '신시 (15:00~16:59)', time: '15:30' },
  { ji: '유시', label: '유시 (17:00~18:59)', time: '17:30' },
  { ji: '술시', label: '술시 (19:00~20:59)', time: '19:30' },
  { ji: '해시', label: '해시 (21:00~22:59)', time: '21:30' },
] as const

export function formatDateKo(date: string, type: 'solar' | 'lunar'): string {
  const [y, m, d] = date.split('-')
  const suffix = type === 'solar' ? '양' : '음'
  return `${y}.${m}.${d}(${suffix})`
}

export const YEARS = Array.from(
  { length: new Date().getFullYear() - 1900 + 1 },
  (_, i) => new Date().getFullYear() - i,
)
