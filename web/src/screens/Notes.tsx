import { useNavigate, useSearch } from '@tanstack/react-router'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useEffect, useMemo, useState } from 'react'
import { useDeleteNote, useNotes, useSaveNote } from '../api/hooks'
import type { Note } from '../api/types'
import { ago } from '../lib/dates'
import { cx } from '../ui/cx'
import { Button, Card, Chip, Empty, PageHead, Skeleton } from '../ui/kit'

export function Notes() {
  const { id } = useSearch({ from: '/app/notes' })
  const navigate = useNavigate()
  const { data, isLoading } = useNotes()
  const [tag, setTag] = useState<string | null>(null)
  const save = useSaveNote()

  const tags = useMemo(() => [...new Set((data ?? []).flatMap((n) => n.tags))].sort(), [data])
  const list = (data ?? []).filter((n) => !tag || n.tags.includes(tag))
  const current = data?.find((n) => n.id === id) ?? list[0]
  const open = (nid: string) => void navigate({ to: '/notes', search: { id: nid } })

  return (
    <>
      <PageHead title="Заметки" sub="Markdown, теги, закреплённые сверху"
        actions={<Button variant="accent" onClick={() => save.mutate({ title: 'Новая заметка', body: '' }, { onSuccess: (n) => open(n.id) })}>Новая заметка</Button>} />
      {tags.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          {[null, ...tags].map((t) => (
            <button key={t ?? '__all'} onClick={() => setTag(t)} className={cx('rounded-full px-2.5 py-0.5 text-[12px]', tag === t ? 'bg-btn text-btn-fg' : 'bg-chip text-ink2')}>
              {t ? `#${t}` : 'все'}
            </button>
          ))}
        </div>
      )}
      {isLoading ? <Skeleton rows={5} /> : (
        <div className="grid grid-cols-[280px_1fr] gap-5 max-md:grid-cols-1">
          <Card bare className="flex max-h-[70vh] flex-col overflow-y-auto p-1.5">
            {list.map((n) => (
              <button key={n.id} onClick={() => open(n.id)}
                className={cx('rounded-[10px] px-3 py-2 text-left transition-colors', current?.id === n.id ? 'bg-bg2' : 'hover:bg-row-hover')}>
                <div className="flex items-center gap-1.5 truncate font-medium">{n.pinned && <span className="text-accent">•</span>}{n.title}</div>
                <div className="truncate text-[12px] text-ink3">{n.body.replace(/[#*`>\-\n]+/g, ' ').trim() || 'пусто'}</div>
              </button>
            ))}
            {!list.length && <Empty title="Нет заметок" />}
          </Card>
          {current ? <Editor key={current.id} note={current} /> : <Empty title="Выберите заметку" />}
        </div>
      )}
    </>
  )
}

function Editor({ note }: { note: Note }) {
  const save = useSaveNote()
  const del = useDeleteNote()
  const navigate = useNavigate()
  const [title, setTitle] = useState(note.title)
  const [body, setBody] = useState(note.body)
  const [edit, setEdit] = useState(!note.body)
  const html = useMemo(() => DOMPurify.sanitize(marked.parse(body, { async: false }) as string), [body])

  // автосохранение через полсекунды тишины
  useEffect(() => {
    if (title === note.title && body === note.body) return
    const t = setTimeout(() => save.mutate({ id: note.id, title: title || 'Без названия', body }), 500)
    return () => clearTimeout(t)
  }, [title, body])

  return (
    <Card className="flex min-h-[60vh] flex-col gap-3">
      <div className="flex items-center gap-2">
        <input value={title} onChange={(e) => setTitle(e.target.value)} className="min-w-0 flex-1 bg-transparent text-[18px] font-semibold outline-none" />
        <Button small variant="ghost" onClick={() => save.mutate({ id: note.id, pinned: !note.pinned })}>{note.pinned ? 'Открепить' : 'Закрепить'}</Button>
        <Button small variant="ghost" onClick={() => setEdit((v) => !v)}>{edit ? 'Просмотр' : 'Править'}</Button>
        <Button small variant="ghost" className="text-alarm" onClick={() => del.mutate(note.id, { onSuccess: () => void navigate({ to: '/notes', search: {} }) })}>Удалить</Button>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-[12px] text-ink3">
        {note.tags.map((t) => <Chip key={t}>#{t}</Chip>)}
        <span>изменена {ago(note.updated_at)}</span>
        {save.isPending && <span>· сохраняю…</span>}
      </div>
      {edit ? (
        <textarea value={body} onChange={(e) => setBody(e.target.value)} autoFocus spellCheck={false}
          className="flex-1 resize-none rounded-[10px] border border-line bg-bg p-3 font-mono text-[12.5px] leading-relaxed outline-none focus:border-accent" />
      ) : (
        <div className="prose-note" onDoubleClick={() => setEdit(true)} dangerouslySetInnerHTML={{ __html: html }} />
      )}
    </Card>
  )
}
