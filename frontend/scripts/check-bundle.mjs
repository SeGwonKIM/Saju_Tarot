/**
 * 빌드 결과물에 비밀값이 섞여 들어갔는지 검사한다 (PRD §12.19).
 *
 * VITE_ 접두사가 붙은 환경변수는 번들에 그대로 박히므로,
 * 실수로 비밀값을 VITE_ 로 만들면 브라우저에 공개된다.
 *
 * 실행: npm run check:secrets   (dist/ 가 있어야 함)
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const DIST = 'dist'

const PATTERNS = [
  { name: 'Anthropic API 키', re: /sk-ant-[A-Za-z0-9_-]{20,}/ },
  { name: '일반 LLM API 키', re: /\bsk-[A-Za-z0-9]{32,}/ },
  { name: 'Supabase service_role', re: /"role"\s*:\s*"service_role"/ },
  { name: 'service_role 문자열', re: /service_role/ },
  { name: 'AWS Access Key', re: /AKIA[0-9A-Z]{16}/ },
  { name: '개인키', re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/ },
  { name: 'DB 접속 문자열', re: /postgres(ql)?:\/\/[^:]+:[^@]+@/ },
]

function walk(dir) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) out.push(...walk(p))
    else out.push(p)
  }
  return out
}

let found = 0
let scanned = 0

try {
  statSync(DIST)
} catch {
  console.error(`✖ ${DIST}/ 가 없습니다. 먼저 npm run build 를 실행하세요.`)
  process.exit(1)
}

for (const file of walk(DIST)) {
  if (!/\.(js|css|html|json|map|txt)$/.test(file)) continue
  scanned++
  const content = readFileSync(file, 'utf8')
  for (const { name, re } of PATTERNS) {
    if (re.test(content)) {
      console.error(`✖ ${file} 안에서 ${name} 로 보이는 문자열이 발견됐습니다.`)
      found++
    }
  }
}

if (found > 0) {
  console.error('')
  console.error('배포를 중단하세요. 비밀값을 VITE_ 환경변수에서 빼고 백엔드로 옮겨야 합니다. (PRD §12.1)')
  process.exit(1)
}

console.log(`✓ 번들 검사 통과 — ${scanned}개 파일에서 비밀값 없음`)
