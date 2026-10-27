import { QueryClient, useMutation, useQuery } from '@tanstack/react-query'
import { api } from './client'
import type { Beat, Day, FeedEvent, Hit, Me, Note, Project, ProjectShort, Task, Today } from './types'

export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15_000, retry: (n, e: unknown) => n < 2 && (e as { status?: number })?.status !== 401 } },
})

// после любой записи — сбросить всё: экранов мало, а сводка «Сегодня» зависит от всего сразу
const invalidate = () => queryClient.invalidateQueries()

export const useMe = () => useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/auth/me'), retry: false, staleTime: 300_000 })
export const useToday = () => useQuery({ queryKey: ['today'], queryFn: () => api<Today>('/today'), refetchInterval: 60_000 })

export const useTasks = (view: string, status = 'open', projectId?: string) =>
  useQuery({ queryKey: ['tasks', view, status, projectId], queryFn: () => api<Task[]>('/tasks', { params: { view, status, project_id: projectId } }) })

export const useProjects = (status: 'active' | 'all' = 'all') =>
  useQuery({ queryKey: ['projects', status], queryFn: () => api<ProjectShort[]>('/projects', { params: { status } }) })
export const useProject = (id: string) => useQuery({ queryKey: ['project', id], queryFn: () => api<Project>(`/projects/${id}`) })

export const useNotes = () => useQuery({ queryKey: ['notes'], queryFn: () => api<Note[]>('/notes') })
export const useWeek = (start?: string) => useQuery({ queryKey: ['week', start], queryFn: () => api<Day[]>('/calendar', { params: { start, days: 7 } }) })
export const useFeed = (hours = 72) => useQuery({ queryKey: ['feed', hours], queryFn: () => api<FeedEvent[]>('/feed', { params: { hours } }), refetchInterval: 30_000 })
export const usePulse = () => useQuery({ queryKey: ['pulse'], queryFn: () => api<Beat[]>('/feed/pulse'), refetchInterval: 30_000 })
export const useSearch = (q: string) =>
  useQuery({ queryKey: ['search', q], queryFn: () => api<Hit[]>('/search', { params: { q } }), enabled: q.trim().length >= 2, staleTime: 5_000 })

export function useSaveTask() {
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Task> & { id?: string }) =>
      id ? api<Task>(`/tasks/${id}`, { method: 'PATCH', body }) : api<Task>('/tasks', { body }),
    onSuccess: invalidate,
  })
}
export const useDeleteTask = () => useMutation({ mutationFn: (id: string) => api(`/tasks/${id}`, { method: 'DELETE' }), onSuccess: invalidate })

export function useMarkStage(projectId: string) {
  return useMutation({
    mutationFn: (b: { n: number; status: 'done' | 'todo' }) => api<{ result: string; project: Project }>(`/projects/${projectId}/stage`, { body: b }),
    onSuccess: invalidate,
  })
}
export function useAddJournal(projectId: string) {
  return useMutation({
    mutationFn: (b: { text: string; kind: 'note' | 'decision' }) => api(`/projects/${projectId}/journal`, { body: b }),
    onSuccess: invalidate,
  })
}
export function useSaveRoadmap(projectId: string) {
  return useMutation({ mutationFn: (text: string) => api<Project>(`/projects/${projectId}/roadmap`, { method: 'PUT', body: { text } }), onSuccess: invalidate })
}

export function useSaveNote() {
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Note> & { id?: string }) =>
      id ? api<Note>(`/notes/${id}`, { method: 'PATCH', body }) : api<Note>('/notes', { body }),
    onSuccess: invalidate,
  })
}
export const useDeleteNote = () => useMutation({ mutationFn: (id: string) => api(`/notes/${id}`, { method: 'DELETE' }), onSuccess: invalidate })

export function useMute() {
  return useMutation({ mutationFn: (b: { source: string; hours: number }) => api(`/feed/beats/${b.source}/mute`, { body: { hours: b.hours } }), onSuccess: invalidate })
}
