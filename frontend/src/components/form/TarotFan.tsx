/**
 * 타로 부채꼴 — 손님이 번호로 세 장을 고른다 (PRD §8.6.1).
 *
 * 화면 문구는 PRD 에서 확정한 것을 그대로 쓴다. 여기서 새로 지어내지 않는다.
 *
 * ⚠️ 회전 부호 함정 — 회전축(`transform-origin`)이 카드 **위**에 있으므로
 *    각도가 **양수일 때 왼쪽**으로 간다. 축이 아래에 있을 때와 반대다.
 *    그래서 1번에 가장 큰 양수 각도를 준다. 부호를 뒤집으면 78번이 왼쪽에 온다
 *    (시안에서 실제로 뒤집혀 나왔다).
 */
import { useState } from 'react'

import { lattice, Rosette } from '../CardBack'
import { FAN_SIZE, SPREAD } from '../../schemas/reading'

/** 카드 사이 각도. 넓을수록 부채가 벌어진다 */
const STEP_DEG = 1.24
/** 회전축이 카드 위쪽 몇 px 에 있는가 — 클수록 호가 완만해지고 부채가 넓어진다 */
const PIVOT_PX = 228
const CARD_H = 152
const CARD_W = 18

type Props = {
  /** 고른 번호. 아직 안 고른 자리는 null */
  picks: (number | null)[]
  onChange: (picks: (number | null)[]) => void
  error?: string
}

