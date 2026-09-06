/**
 * 리포트 화면 (PRD §6.3 — 9블록 구성).
 * LLM 해석이 없어도(report === null) 계산 결과는 보여준다 — 부분 성공 (PRD §11.3).
 */
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { createShareLink, fetchReading, fetchShared, generateReport } from '../api/readings'
import type { Reading } from '../schemas/reading'
import ElementBar from '../components/report/ElementBar'
import PillarGrid from '../components/report/PillarGrid'
import TarotCard from '../components/report/TarotCard'
import { Card } from '../components/ui'
import { getReading, saveReading, getName } from '../lib/store'

/**
 * 풀이를 기다리는 동안 보여주는 자리 (v3.0).
 *
 * 스피너만 돌리지 않는다. 계산은 이미 끝나 위에 다 나와 있으므로,
 * "무엇이 끝났고 무엇이 남았는지"를 말해 주는 편이 덜 불안하다.
 * 예상 시간을 함께 적어 손님이 새로고침하지 않게 한다 — 새로고침하면
 * 결과를 못 보고 요금만 나간다.
 */
function WritingNotice() {
  return (
    <div className="mt-4 rounded-xl border border-paper-200 bg-paper-100/70 px-4 py-4 dark:border-ink-800 dark:bg-ink-900/50">
      <ul className="space-y-1.5 text-sm">
        <li className="text-ink-500 dark:text-ink-300">
          <span aria-hidden="true" className="text-gold-600 dark:text-gold-400">✓</span> 만세력·오행 계산 완료
        </li>
        <li className="text-ink-500 dark:text-ink-300">
          <span aria-hidden="true" className="text-gold-600 dark:text-gold-400">✓</span> 타로 3장 뽑기 완료
        </li>
        <li className="flex items-center gap-2 font-medium text-ink-800 dark:text-paper-100">
          <span
            aria-hidden="true"
            className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gold-500 border-t-transparent motion-reduce:animate-none"
          />
          풀이를 쓰는 중입니다…
        </li>
      </ul>
      <p className="mt-3 text-xs text-ink-400 dark:text-ink-300">
        보통 <strong>10~20초</strong>쯤 걸립니다. 이 화면을 닫거나 새로고침하지 마세요.
      </p>
      <p className="sr-only" role="status" aria-live="polite">
        풀이 문장을 만드는 중입니다. 잠시만 기다려 주세요.
      </p>
    </div>
  )
}

