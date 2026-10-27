import { useFeed, useMute, usePulse } from '../api/hooks'
import type { Beat } from '../api/types'
import { ago } from '../lib/dates'
import { cx } from '../ui/cx'
import { Button, Card, Chip, PageHead, Section, Skeleton } from '../ui/kit'

const MACHINE: Record<string, string> = { server: 'Сервер', 'home-pc': 'Домашний ПК', laptop: 'Ноутбук' }

function every(sec: number) {
  if (sec < 3600) return `${Math.round(sec / 60)} мин`
  if (sec < 86400) return `${Math.round(sec / 3600)} ч`
  return `${Math.round(sec / 86400)} дн`
}

export function Pulse() {
  const pulse = usePulse()
  const feed = useFeed(72)
  const machines = new Map<string, Beat[]>()
  for (const b of pulse.data ?? []) machines.set(b.machine, [...(machines.get(b.machine) ?? []), b])

  return (
    <>
      <PageHead title="Пульс" sub="Фоновые задачи шлют биения; молчание дольше обещанного — тревога. Спящий ноутбук и упавшая машина не плодят шум." />
      {pulse.isLoading ? <Skeleton rows={6} /> : (
        <div className="mb-8 grid grid-cols-3 gap-4 max-lg:grid-cols-1">
          {[...machines].map(([m, beats]) => (
            <Card key={m} className="animate-up">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-semibold">{MACHINE[m] ?? m}</span>
                {beats.some((b) => b.alarm) ? <Chip tone="alarm" dot>тревога</Chip> : beats.some((b) => b.sleeping) ? <Chip>спит</Chip> : <Chip tone="ok" dot>в порядке</Chip>}
              </div>
              <div className="flex flex-col gap-2.5">
                {beats.map((b) => <BeatRow key={b.source} b={b} />)}
              </div>
            </Card>
          ))}
        </div>
      )}
      <Section title="Лента за трое суток">
        <Card bare className="p-1.5">
          {feed.data?.map((f) => (
            <div key={f.id} className="flex items-start gap-3 rounded-[10px] px-3 py-2 hover:bg-row-hover">
              <span className={cx('mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full', f.level === 'error' ? 'bg-alarm' : f.level === 'warn' ? 'bg-warn' : 'bg-ink3')} />
              <div className="min-w-0 flex-1">
                <div>{f.title}</div>
                {f.detail && <div className="text-[12px] text-ink3">{f.detail}</div>}
              </div>
              <span className="shrink-0 font-mono text-[11px] text-ink3">{f.source}</span>
              <span className="w-24 shrink-0 text-right text-[12px] text-ink3">{ago(f.created_at)}</span>
            </div>
          ))}
        </Card>
      </Section>
    </>
  )
}

function BeatRow({ b }: { b: Beat }) {
  const mute = useMute()
  const state = b.muted ? ['заглушена', 'muted'] : b.sleeping ? ['спит', 'muted'] : b.machine_down ? ['машина молчит', 'warn']
    : b.status === 'fail' ? ['сбой', 'alarm'] : b.late ? ['молчит', 'alarm'] : ['ок', 'ok']
  return (
    <div className="group">
      <div className="flex items-center gap-2">
        <span className="min-w-0 flex-1 truncate text-[12.5px]">{b.title}</span>
        <Chip tone={state[1] as 'ok'}>{state[0]}</Chip>
      </div>
      <div className="text-[11.5px] text-ink3">{ago(b.last_at)} · раз в {every(b.expect_every)}</div>
      {b.note && <div className="text-[11.5px] text-ink3">{b.note}</div>}
      {b.alarm && (
        <div className="mt-1 hidden group-hover:block">
          <Button small variant="ghost" onClick={() => mute.mutate({ source: b.source, hours: 24 })}>Заглушить на сутки</Button>
        </div>
      )}
    </div>
  )
}
