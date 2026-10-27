import { Link } from '@tanstack/react-router'
import { useToday } from '../api/hooks'
import { ago, fmtDay, fmtTime, fmtWeekday, todayIso } from '../lib/dates'
import { Card, Chip, Empty, PageHead, Progress, Section, Skeleton } from '../ui/kit'
import { QuickAdd, TaskRow } from './TaskRow'

function greeting() {
  const h = new Date().getHours()
  return h < 5 ? 'Доброй ночи' : h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер'
}

export function Today() {
  const { data, isLoading } = useToday()
  if (isLoading || !data) return <Skeleton rows={6} />

  return (
    <>
      <PageHead title={greeting()} sub={`${fmtWeekday(data.date)}, ${fmtDay(data.date)}`} />

      <div className="mb-6 grid grid-cols-4 gap-3 max-md:grid-cols-2">
        <Stat label="В фокусе" value={data.focus.length} />
        <Stat label="Просрочено" value={data.overdue} tone={data.overdue ? 'alarm' : undefined} />
        <Stat label="Сделано сегодня" value={data.done_today} tone={data.done_today ? 'ok' : undefined} />
        <Link to="/pulse"><Stat label="Тревоги пульса" value={`${data.alarms}/${data.beats_total}`} tone={data.alarms ? 'alarm' : 'ok'} /></Link>
      </div>

      <div className="grid grid-cols-[1.4fr_1fr] gap-6 max-lg:grid-cols-1">
        <Section title="Фокус дня" aside={<Link to="/tasks" search={{ view: 'today' }} className="text-[12px] text-ink3 hover:text-accent">все задачи →</Link>}>
          <Card bare className="p-1.5">
            {data.focus.length ? data.focus.map((t) => <TaskRow key={t.id} t={t} />) : <Empty title="На сегодня пусто" hint="Добавьте задачу ниже или через ⌘K" />}
            <QuickAdd planDate={todayIso()} />
          </Card>
        </Section>

        <div className="flex flex-col gap-6">
          <Section title="Ближайшее">
            <Card className="flex flex-col gap-3">
              {data.events.length ? data.events.map((e) => (
                <div key={e.id} className="flex items-start gap-3">
                  <div className="w-12 shrink-0 font-mono text-[12px] text-ink3">{e.kind === 'event' ? fmtTime(e.starts_at) : '—'}</div>
                  <div className="min-w-0">
                    <div className="truncate">{e.title}</div>
                    <div className="text-[12px] text-ink3">{e.starts_at.slice(0, 10) === data.date ? 'сегодня' : 'завтра'}{e.location ? ` · ${e.location}` : ''}</div>
                  </div>
                  {e.kind !== 'event' && <Chip tone={e.kind === 'deadline' ? 'warn' : 'muted'} className="ml-auto">{e.kind === 'deadline' ? 'срок' : 'напоминание'}</Chip>}
                </div>
              )) : <Empty title="Сегодня и завтра свободны" />}
            </Card>
          </Section>

          <Section title="Проекты в работе" aside={<Link to="/projects" className="text-[12px] text-ink3 hover:text-accent">все →</Link>}>
            <Card className="flex flex-col gap-4">
              {data.projects.map((p) => (
                <Link key={p.id} to="/projects/$id" params={{ id: p.id }} className="group block">
                  <div className="mb-1.5 flex items-baseline justify-between gap-2">
                    <span className="truncate font-medium group-hover:text-accent">{p.name}</span>
                    <span className="font-mono text-[11.5px] text-ink3">{p.stages_done}/{p.stages_total}</span>
                  </div>
                  <Progress value={p.progress} />
                  {p.current_stage && <div className="mt-1 truncate text-[12px] text-ink3">Сейчас: {p.current_stage}</div>}
                </Link>
              ))}
            </Card>
          </Section>

          <Section title="Лента" aside={<Link to="/pulse" className="text-[12px] text-ink3 hover:text-accent">пульс →</Link>}>
            <Card className="flex flex-col gap-2.5">
              {data.feed.map((f) => (
                <div key={f.id} className="flex items-start gap-2.5 text-[12.5px]">
                  <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${f.level === 'error' ? 'bg-alarm' : f.level === 'warn' ? 'bg-warn' : 'bg-ink3'}`} />
                  <span className="min-w-0 flex-1">{f.title}</span>
                  <span className="shrink-0 text-ink3">{ago(f.created_at)}</span>
                </div>
              ))}
            </Card>
          </Section>
        </div>
      </div>
    </>
  )
}

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: 'ok' | 'alarm' }) {
  return (
    <Card className="animate-up">
      <div className="text-[11.5px] text-ink3">{label}</div>
      <div className={`mt-1 text-[28px] font-semibold tracking-[-.02em] ${tone === 'alarm' ? 'text-alarm' : tone === 'ok' ? 'text-ok' : ''}`}>{value}</div>
    </Card>
  )
}
