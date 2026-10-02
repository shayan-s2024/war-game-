import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, errMsg } from '../lib/api'
import { useGameStore } from '../store/gameStore'
import { fmt } from '../lib/utils'
import GlobeMap from '../components/GlobeMap'
import type { ContinentInfo, CountryInfo } from '../lib/types'

type Step = 'name' | 'country' | 'cabinet' | 'codes' | 'done'

const CABINET_KEYS = ['diplomat', 'leader', 'defense', 'economy', 'intelligence'] as const
type CabinetKey = (typeof CABINET_KEYS)[number]

export default function Onboarding() {
  const nav = useNavigate()
  const { fetchDashboard } = useGameStore()
  const [step, setStep] = useState<Step>('name')
  const [name, setName] = useState('')
  const [continents, setContinents] = useState<ContinentInfo[]>([])
  const [countries, setCountries] = useState<Record<string, CountryInfo[]>>({})
  const [selected, setSelected] = useState<CountryInfo | null>(null)
  const [options, setOptions] = useState<Record<string, { name: string; icon: string; options: string[] }>>({})
  const [cabinet, setCabinet] = useState<Partial<Record<CabinetKey, string>>>({})
  const [codes, setCodes] = useState<Record<string, string>>({})
  const [activePos, setActivePos] = useState<CabinetKey | null>(null)
  const [busy, setBusy] = useState(false)

  const [world, setWorld] = useState<any>(null)
  useEffect(() => {
    api.get('/countries/').then(({ data }) => {
      setContinents(data.continents)
      setCountries(data.countries)
    }).catch(() => toast.error('خطا در بارگذاری کشورها'))
    api.get('/cabinet/').then(({ data }) => setOptions(data.options))
    api.get('/world/').then(({ data }) => setWorld(data)).catch(() => {})
  }, [])

  const submitName = async () => {
    setBusy(true)
    try {
      await api.post('/registration/name/', { name })
      setStep('country')
    } catch (e) {
      toast.error(errMsg(e))
    } finally { setBusy(false) }
  }

  const submitCountry = async () => {
    if (!selected) return
    setBusy(true)
    try {
      await api.post('/registration/country/', { country: selected.name })
      setStep('cabinet')
    } catch (e) {
      toast.error(errMsg(e))
    } finally { setBusy(false) }
  }

  const setPos = async (key: CabinetKey, value: string) => {
    setCabinet((c) => ({ ...c, [key]: value }))
    setActivePos(null)
    try { await api.post('/cabinet/set/', { key, value }) } catch { /* offline ok */ }
  }

  const finishCabinet = async () => {
    setBusy(true)
    try {
      await api.post('/cabinet/finish/')
      const { data } = await api.get('/cabinet/')
      setCodes(data.codes || {})
      setStep('codes')
    } catch (e) {
      toast.error(errMsg(e))
    } finally { setBusy(false) }
  }

  const done = async () => {
    await fetchDashboard()
    nav('/', { replace: true })
  }

  const allSet = CABINET_KEYS.every((k) => cabinet[k])

  return (
    <div className="min-h-screen p-4 max-w-3xl mx-auto">
      {/* Stepper */}
      <div className="flex items-center gap-2 my-6">
        {(['name', 'country', 'cabinet', 'codes'] as Step[]).map((s, i) => (
          <div key={s} className="flex-1 flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm
              ${(['name', 'country', 'cabinet', 'codes'].indexOf(step) >= i ? 'bg-primary-500 text-white' : 'bg-white/5 text-slate-500')}`}>
              {i + 1}
            </div>
            {i < 3 && <div className={`flex-1 h-0.5 ${['name', 'country', 'cabinet', 'codes'].indexOf(step) > i ? 'bg-primary-500' : 'bg-white/10'}`} />}
          </div>
        ))}
      </div>

      {step === 'name' && (
        <div className="glass-card p-6 space-y-4">
          <h1 className="section-title text-2xl">👤 نام فرمانده</h1>
          <p className="text-slate-400 text-sm">نام شما به‌عنوان فرمانده رسمی کشور ثبت می‌شود (۳ تا ۳۰ کاراکتر، یکتا).</p>
          <input className="input-dark text-lg" value={name} onChange={(e) => setName(e.target.value)} placeholder="مثلا: شاهین" maxLength={30} />
          <button className="btn-primary w-full" disabled={busy || name.trim().length < 3} onClick={submitName}>ادامه</button>
        </div>
      )}

      {step === 'country' && (
        <div className="space-y-4">
          <div className="glass-card p-6">
            <h1 className="section-title text-2xl">🌍 کشور خود را انتخاب کنید</h1>
            <p className="text-slate-400 text-sm mt-1">۴۵۰ کشور و سرزمین — هر کشور فقط یک صاحب دارد. روی کره بچرخید و روی نشانگرها کلیک کنید.</p>
          </div>
          <div className="glass-card overflow-hidden" style={{ height: 420 }}>
            <GlobeMap
              world={world}
              onSelectCountry={(c: any) => {
                // تبدیل کشور world به فرم CountryInfo صفحه ثبت‌نام
                setSelected({
                  name: c.name, command_name: c.command_name, emoji: c.emoji, population: c.population,
                  taken: c.taken, lat: c.lat, lon: c.lon, continent: c.continent, imaginary: c.imaginary,
                })
              }}
              focusName={selected?.name}
              compact
            />
          </div>
          {selected && (
            <div className="glass-card p-4 flex items-center justify-between">
              <div className="text-lg">
                <div className="flex items-center gap-2 flex-wrap">
                  <span>{selected.emoji}</span><b>{selected.name}</b>
                  {selected.command_name && <code className="text-[10px] text-primary-300 bg-primary-500/10 rounded px-1.5 py-0.5">/{selected.command_name}</code>}
                  {selected.imaginary && <span className="text-[10px] text-gold-300">قلمرو خیالی</span>}
                  <span className="text-slate-500 text-sm">جمعیت: {fmt(selected.population)} میلیون</span>
                </div>
              </div>
              <button className="btn-primary" onClick={submitCountry} disabled={busy || selected.taken}>
                {selected.taken ? '❌ گرفته شده' : 'پایه‌گذاری کشور'}
              </button>
            </div>
          )}
          {/* فهرست سریع */}
          <div className="glass-card p-4">
            <div className="flex gap-2 overflow-x-auto pb-2">
              {continents.map((c) => (
                <span key={c.key} className="stat-chip shrink-0">{c.flag} {c.name}</span>
              ))}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 mt-3 max-h-64 overflow-y-auto">
              {Object.values(countries).flat().map((c) => (
                <button
                  key={c.name}
                  disabled={c.taken}
                  onClick={() => setSelected(c)}
                  className={`text-right px-3 py-2 rounded-lg text-sm transition flex items-center justify-between
                    ${selected?.name === c.name ? 'bg-primary-500/20 border border-primary-500/40' : 'bg-white/5 hover:bg-white/10'}
                    ${c.taken ? 'opacity-35 cursor-not-allowed' : ''}`}
                >
                  <span className="flex items-center gap-1.5 min-w-0"><span>{c.emoji}</span><span className="truncate">{c.name}</span>{c.command_name && <code className="text-[9px] text-slate-500">/{c.command_name}</code>}</span>
                  {c.taken && <span className="text-xs">🔒</span>}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {step === 'cabinet' && (
        <div className="space-y-3">
          <div className="glass-card p-6">
            <h1 className="section-title text-2xl">👥 تشکیل کابینه</h1>
            <p className="text-slate-400 text-sm mt-1">برای هر مقام یک نفر را انتخاب کنید یا دستی بنویسید. برای هر مقام یک کد امنیتی مخفی ساخته می‌شود.</p>
          </div>
          {CABINET_KEYS.map((key) => {
            const opt = options[key]
            if (!opt) return null
            return (
              <div key={key} className="glass-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-bold">{opt.icon} {opt.name}</div>
                    <div className={`text-sm ${cabinet[key] ? 'text-success-400' : 'text-slate-500'}`}>
                      {cabinet[key] || 'انتخاب نشده'}
                    </div>
                  </div>
                  <button className="btn-ghost !py-1.5" onClick={() => setActivePos(activePos === key ? null : key)}>
                    {cabinet[key] ? 'تغییر' : 'انتخاب'}
                  </button>
                </div>
                {activePos === key && (
                  <div className="mt-3 space-y-2">
                    <div className="grid grid-cols-2 gap-1.5">
                      {opt.options.map((o) => (
                        <button key={o} className="btn-ghost !py-1.5 text-xs text-right" onClick={() => setPos(key, o)}>{o}</button>
                      ))}
                    </div>
                    <ManualInput onSet={(v) => setPos(key, v)} />
                  </div>
                )}
              </div>
            )
          })}
          <button className="btn-primary w-full" disabled={!allSet || busy} onClick={finishCabinet}>
            🎯 تایید نهایی و دریافت کدها
          </button>
        </div>
      )}

      {step === 'codes' && (
        <div className="glass-card p-6 space-y-4">
          <h1 className="section-title text-2xl">🔐 کدهای امنیتی شما</h1>
          <div className="bg-danger-500/10 border border-danger-500/30 rounded-xl p-3 text-danger-400 text-sm">
            ⚠️ این کدها را فقط نزد خود نگه دارید! هکرهای حریف با سرقت این کدها می‌توانند مقام‌های شما را ترور کنند.
          </div>
          {CABINET_KEYS.map((key) => (
            <div key={key} className="flex items-center justify-between bg-white/5 rounded-xl px-4 py-3">
              <span className="font-bold">{options[key]?.icon} {options[key]?.name}</span>
              <code className="text-gold-400 font-mono text-lg tracking-widest" dir="ltr">{codes[key]}</code>
            </div>
          ))}
          <button className="btn-primary w-full" onClick={done}>🚀 شروع بازی</button>
        </div>
      )}
    </div>
  )
}

function ManualInput({ onSet }: { onSet: (v: string) => void }) {
  const [v, setV] = useState('')
  return (
    <div className="flex gap-2">
      <input className="input-dark flex-1" placeholder="نوشتن دستی..." value={v} onChange={(e) => setV(e.target.value)} />
      <button className="btn-primary !py-1.5" disabled={!v.trim()} onClick={() => onSet(v.trim())}>ثبت</button>
    </div>
  )
}
