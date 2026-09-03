/**
 * 달력 유틸 — 폼 UX 용 (PRD §6.1 필드 3·4·5·6).
 *
 * ⚠️ 여기 있는 음↔양 변환은 **목업**이다. 실제 변환은 3단계에서
 *    백엔드 `POST /calendar/convert` (korean_lunar_calendar + KASI 검증)로 대체한다.
 *    화면 동작을 먼저 확인하려고 형태만 같게 맞춰 둔 것이다.
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

/** 양력 각 달의 일수 */
export function solarDaysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

/**
 * 음력 각 달의 일수 — 목업(29 또는 30일).
 * 실제 값은 3단계에서 서버가 알려준다.
 */
export function lunarDaysInMonth(year: number, month: number): number {
  return (year + month) % 2 === 0 ? 30 : 29
}

/**
 * 그 해에 윤달이 있는 달 목록 — 목업.
 * 음력을 골랐고, 선택한 달이 이 목록에 있을 때만 윤달 체크박스를 보여준다
 * (PRD §6.1 필드 5).
 */
export function leapMonthsOf(year: number): number[] {
  const table: Record<number, number> = {
    0: 5, 3: 3, 6: 8, 11: 2, 14: 6, 17: 4, // 19년 7윤법 근사 — 목업
  }
  const m = table[year % 19]
  return m ? [m] : []
}

export function daysInMonth(
  calendarType: 'solar' | 'lunar',
  year: number,
  month: number,
): number {
  return calendarType === 'solar'
    ? solarDaysInMonth(year, month)
    : lunarDaysInMonth(year, month)
}

/**
 * 음↔양 변환 — 목업. 형태만 서버 응답과 같다.
 * 토글할 때 입력값을 버리지 않고 변환해 보여주기 위한 보조 텍스트용 (PRD §6.1).
 */
export function mockConvert(
  from: 'solar' | 'lunar',
  date: string,
  isLeap: boolean,
): { solar_date: string; lunar_date: string; is_leap_month: boolean } {
  const [y, m, d] = date.split('-').map(Number)
  // 음력은 양력보다 대략 30일 앞선다는 정도의 근사
  const shift = from === 'lunar' ? 30 : -30
  const base = new Date(y, m - 1, d)
  base.setDate(base.getDate() + shift)
  const other = `${base.getFullYear()}-${String(base.getMonth() + 1).padStart(2, '0')}-${String(
    base.getDate(),
  ).padStart(2, '0')}`

  return from === 'lunar'
    ? { solar_date: other, lunar_date: date, is_leap_month: isLeap }
    : { solar_date: date, lunar_date: other, is_leap_month: false }
}

export function formatDateKo(date: string, type: 'solar' | 'lunar'): string {
  const [y, m, d] = date.split('-')
  const suffix = type === 'solar' ? '양' : '음'
  return `${y}.${m}.${d}(${suffix})`
}

export const YEARS = Array.from(
  { length: new Date().getFullYear() - 1900 + 1 },
  (_, i) => new Date().getFullYear() - i,
)
