import { useNavigate } from '@tanstack/react-router'
import { useState, type FormEvent } from 'react'
import { api, ApiError } from '../api/client'
import { queryClient } from '../api/hooks'
import { Button, Card } from '../ui/kit'

export function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('demo@example.com')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api('/auth/login', { body: { email, password } })
      queryClient.clear()
      void navigate({ to: '/' })
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'сервер недоступен')
    } finally {
      setBusy(false)
    }
  }

  const input = 'h-10 w-full rounded-[10px] border border-line bg-bg px-3 text-[13.5px] outline-none focus:border-accent'
  return (
    <div className="grid h-full place-items-center px-4">
      <Card className="w-full max-w-[360px] animate-up px-7 py-7">
        <div className="mb-5 flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-[8px] bg-accent text-[13px] font-bold text-white">C</span>
          <span className="text-[17px] font-semibold">Вход</span>
        </div>
        <form onSubmit={submit} className="flex flex-col gap-3">
          <input className={input} type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Почта" />
          <input className={input} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Пароль" autoFocus />
          {error && <div className="text-[12.5px] text-alarm">{error}</div>}
          <Button type="submit" variant="accent" disabled={busy} className="mt-1 h-10">Войти</Button>
        </form>
        <p className="mt-4 text-[12px] leading-relaxed text-ink3">Демо: <code className="font-mono">demo@example.com</code> / <code className="font-mono">demo</code></p>
      </Card>
    </div>
  )
}
