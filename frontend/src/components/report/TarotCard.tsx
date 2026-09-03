/**
 * 타로 카드 한 장 (PRD §6.3 ④).
 *
 * 카드 이미지는 라이더-웨이트 1909년판 퍼블릭 도메인 스캔본을 쓸 예정이다(PRD §18.1 Q5).
 * 아직 이미지 파일이 없으므로 지금은 문양 자리표시자로 둔다.
 */
import type { Reading } from '../../schemas/reading'

type Card = Reading['tarot'][number]

export default function TarotCard({ card }: { card: Card }) {
  return (
    <figure className="flex flex-col items-center gap-3">
      <div
        className={[
          'relative flex aspect-[2/3] w-full items-center justify-center overflow-hidden rounded-xl border bg-gradient-to-b from-ink-800 to-ink-950 text-gold-300 shadow-md transition-transform',
          card.reversed ? 'rotate-180 border-plum-400/40' : 'border-gold-500/30',
        ].join(' ')}
      >
        <div className="starfield absolute inset-0 opacity-60" aria-hidden="true" />
        <span aria-hidden="true" className="relative font-display text-3xl">
          ✦
        </span>
      </div>
      <figcaption className="text-center">
        <div className="text-xs font-medium text-gold-600 dark:text-gold-400">{card.category}</div>
        <div className="mt-0.5 font-display text-sm font-bold text-ink-900 dark:text-paper-100">
          {card.card_ko}
        </div>
        <div className="mt-0.5 text-xs text-ink-400 dark:text-ink-300">
          {card.reversed ? '역방향' : '정방향'}
        </div>
        <div className="mt-1.5 text-xs leading-relaxed text-ink-500 dark:text-ink-300">
          {card.keywords.join(' · ')}
        </div>
      </figcaption>
    </figure>
  )
}
