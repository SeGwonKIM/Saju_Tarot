/**
 * API 계약 단일 출처 (PRD §5.4, §10).
 *
 * 3단계에서 백엔드가 붙으면 FastAPI 의 OpenAPI 로부터 타입을 자동 생성해
 * 이 파일과 일치하는지 CI 에서 검사한다. 지금은 이 파일이 계약이다.
 * 폼 검증과 목업 데이터가 모두 이 스키마를 쓴다.
 */
import { z } from 'zod'

export const GENDERS = ['남', '여'] as const
export const CALENDAR_TYPES = ['solar', 'lunar'] as const

/**
 * 상담 주제 5분류 (PRD §3.4, v2.13).
 * 기존 3분류(연애·직업·재물)를 실제로 들어오는 질문에 맞춰 다시 나눴다.
 * 주제마다 사주와 타로의 판단 비중이 다르다 — TOPIC_META 참고.
 */
export const TOPICS = ['재회운', '상대방속마음', '연애', '재물', '대인관계'] as const
export const ELEMENTS = ['목', '화', '토', '금', '수'] as const

export type Topic = (typeof TOPICS)[number]

/** 주제별 메타 — 화면 안내와 LLM 프롬프트가 같은 값을 쓴다 (PRD §3.4) */
export const TOPIC_META: Record<
  Topic,
  { question: string; saju: number; tarot: number; caveat?: string }
> = {
  재회운: {
    question: '그 사람과 다시 만날 수 있을까요',
    saju: 3,
    tarot: 7,
    caveat: '시점을 단정하지 않고 조건으로 읽습니다',
  },
  상대방속마음: {
    question: '그 사람 마음이 어떤 건가요',
    saju: 1,
    tarot: 9,
    caveat: '상대의 생년월일 없이 카드 흐름으로 읽은 것입니다',
  },
  연애: { question: '새로운 인연이 들어올까요', saju: 5, tarot: 5 },
  재물: { question: '돈은 언제 풀릴까요', saju: 7, tarot: 3 },
  대인관계: { question: '사람들과 계속 부딪히는데요', saju: 6, tarot: 4 },
}

export const MAX_TOPICS = TOPICS.length

/**
 * 타로 3장 고정 스프레드 (PRD §8.6).
 * 주제 수(1~5)와 무관하게 항상 3장이다. 이 3장이 모든 주제의 공통 근거가 된다.
 * 주제당 1장씩 뽑지 않는 이유: 5장이 되면 리포트가 길어지고 카드별 해석이 서로 어긋난다.
 */
export const SPREAD = [
  { key: '현재', label: '지금 놓인 자리', reads: '현재 상황·기운의 상태' },
  { key: '조언', label: '지금 할 수 있는 것', reads: '움직일 수 있는 지점' },
  { key: '방향', label: '이대로 가면', reads: '흐름의 방향(확정된 결과가 아니다)' },
] as const

export const SPREAD_POSITIONS = ['현재', '조언', '방향'] as const
export type SpreadPosition = (typeof SPREAD_POSITIONS)[number]
export type ElementName = (typeof ELEMENTS)[number]

/**
 * 출생지 — 진태양시 보정용 경도 (PRD §8.2, §6.1 필드 7).
 *
 * 17개 시·도 전체. 도(道)는 **도청 소재지 기준 근사값**이다.
 * 같은 도 안에서도 동서로 벌어지면 몇 분 차이가 나지만, 시주는 2시간 단위로
 * 갈리므로 도 단위면 충분하다. 필요해지면 시·군 단위로 늘리면 된다.
 *
 * ⚠️ 서버(`backend/app/routers/readings.py` BIRTH_PLACES)와 **이름이 정확히 같아야** 한다.
 *    서버가 화이트리스트로 검증하므로 하나라도 다르면 400 이 난다.
 */
export const BIRTH_PLACES = [
  { name: '서울', longitude: 126.978 },
  { name: '경기(수원)', longitude: 127.01 },
  { name: '인천', longitude: 126.705 },
  { name: '강원(춘천)', longitude: 127.729 },
  { name: '충북(청주)', longitude: 127.489 },
  { name: '충남(홍성)', longitude: 126.661 },
  { name: '세종', longitude: 127.289 },
  { name: '대전', longitude: 127.385 },
  { name: '전북(전주)', longitude: 127.148 },
  { name: '전남(무안)', longitude: 126.463 },
  { name: '광주', longitude: 126.851 },
  { name: '경북(안동)', longitude: 128.729 },
  { name: '대구', longitude: 128.601 },
  { name: '경남(창원)', longitude: 128.682 },
  { name: '부산', longitude: 129.075 },
  { name: '울산', longitude: 129.311 },
  { name: '제주', longitude: 126.531 },
  { name: '해외·모름', longitude: 135.0 },
] as const

