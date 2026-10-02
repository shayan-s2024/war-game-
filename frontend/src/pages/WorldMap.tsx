import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import GlobeMap from '../components/GlobeMap'
import type { WorldState } from '../components/GlobeMap'
import { api } from '../lib/api'
import { useWorldSocket, type WorldEvent } from '../lib/useGameSocket'
import { fmt, timeAgo } from '../lib/utils'

const CONT_FA: Record<string, string> = {
  asia: 'آسیا', europe: 'اروپا', africa: 'آفریقا', north_america: 'آمریکای شمالی',
  south_america: 'آمریکای جنوبی', oceania: 'اقیانوسیه',
}
const EVENT_ICON: Record<string, string> = {
  battle_end: '⚔️', alliance_created: '🤝', base_built: '🏕️',
  large_transaction: '💰', achievement: '🏆', admin_action: '🛠',
  register: '🆕', suspicious: '🚩',
  fleet_launched: '⚓', fleet_returned: '🛳',
}

export default function WorldMap() {
  const [world, setWorld] = useState<WorldState | null>(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [events, setEvents] = useState<WorldEvent[]>([])
  const [params] = useSearchParams()
  const focusName = params.get('focus')
  const [live, setLive] = useState(false)

  const load = useCallback(() => api.get('/world/').then(({ data }) => { setWorld(data); setError('') })
    .catch(() => setError('بارگذاری جهان ناموفق بود — دوباره تلاش کنید')), [])

  const onEvent = useCallback((e: WorldEvent) => {
    setEvents((prev) => {
      if (prev.some((x) => x.id === e.id)) return prev
      return [{ ...e }, ...prev].slice(0, 12)
    })
    // نبردهای جدید بدون refresh — اگر مختصات دارد، مستقیم روی Globe اضافه کن
    if (e.lat != null && e.lon != null) {
      setWorld((prev) => {
        if (!prev || prev.battles.some((b) => b.id === e.id)) return prev
        const battle = {
          id: e.id as number, summary: e.text, attacker: '', defender: '',
          country: null, emoji: '⚔️', lat: e.lat as number, lon: e.lon as number,
          continent: null, created_at: e.created_at,
        }
        return { ...prev, battles: [battle, ...prev.battles].slice(0, 20) }
      })
    }
    if (e.kind === 'fleet_launched' || e.kind === 'fleet_returned') load() // موقعیت ناوگان‌ها زنده شود
    if (e.kind === 'battle_end') setTimeout(load, 1200) // آمار/نبردها از Game Core
  }, [load])

  const wsConnected = useWorldSocket(onEvent)
  useEffect(() => { setLive(wsConnected) }, [wsConnected])

  useEffect(() => {
    load()
    api.get('/admin/feed/').then(({ data }) => setEvents(data.feed.slice(0, 12))).catch(() => {})
    const t = setInterval(load, live ? 120000 : 45000) // با WS زنده، polling فقط پشتیبان است
    return () => clearInterval(t)
  }, [load, live])

  const countries = world?.countries || []
  const visible = useMemo(
    () => filter === 'all' ? countries : countries.filter((c) => c.continent === filter),
    [countries, filter])

  if (error) {
    return (
      <div className="glass-card p-8 text-center space-y-3">
        <p className="text-danger-400 font-bold">⚠️ {error}</p>
        <button className="btn-primary" onClick={load}>🔄 تلاش مجدد</button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Globe — تمام عرض */}
      <div className="glass-card overflow-hidden relative" style={{ height: 560 }}>
        {world ? (
          <GlobeMap world={world} focusName={focusName} />
        ) : (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-500">
            <div className="text-5xl animate-float">🌍</div>
            <p className="text-sm">Initializing World…</p>
            <div className="w-48 h-2 rounded-full skeleton" />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 📡 Event Feed زنده */}
        <div className="glass-card p-4 lg:col-span-1">
          <div className="flex items-center justify-between mb-3">
            <div className="section-title">📡 رویدادهای زنده جهان</div>
            <span className={`stat-chip !py-0.5 !px-2 text-[10px] ${live ? '!border-success-500/50 text-success-300' : 'text-slate-500'}`}>
              {live ? '● زنده' : '○ polling'}
            </span>
          </div>
          <div className="space-y-1.5 max-h-80 overflow-y-auto">
            {events.length === 0 && <p className="text-slate-500 text-sm text-center py-4">هنوز رویدادی ثبت نشده.</p>}
            {events.map((e) => (
              <div key={e.id} className="flex items-start gap-2 bg-white/5 rounded-lg px-3 py-2 text-sm">
                <span>{EVENT_ICON[e.kind] || '📌'}</span>
                <span className="flex-1 leading-5">{e.text}</span>
                <span className="text-[10px] text-slate-600 shrink-0">{timeAgo(e.created_at)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* فهرست کشورها */}
        <div className="glass-card p-4 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div className="section-title">🗺 سرزمین‌ها ({fmt(visible.length)})</div>
            <div className="flex gap-1.5 flex-wrap">
              <button onClick={() => setFilter('all')}
                className={`stat-chip !py-1 text-xs ${filter === 'all' ? '!border-primary-500/50 text-primary-300' : ''}`}>همه</button>
              {world?.continents.map((c) => (
                <button key={c.key} onClick={() => setFilter(c.key)}
                  className={`stat-chip !py-1 text-xs ${filter === c.key ? '!border-primary-500/50 text-primary-300' : ''}`}>
                  {c.flag} {CONT_FA[c.key] || c.name}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-1.5 max-h-80 overflow-y-auto">
            {visible.map((c) => (
              <button key={c.name}
                onClick={() => {
                  const el = document.querySelector<HTMLElement>(`[data-globe-country="${c.name}"]`)
                  // focus از طریق URL param — GlobeMap واکنش نشان می‌دهد
                  window.history.replaceState(null, '', `/map?focus=${encodeURIComponent(c.name)}`)
                  window.dispatchEvent(new PopStateEvent('popstate'))
                }}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition ${c.taken ? 'bg-danger-500/10 text-slate-300' : 'bg-success-500/10'} hover:bg-white/10`}>
                <span className="truncate">{c.emoji} {c.name}</span>
                <span className="text-[10px] text-slate-500 truncate max-w-16">{c.owner?.name || (c.taken ? '' : 'آزاد')}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* پایگاه‌ها و نبردها */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <div className="section-title mb-3">🏕 پایگاه‌های جهان ({fmt(world?.bases.length || 0)})</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-60 overflow-y-auto">
            {world?.bases.length === 0 && <p className="text-slate-500 text-sm">پایگاهی ساخته نشده.</p>}
            {world?.bases.map((b) => (
              <div key={b.id} className="bg-white/5 rounded-xl px-3 py-2 text-sm flex items-center justify-between">
                <span>{b.emoji} {b.country} {!b.ready && <span className="text-[10px] text-gold-400">(ساخت)</span>}</span>
                <span className="text-xs text-slate-500">👤 {b.owner}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="glass-card p-4">
          <div className="section-title mb-3">⚔️ آخرین نبردها</div>
          <div className="space-y-1.5 max-h-60 overflow-y-auto">
            {world?.battles.length === 0 && <p className="text-slate-500 text-sm">نبردی رخ نداده.</p>}
            {world?.battles.map((b) => (
              <div key={b.id} className="bg-white/5 rounded-lg px-3 py-2 text-sm">
                {b.summary}
                <span className="block text-xs text-slate-500 mt-0.5">{timeAgo(b.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
