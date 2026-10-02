import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api, errMsg } from '../lib/api'
import { fmt, WEAPON_LABELS } from '../lib/utils'
import { useGameStore } from '../store/gameStore'
import type { TargetPlayer } from '../lib/types'

interface AttackResult {
  ok: boolean
  outcome?: string
  result?: string
  power_ratio?: number
  attacker_loss?: number
  defender_loss?: number
  loot?: number
  score_change?: number
  remaining_attacks?: number
  heal_notes?: string[]
  extra?: string[]
  damage?: number
  summary?: string
  error?: string
}

const BOMB_META: Record<string, string> = {
  fire: '🔥 ۳ روز شهر حریف در آتش',
  space: '🛰 پدافند بی‌اثر + نابودی هواپیماها',
  continental: '☢️ برد جهانی + نابودی ساختمان‌ها',
}

const ARTILLERY_META: Record<string, string> = {
  anti_ground: 'ضد زمینی',
  towed: 'یدک‌کش',
  braveheart: 'بریوهارت',
  defense: 'پدافنددار (+۱۰٪ قدرت مهاجم، دفاع حریف را می‌گیرد)',
}

export default function AttackPage() {
  const { dashboard, fetchDashboard } = useGameStore()
  const [status, setStatus] = useState<any>(null)
  const [weapon, setWeapon] = useState<string | null>(null)
  const [mode, setMode] = useState<'weapon' | 'bomb' | 'artillery'>('weapon')
  const [targets, setTargets] = useState<TargetPlayer[]>([])
  const [target, setTarget] = useState<TargetPlayer | null>(null)
  const [count, setCount] = useState(1)
  const [result, setResult] = useState<AttackResult | null>(null)
  const [bombKey, setBombKey] = useState<string | null>(null)
  const [artilleryKey, setArtilleryKey] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/attack/status/').then(({ data }) => setStatus(data))
  }, [])

  // 🎯 اهداف — برای سلاح انتخابی؛ برد بمب مثل موشک، برد توپخانه قاره‌ای
  useEffect(() => {
    if (mode === 'weapon' && !weapon) return
    if (mode === 'bomb' && !bombKey) return
    if (mode === 'artillery' && !artilleryKey) return
    const rangeWeapon = mode === 'bomb' ? 'missile' : mode === 'artillery' ? 'artillery' : weapon
    api.get('/attack/targets/', { params: { weapon: rangeWeapon } }).then(({ data }) => setTargets(data.targets))
  }, [weapon, bombKey, artilleryKey, mode])

  const fire = async () => {
    if (!target) return
    setBusy(true)
    try {
      let resp
      if (mode === 'bomb') {
        resp = await api.post('/attack/bomb/', { target_id: target.id, bomb: bombKey, count })
      } else if (mode === 'artillery') {
        resp = await api.post('/attack/artillery/', { target_id: target.id, artillery: artilleryKey, count })
      } else {
        resp = await api.post('/attack/', { target_id: target.id, weapon, count })
      }
      setResult(resp.data)
      if (resp.data.ok) {
        // 🏆 celebration دستاورد تازه
        for (const key of resp.data.achievements_unlocked || []) {
          toast(`🏆 دستاورد باز شد: ${key}`, { icon: '🎖️', duration: 5000 })
        }
        api.get('/attack/status/').then(({ data }) => setStatus(data))
        fetchDashboard()
      }
    } catch (e: any) {
      if (e.response?.data) setResult(e.response.data)
      else toast.error(errMsg(e))
    } finally { setBusy(false) }
  }

  const reset = () => {
    setResult(null)
    setTarget(null)
    setWeapon(null)
    setBombKey(null)
    setArtilleryKey(null)
    setMode('weapon')
  }

  const warOff = status && !status.war_active

  return (
    <div className="space-y-4">
      {/* وضعیت */}
      <div className="glass-card p-4">
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div className="section-title">⚔️ پنل جنگ</div>
          <div className="flex flex-wrap gap-2 text-sm">
            <span className="stat-chip">{status?.war_active ? '🟢 جنگ فعال' : '🔴 جنگ غیرفعال'}</span>
            <span className="stat-chip">🎯 حملات: {status?.remaining}/{status?.limit}</span>
            {status?.missile_disabled && <span className="stat-chip !border-danger-500/40 text-danger-400">🚀 موشک از کار افتاده</span>}
            {status?.defense_disabled && <span className="stat-chip !border-danger-500/40 text-danger-400">🛡 پدافند تضعیف شده</span>}
          </div>
        </div>
        {warOff && <p className="text-slate-400 text-sm mt-2">⛔ جنگ جهانی فعال نیست. تا شروع جنگ نمی‌توانید حمله کنید.</p>}
      </div>

      {/* انتخاب نوع حمله */}
      {!weapon && mode === 'weapon' && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Object.entries(WEAPON_LABELS).map(([k, label]) => (
            <button key={k} disabled={warOff}
              onClick={() => setWeapon(k)}
              className="glass-card p-5 text-center hover:border-danger-500/40 active:scale-95 transition disabled:opacity-40">
              <div className="text-3xl mb-1">{label.split(' ')[0]}</div>
              <div className="font-bold text-sm">{label.split(' ').slice(1).join(' ')}</div>
            </button>
          ))}
          <button disabled={warOff} onClick={() => setMode('bomb')}
            className="glass-card p-5 text-center hover:border-danger-500/40 active:scale-95 transition disabled:opacity-40 !border-gold-500/30">
            <div className="text-3xl mb-1">💣</div>
            <div className="font-bold text-sm">بمب‌افکن</div>
          </button>
          <button disabled={warOff} onClick={() => setMode('artillery')}
            className="glass-card p-5 text-center hover:border-danger-500/40 active:scale-95 transition disabled:opacity-40 !border-gold-500/30">
            <div className="text-3xl mb-1">💥</div>
            <div className="font-bold text-sm">توپخانه</div>
          </button>
        </div>
      )}

      {/* انتخاب بمب */}
      {mode === 'bomb' && !bombKey && (
        <div className="glass-card p-4 space-y-2">
          <div className="section-title mb-2">💣 نوع بمب را انتخاب کنید</div>
          <p className="text-slate-400 text-sm">⚠️ هر بمب یک‌بارمصرف است و جزو سهمیه ۴ حمله روزانه محسوب می‌شود.</p>
          {Object.entries(BOMB_META).map(([k, desc]) => (
            <button key={k} onClick={() => setBombKey(k)} className="w-full text-right bg-white/5 hover:bg-white/10 rounded-xl px-4 py-3 transition">
              <span className="font-bold">{k === 'fire' ? '🔥 بمب آتش‌زا' : k === 'space' ? '🛰 بمب فضاپیل' : '☢️ بمب قاره‌ای'}</span>
              <span className="block text-xs text-slate-400 mt-1">{desc}</span>
            </button>
          ))}
          <button className="btn-ghost w-full" onClick={reset}>بازگشت</button>
        </div>
      )}

      {/* انتخاب توپخانه */}
      {mode === 'artillery' && !artilleryKey && (
        <div className="glass-card p-4 space-y-2">
          <div className="section-title mb-2">💥 نوع توپخانه</div>
          <p className="text-slate-400 text-sm">برد: فقط قاره خودتان | تخصص: نابودی تانک‌های حریف</p>
          {Object.entries(ARTILLERY_META).map(([k, desc]) => (
            <button key={k} onClick={() => setArtilleryKey(k)} className="w-full text-right bg-white/5 hover:bg-white/10 rounded-xl px-4 py-3 transition">
              <span className="font-bold">{k}</span>
              <span className="block text-xs text-slate-400 mt-1">{desc}</span>
            </button>
          ))}
          <button className="btn-ghost w-full" onClick={reset}>بازگشت</button>
        </div>
      )}

      {/* انتخاب هدف */}
      {(weapon || bombKey || artilleryKey) && !target && (
        <div className="glass-card p-4">
          <div className="section-title mb-3">🎯 انتخاب هدف</div>
          <div className="space-y-1.5 max-h-96 overflow-y-auto">
            {targets.length === 0 && <p className="text-slate-500 text-sm">هیچ هدفی در برد این سلاح نیست.</p>}
            {targets.map((t) => (
              <button key={t.id} onClick={() => setTarget(t)}
                className="w-full flex items-center justify-between bg-white/5 hover:bg-white/10 rounded-xl px-4 py-3 transition">
                <span className="font-bold">{t.emoji} {t.name}</span>
                <span className="text-xs text-slate-400">🛡 {fmt(t.defense)} | 🏆 {fmt(t.score)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* شلیک */}
      {target && !result && (
        <div className="glass-card p-6 space-y-4">
          <h3 className="section-title text-lg">
            {mode === 'bomb' ? '💣' : mode === 'artillery' ? '💥' : WEAPON_LABELS[weapon || '']?.split(' ')[0]} حمله به {target.emoji} {target.name}
          </h3>
          <div>
            <label className="text-sm text-slate-400">تعداد: {fmt(count)} (سرور موجودی را اعتبارسنجی می‌کند)</label>
            <input type="range" min={1} max={200} value={count}
              onChange={(e) => setCount(+e.target.value)} className="w-full accent-danger-500" />
            <div className="flex flex-wrap gap-1.5 mt-1">
              {[1, 5, 10, 25, 50, 100, 200].map((n) => (
                <button key={n} onClick={() => setCount(n)} className="btn-ghost !px-3 !py-1 text-xs">{n}</button>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button className="btn-ghost flex-1" onClick={() => setTarget(null)}>انصراف</button>
            <button className="btn-danger flex-1 animate-glow" onClick={fire} disabled={busy}>
              {busy ? '...' : '🚀 شلیک!'}
            </button>
          </div>
        </div>
      )}

      {/* نتیجه نبرد — cinematic */}
      {result && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
             onClick={reset}>
          <div className={`glass-card p-8 w-full max-w-md text-center space-y-4 animate-glow
            ${result.result === 'victory' ? '!border-success-500/50' : result.result === 'defeat' ? '!border-danger-500/50' : '!border-gold-500/50'}`}
            onClick={(e) => e.stopPropagation()}>
            <div className="text-7xl">
              {result.result === 'victory' ? '🏆' : result.result === 'narrow_victory' ? '⚡' :
               result.result === 'narrow_defeat' ? '💔' : result.result === 'defeat' ? '💀' : '📋'}
            </div>
            <h3 className="text-2xl font-black">{result.outcome || (result.ok ? 'گزارش' : result.error)}</h3>
            {result.power_ratio != null && (
              <div className="text-sm text-slate-400">📊 نسبت قدرت: {result.power_ratio}</div>
            )}
            <div className="grid grid-cols-2 gap-2 text-sm">
              {result.attacker_loss != null && <div className="bg-white/5 rounded-xl p-3">💀 تلفات شما: <b>{fmt(result.attacker_loss)}</b></div>}
              {result.defender_loss != null && <div className="bg-white/5 rounded-xl p-3">⚔️ تلفات حریف: <b>{fmt(result.defender_loss)}</b></div>}
              {result.damage != null && <div className="bg-white/5 rounded-xl p-3">💥 آسیب: <b>{fmt(result.damage)}</b></div>}
              {result.loot != null && <div className="bg-white/5 rounded-xl p-3">💰 غنیمت: <b>{fmt(result.loot)}</b></div>}
              {result.score_change != null && (
                <div className="bg-white/5 rounded-xl p-3">🏆 امتیاز: <b className={result.score_change >= 0 ? 'text-success-400' : 'text-danger-400'}>
                  {result.score_change >= 0 ? '+' : ''}{fmt(result.score_change)}</b></div>
              )}
            </div>
            {result.heal_notes?.map((h, i) => <p key={i} className="text-success-400 text-sm">✚ {h}</p>)}
            {result.extra?.map((h, i) => <p key={i} className="text-slate-300 text-sm">{h}</p>)}
            {result.summary && <p className="text-slate-500 text-xs">{result.summary}</p>}
            <button className="btn-primary w-full" onClick={reset}>بازگشت به پنل جنگ</button>
          </div>
        </div>
      )}
    </div>
  )
}
