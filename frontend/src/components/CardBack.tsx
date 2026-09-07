/**
 * 카드 뒷면 무늬 — **직접 그린다** (PRD §8.6.1).
 *
 * 남의 카드 그림을 가져오지 않는다. §18 Q5 가 "퍼블릭 도메인 스캔본만"으로 묶여
 * 있고, 뒷면은 앞면 그림과 달리 격자 무늬 하나로 충분하다.
 * 45도로 교차하는 금색 실선 두 겹 = 옛 카드 뒷면의 마름모 격자다.
 *
 * 부채꼴(TarotFan)과 결과 화면(TarotCard)이 **같은 무늬**를 써야 한다.
 * 뒤집히기 전과 후가 다른 카드처럼 보이면 뽑은 것과 나온 것이 이어지지 않는다.
 */

/** 격자 — `gap` 은 실선 간격(px), `alpha` 는 금색 진하기 */
export function lattice(gap: number, alpha: number) {
  return {
    backgroundImage:
      `repeating-linear-gradient(45deg, rgba(223,187,86,${alpha}) 0 1px, transparent 1px ${gap}px),` +
      `repeating-linear-gradient(-45deg, rgba(223,187,86,${alpha}) 0 1px, transparent 1px ${gap}px)`,
  }
}

/** 뒷면 가운데 문양 — 여덟 갈래 별. 이것도 직접 그린 것이다 */
export function Rosette({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" aria-hidden="true" className={className}>
      <circle cx="20" cy="20" r="13" fill="none" stroke="currentColor" strokeWidth="0.8" />
      <circle cx="20" cy="20" r="4.5" fill="none" stroke="currentColor" strokeWidth="0.8" />
      {Array.from({ length: 8 }, (_, i) => {
        const a = (i * Math.PI) / 4
        return (
          <line
            key={i}
            x1={20 + Math.cos(a) * 5}
            y1={20 + Math.sin(a) * 5}
            x2={20 + Math.cos(a) * 12.5}
            y2={20 + Math.sin(a) * 12.5}
            stroke="currentColor"
            strokeWidth="0.8"
          />
        )
      })}
    </svg>
  )
}

/** 엎어진 카드 한 장 — 격자 + 안쪽 선 + 문양. 번호가 있으면 아래에 얹는다 */
export default function CardBack({
  pick,
  className = '',
}: {
  pick?: number | null
  className?: string
}) {
  return (
    <div
      className={
        'relative h-full w-full overflow-hidden rounded-xl border border-gold-400 bg-ink-600 ' +
        className
      }
      style={lattice(9, 0.4)}
    >
      {/* 이중 테두리 — 옛 카드 뒷면의 안쪽 선 */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-1.5 rounded border border-gold-400/60"
      />
      <Rosette className="pointer-events-none absolute inset-x-0 top-[22%] mx-auto size-2/5 text-gold-300/80" />
      {pick != null && (
        // 카드 폭을 가로지르는 띠를 두면 카드가 두 동으로 잘려 보인다
        <span className="absolute bottom-3 left-1/2 w-12 -translate-x-1/2 rounded-full border border-gold-500/40 bg-ink-950/85 py-0.5 text-center text-lg font-bold text-gold-300">
          {pick}
        </span>
      )}
    </div>
  )
}
