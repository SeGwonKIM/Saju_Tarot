/**
 * 히어로 비주얼 — 동양의 사주와 서양의 타로를 한 화면에.
 *
 * 구성
 *   바깥 고리 : 12지지 한자 (子丑寅卯…) — 사주가 시간을 나누는 단위
 *   안쪽 고리 : 오행 (木火土金水)
 *   중심      : 태극
 *   앞        : 타로 3장이 부채꼴로 — 라이더-웨이트 퍼블릭 도메인 (PRD §18.1 Q5)
 *
 * 이미지가 없어도 원형 도형만으로 성립하게 만들었다.
 * 회전은 아주 느리게 두고, prefers-reduced-motion 이면 멈춘다.
 */

const JIJI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
const OHAENG = ['木', '火', '土', '金', '水']

/** 히어로에 세울 카드 — 별(희망) · 달(무의식) · 운명의 수레바퀴(순환) */
const CARDS = [
  { file: 'the-moon', ko: '달', rotate: -16, x: -78, y: 46, z: 1 },
  { file: 'wheel-of-fortune', ko: '운명의 수레바퀴', rotate: 0, x: 0, y: 34, z: 3 },
  { file: 'the-star', ko: '별', rotate: 16, x: 78, y: 46, z: 1 },
]

function pointOnCircle(index: number, total: number, radius: number) {
  // 12시 방향부터 시계 방향으로
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius }
}

export default function MysticVisual() {
  return (
    <div
      className="pointer-events-none relative mx-auto aspect-square w-full max-w-[26rem] select-none"
      aria-hidden="true"
    >
      {/* ── 동양: 12지지 · 오행 · 태극 ──────────────────────── */}
      <svg viewBox="-200 -200 400 400" className="absolute inset-0 h-full w-full">
        <defs>
          <radialGradient id="halo" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgb(201 162 39)" stopOpacity="0.28" />
            <stop offset="70%" stopColor="rgb(201 162 39)" stopOpacity="0.05" />
            <stop offset="100%" stopColor="rgb(201 162 39)" stopOpacity="0" />
          </radialGradient>
        </defs>

        <circle r="185" fill="url(#halo)" />

        <g className="mystic-spin" stroke="rgb(223 187 86)" fill="none">
          <circle r="175" strokeOpacity="0.35" />
          <circle r="158" strokeOpacity="0.2" />
          {/* 12지지를 가르는 눈금 */}
          {JIJI.map((_, i) => {
            const a = (i / 12) * Math.PI * 2 - Math.PI / 2
            return (
              <line
                key={i}
                x1={Math.cos(a) * 158}
                y1={Math.sin(a) * 158}
                x2={Math.cos(a) * 175}
                y2={Math.sin(a) * 175}
                strokeOpacity="0.35"
              />
            )
          })}
          {JIJI.map((ji, i) => {
            const p = pointOnCircle(i, 12, 167)
            return (
              <text
                key={ji}
                x={p.x}
                y={p.y}
                dy="4"
                textAnchor="middle"
                className="font-display"
                fontSize="16"
                fill="rgb(236 213 145)"
                fillOpacity="0.9"
                stroke="none"
              >
                {ji}
              </text>
            )
          })}
        </g>

        <g className="mystic-spin-reverse" stroke="rgb(223 187 86)" fill="none">
          <circle r="122" strokeOpacity="0.28" strokeDasharray="3 7" />
          {OHAENG.map((el, i) => {
            const p = pointOnCircle(i, 5, 122)
            return (
              <text
                key={el}
                x={p.x}
                y={p.y}
                dy="5"
                textAnchor="middle"
                className="font-display"
                fontSize="18"
                fill="rgb(236 213 145)"
                fillOpacity="0.75"
                stroke="none"
              >
                {el}
              </text>
            )
          })}
        </g>

        {/* 태극 — 사주의 중심 (카드 위쪽에 자리잡게 올린다) */}
        <g opacity="0.6" transform="translate(0,-58)">
          <circle r="26" fill="none" stroke="rgb(223 187 86)" strokeOpacity="0.5" />
          <path
            d="M0,-26 A13,13 0 0,1 0,0 A13,13 0 0,0 0,26 A26,26 0 0,1 0,-26"
            fill="rgb(236 213 145)"
            fillOpacity="0.55"
          />
        </g>
      </svg>

      {/* ── 서양: 타로 3장 ──────────────────────────────────── */}
      <div className="absolute inset-0 flex items-center justify-center">
        {CARDS.map((c) => (
          <figure
            key={c.file}
            className="absolute w-[5.5rem] overflow-hidden rounded-lg border border-gold-400/45 shadow-2xl shadow-ink-950/70 sm:w-[6.25rem]"
            style={{
              transform: `translate(${c.x}px, ${c.y}px) rotate(${c.rotate}deg)`,
              zIndex: c.z,
            }}
          >
            <img
              src={`/cards/${c.file}.jpg`}
              alt=""
              className="block aspect-[2/3] w-full object-cover"
            />
          </figure>
        ))}
      </div>
    </div>
  )
}
