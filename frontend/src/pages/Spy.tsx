import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api, errMsg } from '../lib/api'
import { fmt, HACKER_LABELS } from '../lib/utils'
import type { IntelItem, TargetPlayer } from '../lib/types'

interface SpyData {
  hackers: Record<string, number>
  defense_mode: boolean
  defense_power: number
  intel: IntelItem[]
  my_codes: Record<string, string>
}

const ABILITIES: Record<string, string> = {
  weak: 'فقط دفاعی',
  medium: 'اطلاعاتی + قطع پدافند حریف',
  strong: 'همه قابلیت‌ها (قطع موشک + پدافند + سرقت کد)',
  elite: 'همه قابلیت‌ها — قوی‌ترین',
}

export default function SpyPage() {
  const [data, setData] = useState<SpyData | null>(null)
  const [tab, setTab] = useState<'hack' | 'assassinate' | 'defense'>('hack')
  const [targets, setTargets] = useState<TargetPlayer[]>([])
  const [target, setTarget] = useState<TargetPlayer | null>(null)
  const [level, setLevel] = useState('medium')
  const [count, setCount] = useState(1)
  const [action, setAction] = useState<'steal' | 'disable_missiles' | 'disable_defenses'>('steal')
  const [busy, setBusy] = useState(false)
  const [assassTarget, setAssassTarget] = useState<IntelItem | null>(null)
  const [method, setMethod] = useState('drone')
  const [code, setCode] = useState('')
  const [result, setResult] = useState<any>(null)

  const load = () => api.get('/spy/').then(({ data }) => setData(data))
  useEffect(() => { load() }, [])

  useEffect(() => {
    api.get('/attack/targets/', { params: { weapon: 'navy' } }).then(({ data }) => setTargets(data.targets))
  }, [])

  const runHack = async () => {
    if (!target) return
    setBusy(true)
    try {
      const endpoint = action === 'steal' ? '/spy/hack/' : '/spy/action/'
      const body = action === 'steal'
        ? { target_id: target.id, level, count }
        : { action, target_id: target.id, level, count }
      const { data: res } = await api.post(endpoint, body)
      setResult(res)
      load()
    } catch (e: any) {
      setResult(e.response?.data || { error: errMsg(e) })
    } finally { setBusy(false) }
  }

  const defenseMode = async () => {
    try {
      const { data: res } = await api.post('/spy/action/', { action: 'defense_mode' })
      toast.success(res.message || 'فعال شد')
      load()
    } catch (e) { toast.error(errMsg(e)) }
  }

  const changeCodes = async () => {
    try {
      await api.post('/cabinet/change-codes/', {})
      toast.success('🔐 کدهای جدید صادر شد — همین صفحه را ببینید')
      load()
    } catch (e) { toast.error(errMsg(e)) }
  }

  const assassinate = async () => {
    if (!assassTarget) return
    setBusy(true)
    try {
      const { data: res } = await api.post('/spy/assassinate/', {
        target_id: assassTarget.target_id,
        member_key: assassTarget.member_key,
        method, code,
      })
      setResult(res)
      load()
    } catch (e: any) {
      setResult(e.response?.data || { error: errMsg(e) })
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 flex flex-wrap items-center gap-3 justify-between">
        <h1 className="section-title text-xl">🕵️ جاسوسی و ترور</h1>
        <div className="flex gap-2 text-sm">
          <span className="stat-chip">🛡 قدرت دفاعی: {fmt(data?.defense_power || 0)}</span>
          {data?.defense_mode && <span className="stat-chip !border-success-500/40 text-success-400">✅ حالت تدافعی فعال</span>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {([['hack', '💻 حمله هکری'], ['assassinate', '🗡️ ترور'], ['defense', '🛡 دفاع']] as const).map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 rounded-xl text-sm font-bold transition ${
              tab === k ? 'bg-primary-500/20 text-primary-300 border border-primary-500/40' : 'bg-white/5 text-slate-400'
            }`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'hack' && (
        <div className="space-y-4">
          {/* موجودی هکرها */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {data && Object.entries(data.hackers).map(([k, v]) => (
              <div key={k} className="glass-card p-3 text-center">
                <div className="font-bold text-sm">{HACKER_LABELS[k]}</div>
                <div className="text-2xl font-black mt-1">{fmt(v)}</div>
                <div className="text-[10px] text-slate-500 mt-1">{ABILITIES[k]}</div>
              </div>
            ))}
          </div>

          {/* انتخاب اکشن */}
          <div className="glass-card p-4 space-y-3">
            <div className="section-title">💻 نوع عملیات</div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {([['steal', '🔐 سرقت کدهای کابینه', 'medium'],
                 ['disable_defenses', '🛡 قطع پدافند حریف (۳۰ دقیقه)', 'medium'],
                 ['disable_missiles', '🚀 قطع موشک حریف (۳۰ دقیقه)', 'strong']] as const).map(([k, label, minLevel]) => (
                <button key={k} onClick={() => { setAction(k); setLevel(minLevel) }}
                  className={`p-3 rounded-xl text-sm text-right transition ${action === k ? 'bg-primary-500/20 border border-primary-500/40' : 'bg-white/5'}`}>
                  {label}
                </button>
              ))}
            </div>

            {/* هدف */}
            <div className="section-title">🎯 هدف</div>
            <select className="input-dark" value={target?.id || ''} onChange={(e) => setTarget(targets.find((t) => t.id === +e.target.value) || null)}>
              <option value="">انتخاب کنید...</option>
              {targets.map((t) => <option key={t.id} value={t.id}>{t.emoji} {t.name}</option>)}
            </select>

            <div className="grid grid-cols-2 gap-2">
              <select className="input-dark" value={level} onChange={(e) => setLevel(e.target.value)}>
                {Object.entries(HACKER_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <input type="number" min={1} className="input-dark" value={count} onChange={(e) => setCount(+e.target.value)} />
            </div>
            <button className="btn-danger w-full" onClick={runHack} disabled={busy || !target}>اجرا</button>
          </div>

          {result && <ResultCard result={result} onClose={() => setResult(null)} />}
        </div>
      )}

      {tab === 'assassinate' && (
        <div className="space-y-4">
          <div className="glass-card p-4">
            <div className="section-title mb-2">🔑 کدهای سرقت‌شده</div>
            {data?.intel.length === 0 && <p className="text-slate-500 text-sm">هیچ کدی ندارید. ابتدا با هکر متوسط/قوی کد سرقت کنید.</p>}
            <div className="space-y-2">
              {data?.intel.map((intel, i) => (
                <button key={i} onClick={() => { setAssassTarget(intel); setCode(intel.code) }}
                  className={`w-full flex items-center justify-between rounded-xl px-4 py-3 transition ${assassTarget === intel ? 'bg-primary-500/20 border border-primary-500/40' : 'bg-white/5 hover:bg-white/10'}`}>
                  <span className="font-bold">{intel.icon} {intel.position} — {intel.target_name}</span>
                  <code className="text-gold-400 font-mono" dir="ltr">{intel.code}</code>
                </button>
              ))}
            </div>
          </div>

          {assassTarget && (
            <div className="glass-card p-4 space-y-3">
              <div className="section-title">🗡️ ترور {assassTarget.position} در {assassTarget.target_name}</div>
              <div className="grid grid-cols-3 gap-2">
                {[['drone', '🛸 پهپاد ۶۰٪'], ['fighter', '✈️ جنگنده ۷۵٪'], ['commando', '🥷 کماندو ۵۰٪']].map(([k, label]) => (
                  <button key={k} onClick={() => setMethod(k)}
                    className={`p-3 rounded-xl text-sm transition ${method === k ? 'bg-danger-500/20 border border-danger-500/40' : 'bg-white/5'}`}>
                    {label}
                  </button>
                ))}
              </div>
              <input className="input-dark font-mono tracking-widest text-center" dir="ltr" placeholder="کد ۶ رقمی"
                value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} />
              <button className="btn-danger w-full" onClick={assassinate} disabled={busy || code.length !== 6}>
                🗡️ اجرای ترور
              </button>
            </div>
          )}

          {result && <ResultCard result={result} onClose={() => setResult(null)} />}
        </div>
      )}

      {tab === 'defense' && (
        <div className="glass-card p-4 space-y-4">
          <div className="section-title">🛡 دفاع هکری</div>
          <p className="text-slate-400 text-sm">
            یک هکر ضعیف مصرف می‌شود و به مدت ۱ ساعت حملات هکری به شما ۵۰٪ ضعیف‌تر می‌شوند.
            کدهای کابینه‌تان اینجا محافظت می‌شوند.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {data && Object.entries(data.my_codes).map(([key, val]) => (
              <div key={key} className="bg-white/5 rounded-xl px-4 py-3 flex justify-between items-center">
                <span className="font-bold">{key}</span>
                <code className="text-gold-400 font-mono" dir="ltr">{val}</code>
              </div>
            ))}
          </div>
          <button className="btn-primary w-full" onClick={defenseMode}>🛡 فعال‌سازی حالت تدافعی (۱ هکر ضعیف)</button>
          <button className="btn-ghost w-full" onClick={changeCodes}>🔐 تغییر همه کدهای امنیتی (بعد از لو رفتن)</button>
        </div>
      )}
    </div>
  )
}

function ResultCard({ result, onClose }: { result: any; onClose: () => void }) {
  const ok = result.success === true || result.ok === true
  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className={`glass-card p-8 w-full max-w-md text-center space-y-3 ${ok ? '!border-success-500/50' : '!border-danger-500/50'}`} onClick={(e) => e.stopPropagation()}>
        <div className="text-6xl">{ok ? '✅' : '❌'}</div>
        <h3 className="text-xl font-black">{result.success ? 'عملیات موفق' : result.error || 'عملیات ناموفق'}</h3>
        {result.stolen && (
          <div className="text-right space-y-1 bg-white/5 rounded-xl p-3">
            <div className="font-bold text-sm mb-1">🔐 کدهای به‌دست‌آمده:</div>
            {result.stolen.map((s: any, i: number) => (
              <div key={i} className="text-sm">{s.icon} {s.position}: <code className="text-gold-400" dir="ltr">{s.code}</code></div>
            ))}
          </div>
        )}
        {result.damage_percent != null && (
          <p className="text-slate-300">📉 کاهش استقامت: {result.damage_percent}٪</p>
        )}
        {result.message && <p className="text-slate-300">{result.message}</p>}
        <button className="btn-primary w-full" onClick={onClose}>بستن</button>
      </div>
    </div>
  )
}
