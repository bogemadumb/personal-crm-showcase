import { Link, useParams } from '@tanstack/react-router'
import { useState } from 'react'
import { useAddJournal, useMarkStage, useProject, useSaveRoadmap, useTasks } from '../api/hooks'
import type { Stage } from '../api/types'
import { ago, fmtDay } from '../lib/dates'
import { cx } from '../ui/cx'
import { Button, Card, Chip, Empty, PageHead, Progress, Section, Skeleton } from '../ui/kit'
import { QuickAdd, TaskRow } from './TaskRow'

export function ProjectPage() {
  const { id } = useParams({ from: '/app/projects/$id' })
  const { data: p, isLoading } = useProject(id)
  const tasks = useTasks('all', 'open', id)
  const mark = useMarkStage(id)
  const [editing, setEditing] = useState(false)

  if (isLoading || !p) return <Skeleton rows={6} />

  return (
    <>
      <Link to="/projects" className="mb-3 inline-block text-[12px] text-ink3 hover:text-accent">← Проекты</Link>
      <PageHead title={p.name} sub={p.folder ? <span className="font-mono">{p.folder}</span> : undefined}
        actions={<Button variant="ghost" onClick={() => setEditing((v) => !v)}>{editing ? 'Готово' : 'Править карту'}</Button>} />

      <div className="mb-6 flex items-center gap-4">
        <Progress value={p.progress} className="flex-1" />
        <span className="font-mono text-[12.5px] text-ink2">{p.progress}%</span>
      </div>

      <div className="grid grid-cols-[1.3fr_1fr] gap-6 max-lg:grid-cols-1">
        <div className="flex flex-col gap-6">
          <Section title="Дорожная карта" aside={<span className="text-[11.5px] text-ink3">клик по кружку — закрыть или открыть этап</span>}>
            {editing ? <RoadmapEditor id={id} text={p.roadmap_text} /> : (
              <Card bare className="p-1.5">
                {p.stages.length ? p.stages.map((s) => (
                  <StageRow key={s.n} s={s} busy={mark.isPending}
                    onToggle={() => mark.mutate({ n: s.n, status: s.status === 'done' ? 'todo' : 'done' })} />
                )) : <Empty title="В карте не нашлось этапов" hint="Поддерживаются чекбоксы, заголовки «## Этап N» и таблицы" />}
              </Card>
            )}
          </Section>
          <Section title="Задачи проекта">
            <Card bare className="p-1.5">
              {tasks.data?.map((t) => <TaskRow key={t.id} t={t} showProject={false} />)}
              <QuickAdd projectId={id} />
            </Card>
          </Section>
        </div>
        <Section title="Журнал">
          <Journal id={id} entries={p.journal} />
        </Section>
      </div>
    </>
  )
}

function StageRow({ s, onToggle, busy }: { s: Stage; onToggle: () => void; busy: boolean }) {
  return (
    <div className={cx('flex gap-3 rounded-[10px] px-3 py-2.5', s.status === 'cur' && 'bg-accent-soft/60')}>
      <button disabled={busy || s.frozen} onClick={onToggle} aria-label="Сменить статус этапа"
        className={cx('mt-0.5 grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full border-[1.5px] transition-colors',
          s.status === 'done' ? 'border-ok bg-ok text-white' : s.status === 'cur' ? 'border-accent' : 'border-ink3', s.frozen && 'border-dashed opacity-50')}>
        {s.status === 'done' && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4"><path d="M5 12l5 5L20 7" /></svg>}
      </button>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11.5px] text-ink3">{s.n}</span>
          <span className={cx(s.status === 'done' && 'text-ink2', s.status === 'cur' && 'font-medium')}>{s.title}</span>
          {s.status === 'cur' && <Chip tone="accent">сейчас</Chip>}
          {s.frozen && <Chip>заморожен</Chip>}
          {s.closed_at && <span className="text-[11.5px] text-ink3">закрыт {fmtDay(s.closed_at)}</span>}
        </div>
        {s.marker && <div className="mt-0.5 text-[12px] text-ink3">Маркер: {s.marker}</div>}
      </div>
    </div>
  )
}

function RoadmapEditor({ id, text }: { id: string; text: string }) {
  const save = useSaveRoadmap(id)
  const [v, setV] = useState(text)
  return (
    <Card className="flex flex-col gap-2">
      <textarea value={v} onChange={(e) => setV(e.target.value)} spellCheck={false}
        className="min-h-[320px] w-full resize-y rounded-[10px] border border-line bg-bg p-3 font-mono text-[12px] leading-relaxed outline-none focus:border-accent" />
      <div className="flex justify-end"><Button variant="accent" disabled={save.isPending || v === text} onClick={() => save.mutate(v)}>Сохранить и пересобрать этапы</Button></div>
    </Card>
  )
}

const KIND = { note: ['заметка', 'muted'], decision: ['решение', 'accent'], stage: ['этап', 'ok'] } as const

function Journal({ id, entries }: { id: string; entries: { id: number; kind: 'note' | 'decision' | 'stage'; text: string; created_at: string }[] }) {
  const add = useAddJournal(id)
  const [text, setText] = useState('')
  const [kind, setKind] = useState<'note' | 'decision'>('note')
  return (
    <Card className="flex flex-col gap-4">
      <form onSubmit={(e) => { e.preventDefault(); if (text.trim()) add.mutate({ text: text.trim(), kind }, { onSuccess: () => setText('') }) }} className="flex flex-col gap-2">
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} placeholder="Что сделано или что решили — и почему"
          className="w-full resize-none rounded-[10px] border border-line bg-bg p-2.5 outline-none focus:border-accent" />
        <div className="flex items-center gap-2">
          {(['note', 'decision'] as const).map((k) => (
            <button type="button" key={k} onClick={() => setKind(k)} className={cx('rounded-full px-2.5 py-0.5 text-[12px]', kind === k ? 'bg-btn text-btn-fg' : 'bg-chip text-ink2')}>{KIND[k][0]}</button>
          ))}
          <Button type="submit" small className="ml-auto" disabled={!text.trim() || add.isPending}>Записать</Button>
        </div>
      </form>
      {entries.length ? entries.map((e) => (
        <div key={e.id} className="border-t border-line pt-3">
          <div className="mb-1 flex items-center gap-2"><Chip tone={KIND[e.kind][1]}>{KIND[e.kind][0]}</Chip><span className="text-[11.5px] text-ink3">{ago(e.created_at)}</span></div>
          <p className="whitespace-pre-wrap text-[12.5px] leading-relaxed">{e.text}</p>
        </div>
      )) : <Empty title="Журнал пуст" />}
    </Card>
  )
}
