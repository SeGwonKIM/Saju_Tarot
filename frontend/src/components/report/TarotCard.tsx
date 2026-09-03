/**
 * 타로 카드 한 장 (PRD §6.3 ④).
 *
 * 이미지는 라이더-웨이트 1909년판 **퍼블릭 도메인** 스캔본이다 (PRD §18.1 Q5).
 * `backend/tools/fetch_cards.py` 로 위키미디어 공용에서 받아 public/cards/ 에 둔다.
 * 이미지가 없으면 문양 자리표시자로 떨어진다 — 화면이 깨지지 않게.
 *
 * 역방향은 이미지만 180도 돌린다. 설명 글자는 돌리지 않는다.
 */
import { useState } from 'react'
import type { Reading } from '../../schemas/reading'

type Card = Reading['tarot'][number]

/** 'Eight of Pentacles' → 'eight-of-pentacles' (파일명 규칙은 fetch_cards.py 와 같다) */
function slug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

export default function TarotCard({ card }: { card: Card }) {
  const [imageFailed, setImageFailed] = useState(false)

  return (
    <figure className="flex flex-col items-center gap-3">
      <div
        className={[
          'relative aspect-[2/3] w-full overflow-hidden rounded-xl border shadow-md',
          card.reversed ? 'border-plum-400/50' : 'border-gold-500/40',
        ].join(' ')}
      >
        {imageFailed ? (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-b from-ink-800 to-ink-950 text-gold-300">
            <div className="starfield absolute inset-0 opacity-60" aria-hidden="true" />
            <span aria-hidden="true" className="relative font-display text-3xl">
              ✦
            </span>
          </div>
        ) : (
          <img
            src={`/cards/${slug(card.card)}.jpg`}
            alt={`${card.card_ko} ${card.reversed ? '역방향' : '정방향'}`}
            loading="lazy"
            onError={() => setImageFailed(true)}
            className={[
              'h-full w-full object-cover transition-transform',
              card.reversed ? 'rotate-180' : '',
            ].join(' ')}
          />
        )}
        {card.reversed && (
          <span className="absolute right-1.5 top-1.5 rounded-md bg-plum-500/90 px-1.5 py-0.5 text-[10px] font-medium text-white">
            역
          </span>
        )}
      </div>

      <figcaption className="text-center">
        <div className="text-xs font-medium text-gold-600 dark:text-gold-400">
          {card.position_ko}
        </div>
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
