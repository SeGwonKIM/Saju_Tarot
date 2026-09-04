/**
 * 히어로 비주얼 — 동양의 사주와 서양의 타로를 한 화면에.
 *
 * 동양 쪽을 주인공으로 둔다. 세 겹의 고리와 중심의 태극이 뼈대이고,
 * 타로 카드는 그 앞을 지나가는 손님처럼 아래쪽에 걸친다.
 *
 *   고리 1 (바깥) : 12지지 한자 — 사주가 시간을 나누는 단위
 *   고리 2        : 팔괘 — 선으로 직접 그린다(글꼴에 없어도 깨지지 않게)
 *   고리 3        : 오행 + 오방색
 *   중심          : 태극
 *
 * 이미지가 없어도 도형만으로 성립한다. 회전은 아주 느리고,
 * prefers-reduced-motion 이면 멈춘다.
 */

const JIJI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

/**
 * 오행과 오방색. 흑(수)은 어두운 배경에서 보이지 않으므로 남색으로 옮겼다 —
 * 색이 정보를 전달하는 자리가 아니라 장식이라 허용되는 변형이다.
 */
const OHAENG = [
  { ko: '木', color: '#34d399' }, // 청
  { ko: '火', color: '#f87171' }, // 적
  { ko: '土', color: '#fbbf24' }, // 황
  { ko: '金', color: '#e2e8f0' }, // 백
  { ko: '水', color: '#60a5fa' }, // 흑 → 남색
]

/** 팔괘 — 아래에서 위로 세 효(爻). true = 양(이어짐), false = 음(끊김) */
const TRIGRAMS: [boolean, boolean, boolean][] = [
  [true, true, true], // 건 ☰
  [true, true, false], // 태 ☱
  [true, false, true], // 리 ☲
  [true, false, false], // 진 ☳
  [false, true, true], // 손 ☴
  [false, true, false], // 감 ☵
  [false, false, true], // 간 ☶
  [false, false, false], // 곤 ☷
]

/** 타로 3장 — 달(무의식) · 운명의 수레바퀴(순환) · 별(희망) */
const CARDS = [
  { file: 'the-moon', rotate: -15, x: -70, y: 74, z: 1 },
  { file: 'wheel-of-fortune', rotate: 0, x: 0, y: 64, z: 3 },
  { file: 'the-star', rotate: 15, x: 70, y: 74, z: 1 },
]

const GOLD = 'rgb(223 187 86)'
const GOLD_TEXT = 'rgb(240 219 160)'

function onCircle(index: number, total: number, radius: number) {
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, deg: (index / total) * 360 }
}

