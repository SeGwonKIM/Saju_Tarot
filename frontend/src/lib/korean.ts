/**
 * 조사 처리 — "동의을(를)" 같은 어색한 표기를 없애기 위한 유틸.
 * 한글 음절의 종성(받침) 유무로 조사를 고른다.
 */

function hasFinalConsonant(word: string): boolean {
  const last = word.trim().at(-1)
  if (!last) return false
  const code = last.charCodeAt(0)
  // 한글 음절 영역이 아니면(영문·숫자 등) 받침 없음으로 취급
  if (code < 0xac00 || code > 0xd7a3) return false
  return (code - 0xac00) % 28 !== 0
}

/** 을 / 를 */
export function eulReul(word: string): string {
  return hasFinalConsonant(word) ? '을' : '를'
}

/** 이 / 가 */
export function iGa(word: string): string {
  return hasFinalConsonant(word) ? '이' : '가'
}

/** 은 / 는 */
export function eunNeun(word: string): string {
  return hasFinalConsonant(word) ? '은' : '는'
}
