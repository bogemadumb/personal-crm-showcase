import { Link, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'
import { api, whenUnauthorized } from '../api/client'
import { queryClient, useMe, usePulse } from '../api/hooks'
import { cx } from '../ui/cx'
import { Kbd } from '../ui/kit'
import { IconMoon, IconSearch } from './icons'
import { NAV } from './nav'
import { Palette } from './Palette'
import { toggleTheme } from './theme'

export function Shell() {
  const me = useMe()
  const navigate = useNavigate()
  const path = useRouterState({ select: (s) => s.location.pathname })
  const [palette, setPalette] = useState(false)
  const pulse = usePulse()
  const alarms = pulse.data?.filter((b) => b.alarm).length ?? 0
  const gPressed = useRef(0)

  useEffect(() => whenUnauthorized(() => { void navigate({ to: '/login' }) }), [navigate])
  useEffect(() => { if (me.isError) void navigate({ to: '/login' }) }, [me.isError, navigate])

  // ⌘K — палитра; «g» и буква — раздел (как в почтовых клиентах)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPalette((v) => !v)
        return
      }
      const t = e.target as HTMLElement
      if (t.closest('input, textarea, [contenteditable]') || e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === 'g') { gPressed.current = Date.now(); return }
      if (Date.now() - gPressed.current < 800) {
        const item = NAV.find((n) => n.key === e.key)
        if (item) { gPressed.current = 0; void navigate({ to: item.to }) }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navigate])

  const logout = async () => {
    await api('/auth/logout', { method: 'POST' })
    queryClient.clear()
    void navigate({ to: '/login' })
  }

  if (!me.data) return <div className="grid h-full place-items-center text-ink3">…</div>

  return (
    <div className="flex h-full max-md:flex-col">
      <aside className="flex w-[216px] shrink-0 flex-col gap-1 border-r border-line bg-bg2 px-3 py-4 max-md:w-full max-md:flex-row max-md:items-center max-md:overflow-x-auto max-md:border-r-0 max-md:border-b max-md:py-2">
        <div className="mb-3 flex items-center gap-2 px-2 max-md:mb-0">
          <span className="grid h-6 w-6 place-items-center rounded-[7px] bg-accent text-[12px] font-bold text-white">C</span>
          <span className="font-semibold max-md:hidden">CRM</span>
        </div>
        <button onClick={() => setPalette(true)}
          className="mb-2 flex items-center gap-2 rounded-[9px] border border-line bg-card px-2.5 py-1.5 text-left text-[12.5px] text-ink3 max-md:mb-0 max-md:shrink-0">
          <IconSearch /> <span className="max-md:hidden">Поиск и команды</span> <span className="ml-auto max-md:hidden"><Kbd>⌘K</Kbd></span>
        </button>
        {NAV.map((n) => {
          const on = n.to === '/' ? path === '/' : path.startsWith(n.to)
          return (
            <Link key={n.to} to={n.to}
              className={cx('flex items-center gap-2.5 rounded-[9px] px-2.5 py-[7px] text-[13px] transition-colors max-md:shrink-0',
                on ? 'bg-card font-medium text-ink shadow-card' : 'text-ink2 hover:bg-row-hover')}>
              <n.icon className={on ? 'text-accent' : 'text-ink3'} />
              {n.title}
              {n.to === '/pulse' && alarms > 0 && (
                <span className="relative ml-auto flex h-2 w-2">
                  <span className="absolute inset-0 animate-pulse-dot rounded-full bg-alarm" />
                  <span className="relative h-2 w-2 rounded-full bg-alarm" />
                </span>
              )}
            </Link>
          )
        })}
        <div className="mt-auto flex items-center gap-2 px-2 pt-4 text-[12px] text-ink3 max-md:mt-0 max-md:ml-auto max-md:pt-0">
          <span className="truncate max-md:hidden">{me.data.name}</span>
          <button onClick={toggleTheme} title="Тема" className="ml-auto rounded-[7px] p-1 hover:bg-row-hover"><IconMoon /></button>
          <button onClick={logout} className="rounded-[7px] px-1.5 py-1 hover:bg-row-hover">Выйти</button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1080px] px-8 py-8 max-md:px-4 max-md:py-5">
          <Outlet />
        </div>
      </main>
      <Palette open={palette} onClose={() => setPalette(false)} />
    </div>
  )
}