export default function MysticVisual() {
  return (
    <div
      className="pointer-events-none relative mx-auto aspect-square w-full max-w-[27rem] select-none"
      aria-hidden="true"
    >
      <svg viewBox="-200 -200 400 400" className="absolute inset-0 h-full w-full">
        <defs>
          <radialGradient id="halo" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgb(201 162 39)" stopOpacity="0.3" />
            <stop offset="65%" stopColor="rgb(201 162 39)" stopOpacity="0.07" />
            <stop offset="100%" stopColor="rgb(201 162 39)" stopOpacity="0" />
          </radialGradient>
        </defs>

        <circle r="190" fill="url(#halo)" />

        {/* ── 고리 1 · 12지지 ─────────────────────────────── */}
        <g className="mystic-spin">
          <circle r="180" fill="none" stroke={GOLD} strokeOpacity="0.5" />
          <circle r="152" fill="none" stroke={GOLD} strokeOpacity="0.3" />
          <circle
            r="166"
            fill="rgb(201 162 39)"
            fillOpacity="0.06"
            stroke="none"
          />
          {JIJI.map((_, i) => {
            const a = (i / 12) * Math.PI * 2 - Math.PI / 2
            return (
              <line
                key={`t${i}`}
                x1={Math.cos(a) * 152}
                y1={Math.sin(a) * 152}
                x2={Math.cos(a) * 180}
                y2={Math.sin(a) * 180}
                stroke={GOLD}
                strokeOpacity="0.45"
              />
            )
          })}
          {JIJI.map((ji, i) => {
            const p = onCircle(i, 12, 166)
            return (
              <text
                key={ji}
                x={p.x}
                y={p.y}
                dy="6.5"
                textAnchor="middle"
                className="font-display"
                fontSize="19"
                fontWeight="700"
                fill={GOLD_TEXT}
              >
                {ji}
              </text>
            )
          })}
        </g>

        {/* ── 고리 2 · 팔괘 ──────────────────────────────── */}
        <g className="mystic-spin-reverse">
          <circle r="132" fill="none" stroke={GOLD} strokeOpacity="0.3" strokeDasharray="2 6" />
          {TRIGRAMS.map((bars, i) => {
            const p = onCircle(i, 8, 132)
            return (
              <g key={i} transform={`translate(${p.x} ${p.y}) rotate(${p.deg})`}>
                {bars.map((yang, row) => {
                  const y = (row - 1) * 6
                  return yang ? (
                    <rect
                      key={row}
                      x="-11"
                      y={y - 1.6}
                      width="22"
                      height="3.2"
                      rx="1"
                      fill={GOLD_TEXT}
                      fillOpacity="0.85"
                    />
                  ) : (
                    <g key={row} fill={GOLD_TEXT} fillOpacity="0.85">
                      <rect x="-11" y={y - 1.6} width="9" height="3.2" rx="1" />
                      <rect x="2" y={y - 1.6} width="9" height="3.2" rx="1" />
                    </g>
                  )
                })}
              </g>
            )
          })}
        </g>

        {/* ── 고리 3 · 오행 (오방색) ──────────────────────── */}
        <g className="mystic-spin">
          <circle r="96" fill="none" stroke={GOLD} strokeOpacity="0.28" />
          {OHAENG.map((el, i) => {
            const p = onCircle(i, 5, 96)
            return (
              <g key={el.ko}>
                <circle cx={p.x} cy={p.y} r="17" fill={el.color} fillOpacity="0.16" />
                <circle
                  cx={p.x}
                  cy={p.y}
                  r="17"
                  fill="none"
                  stroke={el.color}
                  strokeOpacity="0.5"
                />
                <text
                  x={p.x}
                  y={p.y}
                  dy="7"
                  textAnchor="middle"
                  className="font-display"
                  fontSize="20"
                  fontWeight="700"
                  fill={el.color}
                  fillOpacity="0.95"
                >
                  {el.ko}
                </text>
              </g>
            )
          })}
        </g>

        {/* ── 중심 · 태극 ────────────────────────────────── */}
        <g transform="translate(0 -6)">
          <circle r="40" fill="rgb(10 14 28)" fillOpacity="0.75" />
          <circle r="40" fill="none" stroke={GOLD} strokeOpacity="0.7" strokeWidth="1.5" />
          {/* 음(어두움) 바탕에 양(밝음) 반쪽 */}
          <path
            d="M0,-40 A20,20 0 0,1 0,0 A20,20 0 0,0 0,40 A40,40 0 0,0 0,-40"
            fill={GOLD_TEXT}
            fillOpacity="0.9"
          />
          <circle cx="0" cy="-20" r="6" fill="rgb(10 14 28)" />
          <circle cx="0" cy="20" r="6" fill={GOLD_TEXT} fillOpacity="0.9" />
        </g>
      </svg>

      {/* ── 서양 · 타로 3장 ─────────────────────────────── */}
      <div className="absolute inset-0 flex items-center justify-center">
        {CARDS.map((c) => (
          <figure
            key={c.file}
            className="absolute w-[4.75rem] overflow-hidden rounded-md border border-gold-400/50 shadow-2xl shadow-ink-950/80 sm:w-[5.5rem]"
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
