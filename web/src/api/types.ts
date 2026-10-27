// Типы ответов API. В приватной версии они генерируются из OpenAPI (npm run api → schema.d.ts);
// здесь — вручную, чтобы сборка не зависела от запущенного сервера.
export interface Me { id: string; name: string; type: string; role: string }

export interface Task {
  id: string
  title: string
  notes: string
  project_id: string | null
  project_name: string | null
  plan_date: string | null
  due: string | null
  priority: 0 | 1 | 2
  status: 'open' | 'done'
  overdue: boolean
  created_at: string
  done_at: string | null
}

export interface Stage { n: number; title: string; marker: string | null; status: 'done' | 'cur' | 'todo'; frozen: boolean; closed_at: string | null }
export interface JournalEntry { id: number; kind: 'note' | 'decision' | 'stage'; text: string; files: string[]; author: string | null; created_at: string }

export interface ProjectShort {
  id: string
  name: string
  folder: string | null
  status: 'active' | 'paused' | 'done'
  progress: number
  stages_total: number
  stages_done: number
  current_stage: string | null
  open_tasks: number
  updated_at: string
}
export interface Project extends ProjectShort { roadmap_text: string; stages: Stage[]; journal: JournalEntry[] }

export interface Note { id: string; title: string; body: string; tags: string[]; pinned: boolean; updated_at: string }

export interface CalEvent { id: string; title: string; starts_at: string; ends_at: string | null; location: string | null; kind: 'event' | 'deadline' | 'reminder' }
export interface Day { day: string; events: CalEvent[]; deadlines: { id: string; title: string }[] }

export interface FeedEvent { id: number; source: string; kind: string; level: 'info' | 'warn' | 'error'; title: string; detail: string | null; payload: Record<string, unknown>; created_at: string }
export interface Beat {
  source: string
  title: string
  machine: string
  expect_every: number
  status: 'ok' | 'fail'
  note: string | null
  fails: number
  last_at: string
  silent_min: number
  late: boolean
  muted: boolean
  sleeping: boolean
  machine_down: boolean
  alarm: boolean
}

export interface Today {
  date: string
  focus: Task[]
  overdue: number
  done_today: number
  events: CalEvent[]
  projects: ProjectShort[]
  alarms: number
  beats_total: number
  feed: FeedEvent[]
}

export interface Hit { type: 'task' | 'note' | 'project'; id: string; title: string; snippet: string; rank: number }
