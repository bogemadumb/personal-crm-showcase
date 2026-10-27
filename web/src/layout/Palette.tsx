import { Command } from 'cmdk'
import DOMPurify from 'dompurify'
import { useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useSaveTask, useSearch } from '../api/hooks'
import { todayIso } from '../lib/dates'
import { Kbd } from '../ui/kit'
import { IconPlus, IconSearch } from './icons'
import { NAV } from './nav'
import { toggleTheme } from './theme'

const TYPE_TITLE = { task: 'Задача', note: 'Заметка', project: 'Проект' } as const

// Палитра ⌘K: переход по разделам, поиск по всему (полнотекстовый, на сервере) и быстрая задача на сегодня.
export function Palette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState('')
  const navigate = useNavigate()
  const hits = useSearch(q)
  const save = useSaveTask()

  useEffect(() => { if (!open) setQ('') }, [open])
  if (!open) return null

  const go = (to: string, search?: Record<string, string>) => {
    onClose()
    void navigate({ to, search: search as never })
  }
  const sections = NAV.filter((n) => !q || n.title.toLowerCase().includes(q.toLowerCase()))
  const showTheme = !q || 'тема'.includes(q.toLowerCase())
  const createTask = () => {
    if (!q.trim()) return
    save.mutate({ title: q.trim(), plan_date: todayIso() }, { onSuccess: onClose })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/25 px-4 pt-[12vh] backdrop-blur-[2px]" onMouseDown={onClose}>
      <Command
        label="Палитра команд"
        shouldFilter={false}
        className="w-full max-w-[560px] overflow-hidden rounded-[16px] bg-card shadow-card animate-up"
        onMouseDown={(e) => e.stopPropagation()}
        onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
      >
        <div className="flex items-center gap-2 border-b border-line px-4">
          <IconSearch className="text-ink3" />
          <Command.Input autoFocus value={q} onValueChange={setQ} placeholder="Куда перейти, что найти или новая задача…"
            className="h-12 flex-1 bg-transparent text-[14px] outline-none placeholder:text-ink3" />
          <Kbd>esc</Kbd>
        </div>
        <Command.List className="max-h-[360px] overflow-y-auto p-1.5">
          <Command.Empty className="px-3 py-6 text-center text-[12.5px] text-ink3">Ничего не нашлось</Command.Empty>
          {q.trim() && (
            <Command.Group heading="Действие" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:text-ink3">
              <Command.Item value="__create" onSelect={createTask} className="flex cursor-pointer items-center gap-2 rounded-[9px] px-3 py-2">
                <IconPlus className="text-accent" /> Задача на сегодня: <b className="font-medium">{q.trim()}</b>
              </Command.Item>
            </Command.Group>
          )}
          {(hits.data?.length ?? 0) > 0 && (
            <Command.Group heading="Найдено" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:text-ink3">
              {hits.data!.map((h) => (
                <Command.Item key={`${h.type}-${h.id}`} value={`${h.type}-${h.id}`}
                  onSelect={() => h.type === 'project' ? go(`/projects/${h.id}`) : h.type === 'note' ? go('/notes', { id: h.id }) : go('/tasks')}
                  className="flex cursor-pointer flex-col gap-0.5 rounded-[9px] px-3 py-2">
                  <span className="flex items-center gap-2"><span className="text-[11px] text-ink3">{TYPE_TITLE[h.type]}</span>{h.title}</span>
                  {/* ts_headline отдаёт <b> вокруг совпадений — пропускаем только его */}
                  {h.snippet && <span className="snippet line-clamp-1 text-[12px] text-ink3" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(h.snippet, { ALLOWED_TAGS: ['b'], ALLOWED_ATTR: [] }) }} />}
                </Command.Item>
              ))}
            </Command.Group>
          )}
          {(sections.length > 0 || showTheme) && (
            <Command.Group heading="Разделы" className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:text-ink3">
              {sections.map((n) => (
                <Command.Item key={n.to} value={n.to} onSelect={() => go(n.to)} className="flex cursor-pointer items-center gap-2 rounded-[9px] px-3 py-2">
                  <n.icon className="text-ink3" /> {n.title}
                  <span className="ml-auto flex gap-1"><Kbd>g</Kbd><Kbd>{n.key}</Kbd></span>
                </Command.Item>
              ))}
              {showTheme && (
                <Command.Item value="__theme" onSelect={() => { toggleTheme(); onClose() }} className="flex cursor-pointer items-center gap-2 rounded-[9px] px-3 py-2">
                  Сменить тему
                </Command.Item>
              )}
            </Command.Group>
          )}
        </Command.List>
      </Command>
    </div>
  )
}
