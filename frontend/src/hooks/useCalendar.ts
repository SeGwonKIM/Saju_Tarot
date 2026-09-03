/**
 * 달력 상태 훅 (PRD §5.3 — 상태는 hooks/, 통신은 api/, 표시는 components/).
 *
 * 폼이 필요한 것 세 가지를 한 곳에서 준다.
 *  ① 선택한 달의 일수(음력은 29/30이 달마다 다르다)
 *  ② 그 달에 윤달이 있는지 (체크박스 노출 조건)
 *  ③ 반대쪽 달력으로 바꾼 날짜 (보조 텍스트)
 */
import { useQuery } from '@tanstack/react-query'
import { convertDate, fetchLunarYear } from '../api/calendar'

const DAY = 1000 * 60 * 60 * 24

/** 음력 연도 정보 — 연도별로 바뀌지 않는 값이라 오래 캐시한다 */
export function useLunarYear(year: number, enabled: boolean) {
  return useQuery({
    queryKey: ['lunar-year', year],
    queryFn: () => fetchLunarYear(year),
    enabled,
    staleTime: DAY,
    gcTime: DAY,
    retry: 1,
  })
}

/** 선택한 날짜를 반대쪽 달력으로 변환 */
export function useConvertedDate(
  calendarType: 'solar' | 'lunar',
  date: string,
  isLeapMonth: boolean,
  enabled = true,
) {
  return useQuery({
    queryKey: ['convert', calendarType, date, isLeapMonth],
    queryFn: () => convertDate({ calendar_type: calendarType, date, is_leap_month: isLeapMonth }),
    enabled,
    staleTime: DAY,
    retry: 0, // 없는 날짜(422)는 재시도해도 같다
  })
}
