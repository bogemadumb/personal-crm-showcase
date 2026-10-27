const pad = (n: number) => String(n).padStart(2, '0')

export const isoDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
export const todayIso = () => isoDate(new Date())
export const addDays = (iso: string, n: number) => {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() + n)
  return isoDate(d)
}
export const mondayOf = (iso: string) => {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return isoDate(d)
}

const DAY = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' })
const WEEKDAY = new Intl.DateTimeFormat('ru-RU', { weekday: 'short' })
const TIME = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' })

export const fmtDay = (iso: string) => DAY.format(new Date(`${iso.slice(0, 10)}T12:00:00`))
export const fmtWeekday = (iso: string) => WEEKDAY.format(new Date(`${iso.slice(0, 10)}T12:00:00`))
export const fmtTime = (iso: string) => TIME.format(new Date(iso))

/** «только что», «12 мин назад», «3 ч назад», «вчера», «5 окт» */
export function ago(iso: string): string {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return 'только что'
  if (s < 3600) return `${Math.floor(s / 60)} мин назад`
  if (s < 86400) return `${Math.floor(s / 3600)} ч назад`
  if (s < 2 * 86400) return 'вчера'
  return DAY.format(new Date(iso))
}

/** срок задачи относительно сегодня */
export function dueLabel(iso: string): string {
  const diff = Math.round((new Date(`${iso}T12:00:00`).getTime() - new Date(`${todayIso()}T12:00:00`).getTime()) / 86400000)
  if (diff === 0) return 'сегодня'
  if (diff === 1) return 'завтра'
  if (diff === -1) return 'вчера'
  if (diff < 0) return `${-diff} дн. назад`
  if (diff < 7) return fmtWeekday(iso)
  return fmtDay(iso)
}

/** 1 задача, 2 задачи, 5 задач */
export function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10, m100 = n % 100
  const w = m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20) ? few : many
  return `${n} ${w}`
}
