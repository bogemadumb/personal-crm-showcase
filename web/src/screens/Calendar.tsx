import { useNavigate, useSearch } from '@tanstack/react-router'
import { useWeek } from '../api/hooks'
import { addDays, fmtDay, fmtTime, fmtWeekday, mondayOf, todayIso } from '../lib/dates'
import { cx } from '../ui/cx'
import { Button, Card, PageHead, Skeleton } from '../ui/kit'

export function Calendar() {
  const { week } = useSearch({ from: '/app/calendar' })
  const navigate = useNavigate()
  const start = mondayOf(week ?? todayIso())
  const { data, isLoading } = useWeek(start)
  const go = (w: string) => void navigate({ to: '/calendar', search: { week: w } })
  const today = todayIso()

  return (
    <>
      <PageHead title="Календарь" sub={`${fmtDay(start)} — ${fmtDay(addDays(start, 6))}`}
        actions={<>
          <Button variant="ghost" onClick={() => go(addDays(start, -7))}>←</Button>
          <Button variant="ghost" onClick={() => go(mondayOf(today))}>Эта неделя</Button>
          <Button variant="ghost" onClick={() => go(addDays(start, 7))}>→</Button>
        </>} />
      {isLoading ? <Skeleton rows={7} /> : (
        <div className="grid grid-cols-7 gap-2 max-lg:grid-cols-1">
          {data!.map((d) => (
            <Card key={d.day} bare className={cx('min-h-[220px] p-2.5', d.day === today && 'ring-2 ring-accent/40')}>
              <div className="mb-2 flex items-baseline justify-between px-1">
                <span className={cx('text-[12px] uppercase', d.day === today ? 'font-semibold text-accent' : 'text-ink3')}>{fmtWeekday(d.day)}</span>
                <span className="text-[12px] text-ink3">{fmtDay(d.day)}</span>
              </div>
              <div className="flex flex-col gap-1.5">
                {d.events.map((e) => (
                  <div key={e.id} className={cx('rounded-[8px] px-2 py-1.5 text-[12px]',
                    e.kind === 'deadline' ? 'bg-warn-soft text-warn' : e.kind === 'reminder' ? 'bg-chip text-ink2' : 'bg-accent-soft text-accent')}>
                    <div className="font-mono text-[10.5px] opacity-80">{fmtTime(e.starts_at)}{e.ends_at ? `–${fmtTime(e.ends_at)}` : ''}</div>
                    <div className="leading-snug [overflow-wrap:anywhere]">{e.title}</div>
                    {e.location && <div className="text-[11px] opacity-70">{e.location}</div>}
                  </div>
                ))}
                {d.deadlines.map((t) => (
                  <div key={t.id} className="rounded-[8px] border border-dashed border-alarm/40 px-2 py-1.5 text-[12px] text-alarm [overflow-wrap:anywhere]">
                    <div className="text-[10.5px]">срок задачи</div>{t.title}
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
