/**
 * 리포트 화면 (PRD §6.3 — 9블록 구성).
 * LLM 해석이 없어도(report === null) 계산 결과는 보여준다 — 부분 성공 (PRD §11.3).
 */
import { Link, useParams } from 'react-router-dom'
import ElementBar from '../components/report/ElementBar'
import PillarGrid from '../components/report/PillarGrid'
import TarotCard from '../components/report/TarotCard'
import { Card } from '../components/ui'
import { getReading } from '../lib/store'

export default function ResultPage() {
  const { id = '' } = useParams()
  const reading = getReading(id)

  if (!reading) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-5 px-6 text-center">
        <p className="font-display text-xl font-bold text-ink-900 dark:text-paper-100">
          리포트를 찾을 수 없습니다
        </p>
        <p className="text-sm leading-relaxed text-ink-500 dark:text-ink-300">
          아직 저장 기능이 붙기 전이라, 탭을 닫으면 리포트가 남지 않습니다.
          <br />
          다시 입력해 주세요.
        </p>
        <Link
          to="/"
          className="rounded-xl bg-ink-900 px-6 py-3 text-sm font-semibold text-paper-50 dark:bg-gold-500 dark:text-ink-950"
        >
          처음으로
        </Link>
      </main>
    )
  }

  const { input_echo: echo, pillars, elements, tarot, report, period, interpretation } = reading

  return (
    <div className="min-h-screen bg-paper-50 pb-20 dark:bg-ink-950">
      {/* ① 헤더 */}
      <header className="border-b border-paper-200 bg-gradient-to-b from-ink-900 to-ink-950 dark:border-ink-800">
        <div className="starfield mx-auto max-w-2xl px-5 py-10">
          <Link to="/" className="text-xs text-ink-400 hover:text-gold-300">
            ← 다시 입력
          </Link>
          <h1 className="mt-4 font-display text-2xl font-bold text-paper-50">
            이번 달 흐름 리포트
          </h1>
          <p className="mt-2 text-sm font-medium text-gold-300">{period.label}</p>
          <p className="mt-1 text-sm text-ink-300">
            {echo.solar_datetime.slice(0, 10)}
            {pillars.hour ? ` ${echo.solar_datetime.slice(11, 16)}` : ' (시간 미상)'} 기준
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-2xl space-y-5 px-5 py-8">
        {report === null && (
          <div
            role="alert"
            className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
          >
            해석 문장이 아직 없습니다. 아래 계산 결과(원국·오행·타로)는 실제 값이며,
            문장 생성은 다음 단계에서 붙습니다.
          </div>
        )}

        {/* 사주 풀이 — 평생 값이라 이번 달 흐름보다 앞에 둔다 (PRD §8.7) */}
        <Card className="p-6 sm:p-7">
          <h2 className="font-display text-lg font-bold text-ink-900 dark:text-paper-100">
            사주 풀이
          </h2>
          <p className="mt-1.5 text-xs text-ink-400 dark:text-ink-300">
            타고난 결 — 달마다 바뀌지 않습니다
          </p>

          <div className="mt-4 rounded-xl bg-paper-100/70 px-4 py-3 dark:bg-ink-900/60">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              <span className="text-xs text-ink-400 dark:text-ink-300">일간(나)</span>
              <span className="font-display text-lg font-bold text-ink-900 dark:text-paper-100">
                {interpretation.day_master_ko} ({interpretation.day_master_gan})
              </span>
              <span className="text-xs text-ink-500 dark:text-ink-300">
                {interpretation.yin_yang}의 {interpretation.element} · {interpretation.day_master_image}
              </span>
            </div>
            {interpretation.dominant.length > 0 && (
              <p className="mt-2 text-xs text-ink-500 dark:text-ink-300">
                가장 두드러진 십성:{' '}
                <strong className="font-semibold text-ink-800 dark:text-paper-200">
                  {interpretation.dominant.join(' · ')}
                </strong>
              </p>
            )}
          </div>

          {report ? (
            <ol className="mt-4 space-y-3">
              {report.saju_reading.map((line, i) => (
                <li key={i} className="flex gap-3 text-[15px] leading-relaxed">
                  <span className="font-display font-bold text-gold-600 dark:text-gold-400">
                    {i + 1}
                  </span>
                  <span className="text-ink-700 dark:text-paper-200">{line}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-4 text-sm text-ink-400 dark:text-ink-300">
              풀이 문장은 아직 없습니다. 위 계산 값은 실제 값입니다.
            </p>
          )}

          {/* 십성 분포 */}
          {Object.keys(interpretation.shishen).length > 0 && (
            <div className="mt-5 flex flex-wrap gap-1.5">
              {Object.entries(interpretation.shishen)
                .sort((a, b) => b[1] - a[1])
                .map(([name, count]) => (
                  <span
                    key={name}
                    className="rounded-md bg-paper-200/70 px-2 py-1 text-xs text-ink-600 dark:bg-ink-800 dark:text-ink-300"
                  >
                    {name} {count}
                  </span>
                ))}
            </div>
          )}
        </Card>

        {/* ⑤ 이번 달 흐름 — 핵심 산출물이므로 위로 올린다 */}
        {report && (
          <Card className="p-6 sm:p-7">
            <h2 className="font-display text-lg font-bold text-ink-900 dark:text-paper-100">
              이번 달 흐름
            </h2>
            <ol className="mt-4 space-y-3">
              {report.monthly_flow.map((line, i) => (
                <li key={i} className="flex gap-3 text-[15px] leading-relaxed">
                  <span className="font-display font-bold text-gold-600 dark:text-gold-400">
                    {i + 1}
                  </span>
                  <span className="text-ink-700 dark:text-paper-200">{line}</span>
                </li>
              ))}
            </ol>
            {report.keywords.length > 0 && (
              <div className="mt-5 flex flex-wrap gap-2">
                {report.keywords.map((k) => (
                  <span
                    key={k}
                    className="rounded-full bg-gold-500/12 px-3 py-1 text-xs font-medium text-gold-700 dark:text-gold-300"
                  >
                    #{k}
                  </span>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* ⑥ 카테고리 조언 */}
        {report && (
          <Card className="divide-y divide-paper-200 dark:divide-ink-800">
            {Object.entries(report.advice).map(([topic, text]) => (
              <div key={topic} className="p-6 sm:px-7">
                <h3 className="font-display text-base font-bold text-ink-900 dark:text-paper-100">
                  {topic}
                </h3>
                <p className="mt-2 text-[15px] leading-relaxed text-ink-600 dark:text-ink-300">
                  {text}
                </p>
              </div>
            ))}
          </Card>
        )}

        {/* ④ 타로 */}
        <Card className="p-6 sm:p-7">
          <h2 className="font-display text-lg font-bold text-ink-900 dark:text-paper-100">
            뽑힌 카드
          </h2>
          <p className="mt-1.5 text-xs text-ink-400 dark:text-ink-300">
            세 장을 다섯 주제의 공통 근거로 읽습니다 · 이 달 안에는 카드가 바뀌지 않습니다
          </p>
          {/* 퍼블릭 도메인 이미지 출처 표기 (PRD §18.1 Q5) */}
          <p className="mt-1 text-[11px] text-ink-300 dark:text-ink-400">
            카드 그림: 라이더-웨이트 타로(1909, Pamela Colman Smith) · 퍼블릭 도메인
          </p>
          {/* 3장 고정 스프레드 (PRD §8.6) */}
          <div className="mt-5 grid grid-cols-3 gap-4">
            {tarot.map((c) => (
              <TarotCard key={c.position} card={c} />
            ))}
          </div>
        </Card>

        {/* ② 원국 4주 */}
        <Card className="p-6 sm:p-7">
          <h2 className="font-display text-lg font-bold text-ink-900 dark:text-paper-100">
            사주 원국
          </h2>
          <p className="mt-1.5 text-xs text-ink-400 dark:text-ink-300">
            무엇을 근거로 읽었는지 함께 보여드립니다
          </p>
          <div className="mt-5">
            <PillarGrid pillars={pillars} />
          </div>
        </Card>

        {/* ③ 오행 */}
        <Card className="p-6 sm:p-7">
          <h2 className="font-display text-lg font-bold text-ink-900 dark:text-paper-100">
            오행 분포
          </h2>
          <div className="mt-5">
            <ElementBar elements={elements} />
          </div>
        </Card>

        {/* ⑦ 계산 기준 — 어떤 기준을 썼는지 밝힌다 (PRD §18.1 Q6) */}
        <details className="rounded-2xl border border-paper-200 bg-white/60 px-6 py-4 text-sm dark:border-ink-800 dark:bg-ink-900/40">
          <summary className="cursor-pointer font-medium text-ink-600 dark:text-ink-300">
            계산 기준 보기
          </summary>
          <dl className="mt-4 space-y-2 text-xs text-ink-500 dark:text-ink-400">
            <div className="flex justify-between gap-4">
              <dt>기준 시각</dt>
              {/* 시간 미상일 때 12:00 을 그대로 보이면 오해를 부른다 (PRD §8.3) */}
              <dd className="tabular-nums">
                {pillars.hour
                  ? echo.solar_datetime
                  : `${echo.solar_datetime.slice(0, 10)} (시간 미상)`}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>진태양시 보정</dt>
              <dd className="tabular-nums">{echo.true_solar_correction_min}분</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>서머타임</dt>
              <dd>{echo.dst_applied ? '적용' : '미적용'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>표준자오선</dt>
              <dd className="tabular-nums">동경 {echo.standard_meridian}°</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>자시 기준</dt>
              <dd>{echo.midnight_rule}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>이번 달 기운</dt>
              <dd>
                세운 {period.year_ko}년 · 월운 {period.month_ko}월
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>엔진 버전</dt>
              <dd>{reading.engine_version}</dd>
            </div>
            {reading.report_model && (
              <div className="flex justify-between gap-4">
                <dt>문장 생성</dt>
                <dd>{reading.report_model}</dd>
              </div>
            )}
          </dl>
        </details>

        {/* ⑧ 면책 */}
        <p className="px-1 text-xs leading-relaxed text-ink-400 dark:text-ink-400">
          {report?.disclaimer ??
            '이 리포트는 상담 참고용이며 의료·법률·투자 판단의 근거가 아닙니다.'}
          {reading.draft_before_tone_learning && ' · 문체 학습 전 초안입니다.'}
        </p>
      </main>
    </div>
  )
}
