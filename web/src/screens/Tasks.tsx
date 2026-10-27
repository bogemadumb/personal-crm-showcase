import { useNavigate, useSearch } from '@tanstack/react-router'
import { useTasks } from '../api/hooks'
import type { Task } from '../api/types'
import { todayIso } from '../lib/dates'
import { cx } from '../ui/cx'
import { Card, Empty, PageHead, Skeleton } from '../ui/kit'
import { QuickAdd, TaskRow } from './TaskRow'

const VIEWS = [
  { key: 'today', title: 'Сегодня' },
  { key: 'upcoming', title: 'Впереди' },
  { key: 'inbox', title: 'Входящие' },
  { key: 'all', title: 'Все открытые' },
  { key: 'done', title: 'Сделано' },
] as const

export function Tasks() {
  const { view = 'today' } = useSearch({ from: '/app/tasks' })
  const navigate = useNavigate()
  const q = useTasks(view === 'done' ? 'all' : view, view === 'done' ? 'done' : 'open')

  return (
    <>
      <PageHead title="Задачи" sub="Фокус — то, что запланировано на сегодня или уже горит по сроку" />
      <div className="mb-4 flex flex-wrap gap-1.5">
        {VIEWS.map((v) => (
          <button key={v.key} onClick={() => void navigate({ to: '/tasks', search: { view: v.key } })}
            className={cx('rounded-full px-3 py-1 text-[12.5px] transition-colors', view === v.key ? 'bg-btn text-btn-fg' : 'bg-chip text-ink2 hover:text-ink')}>
            {v.title}
          </button>
        ))}
      </div>
      <Card bare className="p-1.5">
        {q.isLoading ? <Skeleton /> : <Grouped tasks={q.data ?? []} byProject={view === 'all'} />}
        {view !== 'done' && <QuickAdd planDate={view === 'today' ? todayIso() : undefined} />}
      </Card>
    </>
  )
}

function Grouped({ tasks, byProject }: { tasks: Task[]; byProject: boolean }) {
  if (!tasks.length) return <Empty title="Здесь пусто" hint="Хороший знак — или повод запланировать" />
  if (!byProject) return <>{tasks.map((t) => <TaskRow key={t.id} t={t} />)}</>
  const groups = new Map<string, Task[]>()
  for (const t of tasks) {
    const k = t.project_name ?? 'Без проекта'
    groups.set(k, [...(groups.get(k) ?? []), t])
  }
  return (
    <>
      {[...groups].map(([name, list]) => (
        <div key={name} className="mb-2">
          <div className="px-3 pt-2 pb-1 text-[11.5px] font-semibold uppercase tracking-[.06em] text-ink3">{name}</div>
          {list.map((t) => <TaskRow key={t.id} t={t} showProject={false} />)}
        </div>
      ))}
    </>
  )
}
