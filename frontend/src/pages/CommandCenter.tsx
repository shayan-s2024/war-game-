import { useCallback, useEffect, useState } from 'react'
import { api, errMsg } from '../lib/api'
import { fmt } from '../lib/utils'
import { AG_TYPE_FA, ALERT_TYPE_FA, SEV_FA, type AgreementW, type AlertW, type CommandCenterW } from '../lib/commandTypes'
import { useWorldSocket } from '../lib/useGameSocket'

const TYPE_ICON: Record<string, string> = {
  resource_shortage: '📦', treasury_low: '💰', supply_disruption: '🚚',
  equipment_shortage: '🧰', military_readiness: '🎖', production_failure: '🏭',
  diplomatic_change: '⚡', trade_disruption: '🛒', infrastructure_capacity: '🏗', construction_delay: '⏳',
}

function AlertCard({ a, onAck }: { a: AlertW; onAck: (id: number) => void }) {
  const sev = a.severity === 'critical'
    ? '!border-danger-500/60 bg-danger-500/5'
    : a.severity === 'warning' ? '!border-gold-500/50 bg-gold-500/5' : ''
  return (
    <div className={`glass-card p-3 space-y-1 animate-glow ${sev}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="font-black text-sm">
          {TYPE_ICON[a.type] || '🚨'} {a.title}
          {a.status === 'acknowledged' && <span className="text-[10px] text-slate-500 mr-2">(تأیید شد)</span>}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${a.severity === 'critical' ? 'bg-danger-500/20 text-danger-300' : a.severity === 'warning' ? 'bg-gold-500/20 text-gold-300' : 'bg-white/10 text-slate-400'}`}>
            {SEV_FA[a.severity]} · {fmt(a.priority)}
          </span>
        </div>
      </div>
      {a.description && <p className="text-xs text-slate-300 leading-5">{a.description}</p>}
      {a.cause && <p className="text-[11px] text-slate-500">علت: {a.cause}</p>}
      {a.recommended_action && (
        <p className="text-[11px] text-sky-300">💡 {a.recommended_action}</p>
      )}
      {a.status === 'active' && (
        <button onClick={() => onAck(a.id)} className="btn-ghost !py-1 !px-2.5 text-[10px]">
          ✓ تأیید دیدم
        </button>
      )}
    </div>
  )
}

function AgreementChip({ ag, onCancel }: { ag: AgreementW; onCancel: (id: number) => void }) {
  const isTrade = ag.type === 'trade'
  const terms = ag.terms as { item_key?: string; qty?: number; price?: number }
  return (
    <div className="flex items-center justify-between bg-white/5 rounded-lg px-2.5 py-2 text-xs gap-2">
      <span className="truncate">
        <span className="font-bold">{AG_TYPE_FA[ag.type]}</span>
        <span className="text-slate-400"> با {ag.emoji} {ag.other}</span>
        {isTrade && terms.item_key && (
          <span className="text-[10px] text-gold-300"> — {fmt(terms.qty)}×{terms.item_key} @ {fmt(terms.price || 0)} ({fmt(ag.deliveries || 0)} تحویل)</span>
        )}
      </span>
      <button onClick={() => onCancel(ag.id)} className="text-danger-400 text-[10px] shrink-0 hover:underline">لغو</button>
    </div>
  )
}

