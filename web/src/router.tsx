import { createRootRoute, createRoute, createRouter, Outlet } from '@tanstack/react-router'
import { Shell } from './layout/Shell'
import { Calendar } from './screens/Calendar'
import { Login } from './screens/Login'
import { Notes } from './screens/Notes'
import { ProjectPage } from './screens/ProjectPage'
import { Projects } from './screens/Projects'
import { Pulse } from './screens/Pulse'
import { Tasks } from './screens/Tasks'
import { Today } from './screens/Today'

const root = createRootRoute({ component: Outlet })
const login = createRoute({ getParentRoute: () => root, path: '/login', component: Login })
const app = createRoute({ getParentRoute: () => root, id: 'app', component: Shell })

const today = createRoute({ getParentRoute: () => app, path: '/', component: Today })
const tasks = createRoute({
  getParentRoute: () => app, path: '/tasks', component: Tasks,
  validateSearch: (s: Record<string, unknown>): { view?: 'today' | 'upcoming' | 'inbox' | 'all' | 'done' } =>
    ({ view: ['today', 'upcoming', 'inbox', 'all', 'done'].includes(s.view as string) ? s.view as 'today' : undefined }),
})
const projects = createRoute({ getParentRoute: () => app, path: '/projects', component: Projects })
export const projectRoute = createRoute({ getParentRoute: () => app, path: '/projects/$id', component: ProjectPage })
const notes = createRoute({
  getParentRoute: () => app, path: '/notes', component: Notes,
  validateSearch: (s: Record<string, unknown>): { id?: string } => ({ id: typeof s.id === 'string' ? s.id : undefined }),
})
const calendar = createRoute({
  getParentRoute: () => app, path: '/calendar', component: Calendar,
  validateSearch: (s: Record<string, unknown>): { week?: string } => ({ week: typeof s.week === 'string' ? s.week : undefined }),
})
const pulse = createRoute({ getParentRoute: () => app, path: '/pulse', component: Pulse })

const routeTree = root.addChildren([login, app.addChildren([today, tasks, projects, projectRoute, notes, calendar, pulse])])

export const router = createRouter({ routeTree, defaultPreload: 'intent' })

declare module '@tanstack/react-router' {
  interface Register { router: typeof router }
}
