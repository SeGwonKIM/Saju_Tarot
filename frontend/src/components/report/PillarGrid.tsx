/**
 * 원국 4주 (PRD §6.3 ②).
 * 검증자(선배 역술인)를 위해 항상 노출한다 — 무엇을 근거로 읽었는지 보여야 한다.
 * 전통 표기 순서대로 시주 → 일주 → 월주 → 연주로 배치한다.
 */
import type { Reading } from '../../schemas/reading'

const LABELS = [
  { key: 'hour', label: '시주', sub: '태어난 시간' },
  { key: 'day', label: '일주', sub: '나 자신' },
  { key: 'month', label: '월주', sub: '자라온 환경' },
  { key: 'year', label: '연주', sub: '뿌리' },
] as const

export default function PillarGrid({ pillars }: { pillars: Reading['pillars'] }) {
  return (
    <div className="grid grid-cols-4 gap-2 sm:gap-3">
      {LABELS.map(({ key, label, sub }) => {
        const p = pillars[key]
        return (
          <div
            key={key}
            className="rounded-xl border border-paper-200 bg-white px-2 py-4 text-center dark:border-ink-800 dark:bg-ink-900/60"
          >
            <div className="text-xs font-medium text-ink-400 dark:text-ink-300">{label}</div>
            {p ? (
              <>
                <div className="mt-2 font-display text-2xl font-bold leading-tight text-ink-900 dark:text-paper-100">
                  {p.gan}
                  <br />
                  {p.ji}
                </div>
                <div className="mt-2 text-xs text-ink-500 dark:text-ink-300">{p.ko}</div>
              </>
            ) : (
              <div className="mt-2 flex h-[4.5rem] flex-col items-center justify-center text-xs leading-relaxed text-ink-300 dark:text-ink-400">
                시간
                <br />
                미상
              </div>
            )}
            <div className="mt-2 hidden text-[11px] text-ink-300 sm:block dark:text-ink-400">
              {sub}
            </div>
          </div>
        )
      })}
    </div>
  )
}