export default function CommandCenter() {
  const [data, setData] = useState<CommandCenterW | null>(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [filter, setFilter] = useState<'all' | 'critical' | 'economy' | 'military'>('all')

  const load = useCallback(() => {
    api.get('/command-center/').then(({ data }) => setData(data)).catch((e) => setError(errMsg(e)))
  }, [])
  useEffect(load, [load])

  // 🔴 زنده — رویداد جهانی (نبرد/دیپلماسی) → refresh
  useWorldSocket(() => { load() })

  const ack = async (id: number) => {
    try {
      await api.post('/alerts/', { action: 'ack', id })
      setData((d) => d ? { ...d, alerts: d.alerts.map((a) => a.id === id ? { ...a, status: 'acknowledged' } : a) } : d)
    } catch (e) { setMsg('❌ ' + errMsg(e)); setTimeout(() => setMsg(''), 3000) }
  }
  const cancelAg = async (id: number) => {
    try {
      await api.post('/diplomacy/', { action: 'cancel', id })
      setMsg('📜 توافق لغو شد — هزینه دیپلماتیک اعمال شد')
      load()
      setTimeout(() => setMsg(''), 3500)
    } catch (e) { setMsg('❌ ' + errMsg(e)); setTimeout(() => setMsg(''), 3000) }
  }

  if (error) return <div className="glass-card p-8 text-center text-danger-400">⚠️ {error}</div>
  if (!data) return <div className="glass-card p-8 text-center text-slate-500">⏳ در حال بارگذاری وضعیت کشور…</div>

  const { treasury, stats } = data
  const alerts = data.alerts.filter((a) => {
    if (filter === 'critical') return a.severity === 'critical'
    if (filter === 'economy') return ['treasury_low', 'resource_shortage', 'trade_disruption', 'production_failure'].includes(a.type)
    if (filter === 'military') return ['military_readiness', 'equipment_shortage', 'supply_disruption'].includes(a.type)
    return true
  })
  const criticalCount = data.alerts.filter((a) => a.severity === 'critical' && a.status === 'active').length

  return (
    <div className="space-y-4">
      {/* هدر کشور */}
      <div className="glass-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{data.country.emoji}</span>
            <div>
              <div className="section-title !mb-0">🏛 مرکز فرماندهی — {data.country.name || 'بدون کشور'}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                💰 خزانه {fmt(treasury.current)} · 📈 درآمد {fmt(treasury.income)}/روز
                {treasury.recent_flow !== 0 && (
                  <span className={treasury.recent_flow > 0 ? ' text-success-400' : ' text-danger-400'}>
                    {' '}· جریان اخیر {treasury.recent_flow > 0 ? '+' : ''}{fmt(treasury.recent_flow)}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {criticalCount > 0 && (
              <span className="stat-chip !border-danger-500/50 text-danger-300 animate-pulse">🚨 {fmt(criticalCount)} بحرانی</span>
            )}
            <span className="stat-chip">🤝 {fmt(data.agreements.length)} توافق</span>
            <span className="stat-chip">✉️ {fmt(data.incoming_proposals.length)} پیشنهاد</span>
            <a href="/diplomacy" className="btn-ghost !py-1.5 !px-3 text-[11px]">🤝 دیپلماسی</a>
            <a href="/my-country" className="btn-ghost !py-1.5 !px-3 text-[11px]">🗺 نقشه کشور</a>
          </div>
        </div>
      </div>

      {msg && <div className="glass-card p-2.5 text-center text-xs font-bold text-gold-300">{msg}</div>}

      {/* هشدارها */}
      <div className="glass-card p-4 space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="section-title !mb-0">🚨 هشدارهای فعال ({fmt(alerts.length)})</div>
          <div className="flex gap-1">
            {([['all', 'همه'], ['critical', 'بحرانی'], ['economy', 'اقتصاد'], ['military', 'نظامی']] as const).map(([k, l]) => (
              <button key={k} onClick={() => setFilter(k)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${filter === k ? 'bg-primary-500 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}>{l}</button>
            ))}
          </div>
        </div>
        {alerts.length === 0 && <p className="text-xs text-slate-500 py-3 text-center">✅ هیچ هشدار فعالی نیست — وضعیت کشور پایدار است</p>}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {alerts.map((a) => <AlertCard key={a.id} a={a} onAck={ack} />)}
        </div>
      </div>

      {/* گرید اصلی */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* نظامی */}
        <div className="glass-card p-4 space-y-2">
          <div className="section-title">⚔️ وضعیت نظامی</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex justify-between bg-white/5 rounded-lg px-2.5 py-2"><span className="text-slate-500">حمله</span><b>{fmt(stats.army.attack)}</b></div>
            <div className="flex justify-between bg-white/5 rounded-lg px-2.5 py-2"><span className="text-slate-500">دفاع</span><b>{fmt(stats.army.defense)}</b></div>
            <div className="flex justify-between bg-white/5 rounded-lg px-2.5 py-2"><span className="text-slate-500">جنگنده آماده</span><b>{fmt(stats.army.ready_fighters)}</b></div>
            <div className="flex justify-between bg-white/5 rounded-lg px-2.5 py-2"><span className="text-slate-500">ناوگان فعال</span><b>{fmt(stats.fleets.outbound)} / {fmt(stats.fleets.returning)}</b></div>
          </div>
          {Object.keys(stats.army.categories).length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {Object.entries(stats.army.categories).map(([k, v]) => (
                <span key={k} className="stat-chip !py-0.5 !px-2 text-[10px]">{k}: {fmt(v.count)} <span className={v.quality >= 1.2 ? 'text-gold-400' : 'text-slate-500'}>Q{v.quality}</span></span>
              ))}
            </div>
          )}
        </div>
        {/* اقتصاد */}
        <div className="glass-card p-4 space-y-2">
          <div className="section-title">💰 اقتصاد</div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="flex flex-col bg-white/5 rounded-lg px-2.5 py-2"><span className="text-slate-500 text-[10px]">معادن</span><b>{fmt(stats.income.mines)}/روز</b></div>
            <div className="flex flex-col bg-white/5 rounded-lg px-2.5 py-2"><span className="text-slate-500 text-[10px]">شرکت‌ها</span><b>{fmt(stats.income.economic)}/روز</b></div>
            <div className="flex flex-col bg-white/5 rounded-lg px-2.5 py-2"><span className="text-slate-500 text-[10px]">جمعیت</span><b>{fmt(stats.population)}</b></div>
          </div>
          {(stats.status.viruses.length > 0 || stats.status.sanction.active || stats.status.on_fire) && (
            <div className="text-[11px] text-danger-300 space-y-0.5 pt-1">
              {stats.status.viruses.map((v) => <div key={v}>🦠 ویروس {v}</div>)}
              {stats.status.sanction.active && <div>🚫 تحریم — جریمه {fmt(stats.status.sanction.penalty)}٪</div>}
              {stats.status.on_fire && <div>🔥 کشور در آتش</div>}
            </div>
          )}
        </div>
        {/* توافق‌ها */}
        <div className="glass-card p-4 space-y-2">
          <div className="section-title">📜 توافق‌های فعال ({fmt(data.agreements.length)})</div>
          {data.agreements.length === 0 && <p className="text-xs text-slate-500">توافقی ندارید — از صفحه دیپلماسی پیشنهاد بفرستید</p>}
          <div className="space-y-1.5">
            {data.agreements.map((ag) => <AgreementChip key={ag.id} ag={ag} onCancel={cancelAg} />)}
          </div>
        </div>
        {/* پیشنهادهای ورودی */}
        <div className="glass-card p-4 space-y-2">
          <div className="section-title">✉️ پیشنهادهای دریافتی ({fmt(data.incoming_proposals.length)})</div>
          {data.incoming_proposals.length === 0 && <p className="text-xs text-slate-500">پیشنهادی در انتظار پاسخ نیست</p>}
          <div className="space-y-1.5">
            {data.incoming_proposals.map((p) => (
              <div key={p.id} className="flex items-center justify-between bg-white/5 rounded-lg px-2.5 py-2 text-xs gap-2">
                <span className="truncate">
                  <b>{AG_TYPE_FA[p.type]}</b> <span className="text-slate-400">از {p.emoji} {p.from}</span>
                </span>
                <a href="/diplomacy" className="text-primary-400 text-[10px] shrink-0">پاسخ ←</a>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* روابط */}
      {data.relations.length > 0 && (
        <div className="glass-card p-4">
          <div className="section-title">🌐 روابط دیپلماتیک</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {data.relations.map((r) => (
              <div key={r.country} className="bg-white/5 rounded-lg px-3 py-2 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <b>{r.emoji} {r.country}</b>
                  <span className={r.score >= 30 ? 'text-success-400' : r.score <= -30 ? 'text-danger-400' : 'text-slate-400'}>{r.score > 0 ? '+' : ''}{r.score}</span>
                </div>
                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden flex">
                  <div className="h-full bg-success-500/70" style={{ width: `${r.trust / 2}%` }} />
                  <div className="h-full bg-danger-500/70" style={{ width: `${r.tension / 2}%` }} />
                </div>
                <div className="text-[10px] text-slate-500">اعتماد {r.trust} · تنش {r.tension}{r.agreements.length > 0 && ` · ${fmt(r.agreements.length)} توافق`}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
