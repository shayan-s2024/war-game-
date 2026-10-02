import { useCallback, useEffect, useState } from 'react'
import { api, errMsg } from '../lib/api'
import { fmt } from '../lib/utils'
import { AG_TYPE_FA, type AgreementW, type ProposalW, type RelationW } from '../lib/commandTypes'
import { useWorldSocket } from '../lib/useGameSocket'

interface DiploData {
  relations: RelationW[]
  agreements: AgreementW[]
  proposals_in: ProposalW[]
  proposals_out: ProposalW[]
}

const TRADE_ITEMS = [
  { key: 'iron', name: 'معدن آهن' }, { key: 'silver', name: 'معدن نقره' },
  { key: 'gold', name: 'معدن طلا' }, { key: 'diamond', name: 'معدن الماس' },
  { key: 'emerald', name: 'معدن زمرد' },
]

function ProposalCard({ p, mode, onRespond }: {
  p: ProposalW; mode: 'in' | 'out'
  onRespond: (id: number, decision: string, counter?: Record<string, unknown>) => void
}) {
  const terms = p.terms as { item_key?: string; qty?: number; price?: number; duration_days?: number }
  const isTrade = p.type === 'trade'
  const [counterPrice, setCounterPrice] = useState(String(terms.price || 0))
  const [showCounter, setShowCounter] = useState(false)
  const other = mode === 'in' ? p.from : p.to
  return (
    <div className="glass-card p-3 space-y-2 !border-white/10">
      <div className="flex items-center justify-between">
        <div className="font-black text-sm">{AG_TYPE_FA[p.type]}</div>
        <span className="text-[10px] text-slate-500">#{p.id} · انقضا: {new Date(p.expires_at).toLocaleDateString('fa-IR')}</span>
      </div>
      <div className="text-xs text-slate-300">
        {mode === 'in' ? '📩 از' : '📤 به'} {p.emoji} <b>{other}</b>
      </div>
      {isTrade && terms.item_key && (
        <div className="text-xs bg-white/5 rounded-lg px-2.5 py-1.5">
          📦 {fmt(terms.qty)}× {terms.item_key} · قیمت {fmt(terms.price || 0)} · {terms.duration_days || 7} روز
        </div>
      )}
      {mode === 'in' ? (
        showCounter ? (
          <div className="flex gap-1.5 items-center">
            <input value={counterPrice} onChange={(e) => setCounterPrice(e.target.value)} dir="ltr"
              className="w-24 bg-night-900/80 border border-white/10 rounded-lg px-2 py-1 text-xs" placeholder="قیمت" />
            <button onClick={() => onRespond(p.id, 'counter', { ...terms, price: Number(counterPrice) })}
              className="btn-primary !py-1 !px-3 text-[11px]">ارسال متقابل</button>
            <button onClick={() => setShowCounter(false)} className="text-slate-500 text-[11px]">بازگشت</button>
          </div>
        ) : (
          <div className="flex gap-1.5">
            <button onClick={() => onRespond(p.id, 'accept')} className="btn-primary !py-1 !px-3 text-[11px]">✅ پذیرش</button>
            <button onClick={() => setShowCounter(true)} className="btn-ghost !py-1 !px-3 text-[11px]">🔁 متقابل</button>
            <button onClick={() => onRespond(p.id, 'reject')} className="btn-ghost !py-1 !px-3 text-[11px] !text-danger-300">❌ رد</button>
          </div>
        )
      ) : (
        <div className="text-[10px] text-slate-500">⏳ در انتظار پاسخ طرف مقابل</div>
      )}
    </div>
  )
}

