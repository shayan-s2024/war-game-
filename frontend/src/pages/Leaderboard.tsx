import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { fmt } from '../lib/utils'
import type { PlayerSummary } from '../lib/types'

const METRICS = [
  { key: 'score', label: '🏆 امتیاز' },
  { key: 'credit', label: '💰 ثروت' },
  { key: 'attack_power', label: '💥 قدرت' },
  { key: 'daily_profit', label: '📈 تولید' },
  { key: 'population', label: '👥 جمعیت' },
] as const

type Metric = (typeof METRICS)[number]['key']

export default function LeaderboardPage() {
  const [metric, setMetric] = useState<Metric>('score')
  const [rows, setRows] = useState<PlayerSummary[]>([])
  const [myRank, setMyRank] = useState<number | null>(null)
  const [season, setSeason] = useState<{ season_id: number; winners: { rank: number; player_name: string; country: string; score: number }[] } | null>(null)

  useEffect(() => {
    api.get('/leaderboard/', { params: { metric } }).then(({ data }) => {
      setRows(data.leaderboard)
      setMyRank(data.my_rank)
    })
  }, [metric])

  useEffect(() => {
    api.get('/seasons/').then(({ data }) => setSeason(data)).catch(() => {})
  }, [])

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 flex items-center justify-between flex-wrap gap-2">
        <h1 className="section-title text-xl">🏆 رتبه‌بندی جهانی</h1>
        {myRank != null && <span className="stat-chip">رتبه شما: <b className="text-gold-400">#{fmt(myRank)}</b></span>}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {METRICS.map((m) => (
          <button key={m.key} onClick={() => setMetric(m.key)}
            className={`px-4 py-2 rounded-xl text-sm whitespace-nowrap font-bold transition ${
              metric === m.key ? 'bg-primary-500/20 text-primary-300 border border-primary-500/40' : 'bg-white/5 text-slate-400'
            }`}>
            {m.label}
          </button>
        ))}
      </div>

      <div className="glass-card divide-y divide-white/5">
        {rows.map((p, i) => (
          <Link to={`/players/${p.username || ''}`} key={p.id}
            className={`flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition ${i === 0 ? 'bg-gold-500/5' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-black text-sm shrink-0
              ${i === 0 ? 'bg-gold-400 text-night-900' : i === 1 ? 'bg-slate-300 text-night-900' : i === 2 ? 'bg-amber-700 text-white' : 'bg-white/5 text-slate-400'}`}>
              {i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-bold truncate">{p.player_name}</div>
              <div className="text-xs text-slate-500">{p.country}</div>
            </div>
            <div className="text-left">
              <div className="font-black tabular-nums">
                {fmt(metric === 'score' ? p.score : metric === 'credit' ? p.credit :
                     metric === 'attack_power' ? p.attack_power : metric === 'daily_profit' ? p.daily_profit : p.population)}
              </div>
            </div>
          </Link>
        ))}
      </div>
      {season && season.winners.length > 0 && (
        <div className="glass-card p-4">
          <div className="section-title mb-3">🏁 برندگان فصل {season.season_id}</div>
          <div className="space-y-1.5">
            {season.winners.map((w) => (
              <div key={w.rank} className="flex items-center gap-3 px-3 py-2 bg-white/5 rounded-xl">
                <span className="w-7 h-7 rounded-full bg-gold-500/15 text-gold-400 flex items-center justify-center text-xs font-black">{w.rank}</span>
                <span className="font-bold text-sm flex-1">{w.player_name}</span>
                <span className="text-xs text-slate-500">{w.country}</span>
                <span className="text-sm font-black tabular-nums">🏆 {fmt(w.score)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
