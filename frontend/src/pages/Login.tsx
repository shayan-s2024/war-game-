import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useGameStore } from '../store/gameStore'
import { errMsg } from '../lib/api'

declare global {
  interface Window {
    Telegram?: {
      Login?: { auth: (cb: (data: any) => void, botName: string) => void }
      WebApp?: {
        initData?: string
        ready?: () => void
        expand?: () => void
        setHeaderColor?: (color: string) => void
        setBackgroundColor?: (color: string) => void
        safeAreaInset?: { top: number; right: number; bottom: number; left: number }
        contentSafeAreaInset?: { top: number; right: number; bottom: number; left: number }
        onEvent?: (event: string, handler: () => void) => void
      }
    }
    onTelegramAuth?: (user: any) => void
  }
}

export default function Login() {
  const nav = useNavigate()
  const { login, register, telegramLogin, isLoggedIn } = useGameStore()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [ref] = useState(() => new URLSearchParams(window.location.search).get('ref') || '')
  const [busy, setBusy] = useState(false)
  const miniAppLoginStarted = useRef(false)

  useEffect(() => {
    const initData = window.Telegram?.WebApp?.initData
    if (!initData || isLoggedIn || miniAppLoginStarted.current) return
    miniAppLoginStarted.current = true
    setBusy(true)
    telegramLogin({ init_data: initData })
      .then(() => nav('/', { replace: true }))
      .catch((err) => toast.error(errMsg(err)))
      .finally(() => setBusy(false))
  }, [isLoggedIn, nav, telegramLogin])

  if (isLoggedIn) nav('/', { replace: true })

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      if (mode === 'login') await login(username, password)
      else await register(username, password, ref)
      nav('/', { replace: true })
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setBusy(false)
    }
  }

  const tgAuth = () => {
    if (!window.Telegram?.Login) {
      toast.error('ویجت تلگرام بارگذاری نشده — از نام کاربری استفاده کنید')
      return
    }
    window.onTelegramAuth = async (user) => {
      try {
        // id و auth_date عددی هستند — سرور رشته می‌کند
        await telegramLogin(user as unknown as Record<string, string>)
        nav('/', { replace: true })
      } catch (err) {
        toast.error(errMsg(err))
      }
    }
    window.Telegram.Login.auth(window.onTelegramAuth, (import.meta.env.VITE_TELEGRAM_BOT as string) || '')
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="text-7xl mb-3 animate-float">🌍</div>
          <h1 className="text-4xl font-black bg-gradient-to-l from-primary-400 via-gold-400 to-danger-400 bg-clip-text text-transparent">
            جنگ جهانی
          </h1>
          <p className="text-slate-500 mt-2">۴۵۰ کشور. یک فرمانده. تاج و تخت یا خاکستر.</p>
        </div>

        <form onSubmit={submit} className="glass-card p-6 space-y-4">
          <h2 className="section-title">{mode === 'login' ? '🔐 ورود' : '🚀 ثبت‌نام'}</h2>
          <input
            className="input-dark"
            placeholder="نام کاربری (انگلیسی)"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            dir="ltr"
          />
          <input
            className="input-dark"
            type="password"
            placeholder="رمز عبور"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            dir="ltr"
          />
          {mode === 'register' && ref && (
            <p className="text-gold-400 text-sm">🎁 دعوت از: {ref} — پس از ثبت‌نام ۱۰,۰۰۰ سکه به دوستتان می‌رسد</p>
          )}
          <button disabled={busy} className="btn-primary w-full">
            {busy ? '...' : mode === 'login' ? 'ورود' : 'ساخت حساب'}
          </button>
          <button type="button" onClick={tgAuth} className="btn-ghost w-full">
            ورود با تلگرام
          </button>
          <p className="text-center text-sm text-slate-500">
            {mode === 'login' ? 'حساب ندارید؟' : 'حساب دارید؟'}{' '}
            <button type="button" className="text-primary-400 font-bold" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
              {mode === 'login' ? 'ثبت‌نام' : 'ورود'}
            </button>
          </p>
        </form>
      </div>
    </div>
  )
}
