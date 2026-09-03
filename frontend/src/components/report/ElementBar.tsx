/**
 * 오행 분포 (PRD §6.3 ③).
 * 색 외에 수치도 함께 표기한다 — 색만으로 정보를 전달하지 않는다 (PRD §13 접근성).
 */
import { ELEMENTS, type Reading } from '../../schemas/reading'

const META: Record<string, { hanja: string; color: string; label: string }> = {
  목: { hanja: '木', color: 'bg-emerald-500', label: '나무' },
  화: { hanja: '火', color: 'bg-rose-500', label: '불' },
  토: { hanja: '土', color: 'bg-amber-600', label: '흙' },
  금: { hanja: '金', color: 'bg-slate-400', label: '쇠' },
  수: { hanja: '水', color: 'bg-sky-600', label: '물' },
}

export default function ElementBar({ elements }: { elements: Reading['elements'] }) {
  const total = ELEMENTS.reduce((sum, k) => sum + elements[k], 0) || 1

  return (
    <div className="space-y-3">
      {ELEMENTS.map((k) => {
        const count = elements[k]
        const pct = Math.round((count / total) * 100)
        const m = META[k]
        return (
          <div key={k} className="flex items-center gap-3">
            <div className="w-16 shrink-0 text-sm">
              <span className="font-display font-bold text-ink-900 dark:text-paper-100">
                {m.hanja} {k}
              </span>
            </div>
            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-paper-200 dark:bg-ink-800">
              <div
                className={`h-full rounded-full ${m.color} transition-[width] duration-700`}
                style={{ width: `${Math.max(pct, count > 0 ? 4 : 0)}%` }}
              />
            </div>
            <div className="w-16 shrink-0 text-right text-xs tabular-nums text-ink-500 dark:text-ink-300">
              {count}개 · {pct}%
            </div>
          </div>
        )
      })}

      {elements.verdict.length > 0 && (
        <p className="pt-1 text-sm text-ink-600 dark:text-ink-300">
          {elements.verdict.map((v, i) => (
            <span key={v}>
              {i > 0 && ' · '}
              <strong className="font-semibold text-ink-900 dark:text-paper-100">{v}</strong>
            </span>
          ))}
        </p>
      )}
    </div>
  )
}
