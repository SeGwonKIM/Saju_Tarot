/**
 * 입력 폼 (PRD §6.1 필드 1~10).
 *
 * 상태 하나(calendarType)가 바뀌면 날짜 선택지·윤달 노출·보조 텍스트가 함께 파생된다
 * (PRD §5.3 상태 정의).
 * 프론트 검증은 편의일 뿐이고, 같은 규칙을 서버에서 다시 검증한다 (PRD §12.2).
 */
import { useMemo, useState } from 'react'
import {
  BIRTH_PLACES,
  CALENDAR_TYPES,
  GENDERS,
  MAX_TOPICS,
  TOPICS,
  TOPIC_META,
  readingInputSchema,
  type ReadingInput,
  type ReadingRequest,
  type Topic,
} from '../../schemas/reading'
import {
  JIJI_HOURS,
  YEARS,
  daysInMonth,
  formatDateKo,
  leapMonthsOf,
  mockConvert,
} from '../../lib/calendar'
import { eulReul } from '../../lib/korean'
import { Card, Checkbox, Chip, Field, Segmented, Select, TextInput } from '../ui'

type Errors = Partial<Record<keyof ReadingInput | 'form', string>>

export default function BirthForm({
  onSubmit,
  submitting,
}: {
  onSubmit: (input: ReadingRequest) => void
  submitting: boolean
}) {
  const [name, setName] = useState('')
  const [gender, setGender] = useState<'남' | '여' | undefined>()
  const [calendarType, setCalendarType] = useState<'solar' | 'lunar'>('solar')
  const [year, setYear] = useState('1990')
  const [month, setMonth] = useState('1')
  const [day, setDay] = useState('1')
  const [isLeapMonth, setIsLeapMonth] = useState(false)
  const [timeMode, setTimeMode] = useState<'clock' | 'jiji'>('clock')
  const [hour, setHour] = useState('12')
  const [minute, setMinute] = useState('00')
  const [jiji, setJiji] = useState('11:30')
  const [timeUnknown, setTimeUnknown] = useState(false)
  const [place, setPlace] = useState('서울')
  const [topics, setTopics] = useState<Topic[]>([...TOPICS])
  const [agreed, setAgreed] = useState(false)
  const [errors, setErrors] = useState<Errors>({})
  const [touched, setTouched] = useState<Record<string, boolean>>({})

  const maxDay = daysInMonth(calendarType, Number(year), Number(month))
  const leapMonths = calendarType === 'lunar' ? leapMonthsOf(Number(year)) : []
  const showLeap = leapMonths.includes(Number(month))

  const birthDate = `${year}-${String(month).padStart(2, '0')}-${String(
    Math.min(Number(day), maxDay),
  ).padStart(2, '0')}`

  const birthTime = timeUnknown ? null : timeMode === 'jiji' ? jiji : `${hour.padStart(2, '0')}:${minute}`

  /** 토글해도 입력값을 버리지 않고 변환해 보여준다 (PRD §6.1 폼 UX 규칙) */
  const converted = useMemo(
    () => mockConvert(calendarType, birthDate, isLeapMonth),
    [calendarType, birthDate, isLeapMonth],
  )

  const missing: string[] = []
  if (!name.trim()) missing.push('이름')
  if (!gender) missing.push('성별')
  if (topics.length === 0) missing.push('상담 주제')
  if (!agreed) missing.push('개인정보 동의')
  const ready = missing.length === 0

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const candidate = {
      name,
      gender: gender as '남' | '여',
      calendar_type: calendarType,
      birth_date: birthDate,
      is_leap_month: showLeap ? isLeapMonth : false,
      birth_time: birthTime,
      birth_place: place,
      topics,
      tarot_mode: 'auto' as const,
      privacy_agreed: agreed,
    }
    const parsed = readingInputSchema.safeParse(candidate)
    if (!parsed.success) {
      const next: Errors = {}
      for (const issue of parsed.error.issues) {
        const key = (issue.path[0] as keyof ReadingInput) ?? 'form'
        next[key] ??= issue.message
      }
      setErrors(next)
      setTouched({ name: true, gender: true, topics: true, privacy_agreed: true })
      return
    }
    setErrors({})
    const { privacy_agreed: _agreed, ...request } = parsed.data
    onSubmit(request)
  }

  return (
    <Card className="p-6 sm:p-8">
      <form onSubmit={handleSubmit} className="space-y-7" noValidate>
        {/* ── 1. 누구의 사주인가 ───────────────────────────── */}
        <fieldset className="space-y-5">
          <legend className="mb-1 font-display text-lg font-bold text-ink-900 dark:text-paper-100">
            누구의 사주인가요
          </legend>

          <Field
            label="이름"
            required
            htmlFor="name"
            error={touched.name ? errors.name : undefined}
            hint="리포트 인사말에만 쓰입니다"
          >
            <TextInput
              id="name"
              value={name}
              onChange={(v) => {
                setName(v)
                if (errors.name) setErrors((e) => ({ ...e, name: undefined }))
              }}
              placeholder="홍길동"
              maxLength={20}
              invalid={Boolean(touched.name && errors.name)}
            />
          </Field>

          <Field
            label="성별"
            required
            error={touched.gender ? errors.gender : undefined}
            hint="대운의 방향을 정하는 데 쓰입니다"
          >
            <Segmented
              ariaLabel="성별"
              value={gender}
              onChange={(v) => setGender(v)}
              options={GENDERS.map((g) => ({ value: g, label: g }))}
            />
          </Field>
        </fieldset>

        <hr className="border-paper-200 dark:border-ink-800" />

        {/* ── 2. 태어난 날 ─────────────────────────────────── */}
        <fieldset className="space-y-5">
          <legend className="mb-1 font-display text-lg font-bold text-ink-900 dark:text-paper-100">
            태어난 날과 시간
          </legend>

          <Field label="달력" required hint="어느 달력으로 아시나요">
            <Segmented
              ariaLabel="달력 구분"
              value={calendarType}
              onChange={(v) => setCalendarType(v)}
              options={CALENDAR_TYPES.map((c) => ({
                value: c,
                label: c === 'solar' ? '양력' : '음력',
              }))}
            />
          </Field>

          <Field label="생년월일" required htmlFor="year" error={errors.birth_date}>
            <div className="grid grid-cols-3 gap-2">
              <Select id="year" ariaLabel="태어난 해" value={year} onChange={setYear}>
                {YEARS.map((y) => (
                  <option key={y} value={String(y)}>
                    {y}년
                  </option>
                ))}
              </Select>
              <Select ariaLabel="태어난 달" value={month} onChange={setMonth}>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={String(m)}>
                    {m}월
                  </option>
                ))}
              </Select>
              <Select ariaLabel="태어난 날" value={day} onChange={setDay}>
                {Array.from({ length: maxDay }, (_, i) => i + 1).map((d) => (
                  <option key={d} value={String(d)}>
                    {d}일
                  </option>
                ))}
              </Select>
            </div>

            {/* 변환 결과를 보조 텍스트로 (PRD §6.1) */}
            <p className="pt-1 text-xs text-ink-400 dark:text-ink-300">
              {calendarType === 'solar'
                ? `${formatDateKo(birthDate, 'solar')} · 음력 ${converted.lunar_date.slice(5).replace('-', '.')} 무렵`
                : `음력 ${birthDate.slice(5).replace('-', '.')}${isLeapMonth ? ' 윤달' : ' 평달'} · 양력 ${converted.solar_date} 무렵`}
              <span className="ml-1 opacity-70">(정확한 변환은 저장 시 계산됩니다)</span>
            </p>

            {/* 음력 + 그 해 그 달에 윤달이 있을 때만 (PRD §6.1 필드 5) */}
            {showLeap && (
              <div className="rise rounded-xl bg-plum-500/8 px-4 py-3 dark:bg-plum-400/12">
                <Checkbox id="leap" checked={isLeapMonth} onChange={setIsLeapMonth}>
                  이 해 {month}월은 <strong>윤달</strong>이 있습니다 — 윤달에 태어나셨나요?
                </Checkbox>
              </div>
            )}
          </Field>

          <Field
            label="태어난 시간"
            required
            hint={timeUnknown ? '시주를 제외해 계산합니다' : '시간대로 골라도 됩니다'}
          >
            {!timeUnknown && (
              <>
                <Segmented
                  ariaLabel="시간 입력 방식"
                  value={timeMode}
                  onChange={(v) => setTimeMode(v)}
                  options={[
                    { value: 'clock' as const, label: '시각으로' },
                    { value: 'jiji' as const, label: '12지시로' },
                  ]}
                />
                <div className="pt-2">
                  {timeMode === 'clock' ? (
                    <div className="grid grid-cols-2 gap-2">
                      <Select ariaLabel="시" value={hour} onChange={setHour}>
                        {Array.from({ length: 24 }, (_, i) => i).map((h) => (
                          <option key={h} value={String(h)}>
                            {String(h).padStart(2, '0')}시
                          </option>
                        ))}
                      </Select>
                      <Select ariaLabel="분" value={minute} onChange={setMinute}>
                        {['00', '10', '20', '30', '40', '50'].map((m) => (
                          <option key={m} value={m}>
                            {m}분
                          </option>
                        ))}
                      </Select>
                    </div>
                  ) : (
                    <Select ariaLabel="12지시" value={jiji} onChange={setJiji}>
                      {JIJI_HOURS.map((j) => (
                        <option key={j.ji} value={j.time}>
                          {j.label}
                        </option>
                      ))}
                    </Select>
                  )}
                </div>
              </>
            )}
            <div className="pt-2">
              <Checkbox id="time-unknown" checked={timeUnknown} onChange={setTimeUnknown}>
                태어난 시간을 모릅니다
              </Checkbox>
            </div>
          </Field>

          <Field label="태어난 곳" hint="시간을 더 정확히 보정합니다">
            <Select ariaLabel="태어난 곳" value={place} onChange={setPlace}>
              {BIRTH_PLACES.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
            </Select>
          </Field>
        </fieldset>

        <hr className="border-paper-200 dark:border-ink-800" />

        {/* ── 3. 무엇이 궁금한가 ───────────────────────────── */}
        <fieldset className="space-y-5">
          <legend className="mb-1 font-display text-lg font-bold text-ink-900 dark:text-paper-100">
            무엇이 궁금하세요
          </legend>
          <Field
            label="상담 주제"
            required
            error={touched.topics ? errors.topics : undefined}
            hint={`${topics.length}/${MAX_TOPICS} 선택 · 고른 주제만 담깁니다`}
          >
            <div className="grid gap-2 sm:grid-cols-2">
              {TOPICS.map((t) => (
                <Chip
                  key={t}
                  label={t}
                  sub={TOPIC_META[t].question}
                  active={topics.includes(t)}
                  onClick={() =>
                    setTopics((prev) =>
                      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
                    )
                  }
                />
              ))}
            </div>

            {/* 상대의 사주 없이 읽는 주제는 한계를 미리 밝힌다 (PRD §3.4) */}
            {topics.some((t) => TOPIC_META[t].caveat) && (
              <ul className="rise mt-1 space-y-1 rounded-xl bg-plum-500/8 px-4 py-3 text-xs leading-relaxed text-ink-600 dark:bg-plum-400/12 dark:text-ink-300">
                {topics
                  .filter((t) => TOPIC_META[t].caveat)
                  .map((t) => (
                    <li key={t}>
                      <strong className="font-semibold">{t}</strong> — {TOPIC_META[t].caveat}
                    </li>
                  ))}
              </ul>
            )}
          </Field>
        </fieldset>

        {/* ── 동의 + 제출 ──────────────────────────────────── */}
        <div className="space-y-4 rounded-xl bg-paper-100/70 p-4 dark:bg-ink-900/60">
          <Checkbox id="agree" checked={agreed} onChange={setAgreed}>
            생년월일·시간을 <strong>리포트 생성 목적</strong>으로만 쓰고,{' '}
            <strong>90일 뒤 자동 삭제</strong>하는 것에 동의합니다.
            <span className="ml-1 text-gold-600 dark:text-gold-400">*</span>
          </Checkbox>
          {touched.privacy_agreed && errors.privacy_agreed && (
            <p role="alert" className="text-xs font-medium text-rose-600 dark:text-rose-400">
              {errors.privacy_agreed}
            </p>
          )}

          <button
            type="submit"
            disabled={!ready || submitting}
            className="w-full rounded-xl bg-gradient-to-b from-ink-800 to-ink-900 px-6 py-4 text-base font-semibold text-paper-50 shadow-lg transition-all hover:from-ink-700 hover:to-ink-800 disabled:cursor-not-allowed disabled:from-paper-300 disabled:to-paper-300 disabled:text-ink-400 disabled:shadow-none dark:from-gold-500 dark:to-gold-600 dark:text-ink-950 dark:hover:from-gold-400 dark:hover:to-gold-500 dark:disabled:from-ink-800 dark:disabled:to-ink-800 dark:disabled:text-ink-400"
          >
            {submitting ? '사주팔자를 세우는 중…' : '리포트 만들기'}
          </button>

          {/* 무엇이 남았는지 알려준다 (PRD §6.1) */}
          <p className="text-center text-xs text-ink-400 dark:text-ink-300">
            {ready
              ? '입력하신 정보는 리포트 생성에만 쓰입니다'
              : `${missing.join(' · ')}${eulReul(missing[missing.length - 1])} 입력하면 시작할 수 있어요`}
          </p>
        </div>
      </form>
    </Card>
  )
}
