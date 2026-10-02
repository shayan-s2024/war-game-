import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { fmt } from '../lib/utils'

interface AchievementItem {
  key: string; name: string; icon: string; tier: 'bronze' | 'silver' | 'gold'
  description: string; reward: number; threshold: number
  unlocked: boolean; unlocked_at: string | null; progress: number
}

const TIER_STYLE: Record<string, string> = {
  bronze: 'border-amber-700/40 bg-amber-700/5',
  silver: 'border-slate-300/30 bg-slate-300/5',
  gold: 'border-gold-500/40 bg-gold-500/5',
}
const TIER_LABEL: Record<string, string> = { bronze: '🥉 برنز', silver: '🥈 نقره', gold: '🥇 طلا' }

export default function AchievementsPage() {
  const [data, setData] = useState<{
    achievements: AchievementItem[]; unlocked_count: number; total_count: number; just_unlocked: string[]
  } | null>(null)
  const [celebrating, setCelebrating] = useState<string | null>(null)

  const load = () => api.get('/achievements/').then(({ data }) => setData(data))
  useEffect(() => { load() }, [])

  // celebration برای دستاوردهای تازه
  useEffect(() => {
    if (data?.just_unlocked?.length) {
      setCelebrating(data.just_unlocked[0])
      const t = setTimeout(() => setCelebrating(null), 4000)
      return () => clearTimeout(t)
    }
  }, [data])

  if (!data) {
    return <div className="flex justify-center py-16"><div className="w-48 h-2 rounded-full skeleton" /></div>
  }

  const celebratingAch = data.achievements.find((a) => a.key === celebrating)

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="section-title text-xl">🏆 دستاوردها</h1>
          <p className="text-slate-400 text-sm mt-1">با پیشرفت در بازی، دستاوردها باز می‌شوند و جایزه سکه می‌گیرید.</p>
        </div>
        <span className="stat-chip">
          ✅ {fmt(data.unlocked_count)} از {fmt(data.total_count)}
        </span>
      </div>

      {/* progress bar کلی */}
      <div className="glass-card p-4">
        <div className="h-2.5 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-l from-primary-500 via-gold-400 to-gold-500 transition-all duration-700"
            style={{ width: `${(data.unlocked_count / data.total_count) * 100}%` }} />
        </div>
      </div>

      {/* celebration modal */}
      {celebratingAch && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setCelebrating(null)}>
          <div className="glass-card p-8 w-full max-w-sm text-center space-y-3 animate-glow !border-gold-500/50"
            onClick={(e) => e.stopPropagation()}>
            <div className="text-7xl animate-float">{celebratingAch.icon}</div>
            <h3 className="text-2xl font-black text-gold-400">دستاورد باز شد!</h3>
            <div className="text-lg font-bold">{celebratingAch.name}</div>
            <p className="text-slate-400 text-sm">{celebratingAch.description}</p>
            <div className="text-gold-400 font-black">🎁 جایزه: {fmt(celebratingAch.reward)} سکه</div>
            <button className="btn-primary w-full" onClick={() => setCelebrating(null)}>عالی!</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.achievements.map((a) => (
          <div key={a.key}
            className={`glass-card p-4 space-y-2 transition-all ${a.unlocked ? TIER_STYLE[a.tier] + ' opacity-100' : 'opacity-60'}`}>
            <div className="flex items-start justify-between">
              <div className="text-3xl" style={{ filter: a.unlocked ? 'none' : 'grayscale(1)' }}>{a.icon}</div>
              <span className="text-[10px] text-slate-500">{TIER_LABEL[a.tier]}</span>
            </div>
            <div className="font-bold text-sm">{a.name}</div>
            <p className="text-xs text-slate-400 leading-5">{a.description}</p>
            {a.unlocked ? (
              <div className="text-success-400 text-xs font-bold">✅ باز شد — جایزه {fmt(a.reward)} سکه</div>
            ) : (
              <>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-l from-primary-600 to-primary-400 transition-all"
                    style={{ width: `${a.progress}%` }} />
                </div>
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>پیشرفت: {a.progress}٪</span>
                  <span>🎁 {fmt(a.reward)} سکه</span>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
