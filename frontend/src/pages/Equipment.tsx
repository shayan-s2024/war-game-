import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../lib/api'
import { CATEGORY_LABELS, fmt } from '../lib/utils'

interface EquipItem {
  key: string; name: string; icon: string; qty: number
  cap?: number | null; q?: number | null; power?: number | null
}

export default function Equipment() {
  const [categories, setCategories] = useState<Record<string, EquipItem[]>>({})
  const [active, setActive] = useState('tank')

  useEffect(() => {
    api.get('/equipment/').then(({ data }) => {
      setCategories(data.categories)
      // اولین دسته غیرخالی را انتخاب کن
      const first = Object.keys(data.categories).find((k) => data.categories[k].some((i: EquipItem) => i.qty > 0))
      if (first) setActive(first)
    })
  }, [])

  const items = categories[active] || []
  const owned = items.filter((i) => i.qty > 0)

  // داده نمودار: قدرت کل هر آیتم (qty × power)
  const chartData = owned
    .map((i) => ({ name: `${i.icon} ${i.name}`, value: (i.power || 0) * i.qty }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)

  const COLORS = ['#38bdf8', '#fbbf24', '#ef4444', '#22c55e', '#a78bfa', '#f472b6', '#34d399', '#f97316']

  return (
    <div className="space-y-4">
      <div className="glass-card p-4">
        <h1 className="section-title text-xl">📦 تجهیزات من</h1>
        <p className="text-slate-400 text-sm mt-1">موجودی کامل ارتش، پدافند، اقتصاد و ساختمان‌ها — با کیفیت و سقف هر قلم.</p>
      </div>

      {/* دسته‌بندی */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {Object.keys(categories).filter((c) => categories[c].some((i) => i.qty > 0)).map((c) => (
          <button key={c} onClick={() => setActive(c)}
            className={`px-4 py-2 rounded-xl text-sm whitespace-nowrap font-bold transition ${
              active === c ? 'bg-primary-500/20 text-primary-300 border border-primary-500/40' : 'bg-white/5 text-slate-400'
            }`}>
            {CATEGORY_LABELS[c] || c}
          </button>
        ))}
        {Object.keys(categories).every((c) => !categories[c].some((i) => i.qty > 0)) && (
          <p className="text-slate-500 text-sm">هنوز تجهیزی ندارید — از 🛒 فروشگاه خرید کنید.</p>
        )}
      </div>

      {/* نمودار قدرت — فقط برای دسته‌های نظامی */}
      {chartData.length > 0 && (i18n_isMilitary(active)) && (
        <div className="glass-card p-4">
          <div className="section-title mb-3">📊 توزیع قدرت تخریب — برترین اقلام</div>
          <div style={{ height: 240 }} dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" width={140} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,.1)', borderRadius: 12 }}
                  labelStyle={{ color: '#e2e8f0' }}
                  formatter={(v: any) => [fmt(Number(v)), 'قدرت کل']}
                />
                <Bar dataKey="value" radius={[0, 8, 8, 0]}>
                  {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* آیتم‌ها */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
        {owned.map((i) => (
          <div key={i.key} className="glass-card p-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm">{i.icon} {i.name}</span>
              <span className="text-gold-400 font-black tabular-nums">{fmt(i.qty)}</span>
            </div>
            <div className="flex flex-wrap gap-1 mt-1.5 text-[11px] text-slate-400">
              {i.q != null && <span className="stat-chip !px-2 !py-0.5">⚖️ کیفیت {i.q}</span>}
              {i.power != null && <span className="stat-chip !px-2 !py-0.5">💥 {fmt(i.power)}</span>}
              {i.cap != null && (
                <span className="stat-chip !px-2 !py-0.5">
                  🚫 {fmt(i.qty)}/{fmt(i.cap)}
                </span>
              )}
            </div>
            {/* progress bar نسبت به سقف */}
            {i.cap != null && i.cap > 0 && (
              <div className="h-1.5 rounded-full bg-white/10 mt-2 overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-l from-primary-500 to-gold-400 transition-all"
                  style={{ width: `${Math.min(100, (i.qty / i.cap) * 100)}%` }} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function i18n_isMilitary(category: string): boolean {
  return ['tank', 'fighter', 'helicopter', 'drone', 'naval', 'submarine', 'carrier',
          'ground', 'artillery', 'missile'].includes(category)
}