export default function ResultPage({ mode = 'own' }: { mode?: 'own' | 'shared' }) {
  const { id = '', token = '' } = useParams()
  // 세션에 남아 있으면 그걸 쓰고, 없으면 서버에서 불러온다(새로고침·링크 재방문)
  const [reading, setReading] = useState<Reading | null>(
    mode === 'own' ? getReading(id) : null,
  )
  const [loading, setLoading] = useState(reading === null)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [sharing, setSharing] = useState(false)
  const [copied, setCopied] = useState(false)
  // 이름은 서버가 주지 않는다. 만든 사람의 브라우저에만 있고, 없으면 안 보인다.
  const name = mode === 'own' ? getName(id) : null

  // 풀이 문장은 계산과 따로 온다 (v3.0). 계산은 0.3초, 풀이는 14초.
  const [writing, setWriting] = useState(false)
  const [writeError, setWriteError] = useState<string | null>(null)

  useEffect(() => {
    if (reading) return
    const load = mode === 'shared' ? fetchShared(token) : fetchReading(id)
    load
      .then(setReading)
      .catch(() => setReading(null))
      .finally(() => setLoading(false))
  }, [id, token, mode, reading])

  // 계산만 있고 풀이가 없으면 이어서 받아온다.
  // 공유 링크(shared)는 남의 리포트라 만들지 않는다 — 요금이 나가면 안 된다.
  //
  // 요청 여부를 state 가 아니라 **ref** 로 기억한다. state 를 쓰면
  // setWriting(true) 가 이 effect 를 다시 돌리고, 그때 첫 실행의 정리 함수가
  // 취소 플래그를 세워 버려서 **응답이 와도 화면에 쓰지 못한다**(실제로 겪었다.
  // 서버는 200 을 줬는데 화면은 계속 "쓰는 중"이었다).
  const requestedFor = useRef<string | null>(null)

  useEffect(() => {
    if (mode !== 'own' || !reading || reading.report) return
    if (requestedFor.current === reading.id) return
    requestedFor.current = reading.id

    setWriting(true)
    setWriteError(null)
    generateReport(reading.id)
      .then((full) => {
        setReading(full)
        saveReading(full)
      })
      .catch((e) => {
        setWriteError(e instanceof Error ? e.message : '풀이를 만들지 못했습니다.')
      })
      .finally(() => setWriting(false))
  }, [mode, reading])

  // 풀이를 만드는 중에 창을 닫으려 하면 붙잡는다.
  // 여기서 나가면 손님은 결과를 못 보는데 요금은 이미 나간 뒤다.
  useEffect(() => {
    if (!writing) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [writing])

  async function handleShare() {
    setSharing(true)
    try {
      const url = await createShareLink(reading!.id)
      setShareUrl(url)
      await navigator.clipboard?.writeText(url).then(
        () => setCopied(true),
        () => setCopied(false),
      )
    } catch {
      setShareUrl(null)
    } finally {
      setSharing(false)
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm text-ink-400">
        리포트를 불러오는 중…
      </main>
    )
  }

  if (!reading) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-5 px-6 text-center">
        <p className="font-display text-xl font-bold text-ink-900 dark:text-paper-100">
          리포트를 찾을 수 없습니다
        </p>
        <p className="text-sm leading-relaxed text-ink-500 dark:text-ink-300">
          링크가 만료되었거나 없는 리포트입니다.
          <br />
          보관 기간(90일)이 지나면 자동으로 삭제됩니다.
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
          <h1 className="font-display text-2xl font-bold text-paper-50">
            이번 달 흐름 리포트
          </h1>
          <p className="mt-2 text-sm font-medium text-gold-300">{period.label}</p>
          {/* 공유 링크에는 생년월일시도 이름도 오지 않는다 (PRD §12.14).
              이름은 서버가 주지 않는다 — 만든 사람의 브라우저에만 있다. */}
          {echo.solar_datetime ? (
            <p className="mt-1 text-sm text-ink-300">
              {name && <span className="font-semibold text-paper-100">{name}</span>}
              {name && ' · '}
              {echo.solar_datetime.slice(0, 10)}
              {pillars.hour ? ` ${echo.solar_datetime.slice(11, 16)}` : ' (시간 미상)'} 기준
            </p>
          ) : (
            <p className="mt-1 text-sm text-ink-400">청단사주타로</p>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-2xl space-y-5 px-5 py-8">
        {/* 풀이를 기다리는 중에는 띄우지 않는다 — 아래 사주 풀이 칸이 진행 상황을
            보여주고 있고, 여기까지 경고를 띄우면 뭔가 잘못된 것처럼 보인다.
            정말로 만들지 못한 경우(생성 실패·옛 리포트)에만 알린다. */}
        {report === null && !writing && (
          <div
            role="alert"
            className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
          >
            해석 문장이 아직 없습니다. 아래 계산 결과(원국·오행·타로)는 실제 값입니다.
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
          ) : writing ? (
            <WritingNotice />
          ) : writeError ? (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3.5 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              <p>{writeError}</p>
              <button
                type="button"
                onClick={() => {
                  requestedFor.current = null
                  setWriteError(null)
                  setReading((r) => (r ? { ...r } : r))
                }}
                className="mt-2 rounded-lg border border-amber-300 px-3 py-1.5 text-xs font-semibold hover:bg-amber-100 dark:border-amber-800 dark:hover:bg-amber-900/40"
              >
                다시 시도
              </button>
              <p className="mt-2 text-xs opacity-80">위 계산 값은 이미 확정된 실제 값입니다.</p>
            </div>
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

        {/* 공유 — 본인 리포트에서만 (PRD §12.3) */}
        {mode === 'own' && (
          <Card className="p-6 sm:p-7">
            <h2 className="font-display text-lg font-bold text-ink-900 dark:text-paper-100">
              손님에게 보내기
            </h2>
            <p className="mt-1.5 text-xs text-ink-400 dark:text-ink-300">
              읽기 전용 링크입니다. 생년월일·시간은 링크에 담기지 않습니다.
            </p>
            {shareUrl && (
              <div className="mt-4 space-y-2">
                <code className="block break-all rounded-lg bg-paper-100 px-3 py-2 text-xs text-ink-700 dark:bg-ink-900 dark:text-paper-200">
                  {shareUrl}
                </code>
                <p className="text-xs text-ink-400 dark:text-ink-300">
                  {copied ? '복사했습니다. 그대로 붙여넣으시면 됩니다.' : '위 주소를 복사해 보내세요.'}
                </p>
              </div>
            )}

            {/* 두 단추는 항상 보인다. 공유 링크를 만든 뒤에도
                "다시 시작하기"가 사라지면 손님이 나갈 길을 잃는다. */}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              {!shareUrl && (
                <button
                  type="button"
                  onClick={handleShare}
                  disabled={sharing}
                  className="rounded-xl bg-ink-900 px-5 py-3 text-sm font-semibold text-paper-50 disabled:opacity-60 dark:bg-gold-500 dark:text-ink-950"
                >
                  {sharing ? '만드는 중…' : '공유 링크 만들기'}
                </button>
              )}
              <Link
                to="/"
                className="rounded-xl border border-paper-300 px-5 py-3 text-sm font-semibold text-ink-700 hover:bg-paper-100 dark:border-ink-700 dark:text-paper-200 dark:hover:bg-ink-900"
              >
                다시 시작하기
              </Link>
            </div>
          </Card>
        )}

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
