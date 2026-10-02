import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { fmt, timeAgo } from '../lib/utils'

interface ProfileData {
  name: string; joined: string
  country: string | null; country_emoji: string | null; continent: string | null
  union: string | null; union_level: number | null
  stats: Record<string, any>
  battles: { total: number; wins: number; losses: number; win_rate: number }
  achievements: { key: string; name: string; icon: string; tier: string; description: string; unlocked_at: string }[]
  achievement_points: number
  statements: { id: number; kind: string; text: string; created_at: string }[]
  timeline: { ts: string; icon: string; text: string }[]
  ranks: { global: number; country?: number }
  last_active: string | null
  error?: string
}

type Tab = 'overview' | 'military' | 'achievements' | 'statements' | 'timeline'

const TIER_COLOR: Record<string, string> = {
  bronze: 'text-amber-400', silver: 'text-slate-300', gold: 'text-gold-400',
}

export default function PlayerProfile() {
  const { username } = useParams()
  const [data, setData] = useState<ProfileData | null>(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<Tab>('overview')

  useEffect(() => {
    api.get(`/players/${username}/`).then(({ data }) => setData(data))
      .catch((e) => setError(e.response?.data?.error || 'خطا در بارگذاری پروفایل'))
  }, [username])

  if (error) {
    return <div className="glass-card p-8 text-center text-danger-400">⛔ {error}</div>
  }
  if (!data) {
    return <div className="flex justify-center py-16"><div className="w-48 h-2 rounded-full skeleton" /></div>
  }

  return (
    <div className="space-y-4">
      {/* Header — Player Passport */}
      <div className="glass-card p-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-l from-primary-500/5 via-transparent to-gold-500/5 pointer-events-none" />
        <div className="flex flex-wrap items-center gap-4 relative">
          <div className="text-5xl">{data.country_emoji || '🏳️'}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-2xl font-black">{data.name}</h1>
              <span className="stat-chip text-xs">🏅 رتبه جهانی #{fmt(data.ranks.global)}</span>
              {data.ranks.country && <span className="stat-chip text-xs">🌍 رتبه قاره #{fmt(data.ranks.country)}</span>}
            </div>
            <div className="text-slate-400 text-sm mt-1 flex flex-wrap gap-x-3">
              {data.country && <span>🗺 {data.country}</span>}
              {data.union && <span>🤝 اتحاد {data.union} (لول {data.union_level})</span>}
              <span>📅 عضویت: {new Date(data.joined).toLocaleDateString('fa-IR')}</span>
              {data.last_active && <span>🟢 فعال {timeAgo(data.last_active)}</span>}
            </div>
          </div>
          <div className="text-left flex flex-col gap-2">
            <div>
              <div className="text-gold-400 font-black text-xl">🎖 {fmt(data.achievement_points)}</div>
              <div className="text-xs text-slate-500">امتیاز دستاورد</div>
            </div>
            {data.country && (
              <Link to={`/map?focus=${encodeURIComponent(data.country)}`} className="btn-ghost !py-1 text-[11px]">
                🌍 View On World Map
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {([['overview', '📊 مرور'], ['military', '⚔️ نظامی'], ['achievements', '🏆 دستاوردها'],
          ['statements', '📢 بیانیه‌ها'], ['timeline', '🕐 تایم‌لاین']] as const).map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 rounded-xl text-sm whitespace-nowrap font-bold transition ${
              tab === k ? 'bg-primary-500/20 text-primary-300 border border-primary-500/40' : 'bg-white/5 text-slate-400'
            }`}>{label}</button>
        ))}
      </div>

      {/* Overview */}
      {tab === 'overview' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {Object.entries({
              '🏆 امتیاز': data.stats.score, '👥 جمعیت': data.stats.population,
              '💥 قدرت': data.stats.attack_power, '📈 سود روزانه': data.stats.daily_profit,
            }).map(([label, v]) => (
              <div key={label} className="glass-card p-4">
                <div className="text-slate-400 text-sm">{label}</div>
                <div className="text-xl font-black tabular-nums mt-1">{v != null ? fmt(v) : '🔒 خصوصی'}</div>
              </div>
            ))}
          </div>
          <div className="glass-card p-4">
            <div className="section-title mb-2">⚔️ سابقه نظامی</div>
            <div className="grid grid-cols-4 gap-2 text-center">
              <div><div className="text-2xl font-black">{fmt(data.battles.total)}</div><div className="text-xs text-slate-500">نبرد</div></div>
              <div><div className="text-2xl font-black text-success-400">{fmt(data.battles.wins)}</div><div className="text-xs text-slate-500">برد</div></div>
              <div><div className="text-2xl font-black text-danger-400">{fmt(data.battles.losses)}</div><div className="text-xs text-slate-500">باخت</div></div>
              <div><div className="text-2xl font-black text-gold-400">{data.battles.win_rate}٪</div><div className="text-xs text-slate-500">نرخ برد</div></div>
            </div>
          </div>
        </div>
      )}

      {/* Military */}
      {tab === 'military' && (
        <div className="glass-card p-4 space-y-3">
          <div className="section-title">⚔️ رکورد نبردها (داده واقعی GlobalBattleEvent)</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <Stat label="کل نبردها" value={fmt(data.battles.total)} />
            <Stat label="پیروزی" value={fmt(data.battles.wins)} cls="text-success-400" />
            <Stat label="شکست" value={fmt(data.battles.losses)} cls="text-danger-400" />
            <Stat label="نرخ برد" value={`${data.battles.win_rate}٪`} cls="text-gold-400" />
          </div>
          {data.stats.defense != null && (
            <div className="grid grid-cols-2 gap-3 text-center pt-2">
              <Stat label="🛡 استقامت" value={fmt(data.stats.defense)} />
              <Stat label="💥 قدرت تخریب" value={fmt(data.stats.attack_power)} />
            </div>
          )}
        </div>
      )}

      {/* Achievements */}
      {tab === 'achievements' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.achievements.length === 0 && <p className="text-slate-500 text-sm">دستاوردی باز نشده.</p>}
          {data.achievements.map((a) => (
            <div key={a.key} className="glass-card p-4 flex gap-3">
              <span className="text-3xl">{a.icon}</span>
              <div>
                <div className={`font-bold ${TIER_COLOR[a.tier]}`}>{a.name}</div>
                <p className="text-xs text-slate-400">{a.description}</p>
                <span className="text-[10px] text-slate-500">{timeAgo(a.unlocked_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Statements */}
      {tab === 'statements' && (
        <div className="space-y-2">
          {data.statements.length === 0 && <p className="text-slate-500 text-sm">بیانیه‌ای منتشر نشده.</p>}
          {data.statements.map((s) => (
            <div key={s.id} className="glass-card p-4">
              <div className="flex items-center gap-2 mb-1 text-sm">
                <span>{s.kind === 'tweet' ? '🐦' : '📢'}</span>
                <span className="text-slate-500">{timeAgo(s.created_at)}</span>
              </div>
              <p className="text-slate-200 text-sm whitespace-pre-wrap">{s.text}</p>
            </div>
          ))}
        </div>
      )}

      {/* Timeline */}
      {tab === 'timeline' && (
        <div className="glass-card p-4 space-y-3">
          {data.timeline.length === 0 && <p className="text-slate-500 text-sm">فعالیتی ثبت نشده.</p>}
          {data.timeline.map((t, i) => (
            <div key={i} className="flex gap-3 items-start">
              <span className="text-xl">{t.icon}</span>
              <div className="flex-1 border-r border-white/10 pr-3">
                <p className="text-sm text-slate-200">{t.text}</p>
                <span className="text-[10px] text-slate-500">{timeAgo(t.ts)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, cls = '' }: { label: string; value: string; cls?: string }) {
  return (
    <div>
      <div className={`text-2xl font-black ${cls}`}>{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  )
}