export default function TarotFan({ picks, onChange, error }: Props) {
  /**
   * 막은 이유를 손님에게 말해 준다. 조용히 무시하면 왜 입력이 안 되는지 모른다
   * (실제로 그렇게 만들었다가 시험에서 걸렸다).
   */
  const [warn, setWarn] = useState<string | null>(null)
  const chosen = picks.filter((p): p is number => p !== null)
  /** 지금 고르는 중인 자리 — 앞에서부터 처음 빈 자리다 */
  const activeIndex = picks.findIndex((p) => p === null)

  function setPick(index: number, raw: string) {
    const next = [...picks]
    if (raw.trim() === '') {
      next[index] = null
      setWarn(null)
    } else {
      const digits = raw.replace(/[^0-9]/g, '')
      if (digits === '') return
      const n = Number(digits)
      if (n < 1 || n > FAN_SIZE) {
        setWarn(`1부터 ${FAN_SIZE}까지 중에서 골라 주세요.`)
        return
      }
      // 중복은 받지 않는다 — 같은 자리를 두 번 고르면 3장 스프레드가 성립하지 않는다
      if (picks.some((p, i) => i !== index && p === n)) {
        setWarn('이미 고른 번호입니다. 다른 번호를 골라 주세요.')
        return
      }
      next[index] = n
      setWarn(null)
    }
    onChange(next)
  }

  return (
    <div data-field="tarot_picks" className="space-y-4">
      {/* ── 경계 — 위쪽은 사주다. 두 구역을 완전히 갈라 놓는다 ────── */}
      <div className="border-t border-paper-300 pt-7 dark:border-ink-700">
        <p className="font-display text-lg font-bold text-ink-900 dark:text-paper-100">
          여기까지가 사주입니다. 이제 타로카드 3장을 뽑습니다.
        </p>
        <p className="mt-2 text-sm leading-relaxed text-ink-600 dark:text-ink-300">
          카드는 보이지 않게 섞여 있습니다. 왼쪽부터 번호로 세 장을 고르세요.
        </p>
      </div>

      {/* ── 부채꼴 ─────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-b from-ink-900 to-ink-950 px-2 pb-3 pt-4">
        <div className="starfield absolute inset-0 opacity-60" aria-hidden="true" />
        <div
          className="relative mx-auto"
          style={{ height: CARD_H + 60 }}
          role="img"
          aria-label={`타로카드 ${FAN_SIZE}장이 뒷면으로 부채꼴로 깔려 있습니다. 왼쪽이 1번, 오른쪽이 ${FAN_SIZE}번입니다.`}
        >
          {Array.from({ length: FAN_SIZE }, (_, k) => {
            const n = k + 1
            const on = chosen.includes(n)
            // 고른 카드 자리가 벌어진다 — 부채에서 한 장을 뽑으면 그 자리가 벌어진다
            const part = chosen.reduce((acc, p) => acc + (n > p ? 0.5 : n < p ? -0.5 : 0), 0)
            const deg = (FAN_SIZE + 1) / 2 - n
            return (
              <div
                key={n}
                aria-hidden="true"
                className={
                  'absolute left-1/2 top-0 flex items-end justify-center rounded-b pb-1.5 text-[10px] font-semibold ' +
                  (on
                    ? 'border border-gold-400 bg-ink-700 text-gold-300 z-10'
                    : 'border border-gold-500/25 bg-ink-800 text-transparent')
                }
                style={{
                  width: CARD_W,
                  height: CARD_H,
                  marginLeft: -CARD_W / 2,
                  transformOrigin: `50% -${PIVOT_PX}px`,
                  transform: `rotate(${(deg * STEP_DEG - part).toFixed(2)}deg)${on ? ' translateY(26px)' : ''}`,
                  ...lattice(6, on ? 0.3 : 0.14),
                }}
              >
                {on ? n : ''}
              </div>
            )
          })}

          {/* 양 끝 번호 — 카드 **바깥**, 그러나 호 위에 (PRD §8.6.1) */}
          {[1, FAN_SIZE].map((n) => (
            <div
              key={`edge-${n}`}
              aria-hidden="true"
              className="pointer-events-none absolute left-1/2 top-0 flex items-end justify-center text-[13px] font-semibold text-gold-300/80"
              style={{
                width: 26,
                height: CARD_H + 26,
                marginLeft: -13,
                transformOrigin: `50% -${PIVOT_PX}px`,
                transform: `rotate(${(((FAN_SIZE + 1) / 2 - n) * STEP_DEG).toFixed(2)}deg)`,
              }}
            >
              {n}
            </div>
          ))}
        </div>
        <p className="relative mt-1 text-center text-xs text-ink-300">
          카드를 눌러 크게 볼 수 있습니다
        </p>
      </div>

      {/* ── 뽑힌 세 자리 — 카드 비율 그대로 (PRD §8.6.1) ─────────── */}
      <div className="grid grid-cols-3 gap-3">
        {SPREAD.map((slot, i) => {
          const filled = picks[i] !== null
          const active = i === activeIndex
          return (
            <div key={slot.key}>
              <label
                htmlFor={`pick-${i}`}
                className={
                  'block text-center text-xs ' +
                  (active
                    ? 'font-semibold text-gold-700 dark:text-gold-300'
                    : 'text-ink-600 dark:text-ink-300')
                }
              >
                {slot.label}
              </label>
              <div
                className={
                  'relative mt-1.5 flex items-center justify-center overflow-hidden rounded-lg ' +
                  (filled
                    ? 'border border-gold-400 bg-ink-900'
                    : active
                      ? 'border-2 border-dashed border-gold-500/60 bg-paper-100 dark:bg-ink-900'
                      : 'border border-dashed border-paper-300 bg-paper-100 dark:border-ink-700 dark:bg-ink-900')
                }
                style={{ aspectRatio: '1 / 1.72', ...(filled ? lattice(9, 0.22) : {}) }}
              >
                {filled && (
                  <>
                    {/* 이중 테두리 — 옛 카드 뒷면의 안쪽 선 */}
                    <span
                      aria-hidden="true"
                      className="pointer-events-none absolute inset-1.5 rounded border border-gold-500/35"
                    />
                    <Rosette className="pointer-events-none absolute inset-x-0 top-[22%] mx-auto size-2/5 text-gold-400/50" />
                  </>
                )}
                <input
                  id={`pick-${i}`}
                  inputMode="numeric"
                  autoComplete="off"
                  value={picks[i] ?? ''}
                  placeholder={`1~${FAN_SIZE}`}
                  onChange={(e) => setPick(i, e.target.value)}
                  aria-label={`${slot.label} — 카드 번호`}
                  className={
                    'text-center outline-none ' +
                    (filled
                      // 무늬 위에 얹히니 번호만 감싸는 작은 자리를 둔다.
                      // 카드 폭을 가로지르는 띠를 두면 카드가 두 동으로 잘려 보인다.
                      ? 'absolute bottom-3 left-1/2 w-12 -translate-x-1/2 rounded-full border border-gold-500/40 bg-ink-950/85 py-0.5 text-lg font-bold text-gold-300'
                      : 'w-full bg-transparent text-sm text-ink-400 placeholder:text-ink-400')
                  }
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* 지금 몇 번째 자리를 고르는 중인지 — 다 고른 뒤에 순서가 정해지면 안 된다 */}
      {activeIndex >= 0 && (
        <p className="text-sm text-ink-600 dark:text-ink-300">
          <span className="font-semibold text-ink-900 dark:text-paper-100">
            {SPREAD[activeIndex].label}
          </span>
          {' — '}
          {activeIndex === SPREAD.length - 1 ? '마지막' : activeIndex === 0 ? '첫 번째' : '두 번째'}{' '}
          카드를 고르세요
        </p>
      )}

      {(warn ?? error) && (
        <p role="status" className="text-sm text-red-600 dark:text-red-400">
          {warn ?? error}
        </p>
      )}
    </div>
  )
}
