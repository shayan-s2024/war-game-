import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, errMsg } from '../lib/api'
import { useGameStore } from '../store/gameStore'
import { fmt, timeAgo } from '../lib/utils'
import type { BattleLogItem, GlobalEventItem } from '../lib/types'

const CABINET_META: Record<string, { name: string; icon: string; options?: string[] }> = {
  diplomat: { name: 'وزیر خارجه', icon: '🤝' },
  leader: { name: 'رهبر', icon: '👑' },
  defense: { name: 'وزیر دفاع', icon: '🛡️' },
  economy: { name: 'وزیر اقتصاد', icon: '💰' },
  intelligence: { name: 'وزیر اطلاعات', icon: '🕵️' },
}
const CABINET_KEYS = Object.keys(CABINET_META)

export default function Dashboard() {
  const { dashboard, fetchDashboard } = useGameStore()
  const [events, setEvents] = useState<GlobalEventItem[]>([])
  const [logs, setLogs] = useState<BattleLogItem[]>([])
  const [cabinet, setCabinet] = useState<Record<string, string>>({})
  const [options, setOptions] = useState<Record<string, { name: string; icon: string; options: string[] }>>({})
  const [editing, setEditing] = useState<string | null>(null)
  const [manual, setManual] = useState('')
  const [codes, setCodes] = useState<Record<string, string>>({})
  const [showCodes, setShowCodes] = useState(false)
  const [busy, setBusy] = useState(false)

  const loadCabinet = () => api.get('/cabinet/').then(({ data }) => {
    setCabinet(data.cabinet || {})
    setOptions(data.options || {})
    setCodes(data.codes || {})
  })

  useEffect(() => {
    api.get('/events/').then(({ data }) => setEvents(data.events)).catch(() => {})
    api.get('/battles/').then(({ data }) => setLogs(data.logs)).catch(() => {})
    loadCabinet()
  }, [])

  useEffect(() => { if (dashboard?.cabinet) setCabinet((c) => ({ ...dashboard.cabinet, ...c })) }, [dashboard])

  if (!dashboard?.player) return null
  const p = dashboard.player

  const setPos = async (key: string, value: string) => {
    setBusy(true)
    try {
      const { data } = await api.post('/cabinet/set/', { key, value })
      setCabinet(data.cabinet)
      setEditing(null); setManual('')
      toast.success('مقام کابینه به‌روز شد')
      fetchDashboard()
    } catch (e) { toast.error(errMsg(e)) } finally { setBusy(false) }
  }

  const rotateCodes = async () => {
    setBusy(true)
    try {
      await api.post('/cabinet/change-codes/', {})
      await loadCabinet()
      setShowCodes(true)
      toast.success('🔐 کدهای امنیتی جدید صادر شد')
    } catch (e) { toast.error(errMsg(e)) } finally { setBusy(false) }
  }

  const nextStepGuide = dashboard.next_step === 'country'
    ? { text: 'کشور خود را انتخاب کنید', to: '/onboarding' }
    : dashboard.next_step === 'cabinet'
      ? { text: 'کابینه خود را تکمیل کنید', to: '/onboarding' }
      : null

  return (
    <div className="space-y-4">
      {nextStepGuide && (
        <Link to={nextStepGuide.to} className="block glass-card p-4 border-gold-500/40 bg-gold-500/5 hover:bg-gold-500/10 transition animate-glow">
          <span className="font-bold text-gold-400">🎯 قدم بعدی: {nextStepGuide.text}</span>
        </Link>
      )}

      {/* وضعیت جنگ */}
      <div className={`glass-card p-4 flex items-center justify-between ${dashboard.war_active ? '!border-danger-500/40' : ''}`}>
        <div>
          <div className="section-title">
            {dashboard.war_active ? '⚔️ جنگ جهانی فعال است!' : '🕊️ وضعیت صلح'}
          </div>
          <p className="text-slate-400 text-sm mt-1">
            {dashboard.war_active ? 'سهمیه حملات فعال است — اهداف را در منوی حمله ببینید.' : 'تا شروع جنگ، اقتصاد و دفاع بسازید.'}
          </p>
        </div>
        <Link to="/attack" className={dashboard.war_active ? 'btn-danger' : 'btn-ghost'}>
          {dashboard.war_active ? 'حمله' : 'آماده‌سازی'}
        </Link>
      </div>

      {/* هشدارها */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {p.on_fire && (
          <div className="glass-card p-4 !border-danger-500/40 bg-danger-500/5">
            <div className="font-bold text-danger-400">🔥 شهر شما در آتش می‌سوزد!</div>
            <p className="text-slate-400 text-sm mt-1">متروها تلفات را کم می‌کنند.</p>
          </div>
        )}
        {Object.entries(p.viruses).map(([k, v]) => (
          <div key={k} className="glass-card p-4 !border-danger-500/40 bg-danger-500/5">
            <div className="font-bold text-danger-400">🦠 ویروس فعال ({v.remaining_days} روز مانده)</div>
            <p className="text-slate-400 text-sm mt-1">تلفات روزانه: {fmt(v.daily_loss)} نفر</p>
          </div>
        ))}
        {dashboard.sanctioned && (
          <div className="glass-card p-4 !border-gold-500/40 bg-gold-500/5">
            <div className="font-bold text-gold-400">🌐 کشور شما تحریم شده!</div>
            <p className="text-slate-400 text-sm mt-1">خریدها با جریمه محاسبه می‌شود.</p>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <StatCard icon="💰" label="خزانه" value={fmt(p.credit)} sub={`📈 ${fmt(p.daily_profit)}/روز`} to="/shop" />
        <StatCard icon="🛡️" label="استقامت" value={fmt(p.defense)} sub="پدافند بسازید" to="/shop" />
        <StatCard icon="💥" label="قدرت تخریب" value={fmt(p.attack_power)} sub="ارتش را تقویت کنید" to="/shop" />
        <StatCard icon="👥" label="جمعیت" value={fmt(p.population)} />
        <StatCard icon="🏆" label="امتیاز" value={fmt(p.score)} to={`/players/${p.name}`} />
        <StatCard icon="⚔️" label="حملات مانده" value={`${dashboard.attacks_remaining}/${dashboard.attack_limit}`} to="/attack" />
      </div>

      {/* 👥 کابینه — قابل‌ویرایش درجا */}
      <div className="glass-card p-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="section-title">👥 کابینه — قابل‌ویرایش</div>
          <div className="flex gap-2">
            <button className="btn-ghost !py-1.5 text-xs" onClick={() => setShowCodes(!showCodes)}>
              🔐 {showCodes ? 'پنهان' : 'کدهای امنیتی'}
            </button>
            <button className="btn-ghost !py-1.5 text-xs" disabled={busy} onClick={rotateCodes}>
              🔄 تغییر همه کدها
            </button>
          </div>
        </div>

        {showCodes && (
          <div className="bg-danger-500/10 border border-danger-500/30 rounded-xl p-3 mt-3 space-y-1">
            <p className="text-danger-400 text-xs font-bold">⚠️ این کدها را فقط نزد خود نگه دارید — سرقت = ترور!</p>
            {CABINET_KEYS.map((key) => (
              <div key={key} className="flex justify-between text-sm bg-white/5 rounded-lg px-3 py-1.5">
                <span>{CABINET_META[key].icon} {CABINET_META[key].name}</span>
                <code className="text-gold-400 font-mono tracking-widest" dir="ltr">{codes[key] || '—'}</code>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3">
          {CABINET_KEYS.map((key) => (
            <div key={key} className="bg-white/5 rounded-xl p-3 text-center">
              <div className="text-2xl">{CABINET_META[key].icon}</div>
              <div className="text-xs text-slate-400 mt-1">{CABINET_META[key].name}</div>
              <div className={`text-sm font-bold truncate ${cabinet[key] ? 'text-slate-200' : 'text-slate-600'}`}>
                {cabinet[key] || '—'}
              </div>
              <button className="text-[11px] text-primary-400 mt-1" onClick={() => { setEditing(editing === key ? null : key); setManual('') }}>
                {cabinet[key] ? 'تغییر' : 'انتخاب'}
              </button>
              {editing === key && (
                <div className="mt-2 space-y-1.5">
                  {options[key]?.options?.slice(0, 4).map((o) => (
                    <button key={o} disabled={busy} onClick={() => setPos(key, o)}
                      className="block w-full text-[11px] bg-white/5 hover:bg-white/10 rounded px-1.5 py-1 truncate">{o}</button>
                  ))}
                  <div className="flex gap-1">
                    <input value={manual} onChange={(e) => setManual(e.target.value)} maxLength={64}
                      placeholder="دستی..." className="w-full bg-night-900 border border-white/10 rounded px-1.5 py-1 text-[11px]" />
                    <button disabled={busy || !manual.trim()} onClick={() => setPos(key, manual.trim())}
                      className="bg-primary-500 text-white rounded px-2 text-[11px]">✓</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <QuickAction to="/shop" icon="🛒" label="فروشگاه" />
        <QuickAction to="/spy" icon="🕵️" label="جاسوسی" />
        <QuickAction to="/unions" icon="🤝" label="اتحاد" />
        <QuickAction to="/map" icon="🌍" label="نقشه جهانی" />
      </div>

      {/* Events + logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <div className="section-title mb-3">📡 اخبار جهانی</div>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {events.length === 0 && <p className="text-slate-500 text-sm">هنوز رویدادی رخ نداده.</p>}
            {events.map((e) => (
              <div key={e.id} className="bg-white/5 rounded-lg px-3 py-2 text-sm">
                {e.summary}
                <span className="block text-xs text-slate-500 mt-1">{timeAgo(e.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="glass-card p-4">
          <div className="section-title mb-3">📜 نبردهای من</div>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {logs.length === 0 && <p className="text-slate-500 text-sm">هنوز نبرده‌ای ثبت نشده.</p>}
            {logs.map((l) => (
              <div key={l.id} className="bg-white/5 rounded-lg px-3 py-2 text-sm">{l.text}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, sub, to }: {
  icon: string; label: string; value: string; sub?: string; to?: string
}) {
  const inner = (
    <div className="glass-card p-4 h-full hover:border-primary-500/30 transition-all active:scale-[0.98]">
      <div className="flex items-center gap-2 text-slate-400 text-sm">
        <span className="text-xl">{icon}</span> {label}
      </div>
      <div className="text-2xl font-black mt-1 tabular-nums">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
    </div>
  )
  return to ? <Link to={to}>{inner}</Link> : inner
}

function QuickAction({ to, icon, label }: { to: string; icon: string; label: string }) {
  return (
    <Link to={to} className="glass-card p-4 flex items-center gap-3 hover:border-primary-500/30 active:scale-[0.98] transition-all">
      <span className="text-2xl">{icon}</span>
      <span className="font-bold">{label}</span>
    </Link>
  )
}
