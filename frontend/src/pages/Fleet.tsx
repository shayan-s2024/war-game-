import { useCallback, useEffect, useState } from 'react'
import { api, errMsg } from '../lib/api'
import { fmt } from '../lib/utils'

interface Mission {
  id: number; player: string; username: string
  status: 'outbound' | 'returning'; progress: number
  origin: { name: string | null }; target: { name: string | null }
  ships: Record<string, number>; loot: number; summary: string
  arrive_at: string | null; return_at: string | null
}
interface Ship { qty: number; name: string; icon: string; q: number | null }

/** ⏳ زمان باقیمانده تا ISO — زنده (هر ثانیه re-render) */
function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(t)
  }, [intervalMs])
  return now
}

function Countdown({ iso }: { iso: string | null }) {
  const now = useNow()
  if (!iso) return <span>—</span>
  const diff = new Date(iso).getTime() - now
  if (diff <= 0) return <span className="text-success-400">رسید!</span>
  const m = Math.floor(diff / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  return <span className="font-mono">{m}:{String(s).padStart(2, '0')}</span>
}

export default function Fleet() {
  const [data, setData] = useState<{
    missions: Mission[]; history: { id: number; summary: string; loot: number; created_at: string }[]
    ships: Record<string, Ship>; docks: number; has_dock: boolean
  } | null>(null)
  const [targets, setTargets] = useState<{ id: number; label: string }[]>([])
  const [picked, setPicked] = useState<Record<string, number>>({})
  const [targetId, setTargetId] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    api.get('/fleet/').then(({ data }) => setData(data)).catch(() => setMsg('❌ بارگذاری ناموفق'))
    api.get('/leaderboard/').then(({ data }) => {
      const rows = Array.isArray(data) ? data : (data.players || data.results || [])
      setTargets(rows.filter((p: any) => p.id && p.username).map((p: any) => ({
        id: p.id, label: `${p.player_name || p.username}`,
      })))
    }).catch(() => {})
  }, [])
  useEffect(load, [])

  const totalPicked = Object.values(picked).reduce((a, b) => a + b, 0)

  const launch = async () => {
    if (!targetId || totalPicked === 0) {
      setMsg('❌ هدف و حداقل یک شناور انتخاب کنید')
      return
    }
    setBusy(true)
    try {
      const { data } = await api.post('/fleet/', { action: 'launch', target_id: Number(targetId), ships: picked })
      setMsg(`✅ ناوگان اعزام شد — رسیدن تا ${Math.round((data.sail_seconds || 0) / 60)} دقیقه`)
      setPicked({})
      load()
    } catch (e) {
      setMsg('❌ ' + errMsg(e))
    } finally {
      setBusy(false)
      setTimeout(() => setMsg(''), 4000)
    }
  }

  const ships = Object.entries(data?.ships || {})
  const war = data?.has_dock

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="section-title">⚓ ناوگان دریایی</div>
          <p className="text-xs text-slate-500 mt-1">
            {war ? `🏗 اسکله: ${fmt(data?.docks || 0)} — اعزام از بندر کشور شما` : '⛔ برای اعزام ناوگان به اسکله (dock) نیاز دارید — از فروشگاه بخرید'}
          </p>
        </div>
        {msg && <div className="text-xs font-bold text-gold-300 bg-gold-500/10 rounded-lg px-3 py-1.5">{msg}</div>}
      </div>

      {/* مأموریت‌های فعال */}
      <div className="glass-card p-4">
        <div className="section-title mb-3">🚢 مأموریت‌های فعال ({fmt(data?.missions.length || 0)}/۲)</div>
        {(data?.missions.length || 0) === 0 && <p className="text-sm text-slate-500">ناوگانی در دریا نیست.</p>}
        <div className="space-y-2">
          {data?.missions.map((m) => (
            <div key={m.id} className="bg-white/5 rounded-xl px-3 py-2.5 space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="font-bold">
                  {m.status === 'returning' ? '🏠 بازگشت' : '⚓ در مسیر'}: {m.origin.name || '؟'} → {m.target.name || '؟'}
                </span>
                <span className="text-xs text-slate-400">
                  {m.status === 'outbound'
                    ? <>رسیدن: <Countdown iso={m.arrive_at} /></>
                    : <>برگشت: <Countdown iso={m.return_at} /></>}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div className={`h-full rounded-full transition-all ${m.status === 'returning' ? 'bg-cyan-500' : 'bg-gold-500'}`}
                  style={{ width: `${Math.round(m.progress * 100)}%` }} />
              </div>
              <div className="text-xs text-slate-500">
                🚢 {Object.entries(m.ships).map(([k, v]) => `${fmt(v)}×${k}`).join('، ')}
                {m.summary && <span className="block text-gold-300 mt-0.5">{m.summary}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* اعزام ناوگان */}
      <div className="glass-card p-4 space-y-3">
        <div className="section-title">🎯 اعزام ناوگان جدید</div>
        {!war ? (
          <p className="text-sm text-slate-500">اول از <a href="/shop" className="text-primary-400 underline">فروشگاه</a> اسکله بخرید و ناو بسازید.</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-1.5">
              {ships.length === 0 && <p className="text-sm text-slate-500">شناوری در بندر ندارید — ناو جنگی/زیردریایی بخرید.</p>}
              {ships.map(([key, s]) => (
                <div key={key} className="flex items-center gap-1.5 bg-white/5 rounded-lg px-2.5 py-1.5 text-xs">
                  <span>{s.icon}</span>
                  <span>{s.name}</span>
                  <span className="text-slate-500">({fmt(s.qty)})</span>
                  <input type="number" min={0} max={s.qty} value={picked[key] || ''}
                    onChange={(e) => {
                      const v = Math.min(s.qty, Math.max(0, Number(e.target.value) || 0))
                      setPicked((prev) => ({ ...prev, [key]: v }))
                    }}
                    className="w-14 bg-night-900 border border-white/15 rounded px-1.5 py-0.5 text-xs text-center" />
                </div>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select value={targetId} onChange={(e) => setTargetId(e.target.value)}
                className="bg-night-900 border border-white/15 rounded-lg px-3 py-2 text-xs text-slate-200">
                <option value="">— هدف را انتخاب کنید —</option>
                {targets.map((t) => <option key={t.id} value={t.id}>👤 {t.label}</option>)}
              </select>
              <span className="text-xs text-slate-500">مجموع: {fmt(totalPicked)} شناور</span>
              <button onClick={launch} disabled={busy || totalPicked === 0 || !targetId}
                className="btn-primary !py-2 text-xs disabled:opacity-40">
                {busy ? '…' : '⚓ اعزام'}
              </button>
            </div>
          </>
        )}
      </div>

      {/* تاریخچه */}
      <div className="glass-card p-4">
        <div className="section-title mb-3">📜 تاریخچه مأموریت‌ها</div>
        {(data?.history.length || 0) === 0 && <p className="text-sm text-slate-500">هنوز مأموریتی کامل نشده.</p>}
        <div className="space-y-1">
          {data?.history.map((h) => (
            <div key={h.id} className="bg-white/5 rounded-lg px-3 py-2 text-sm">
              {h.summary}
              {h.loot > 0 && <span className="block text-xs text-success-400 mt-0.5">💰 غنیمت: {fmt(h.loot)} سکه</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
