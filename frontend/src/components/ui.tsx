/**
 * 폼·화면 공통 조각 (PRD §5.3 컴포넌트).
 * 디자인을 한 번 바꿀 때 한 곳만 고치기 위해 여기 모았다.
 */
import type { ReactNode } from 'react'

export function Field({
  label,
  required,
  hint,
  error,
  htmlFor,
  children,
}: {
  label: string
  required?: boolean
  hint?: ReactNode
  error?: string
  htmlFor?: string
  children: ReactNode
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <label
          htmlFor={htmlFor}
          className="text-sm font-semibold text-ink-800 dark:text-paper-200"
        >
          {label}
          {required && <span className="ml-1 text-gold-600 dark:text-gold-400">*</span>}
        </label>
        {hint && (
          <span className="text-xs text-ink-400 dark:text-ink-300">{hint}</span>
        )}
      </div>
      {children}
      {error && (
        <p role="alert" className="text-xs font-medium text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  )
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: {
  options: readonly { value: T; label: string; sub?: string }[]
  value: T | undefined
  onChange: (v: T) => void
  ariaLabel: string
}) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="grid gap-1.5 rounded-xl bg-paper-100 p-1.5 dark:bg-ink-900"
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0,1fr))` }}
    >
      {options.map((o) => {
        const active = value === o.value
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={[
              'rounded-lg px-3 py-2.5 text-sm transition-all',
              active
                ? 'bg-white font-semibold text-ink-900 shadow-sm ring-1 ring-gold-300 dark:bg-ink-700 dark:text-paper-50 dark:ring-gold-600'
                : 'text-ink-600 hover:bg-white/60 dark:text-ink-300 dark:hover:bg-ink-800/60',
            ].join(' ')}
          >
            {o.label}
            {o.sub && <span className="ml-1 text-xs opacity-60">{o.sub}</span>}
          </button>
        )
      })}
    </div>
  )
}

export function Chip({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={[
        'rounded-full border px-4 py-2 text-sm transition-all',
        active
          ? 'border-gold-500 bg-gold-500/12 font-semibold text-gold-700 dark:border-gold-400 dark:text-gold-300'
          : 'border-paper-300 text-ink-500 hover:border-ink-300 dark:border-ink-700 dark:text-ink-300',
      ].join(' ')}
    >
      {active && <span aria-hidden="true">✓ </span>}
      {label}
    </button>
  )
}

export function Select({
  id,
  value,
  onChange,
  children,
  ariaLabel,
}: {
  id?: string
  value: string
  onChange: (v: string) => void
  children: ReactNode
  ariaLabel?: string
}) {
  return (
    <select
      id={id}
      aria-label={ariaLabel}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full appearance-none rounded-xl border border-paper-300 bg-white px-3 py-2.5 text-sm text-ink-900 transition-colors hover:border-ink-300 dark:border-ink-700 dark:bg-ink-900 dark:text-paper-100"
    >
      {children}
    </select>
  )
}

export function TextInput({
  id,
  value,
  onChange,
  placeholder,
  maxLength,
  invalid,
}: {
  id: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  maxLength?: number
  invalid?: boolean
}) {
  return (
    <input
      id={id}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      maxLength={maxLength}
      aria-invalid={invalid || undefined}
      className={[
        'w-full rounded-xl border bg-white px-4 py-3 text-base text-ink-900 placeholder:text-ink-300 transition-colors dark:bg-ink-900 dark:text-paper-100',
        invalid
          ? 'border-rose-400'
          : 'border-paper-300 hover:border-ink-300 dark:border-ink-700',
      ].join(' ')}
    />
  )
}

export function Checkbox({
  id,
  checked,
  onChange,
  children,
}: {
  id: string
  checked: boolean
  onChange: (v: boolean) => void
  children: ReactNode
}) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-3 text-sm text-ink-600 dark:text-ink-300"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 size-4 shrink-0 accent-gold-500"
      />
      <span>{children}</span>
    </label>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={[
        'rounded-2xl border border-paper-200 bg-white/90 shadow-[0_1px_2px_rgba(16,22,50,0.04),0_12px_32px_-12px_rgba(16,22,50,0.12)] backdrop-blur-sm dark:border-ink-800 dark:bg-ink-900/70',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}
