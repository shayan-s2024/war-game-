import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, errMsg } from '../lib/api'
import { fmt, timeAgo } from '../lib/utils'

interface KPI {
  label: string; value: number; prev: number | null
  change_pct: number | null; trend: string; icon: string
}
interface Overview {
  period_days: number; updated_at: string; online_now: number
  kpis: KPI[]; feed: FeedItem[]; ws_connections: number
}
interface FeedItem {
  id: number; kind: string; actor: string; text: string
  target_id: number | null; target_kind: string; created_at: string
}
interface PlayerRow {
  id: number; name: string; country: string | null; country_emoji: string | null
  credit: number; score: number; defense: number; attack_power: number
  daily_profit: number; population: number; union: string | null
  banned: boolean; ban_reason: string; username: string; online: boolean
}
interface CountryRow {
  id: number; name: string; command_name: string; emoji: string; continent: string
  imaginary: boolean; lat: number | null; lon: number | null
  owner_id: number | null; owner: string | null; owner_username: string | null
}

const RANGE_OPTIONS = [
  { key: '1', label: 'امروز' }, { key: '7', label: '۷ روز' },
  { key: '30', label: '۳۰ روز' }, { key: '90', label: '۹۰ روز' },
]
const CHART_COLORS = ['#38bdf8', '#fbbf24', '#ef4444', '#22c55e', '#a78bfa', '#f472b6', '#34d399', '#f97316']
const FEED_ICON: Record<string, string> = {
  register: '🆕', login: '🔑', battle_end: '⚔️', alliance_created: '🤝',
  large_transaction: '💰', suspicious: '🚩', admin_action: '🛠',
  achievement: '🏆', base_built: '🏕️', system_warning: '⚠️',
}
const REASON_LABEL: Record<string, string> = {
  purchase: 'خرید فروشگاه', daily_profit: 'سود روزانه', battle_loot: 'غنیمت نبرد',
  bomb_loot: 'غنیمت بمب', start_bonus: 'سرمایه اولیه', base_build: 'ساخت پایگاه',
  union_deposit: 'واریز خزانه', union_withdraw: 'برداشت خزانه', donation_sent: 'اهدای سکه',
  donation_received: 'دریافت اهدا', admin_grant: 'اهدا ادمین', toman_purchase: 'خرید تومانی',
  achievement_reward: 'جایزه دستاورد', referral_bonus: 'جایزه دعوت', artillery_win: 'غنیمت توپخانه',
}

type Tab = 'overview' | 'battles' | 'economy' | 'players' | 'countries' | 'audit'

