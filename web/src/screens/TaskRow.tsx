import { useState } from 'react'
import { useDeleteTask, useSaveTask } from '../api/hooks'
import type { Task } from '../api/types'
import { dueLabel } from '../lib/dates'
import { cx } from '../ui/cx'
import { Chip } from '../ui/kit'

const PRIORITY = ['', 'важно', 'срочно'] as const

export function TaskRow({ t, showProject = true }: { t: Task; showProject?: boolean }) {
  const save = useSaveTask()
  const del = useDeleteTask()
  const [open, setOpen] = useState(false)
  const done = t.status === 'done'

  return (
    <div className="group rounded-[10px] transition-colors hover:bg-row-hover">
      <div className="flex min-h-10 items-center gap-3 px-3 py-1.5">
        <button
          aria-label={done ? 'Вернуть в работу' : 'Отметить выполненной'}
          onClick={() => save.mutate({ id: t.id, status: done ? 'open' : 'done' })}
          className={cx('grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full border-[1.5px] transition-colors',
            done ? 'border-ok bg-ok text-white' : t.priority === 2 ? 'border-alarm' : t.priority === 1 ? 'border-warn' : 'border-ink3 hover:border-accent')}
        >
          {done && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4"><path d="M5 12l5 5L20 7" /></svg>}
        </button>
        <button onClick={() => setOpen((v) => !v)} className={cx('min-w-0 flex-1 truncate text-left', done && 'text-ink3 line-through')}>{t.title}</button>
        <div className="flex shrink-0 items-center gap-1.5">
          {t.priority > 0 && !done && <Chip tone={t.priority === 2 ? 'alarm' : 'warn'}>{PRIORITY[t.priority]}</Chip>}
          {showProject && t.project_name && <Chip>{t.project_name}</Chip>}
          {t.due && !done && <Chip tone={t.overdue ? 'alarm' : 'muted'} dot={t.overdue}>{dueLabel(t.due)}</Chip>}
        </div>
      </div>
      {open && (
        <div className="flex flex-col gap-2 px-[42px] pb-3 text-[12.5px] text-ink2">
          {t.notes && <p className="whitespace-pre-wrap">{t.notes}</p>}
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1.5">План
              <input type="date" value={t.plan_date ?? ''} onChange={(e) => save.mutate({ id: t.id, plan_date: e.target.value || null })}
                className="rounded-[7px] border border-line bg-card px-1.5 py-0.5" />
            </label>
            <label className="flex items-center gap-1.5">Срок
              <input type="date" value={t.due ?? ''} onChange={(e) => save.mutate({ id: t.id, due: e.target.value || null })}
                className="rounded-[7px] border border-line bg-card px-1.5 py-0.5" />
            </label>
            <select value={t.priority} onChange={(e) => save.mutate({ id: t.id, priority: Number(e.target.value) as Task['priority'] })}
              className="rounded-[7px] border border-line bg-card px-1.5 py-0.5">
              <option value={0}>обычная</option><option value={1}>важная</option><option value={2}>срочная</option>
            </select>
            <button onClick={() => del.mutate(t.id)} className="ml-auto text-alarm hover:underline">Удалить</button>
          </div>
        </div>
      )}
    </div>
  )
}

export function QuickAdd({ planDate, projectId, placeholder = 'Новая задача — Enter' }: { planDate?: string; projectId?: string; placeholder?: string }) {
  const save = useSaveTask()
  const [title, setTitle] = useState('')
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (!title.trim()) return
        save.mutate({ title: title.trim(), plan_date: planDate ?? null, project_id: projectId ?? null }, { onSuccess: () => setTitle('') })
      }}
      className="flex items-center gap-3 rounded-[10px] px-3 py-1.5"
    >
      <span className="grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full border-[1.5px] border-dashed border-ink3 text-ink3">+</span>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={placeholder}
        className="h-7 flex-1 bg-transparent outline-none placeholder:text-ink3" />
    </form>
  )
}
