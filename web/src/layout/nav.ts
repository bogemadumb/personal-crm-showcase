import type { ComponentType, SVGProps } from 'react'
import { IconCalendar, IconNotes, IconProjects, IconPulse, IconTasks, IconToday } from './icons'

export interface NavItem { to: string; title: string; key: string; icon: ComponentType<SVGProps<SVGSVGElement>> }

// key — сочетание «g + буква» для перехода с клавиатуры
export const NAV: NavItem[] = [
  { to: '/', title: 'Сегодня', key: 'h', icon: IconToday },
  { to: '/tasks', title: 'Задачи', key: 't', icon: IconTasks },
  { to: '/projects', title: 'Проекты', key: 'p', icon: IconProjects },
  { to: '/notes', title: 'Заметки', key: 'n', icon: IconNotes },
  { to: '/calendar', title: 'Календарь', key: 'c', icon: IconCalendar },
  { to: '/pulse', title: 'Пульс', key: 'u', icon: IconPulse },
]
