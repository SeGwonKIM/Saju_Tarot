/**
 * 달력 변환 API (PRD §10.1).
 *
 * 3단계에서 목업(lib/calendar.ts 의 mockConvert·leapMonthsOf)을 이 호출로 교체했다.
 * 서버가 아직 안 떴거나 잠들어 있을 수 있으므로, 실패하면 **틀린 숫자를 보여주지 않고**
 * 안전한 기본값(29일·윤달 없음)으로 폼을 굴리고 화면에 그 사실을 알린다.
 */
import { z } from 'zod'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export const convertSchema = z.object({
  solar_date: z.string(),
  lunar_date: z.string(),
  is_leap_month: z.boolean(),
  ganji: z.string(),
})
export type Converted = z.infer<typeof convertSchema>

export const lunarYearSchema = z.object({
  year: z.number(),
  months: z.array(
    z.object({
      month: z.number(),
      days: z.number(),
      has_leap: z.boolean(),
      leap_days: z.number().nullable(),
    }),
  ),
})
export type LunarYear = z.infer<typeof lunarYearSchema>

/** 없는 날짜(422)와 서버 장애를 구분한다 — 화면 문구가 달라야 한다 */
export class DateNotFound extends Error {}

export async function convertDate(input: {
  calendar_type: 'solar' | 'lunar'
  date: string
  is_leap_month: boolean
}): Promise<Converted> {
  const res = await fetch(`${API_BASE}/calendar/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (res.status === 422) {
    const body = await res.json().catch(() => null)
    throw new DateNotFound(body?.error?.message ?? '없는 날짜입니다.')
  }
  if (!res.ok) throw new Error('변환에 실패했습니다.')
  return convertSchema.parse(await res.json())
}

export async function fetchLunarYear(year: number): Promise<LunarYear> {
  const res = await fetch(`${API_BASE}/calendar/lunar-year/${year}`)
  if (!res.ok) throw new Error('음력 정보를 가져오지 못했습니다.')
  return lunarYearSchema.parse(await res.json())
}