export default function Diplomacy() {
  const [data, setData] = useState<DiploData | null>(null)
  const [countries, setCountries] = useState<{ name: string; emoji: string; taken: boolean }[]>([])
  const [msg, setMsg] = useState('')
  const [ptype, setPtype] = useState<'non_aggression' | 'alliance' | 'transit' | 'trade'>('non_aggression')
  const [target, setTarget] = useState('')
  const [trade, setTrade] = useState({ item_key: 'iron', qty: 3, price: 800, duration_days: 7 })

  const load = useCallback(() => {
    api.get('/diplomacy/').then(({ data }) => setData(data)).catch((e) => setMsg('❌ ' + errMsg(e)))
  }, [])
  useEffect(() => {
    load()
    api.get('/countries/').then(({ data }) => {
      const all: { name: string; emoji: string; taken: boolean }[] = []
      for (const list of Object.values(data.countries || {})) all.push(...(list as typeof all))
      setCountries(all.filter((c) => c.taken))
    }).catch(() => {})
  }, [load])

  // 🔴 زنده
  useWorldSocket(() => { load() })

  const send = async () => {
    const terms = ptype === 'trade' ? { ...trade } : {}
    try {
      const { data: r } = await api.post('/diplomacy/', {
        action: 'send', to_country: target, type: ptype, terms,
        command_id: `ui-${Date.now()}`,
      })
      if (r.ok) { setMsg(`✅ پیشنهاد به ${target} ارسال شد`); load() }
      else setMsg('❌ ' + (r.error || 'خطا'))
    } catch (e) { setMsg('❌ ' + errMsg(e)) }
    setTimeout(() => setMsg(''), 3500)
  }
  const respond = async (id: number, decision: string, counter?: Record<string, unknown>) => {
    try {
      const { data: r } = await api.post('/diplomacy/', { action: 'respond', id, decision, counter_terms: counter })
      if (r.ok) { setMsg(decision === 'accept' ? '✅ توافق امضا شد' : decision === 'counter' ? '🔁 پیشنهاد متقابل ارسال شد' : '❌ پیشنهاد رد شد'); load() }
      else setMsg('❌ ' + (r.error || 'خطا'))
    } catch (e) { setMsg('❌ ' + errMsg(e)) }
    setTimeout(() => setMsg(''), 3500)
  }

  const takenCountries = countries.filter((c) => c.name !== data?.relations?.[0]?.country)

  return (
    <div className="space-y-4">
      <div className="glass-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="section-title !mb-0">🤝 دیپلماسی و روابط بین‌الملل</div>
          <a href="/command-center" className="btn-ghost !py-1.5 !px-3 text-[11px]">🏛 مرکز فرماندهی</a>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">پیمان عدم تجاوز حمله دشمن را بلاک می‌کند · توافق تجاری هر tick واقعاً کالا و پول جابه‌جا می‌کند.</p>
      </div>

      {msg && <div className="glass-card p-2.5 text-center text-xs font-bold text-gold-300">{msg}</div>}

      {/* ارسال پیشنهاد */}
      <div className="glass-card p-4 space-y-3">
        <div className="section-title">✉️ پیشنهاد جدید</div>
        <div className="flex flex-wrap gap-1.5">
          {(['non_aggression', 'alliance', 'transit', 'trade'] as const).map((t) => (
            <button key={t} onClick={() => setPtype(t)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-bold ${ptype === t ? 'bg-primary-500 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}>
              {AG_TYPE_FA[t]}
            </button>
          ))}
        </div>
        {ptype === 'trade' && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <select value={trade.item_key} onChange={(e) => setTrade({ ...trade, item_key: e.target.value })}
              className="bg-night-900/80 border border-white/10 rounded-lg px-2 py-1.5 text-xs">
              {TRADE_ITEMS.map((i) => <option key={i.key} value={i.key} className="bg-night-900">{i.name}</option>)}
            </select>
            <input type="number" min={1} value={trade.qty} onChange={(e) => setTrade({ ...trade, qty: Number(e.target.value) })}
              className="bg-night-900/80 border border-white/10 rounded-lg px-2 py-1.5 text-xs" placeholder="تعداد" />
            <input type="number" min={1} value={trade.price} onChange={(e) => setTrade({ ...trade, price: Number(e.target.value) })}
              className="bg-night-900/80 border border-white/10 rounded-lg px-2 py-1.5 text-xs" placeholder="قیمت هر واحد" />
            <input type="number" min={1} max={30} value={trade.duration_days} onChange={(e) => setTrade({ ...trade, duration_days: Number(e.target.value) })}
              className="bg-night-900/80 border border-white/10 rounded-lg px-2 py-1.5 text-xs" placeholder="مدت (روز)" />
          </div>
        )}
        <div className="flex gap-2 flex-wrap">
          <select value={target} onChange={(e) => setTarget(e.target.value)}
            className="flex-1 min-w-40 bg-night-900/80 border border-white/10 rounded-lg px-2 py-1.5 text-xs">
            <option value="" className="bg-night-900">— کشور مقصد (صاحب‌دار) —</option>
            {takenCountries.map((c) => <option key={c.name} value={c.name} className="bg-night-900">{c.emoji} {c.name}</option>)}
          </select>
          <button onClick={send} disabled={!target} className={`!py-1.5 !px-4 text-xs font-black rounded-lg ${target ? 'btn-primary' : 'bg-white/5 text-slate-600 cursor-not-allowed'}`}>
            ارسال پیشنهاد
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* دریافتی */}
        <div className="glass-card p-4 space-y-2">
          <div className="section-title">📩 پیشنهادهای دریافتی ({fmt(data?.proposals_in.length || 0)})</div>
          {(!data || data.proposals_in.length === 0) && <p className="text-xs text-slate-500">پیشنهادی نیست</p>}
          <div className="space-y-2">
            {data?.proposals_in.map((p) => <ProposalCard key={p.id} p={p} mode="in" onRespond={respond} />)}
          </div>
        </div>
        {/* ارسالی */}
        <div className="glass-card p-4 space-y-2">
          <div className="section-title">📤 پیشنهادهای ارسالی ({fmt(data?.proposals_out.length || 0)})</div>
          {(!data || data.proposals_out.length === 0) && <p className="text-xs text-slate-500">پیشنهادی در جریان نیست</p>}
          <div className="space-y-2">
            {data?.proposals_out.map((p) => <ProposalCard key={p.id} p={p} mode="out" onRespond={respond} />)}
          </div>
        </div>
      </div>

      {/* روابط */}
      <div className="glass-card p-4">
        <div className="section-title">🌐 روابط کشور شما</div>
        {(!data || data.relations.length === 0) && <p className="text-xs text-slate-500">هنوز رابطه‌ای ثبت نشده — با ارسال پیشنهاد شروع کنید</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 mt-2">
          {data?.relations.map((r) => (
            <div key={r.country} className="bg-white/5 rounded-lg px-3 py-2 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <b>{r.emoji} {r.country}</b>
                <span className={r.score >= 30 ? 'text-success-400' : r.score <= -30 ? 'text-danger-400' : 'text-slate-400'}>
                  {r.score > 0 ? '+' : ''}{r.score}
                </span>
              </div>
              <div className="h-1.5 bg-white/10 rounded-full overflow-hidden flex">
                <div className="h-full bg-success-500/70" style={{ width: `${r.trust / 2}%` }} />
                <div className="h-full bg-danger-500/70" style={{ width: `${r.tension / 2}%` }} />
              </div>
              {r.agreements.length > 0 && (
                <div className="text-[10px] text-slate-400">📜 {r.agreements.map((a) => a.type_fa).join('، ')}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
