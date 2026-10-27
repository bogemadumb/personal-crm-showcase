import { Link } from '@tanstack/react-router'
import { useProjects } from '../api/hooks'
import { ago, plural } from '../lib/dates'
import { Card, Chip, PageHead, Progress, Skeleton } from '../ui/kit'

const STATUS = { active: ['в работе', 'accent'], paused: ['на паузе', 'muted'], done: ['закрыт', 'ok'] } as const

export function Projects() {
  const { data, isLoading } = useProjects('all')
  return (
    <>
      <PageHead title="Проекты" sub="Проект — папка со спецификацией, дорожной картой и журналом. Прогресс считается по карте." />
      {isLoading ? <Skeleton rows={4} /> : (
        <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
          {data!.map((p, i) => (
            <Link key={p.id} to="/projects/$id" params={{ id: p.id }} style={{ animationDelay: `${i * 40}ms` }} className="animate-up">
              <Card className="h-full transition-transform duration-200 ease-soft hover:-translate-y-0.5">
                <div className="mb-3 flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-[15px] font-semibold">{p.name}</div>
                    {p.folder && <div className="truncate font-mono text-[11px] text-ink3">{p.folder}</div>}
                  </div>
                  <Chip tone={STATUS[p.status][1]}>{STATUS[p.status][0]}</Chip>
                </div>
                <Progress value={p.progress} />
                <div className="mt-2 flex items-center justify-between text-[12px] text-ink3">
                  <span>{p.stages_done} из {plural(p.stages_total, 'этапа', 'этапов', 'этапов')} · {plural(p.open_tasks, 'задача', 'задачи', 'задач')}</span>
                  <span>{ago(p.updated_at)}</span>
                </div>
                {p.current_stage && <div className="mt-2 truncate text-[12.5px] text-ink2">Сейчас: {p.current_stage}</div>}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
