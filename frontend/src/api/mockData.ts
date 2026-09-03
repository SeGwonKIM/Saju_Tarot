/**
 * 목업 데이터 (PRD §7).
 *
 * 규칙
 *  - 컴포넌트 안에 데이터를 두지 않는다. 전부 이 파일에 모은다.
 *  - 모양은 PRD §10.2 응답 예시와 **똑같이** 맞춘다. 모양이 다르면 그 자체가 계약 불일치다.
 *  - 정상 / 시간 모름 / 오행 0 / LLM 실패 / 429 / 500 케이스를 모두 담는다 (§7.3).
 */
import type { Reading, ReadingRequest } from '../schemas/reading'

const GAN = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
const GAN_H = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
const JI = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']
const JI_H = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

function pillar(ganIdx: number, jiIdx: number) {
  const g = ((ganIdx % 10) + 10) % 10
  const j = ((jiIdx % 12) + 12) % 12
  return { gan: GAN_H[g], ji: JI_H[j], ko: `${GAN[g]}${JI[j]}` }
}

const TAROT_POOL = [
  { card: 'The Star', card_ko: '별', keywords: ['희망', '회복', '치유'] },
  { card: 'The Sun', card_ko: '태양', keywords: ['성취', '활력', '명료'] },
  { card: 'Wheel of Fortune', card_ko: '운명의 수레바퀴', keywords: ['전환점', '순환', '기회'] },
  { card: 'Eight of Pentacles', card_ko: '펜타클 8', keywords: ['숙련', '반복', '축적'] },
  { card: 'Two of Cups', card_ko: '컵 2', keywords: ['교류', '균형', '약속'] },
  { card: 'The Hermit', card_ko: '은둔자', keywords: ['성찰', '거리두기', '준비'] },
  { card: 'Three of Wands', card_ko: '완드 3', keywords: ['확장', '전망', '기다림'] },
  { card: 'The Empress', card_ko: '여황제', keywords: ['풍요', '돌봄', '결실'] },
]

/** 입력값으로부터 결정론적으로 목업 리포트를 만든다 (같은 입력 → 같은 결과) */
export function mockReading(input: ReadingRequest): Reading {
  const [y, m, d] = input.birth_date.split('-').map(Number)
  const seed = y * 372 + m * 31 + d + (input.birth_time ? Number(input.birth_time.slice(0, 2)) : 0)

  const hourKnown = input.birth_time !== null
  const counts: Record<'목' | '화' | '토' | '금' | '수', number> = {
    목: 0, 화: 0, 토: 0, 금: 0, 수: 0,
  }
  const order = ['목', '화', '토', '금', '수'] as const
  const total = hourKnown ? 8 : 6
  for (let i = 0; i < total; i++) counts[order[(seed + i * 3) % 5]]++

  const verdict: string[] = []
  for (const k of order) {
    const ratio = counts[k] / total
    if (counts[k] === 0) verdict.push(`${k} 없음`)
    else if (ratio >= 0.4) verdict.push(`${k} 과다`)
    else if (ratio <= 0.05) verdict.push(`${k} 부족`)
  }
  if (verdict.length === 0) verdict.push('오행이 고르게 분포')

  const tarot = input.topics.map((category, i) => {
    const t = TAROT_POOL[(seed + i * 3) % TAROT_POOL.length]
    return { category, ...t, reversed: (seed + i) % 3 === 0 }
  })

  return {
    id: `mock-${seed}`,
    input_echo: {
      solar_datetime: `${input.birth_date}T${input.birth_time ?? '12:00'}:00+09:00`,
      true_solar_correction_min: -32,
      dst_applied: false,
      midnight_rule: '조자시',
    },
    pillars: {
      year: pillar(seed, seed + 4),
      month: pillar(seed + 2, m + 1),
      day: pillar(seed + 5, seed + 7),
      hour: hourKnown ? pillar(seed + 8, Number(input.birth_time!.slice(0, 2)) / 2) : null,
    },
    elements: { ...counts, verdict },
    tarot,
    report: {
      monthly_flow: [
        '큰 결정을 서두르기보다 흐름을 살피기 좋은 달입니다.',
        '중순 무렵 미뤄둔 일에서 진척이 생기는 흐름입니다.',
        '몸보다 마음이 먼저 지치기 쉬우니 쉬는 시간을 먼저 정해 두시면 좋습니다.',
      ],
      advice: Object.fromEntries(
        input.topics.map((t) => [
          t,
          {
            연애: '먼저 다가가기보다 상대의 속도를 한 번 확인해 보시는 편이 좋습니다.',
            직업: '새 일을 벌이기보다 하던 일의 완성도를 올리는 데 힘이 붙는 흐름입니다.',
            재물: '큰 지출은 다음 달로 미루고 고정비를 한 번 정리해 보시면 좋습니다.',
          }[t],
        ]),
      ),
      keywords: ['정리', '기다림', '회복'],
      disclaimer: '이 리포트는 상담 참고용이며 의료·법률·투자 판단의 근거가 아닙니다.',
    },
    engine_version: 'mock-0.1.0',
    draft_before_tone_learning: true,
  }
}

/** LLM 실패 — 계산 결과만 보여주는 부분 성공 케이스 (PRD §11.3) */
export function mockReadingWithoutReport(input: ReadingRequest): Reading {
  return { ...mockReading(input), report: null }
}

/** 화면 개발용 고정 샘플 3건 */
export const MOCK_SAMPLES: Reading[] = [
  mockReading({
    name: '홍길동', gender: '여', calendar_type: 'lunar', birth_date: '1988-03-05',
    is_leap_month: false, birth_time: '20:30', birth_place: '서울',
    topics: ['연애', '직업', '재물'], tarot_mode: 'auto',
  }),
  // 시간 모름 (PRD §8.3)
  mockReading({
    name: '김세권', gender: '남', calendar_type: 'solar', birth_date: '1975-11-20',
    is_leap_month: false, birth_time: null, birth_place: '부산',
    topics: ['직업', '재물'], tarot_mode: 'auto',
  }),
  // LLM 실패
  mockReadingWithoutReport({
    name: '이영희', gender: '여', calendar_type: 'solar', birth_date: '2001-07-14',
    is_leap_month: false, birth_time: '03:10', birth_place: '대전',
    topics: ['연애'], tarot_mode: 'auto',
  }),
]
