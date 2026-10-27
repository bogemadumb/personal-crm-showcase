import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react'
import { cx } from './cx'

type Variant = 'solid' | 'ghost' | 'accent'
const VARIANT: Record<Variant, string> = {
  solid: 'bg-btn text-btn-fg',
  ghost: 'bg-card text-ink border border-line',
  accent: 'bg-accent text-white',
}

export function buttonClass(variant: Variant = 'solid', small = false, className?: string) {
  return cx(
    'inline-flex cursor-pointer select-none items-center justify-center gap-1.5 whitespace-nowrap font-medium',
    'transition-[transform,opacity] duration-150 ease-soft active:scale-[.97] disabled:pointer-events-none disabled:opacity-50',
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
    small ? 'px-2 py-[3px] rounded-[7px] text-[11.5px]' : 'px-[13px] py-[7px] rounded-[9px] text-[12.5px]',
    VARIANT[variant],
    className,
  )
}

export function Button({ variant = 'solid', small, className, type = 'button', ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; small?: boolean }) {
  return <button {...rest} type={type} className={buttonClass(variant, small, className)} />
}

export function Card({ className, bare, ...rest }: HTMLAttributes<HTMLDivElement> & { bare?: boolean }) {
  return <div {...rest} className={cx('rounded-[14px] bg-card shadow-card', !bare && 'px-[18px] py-4', className)} />
}

export type Tone = 'muted' | 'accent' | 'ok' | 'warn' | 'alarm'
const TONE: Record<Tone, string> = {
  muted: 'text-ink2 bg-chip',
  accent: 'text-accent bg-accent-soft',
  ok: 'text-ok bg-ok-soft',
  warn: 'text-warn bg-warn-soft',
  alarm: 'text-alarm bg-alarm-soft',
}

export function Chip({ tone = 'muted', dot, children, className }: { tone?: Tone; dot?: boolean; children: ReactNode; className?: string }) {
  return (
    <span className={cx('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[11.5px] font-medium leading-[1.45]', TONE[tone], className)}>
      {dot && <i aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-current" />}
      {children}
    </span>
  )
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="rounded-[5px] border border-line bg-bg2 px-1.5 py-px font-mono text-[10.5px] text-ink3">{children}</kbd>
}

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cx('h-1.5 overflow-hidden rounded-full bg-bar', className)}>
      <div className="h-full rounded-full bg-accent transition-[width] duration-500 ease-soft" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center gap-1 py-10 text-center">
      <div className="text-[13px] font-medium text-ink2">{title}</div>
      {hint && <div className="text-[12px] text-ink3">{hint}</div>}
    </div>
  )
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: rows }, (_, i) => <div key={i} className="h-9 animate-pulse rounded-[10px] bg-bar" />)}
    </div>
  )
}

export function Section({ title, aside, children, className }: { title: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cx('animate-up', className)}>
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-[11.5px] font-semibold uppercase tracking-[.06em] text-ink3">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

export function PageHead({ title, sub, actions }: { title: string; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-[22px] font-semibold tracking-[-.01em]">{title}</h1>
        {sub && <div className="mt-0.5 text-[12.5px] text-ink3">{sub}</div>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </header>
  )
}
