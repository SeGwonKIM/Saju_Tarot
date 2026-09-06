/**
 * 초기화면 — 랜딩 + 입력 폼 (PRD §6.1).
 *
 * 첫 화면에서 세 가지를 분명히 한다.
 *  ① 무엇을 받는지(이번 달 흐름 + 조언 3줄)
 *  ② 무엇을 입력해야 하는지(3분)
 *  ③ 내 정보가 어떻게 다뤄지는지(90일 후 삭제)
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import BirthForm from '../components/form/BirthForm'
import MysticVisual from '../components/MysticVisual'
import { createReading, getHealth, usingMock } from '../api/readings'
import { saveReading, saveName } from '../lib/store'
import type { ReadingRequest } from '../schemas/reading'

export default function HomePage() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [slow, setSlow] = useState(false)

  // 콜드 스타트 예열 — 첫 방문자가 1분 기다리는 일을 줄인다 (PRD §13)
  useEffect(() => {
    if (!usingMock) void getHealth()
  }, [])

  async function handleSubmit(input: ReadingRequest) {
    setSubmitting(true)
    setError(null)
    // 계산만 하는 호출이라 0.3초면 끝난다(v3.0). 이보다 오래 걸리는 이유는
    // 서버가 자고 있었던 것뿐이라, 그때만 안내를 띄운다.
    const slowTimer = setTimeout(() => setSlow(true), 6_000)
    try {
      const reading = await createReading(input)
      saveReading(reading)
      saveName(reading.id, input.name)   // 서버로는 안 간다 (store.ts 주석 참고)
      navigate(`/result/${reading.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '잠시 후 다시 시도해 주세요.')
    } finally {
      clearTimeout(slowTimer)
      setSlow(false)
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-paper-50 dark:bg-ink-950">
      {/* ── 헤더 ─────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 border-b border-paper-200/80 bg-paper-50/85 backdrop-blur-md dark:border-ink-800/80 dark:bg-ink-950/85">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <span aria-hidden="true" className="text-lg">☾</span>
            <span className="font-display font-bold tracking-tight text-ink-900 dark:text-paper-100">
              <span className="text-lg text-gold-600 sm:text-xl dark:text-gold-400">세권사주타로에서</span>{' '}
              <span className="text-sm font-semibold sm:text-base">
                당신의 운세, 사주와 타로로 정확하게 집어드립니다
              </span>
            </span>
          </div>
          <a
            href="#form"
            className="rounded-full border border-paper-300 px-4 py-1.5 text-sm text-ink-600 transition-colors hover:border-gold-500 hover:text-gold-700 dark:border-ink-700 dark:text-ink-300 dark:hover:border-gold-400 dark:hover:text-gold-300"
          >
            바로 보기
          </a>
        </div>
      </header>

      {/* ── 히어로 ───────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-gradient-to-b from-ink-900 via-ink-900 to-ink-950 text-paper-100">
        <div className="starfield absolute inset-0 opacity-70" aria-hidden="true" />
        <div
          className="absolute -top-32 left-1/2 size-[28rem] -translate-x-1/2 rounded-full bg-gold-500/12 blur-3xl"
          aria-hidden="true"
        />
        <div className="relative mx-auto grid max-w-5xl items-center gap-10 px-5 py-16 sm:py-24 lg:grid-cols-[1.05fr_1fr] lg:gap-8">
          <div>
          <p className="rise mb-5 inline-flex items-center gap-2 rounded-full border border-gold-400/30 bg-gold-400/8 px-3.5 py-1.5 text-xs text-gold-300">
            <span aria-hidden="true">✦</span>
            사주팔자 · 타로 · 오행을 한 번에
          </p>
          <h1 className="rise font-display font-bold tracking-tight">
            <span className="block text-2xl text-gold-400 sm:text-4xl">세권사주타로에서</span>
            <span className="mt-2 block text-3xl leading-[1.3] sm:text-[2.75rem] sm:leading-[1.25]">
              당신의 운세,
              <br />
              사주와 타로로
              <br />
              정확하게 집어드립니다
            </span>
          </h1>
          <p className="rise mt-6 max-w-xl text-base leading-relaxed text-ink-300 sm:text-lg">
            이름과 태어난 장소, 시간만 알려주시면 사주팔자와 타로를 함께 읽어
            <strong className="font-semibold text-paper-100"> 이번 달 흐름 세 줄</strong>과
            <strong className="font-semibold text-paper-100"> 재회운·상대방속마음·연애·재물·대인관계 조언</strong>을
            한 장으로 정리해 드립니다.
          </p>

          <div className="rise mt-9 flex flex-wrap items-center gap-3">
            <a
              href="#form"
              className="rounded-2xl bg-gold-500 px-10 py-5 text-xl font-bold tracking-tight text-ink-950 shadow-xl shadow-gold-500/30 transition-transform hover:-translate-y-0.5 hover:bg-gold-400 sm:px-12 sm:text-2xl"
            >
              시작하기
            </a>
            <span className="text-sm text-ink-400">3분 · 회원가입 없이</span>
          </div>
          </div>

          {/* 동양의 사주 + 서양의 타로 */}
          <div className="rise order-first lg:order-none">
            <MysticVisual />
          </div>

        </div>

        {/* 신뢰 요소 */}
        <div className="relative mx-auto max-w-5xl px-5 pb-16 sm:pb-20">
          <dl className="grid gap-4 border-t border-ink-800 pt-8 sm:grid-cols-3">
            {[
              { t: '만세력 기준 계산', d: '절기와 진태양시까지 보정해 원국을 세웁니다' },
              { t: '90일 뒤 자동 삭제', d: '생년월일은 리포트 생성에만 쓰고 지웁니다' },
              { t: '상담 참고용', d: '의료·법률·투자 판단의 근거로 쓰지 않습니다' },
            ].map((f) => (
              <div key={f.t}>
                <dt className="text-sm font-semibold text-gold-300">{f.t}</dt>
                <dd className="mt-1.5 text-sm leading-relaxed text-ink-400">{f.d}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ── 무엇을 받나 ──────────────────────────────────── */}
      <section className="mx-auto max-w-5xl px-5 py-16">
        <h2 className="font-display text-2xl font-bold text-ink-900 dark:text-paper-100">
          이런 리포트를 받게 됩니다
        </h2>
        <ol className="mt-8 grid gap-5 sm:grid-cols-3">
          {[
            {
              n: '01',
              t: '사주 원국과 오행',
              d: '연·월·일·시 네 기둥과 목화토금수 분포를 함께 보여드립니다. 무엇을 근거로 읽었는지 감추지 않습니다.',
            },
            {
              n: '02',
              t: '타로 세 장',
              d: '지금 놓인 자리·지금 할 수 있는 것·이대로 가면. 세 장을 모든 주제의 공통 근거로 읽습니다.',
            },
            {
              n: '03',
              t: '이번 달 흐름과 조언',
              d: '길게 늘이지 않습니다. 흐름 세 줄과 고르신 주제마다 조언 한 줄씩으로 정리합니다.',
            },
          ].map((s) => (
            <li
              key={s.n}
              className="rounded-2xl border border-paper-200 bg-white/70 p-6 dark:border-ink-800 dark:bg-ink-900/50"
            >
              <span className="font-display text-sm font-bold text-gold-600 dark:text-gold-400">
                {s.n}
              </span>
              <h3 className="mt-2.5 font-semibold text-ink-900 dark:text-paper-100">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-500 dark:text-ink-300">{s.d}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ── 입력 폼 ──────────────────────────────────────── */}
      <section id="form" className="mx-auto max-w-2xl scroll-mt-20 px-5 pb-20">
        <div className="mb-7 text-center">
          <h2 className="font-display text-2xl font-bold text-ink-900 dark:text-paper-100">
            태어난 정보를 알려주세요
          </h2>
          <p className="mt-2.5 text-sm text-ink-500 dark:text-ink-300">
            시간을 모르셔도 괜찮습니다. 그 경우 시주를 빼고 계산합니다.
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="mb-5 rounded-xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
          >
            {error}
          </div>
        )}
        {slow && submitting && (
          <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            서버가 깨어나는 중입니다. 쉬고 있던 서버는 깨어나는 데 1분쯤 걸립니다 — 고장이
            아닙니다. 사주 계산 자체는 1초도 걸리지 않습니다.
          </div>
        )}

        <BirthForm onSubmit={handleSubmit} submitting={submitting} />
      </section>

      {/* ── 푸터 ─────────────────────────────────────────── */}
      <footer className="border-t border-paper-200 bg-paper-100/60 dark:border-ink-800 dark:bg-ink-900/40">
        <div className="mx-auto max-w-5xl space-y-3 px-5 py-10 text-xs leading-relaxed text-ink-400 dark:text-ink-300">
          <p className="font-display text-sm font-bold text-ink-600 dark:text-paper-200">사주한장</p>
          <p>
            이 서비스가 만드는 리포트는 <strong>상담 참고용</strong>이며, 의료·법률·투자 판단의
            근거가 아닙니다. 중요한 결정은 해당 분야 전문가와 상의하세요.
          </p>
          <p>
            입력하신 이름·생년월일·시간은 리포트 생성에만 쓰이고 90일 뒤 자동 삭제됩니다. 언제든 직접
            삭제할 수 있습니다.
          </p>
          {usingMock && (
            <p className="inline-block rounded-md bg-plum-500/12 px-2.5 py-1 font-medium text-plum-500 dark:text-plum-400">
              개발 중 · 지금은 목업 데이터로 동작합니다 (PRD §7)
            </p>
          )}
        </div>
      </footer>
    </div>
  )
}