export default function AdminPage() {
  const [denied, setDenied] = useState(false)
  const [tab, setTab] = useState<Tab>('overview')
  const [range, setRange] = useState('7')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [charts, setCharts] = useState<any>(null)
  const [economy, setEconomy] = useState<any>(null)
  const [players, setPlayers] = useState<PlayerRow[]>([])
  const [q, setQ] = useState('')
  const [bannedOnly, setBannedOnly] = useState(false)
  const [selected, setSelected] = useState<PlayerRow | null>(null)
  const [audit, setAudit] = useState<any[]>([])
  const [countries, setCountries] = useState<CountryRow[]>([])
  const [countryQ, setCountryQ] = useState('')
  const [selectedCountry, setSelectedCountry] = useState<CountryRow | null>(null)
  const [countryAlias, setCountryAlias] = useState('')
  const [countryLat, setCountryLat] = useState('')
  const [countryLon, setCountryLon] = useState('')
  const [countryPlayer, setCountryPlayer] = useState('')
  const [tick, setTick] = useState(0)

  const loadOverview = useCallback(() => {
    api.get('/admin/analytics/', { params: { days: range } }).then(({ data }) => setOverview(data)).catch(() => setDenied(true))
  }, [range])
  const loadCharts = useCallback(() => {
    api.get('/admin/charts/', { params: { days: range } }).then(({ data }) => setCharts(data)).catch(() => {})
  }, [range])

  useEffect(() => { loadOverview(); loadCharts() }, [loadOverview, loadCharts])
  // Live: هر ۳۰ ثانیه KPI و feed — در production با WS /ws/admin/ جایگزین نصفه می‌شود
  useEffect(() => {
    const t = setInterval(() => { loadOverview() }, 30000)
    return () => clearInterval(t)
  }, [loadOverview])
  useEffect(() => {
    if (tab === 'economy') api.get('/admin/economy/', { params: { days: range } }).then(({ data }) => setEconomy(data)).catch(() => {})
    if (tab === 'players') loadPlayers()
    if (tab === 'countries') loadCountries()
    if (tab === 'audit') api.get('/admin/audit-log/').then(({ data }) => setAudit(data.logs)).catch(() => {})
  }, [tab, range, tick])

  const loadCountries = (query = countryQ) => {
    api.get('/admin/countries/', { params: { q: query } })
      .then(({ data }) => setCountries(data.countries || []))
      .catch(() => setDenied(true))
  }

  const manageCountry = async (body: any, msg: string) => {
    try {
      await api.post('/admin/country-manage/', body)
      toast.success(msg)
      setSelectedCountry(null)
      setTick((t) => t + 1)
      loadCountries()
    } catch (e) { toast.error(errMsg(e)) }
  }

  const loadPlayers = (query = q, banned = bannedOnly) => {
    api.get('/admin/players-v2/', { params: { q: query, banned: banned ? '1' : '' } })
      .then(({ data }) => setPlayers(data.players)).catch(() => setDenied(true))
  }

  const manage = async (body: any, msg: string) => {
    try {
      await api.post('/admin/player-manage/', body)
      toast.success(msg)
      setTick((t) => t + 1)
      loadPlayers()
    } catch (e) { toast.error(errMsg(e)) }
  }

  const exportCsv = () => {
    api.get('/admin/export/players.csv', { responseType: 'blob' }).then((res) => {
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url; a.download = 'players_export.csv'; a.click()
      URL.revokeObjectURL(url)
    }).catch(() => toast.error('خطا در export'))
  }

  if (denied) return <div className="glass-card p-8 text-center">⛔ این بخش فقط برای ادمین‌ها است.</div>
  if (!overview) return <div className="flex justify-center py-16"><div className="w-48 h-2 rounded-full skeleton" /></div>

  const chartTooltip = {
    contentStyle: { background: '#0f172a', border: '1px solid rgba(255,255,255,.1)', borderRadius: 12 },
    labelStyle: { color: '#e2e8f0' },
  }

  return (
    <div className="space-y-4 admin-console">
      {/* Header + Global Range Filter */}
      <div className="glass-card p-5 flex flex-wrap items-center justify-between gap-2 depth-card admin-hero">
        <div>
          <h1 className="section-title text-xl">👑 داشبورد عملیات بازی</h1>
          <p className="text-xs text-slate-500 mt-0.5">آخرین بروزرسانی: {new Date(overview.updated_at).toLocaleTimeString('fa-IR')} · اتصال WS: {overview.ws_connections}</p>
        </div>
        <div className="flex gap-1.5">
          {RANGE_OPTIONS.map((r) => (
            <button key={r.key} onClick={() => setRange(r.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                range === r.key ? 'bg-primary-500 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'
              }`}>{r.label}</button>
          ))}
          <button onClick={exportCsv} className="btn-ghost !py-1.5 text-xs">⬇ CSV</button>
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs flex gap-2 overflow-x-auto">
        {([['overview', '📊 مرور'], ['battles', '⚔️ نبردها'], ['economy', '💰 اقتصاد'],
           ['players', '👥 بازیکنان'], ['countries', '🌍 کشورها'], ['audit', '📜 audit']] as const).map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition ${
              tab === k ? 'bg-primary-500/20 text-primary-300 border border-primary-500/40' : 'bg-white/5 text-slate-400'
            }`}>{label}</button>
        ))}
      </div>

      {/* ============ OVERVIEW ============ */}
      {tab === 'overview' && (
        <div className="space-y-4">
          {/* KPI Grid — مقدار + trend + درصد تغییر */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
            {overview.kpis.map((k) => (
              <div key={k.label} className="glass-card p-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 text-xs">{k.icon} {k.label}</span>
                  {k.trend !== 'flat' && (
                    <span className={`text-[10px] font-bold ${k.trend === 'up' ? 'text-success-400' : 'text-danger-400'}`}>
                      {k.trend === 'up' ? '▲' : '▼'} {k.change_pct != null ? `${Math.abs(k.change_pct)}٪` : ''}
                    </span>
                  )}
                </div>
                <div className="text-xl font-black mt-1 tabular-nums">{fmt(k.value)}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* ثبت‌نام */}
            <ChartCard title="🆕 روند ثبت‌نام">
              <ResponsiveContainer>
                <AreaChart data={charts?.registration_trend || []}>
                  <defs>
                    <linearGradient id="regGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(5)} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} allowDecimals={false} />
                  <Tooltip {...chartTooltip} />
                  <Area type="monotone" dataKey="count" name="ثبت‌نام" stroke="#38bdf8" fill="url(#regGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* گردش مالی */}
            <ChartCard title="💰 گردش مالی روزانه (ورودی/خروجی)">
              <ResponsiveContainer>
                <AreaChart data={charts?.tx_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(5)} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(v) => `${Math.round(v / 1000)}K`} />
                  <Tooltip {...chartTooltip} formatter={(v: any) => fmt(Number(v))} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area type="monotone" dataKey="in" name="ورودی" stroke="#22c55e" fill="#22c55e" fillOpacity={0.15} strokeWidth={2} />
                  <Area type="monotone" dataKey="out" name="خروجی" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          {/* Activity Feed */}
          <div className="glass-card p-4">
            <div className="section-title mb-3">📡 Activity Feed زنده</div>
            <div className="space-y-1.5 max-h-96 overflow-y-auto">
              {overview.feed.length === 0 && <p className="text-slate-500 text-sm">رویدادی ثبت نشده.</p>}
              {overview.feed.map((f) => (
                <FeedRow key={f.id} f={f} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ============ BATTLES ============ */}
      {tab === 'battles' && charts && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard title="⚔️ روند نبردها">
              <ResponsiveContainer>
                <BarChart data={charts.battle_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(d) => d.slice(5)} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} allowDecimals={false} />
                  <Tooltip {...chartTooltip} />
                  <Bar dataKey="battles" name="نبرد" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="🕐 فعالیت نبرد بر اساس ساعت">
              <ResponsiveContainer>
                <AreaChart data={charts.battle_by_hour}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="hour" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(h) => `${h}:00`} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} allowDecimals={false} />
                  <Tooltip {...chartTooltip} />
                  <Area type="monotone" dataKey="battles" name="نبرد" stroke="#fbbf24" fill="#fbbf24" fillOpacity={0.2} strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard title="🏆 توزیع نتیجه نبردها">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={[
                    { name: 'پیروزی قاطع', value: charts.battle_outcomes.victory },
                    { name: 'پیروزی سخت', value: charts.battle_outcomes.narrow_victory },
                    { name: 'شکست نزدیک', value: charts.battle_outcomes.narrow_defeat },
                    { name: 'شکست سنگین', value: charts.battle_outcomes.defeat },
                  ].filter((d) => d.value > 0)} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={3}>
                    {['#22c55e', '#38bdf8', '#f97316', '#ef4444'].map((c, i) => <Cell key={i} fill={c} />)}
                  </Pie>
                  <Tooltip {...chartTooltip} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="🌍 برترین کشورها (نبرد)">
              <ResponsiveContainer>
                <BarChart data={charts.top_countries} layout="vertical">
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="country" width={90} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip {...chartTooltip} />
                  <Bar dataKey="battles" name="نبرد" radius={[0, 8, 8, 0]}>
                    {charts.top_countries.map((_: any, i: number) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </div>
      )}

      {/* ============ ECONOMY ============ */}
      {tab === 'economy' && economy && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <BigStat icon="🏦" label="عرضه کل سکه" value={fmt(economy.supply)} />
            <BigStat icon="📈" label="تولید دوره" value={fmt(economy.generated)} />
            <BigStat icon="📉" label="مصرف دوره" value={fmt(economy.spent)} />
          </div>
          <ChartCard title="💰 جریان سکه بر اساس دلیل">
            <ResponsiveContainer>
              <BarChart data={economy.by_reason.map((r: any) => ({ ...r, label: REASON_LABEL[r.reason] || r.reason }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 9 }} interval={0} angle={-25} textAnchor="end" height={60} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(v) => `${Math.round(v / 1000)}K`} />
                <Tooltip {...chartTooltip} formatter={(v: any) => fmt(Number(v))} />
                <Bar dataKey="total" radius={[6, 6, 0, 0]}>
                  {economy.by_reason.map((_: any, i: number) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}

      {/* ============ PLAYERS (Drill-down) ============ */}
      {tab === 'players' && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <input className="input-dark flex-1 min-w-48" placeholder="جستجوی نام/کشور..." value={q}
              onChange={(e) => { setQ(e.target.value); loadPlayers(e.target.value, bannedOnly) }} />
            <button className={`btn-ghost !py-2 text-xs ${bannedOnly ? '!border-danger-500/50 text-danger-400' : ''}`}
              onClick={() => { const b = !bannedOnly; setBannedOnly(b); loadPlayers(q, b) }}>
              ⛔ فقط بن‌شده‌ها
            </button>
          </div>
          <div className="glass-card divide-y divide-white/5 max-h-[480px] overflow-y-auto">
            {players.map((p) => (
              <div key={p.id} className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-white/5">
                <span className={`w-2 h-2 rounded-full shrink-0 ${p.online ? 'bg-success-500' : 'bg-slate-600'}`} />
                <Link to={`/players/${p.username}`} className="font-bold hover:text-primary-300 min-w-24">{p.name}</Link>
                <span className="text-xs text-slate-500 hidden sm:inline">{p.country_emoji} {p.country}</span>
                <span className="text-xs tabular-nums text-gold-400 mr-auto">💰 {fmt(p.credit)}</span>
                <span className="text-xs tabular-nums hidden sm:inline">🏆 {fmt(p.score)}</span>
                {p.banned && <span className="text-[10px] text-danger-400">⛔ {p.ban_reason}</span>}
                <button className="btn-ghost !px-2 !py-0.5 text-[10px]" onClick={() => setSelected(selected?.id === p.id ? null : p)}>⚙️</button>
              </div>
            ))}
          </div>
          {selected && (
            <div className="glass-card p-4 space-y-3">
              <div className="font-bold">⚙️ مدیریت {selected.name} — <Link className="text-primary-400 text-sm" to={`/players/${selected.username}`}>پروفایل ↗</Link></div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <button className="btn-ghost text-xs" onClick={() => manage({ action: 'unban', player_id: selected.id }, 'رفع بن شد')} disabled={!selected.banned}>✅ رفع بن</button>
                <button className="btn-danger text-xs" onClick={() => {
                  const reason = prompt('دلیل بن؟')
                  if (reason) manage({ action: 'ban', player_id: selected.id, reason }, 'بن شد')
                }} disabled={selected.banned}>⛔ بن</button>
                <button className="btn-ghost text-xs" onClick={() => api.get(`/players/${selected.username}/`).then(() => toast.success('پروفایل عمومی سالم'))}>🔍 تست پروفایل</button>
              </div>
              <div className="text-xs text-slate-500">اطلاعات کامل: 💰 {fmt(selected.credit)} | 🛡 {fmt(selected.defense)} | 💥 {fmt(selected.attack_power)} | 👥 {fmt(selected.population)} | 📈 {fmt(selected.daily_profit)}</div>
            </div>
          )}
        </div>
      )}

      {/* ============ COUNTRIES ============ */}
      {tab === 'countries' && (
        <div className="space-y-3">
          <div className="glass-card p-4 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <div>
                <div className="section-title mb-0">🌍 فهرست کشورها</div>
                <div className="text-[11px] text-slate-500">نام کشور + نام فرمان + مالکیت + مختصات واقعی/جزیره‌های خیالی</div>
              </div>
              <input className="input-dark flex-1 min-w-52" placeholder="جستجو: ایران / iran / boss..." value={countryQ}
                onChange={(e) => { setCountryQ(e.target.value); loadCountries(e.target.value) }} />
              <span className="stat-chip">{fmt(countries.length)} مورد</span>
            </div>
          </div>

          <div className="glass-card divide-y divide-white/5 max-h-[560px] overflow-y-auto">
            {countries.map((c) => (
              <button key={c.id} onClick={() => { setSelectedCountry(c); setCountryAlias(c.command_name || ''); setCountryLat(c.lat == null ? '' : String(c.lat)); setCountryLon(c.lon == null ? '' : String(c.lon)); setCountryPlayer('') }}
                className={`w-full text-right flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 ${selectedCountry?.id === c.id ? 'bg-primary-500/10' : ''}`}>
                <span className="text-lg">{c.emoji}</span>
                <span className="min-w-28 font-bold truncate">{c.name}</span>
                <code className="text-[10px] text-primary-300 bg-primary-500/10 rounded px-1.5 py-0.5">/{c.command_name}</code>
                {c.imaginary && <span className="text-[10px] text-gold-300">🏝 خیالی</span>}
                <span className="text-[10px] text-slate-600 hidden md:inline">{c.continent}</span>
                <span className="text-[10px] text-slate-500 mr-auto">{c.owner ? `👑 ${c.owner}` : '🟢 آزاد'}</span>
              </button>
            ))}
          </div>

          {selectedCountry && (
            <div className="glass-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="font-black text-lg">{selectedCountry.emoji} {selectedCountry.name}</div>
                <button className="btn-ghost !py-1" onClick={() => setSelectedCountry(null)}>بستن</button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <label className="text-xs text-slate-500">نام فرمان
                  <input className="input-dark mt-1" value={countryAlias} onChange={(e) => setCountryAlias(e.target.value)} placeholder="iran" />
                </label>
                <label className="text-xs text-slate-500">Latitude
                  <input className="input-dark mt-1" value={countryLat} onChange={(e) => setCountryLat(e.target.value)} placeholder="32.0" />
                </label>
                <label className="text-xs text-slate-500">Longitude
                  <input className="input-dark mt-1" value={countryLon} onChange={(e) => setCountryLon(e.target.value)} placeholder="53.0" />
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                <button className="btn-primary text-xs" onClick={() => manageCountry({ action: 'update', country_id: selectedCountry.id, command_name: countryAlias, lat: countryLat, lon: countryLon }, 'اطلاعات کشور ذخیره شد')}>💾 ذخیره</button>
                <button className="btn-ghost text-xs" onClick={() => { const p = prompt('نام کاربری یا نام فرمانده را وارد کنید:', 'boss'); if (p) { setCountryPlayer(p); manageCountry({ action: 'assign', country_id: selectedCountry.id, player: p }, `کشور به ${p} واگذار شد`) } }}>👑 واگذاری به بازیکن</button>
                {selectedCountry.owner && <button className="btn-danger text-xs" onClick={() => { if (confirm('رزرو این کشور آزاد شود؟')) manageCountry({ action: 'release', country_id: selectedCountry.id }, 'رزرو کشور آزاد شد') }}>🔓 آزاد کردن رزرو</button>}
              </div>
              <div className="text-[10px] text-slate-500">مالک فعلی: {selectedCountry.owner || 'آزاد'} · مختصات: {selectedCountry.lat ?? '—'}, {selectedCountry.lon ?? '—'}</div>
            </div>
          )}
        </div>
      )}

      {/* ============ AUDIT ============ */}
      {tab === 'audit' && (
        <div className="glass-card p-4 space-y-1.5">
          <div className="section-title mb-2">📜 Audit Log — اکشن‌های ادمین</div>
          {audit.length === 0 && <p className="text-slate-500 text-sm">اکشنی ثبت نشده.</p>}
          {audit.map((a) => (
            <div key={a.id} className="flex flex-wrap items-center gap-2 bg-white/5 rounded-lg px-3 py-2 text-sm">
              <span className="font-bold text-primary-300">{a.admin || 'سیستم'}</span>
              <span>{a.action}</span>
              <span className="text-slate-400">{a.target}</span>
              <span className="text-xs text-slate-600 mr-auto">{new Date(a.created_at).toLocaleString('fa-IR')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function FeedRow({ f }: { f: FeedItem }) {
  const inner = (
    <>
      <span className="text-base shrink-0">{FEED_ICON[f.kind] || '📌'}</span>
      <span className="text-sm flex-1">{f.text}</span>
      <span className="text-[10px] text-slate-600 shrink-0">{timeAgo(f.created_at)}</span>
    </>
  )
  // Drill-down: eventهای دارای target به پروفایل بازیکن لینک می‌شوند
  if (f.target_kind === 'player' && f.actor) {
    return <Link to={`/players/${f.actor}`} className="flex items-center gap-2 bg-white/5 rounded-lg px-3 py-2 hover:bg-white/10 transition">{inner}</Link>
  }
  return <div className="flex items-center gap-2 bg-white/5 rounded-lg px-3 py-2">{inner}</div>
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass-card p-4">
      <div className="section-title mb-3 text-base">{title}</div>
      <div style={{ height: 250 }} dir="ltr">{children}</div>
    </div>
  )
}

function BigStat({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="glass-card p-4">
      <div className="text-slate-400 text-sm">{icon} {label}</div>
      <div className="text-2xl font-black tabular-nums mt-1">{value}</div>
    </div>
  )
}
