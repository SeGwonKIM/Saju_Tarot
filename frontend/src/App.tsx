import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

type Health = 'checking' | 'ok' | 'waking' | 'down'

/**
 * 1단계 스캐폴드 화면.
 * 페이지가 뜨는 즉시 /health 를 호출해 백엔드를 미리 깨운다 (PRD §13 콜드 스타트).
 */
export default function App() {
  const [health, setHealth] = useState<Health>('checking')

  useEffect(() => {
    const slow = setTimeout(() => setHealth((h) => (h === 'checking' ? 'waking' : h)), 10_000)
    fetch(`${API_BASE}/health`)
      .then((r) => setHealth(r.ok ? 'ok' : 'down'))
      .catch(() => setHealth('down'))
      .finally(() => clearTimeout(slow))
    return () => clearTimeout(slow)
  }, [])

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6 py-12">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">사주·타로 상담 리포트</h1>
        <p className="mt-2 text-sm text-neutral-500">
          이름과 생년월일시를 입력하면 이번 달 흐름과 조언을 한 장으로 정리해 드립니다.
        </p>
      </header>

      <section className="rounded-xl border border-neutral-200 p-4 text-sm dark:border-neutral-700">
        <div className="font-medium">1단계 · 배포 파이프라인 확인</div>
        <ul className="mt-2 space-y-1 text-neutral-500">
          <li>프론트 화면: <span className="text-green-600">떠 있음</span></li>
          <li>
            백엔드 <code>/health</code>:{' '}
            <HealthLabel state={health} />
          </li>
        </ul>
      </section>

      <p className="text-xs text-neutral-400">
        다음 단계: 목업 데이터로 입력 폼과 리포트 화면 완성 (PRD §7, §15 2단계)
      </p>
    </main>
  )
}

function HealthLabel({ state }: { state: Health }) {
  switch (state) {
    case 'checking':
      return <span className="text-neutral-400">확인 중…</span>
    case 'ok':
      return <span className="text-green-600">연결됨</span>
    case 'waking':
      // 무료 플랜은 15분 미사용 시 잠든다 — 고장이 아님을 명시 (PRD §6.2)
      return <span className="text-amber-600">서버가 깨어나는 중입니다 (최대 1분)</span>
    case 'down':
      return <span className="text-red-600">연결 안 됨 — 백엔드를 실행해 주세요</span>
  }
}