/** 표준자오선(동경 135°) 대비 진태양시 보정값(분). 1° = 4분 */
export function correctionMinutes(longitude: number): number {
  return Math.round((longitude - 135) * 4)
}

// ── 요청 (PRD §10.2) ─────────────────────────────────────────

export const readingInputSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, '이름을 입력해 주세요.')
      .max(20, '이름은 20자까지 입력할 수 있습니다.')
      // 개행·제어문자 제거는 프롬프트 인젝션 대비 (PRD §12.18)
      .refine((v) => !/[\r\n\t]/.test(v), '이름에 줄바꿈은 넣을 수 없습니다.'),
    gender: z.enum(GENDERS, {
      errorMap: () => ({ message: '성별을 선택해 주세요.' }),
    }),
    calendar_type: z.enum(CALENDAR_TYPES),
    birth_date: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/, '생년월일을 선택해 주세요.'),
    is_leap_month: z.boolean(),
    /** null = 시간 모름 (PRD §8.3) */
    birth_time: z
      .string()
      .regex(/^([01]\d|2[0-3]):[0-5]\d$/, '시각 형식이 올바르지 않습니다.')
      .nullable(),
    birth_place: z.string().min(1),
    topics: z
      .array(z.enum(TOPICS))
      .min(1, '주제를 하나 이상 선택해 주세요.')
      .max(MAX_TOPICS),
    tarot_mode: z.enum(['auto', 'manual']),
    privacy_agreed: z
      .boolean()
      .refine((v) => v === true, '개인정보 수집·이용에 동의해 주세요.'),
  })
  .refine(
    (v) => {
      const [y] = v.birth_date.split('-').map(Number)
      return y >= 1900 && y <= new Date().getFullYear()
    },
    { message: '1900년 이후 날짜만 지원합니다.', path: ['birth_date'] },
  )

export type ReadingInput = z.infer<typeof readingInputSchema>

/** 서버로 보내는 형태 — 동의 여부는 별도 필드로 전달하지 않는다 */
export type ReadingRequest = Omit<ReadingInput, 'privacy_agreed'>

// ── 응답 (PRD §10.2) ─────────────────────────────────────────

export const pillarSchema = z.object({
  gan: z.string(),
  ji: z.string(),
  ko: z.string(),
})

export const readingSchema = z.object({
  id: z.string(),
  input_echo: z.object({
    solar_datetime: z.string(),
    true_solar_correction_min: z.number(),
    dst_applied: z.boolean(),
    midnight_rule: z.string(),
    standard_meridian: z.number(),
  }),
  pillars: z.object({
    year: pillarSchema,
    month: pillarSchema,
    day: pillarSchema,
    /** 시간 모름이면 null (PRD §8.3) */
    hour: pillarSchema.nullable(),
  }),
  elements: z.object({
    목: z.number(),
    화: z.number(),
    토: z.number(),
    금: z.number(),
    수: z.number(),
    verdict: z.array(z.string()),
  }),
  /** 항상 3장 (PRD §8.6) */
  tarot: z
    .array(
      z.object({
        position: z.enum(SPREAD_POSITIONS),
        position_ko: z.string(),
        card: z.string(),
        card_ko: z.string(),
        reversed: z.boolean(),
        keywords: z.array(z.string()),
      }),
    )
    .length(3),
  /** LLM 실패 시 null — 계산 결과만 보여준다 (부분 성공, PRD §11.3) */
  report: z
    .object({
      monthly_flow: z.array(z.string()),
      advice: z.record(z.string(), z.string()),
      keywords: z.array(z.string()),
      disclaimer: z.string(),
    })
    .nullable(),
  /** 어떤 모델이 문장을 썼는지 — 리포트에 표기한다 (PRD §6.3 ⑦) */
  report_model: z.string().nullable().optional(),
  engine_version: z.string(),
  /** 같은 링크가 항상 같은 카드를 내도록 저장한다 (PRD §8.6) */
  tarot_seed: z.number().optional(),
  /** 문체 학습(Q7) 전 초안임을 표시 (PRD §11.5) */
  draft_before_tone_learning: z.boolean(),
})

export type Reading = z.infer<typeof readingSchema>

// ── 에러 (PRD §10.6) ─────────────────────────────────────────

export const apiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    field: z.string().optional(),
    trace_id: z.string().optional(),
  }),
})

export type ApiError = z.infer<typeof apiErrorSchema>
