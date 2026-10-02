import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api, errMsg } from '../lib/api'
import { CATEGORY_LABELS, fmt } from '../lib/utils'
import type { ShopItem } from '../lib/types'

const CATEGORY_ORDER = ['mine', 'economic', 'defense', 'building', 'tank', 'fighter',
  'helicopter', 'drone', 'naval', 'submarine', 'carrier', 'ground', 'artillery',
  'hacker', 'bomb', 'pilot']

export default function ShopPage() {
  const [categories, setCategories] = useState<Record<string, ShopItem[]>>({})
  const [active, setActive] = useState('mine')
  const [sanctionPct, setSanctionPct] = useState(0)
  const [buying, setBuying] = useState<ShopItem | null>(null)
  const [qty, setQty] = useState(1)
  const [busy, setBusy] = useState(false)
  const [tomanItems, setTomanItems] = useState<Record<string, { coins: number; price_toman: number; price_text: string }>>({})
  const [showToman, setShowToman] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [pkg, setPkg] = useState('60000')

  const load = () => api.get('/shop/catalog/').then(({ data }) => {
    setCategories(data.categories)
    setSanctionPct(data.sanction_penalty)
    setTomanItems(data.toman_items)
  })

  useEffect(() => { load() }, [])

  // Keep every category predictable and make price progression easy to scan.
  const items = [...(categories[active] || [])].sort((a, b) => a.price - b.price || a.name.localeCompare(b.name, 'fa'))

  const buy = async () => {
    if (!buying) return
    setBusy(true)
    try {
      const { data } = await api.post('/shop/buy/', { category: active, item: buying.key, count: qty })
      toast.success(`✅ ${data.units} عدد ${data.item_name} خریداری شد — ${fmt(data.total_price)} سکه`)
      // 🏆 celebration دستاورد تازه
      for (const key of data.achievements_unlocked || []) {
        toast(`🏆 دستاورد باز شد: ${key}`, { icon: '🎖️', duration: 5000 })
      }
      setBuying(null)
      load()
    } catch (e) {
      toast.error(errMsg(e))
    } finally { setBusy(false) }
  }

  const submitReceipt = async () => {
    if (!file) return toast.error('رسید را انتخاب کنید')
    const form = new FormData()
    form.append('package', pkg)
    form.append('receipt', file)
    try {
      await api.post('/payments/request/', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      toast.success('رسید ثبت شد — پس از تایید ادمین سکه اضافه می‌شود')
      setShowToman(false)
    } catch (e) {
      toast.error(errMsg(e))
    }
  }

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 flex items-center justify-between">
        <div>
          <h1 className="section-title text-xl">🛒 فروشگاه</h1>
          {sanctionPct > 0 && (
            <p className="text-gold-400 text-sm mt-1">⚠️ تحریم فعال — همه قیمت‌ها {sanctionPct}٪ جریمه دارند</p>
          )}
        </div>
        <button className="btn-ghost" onClick={() => setShowToman(!showToman)}>💳 خرید با تومان</button>
      </div>

      {showToman && (
        <div className="glass-card p-4 space-y-3">
          <h2 className="section-title">💳 بسته‌های سکه (پرداخت واقعی)</h2>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(tomanItems).map(([key, item]) => (
              <button key={key} onClick={() => setPkg(key)}
                className={`p-3 rounded-xl text-right transition ${pkg === key ? 'bg-primary-500/20 border border-primary-500/40' : 'bg-white/5'}`}>
                <div className="font-bold">{fmt(item.coins)} سکه</div>
                <div className="text-xs text-slate-400">{item.price_text}</div>
              </button>
            ))}
          </div>
          <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-slate-400 file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:bg-primary-600 file:text-white" />
          <button className="btn-primary w-full" onClick={submitReceipt}>ارسال رسید</button>
          <p className="text-xs text-slate-500">پس از واریز به کارت اعلامی، رسید را بارگذاری کنید. تایید نهایی با ادمین است.</p>
        </div>
      )}

      {/* دسته‌بندی */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {CATEGORY_ORDER.filter((c) => categories[c]).map((c) => (
          <button key={c} onClick={() => setActive(c)}
            className={`px-4 py-2 rounded-xl text-sm whitespace-nowrap transition font-bold ${
              active === c ? 'bg-primary-500/20 text-primary-300 border border-primary-500/40' : 'bg-white/5 text-slate-400 hover:bg-white/10'
            }`}>
            {CATEGORY_LABELS[c] || c}
          </button>
        ))}
      </div>

      {/* آیتم‌ها */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {items.map((item) => (
          <div key={item.key} className="glass-card p-4 flex flex-col gap-2 hover:border-primary-500/30 transition">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-bold">{item.icon} {item.name}</div>
                {item.q != null && (
                  <div className="text-xs text-slate-400">⚖️ کیفیت: {item.q}</div>
                )}
              </div>
              {item.power != null && <span className="text-xs text-danger-400">💥 {fmt(item.power)}</span>}
            </div>
            <div className="text-xs text-slate-400 space-y-0.5">
              {item.daily_profit != null && <div>📈 سود روزانه: {fmt(item.daily_profit)} سکه</div>}
              {item.count > 1 && <div>📦 هر خرید: {fmt(item.count)} عدد</div>}
              {item.cap != null && <div>🚫 سقف: {fmt(item.cap)} عدد</div>}
              {item.description && <div className="text-slate-500">📝 {item.description}</div>}
              {item.fighters && <div className="text-slate-500">✈️ برای: {item.fighters.slice(0, 3).join('، ')}...</div>}
            </div>
            <div className="flex items-center justify-between mt-auto pt-2">
              <div className="font-black text-gold-400">{fmt(item.price)} 🪙</div>
              <button className="btn-primary !py-1.5 text-sm" onClick={() => { setBuying(item); setQty(1) }}>
                خرید
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* مودال خرید */}
      {buying && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setBuying(null)}>
          <div className="glass-card p-6 w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title text-lg">{buying.icon} خرید {buying.name}</h3>
            <div className="text-sm text-slate-400 space-y-1">
              <div>قیمت هر واحد: <b className="text-gold-400">{fmt(buying.price)}</b> سکه</div>
              {buying.count > 1 && <div>هر واحد شامل <b>{fmt(buying.count)}</b> عدد تجهیز است</div>}
            </div>
            <div>
              <label className="text-sm text-slate-400">تعداد: {fmt(qty)}</label>
              <input type="range" min={1} max={100} value={qty} onChange={(e) => setQty(+e.target.value)} className="w-full accent-primary-500" />
              <div className="flex gap-2 mt-1">
                {[1, 5, 10, 25, 50, 100].map((n) => (
                  <button key={n} onClick={() => setQty(n)} className="btn-ghost !px-3 !py-1 text-xs">{n}</button>
                ))}
              </div>
            </div>
            <div className="text-lg font-black">
              مجموع: <span className="text-gold-400">{fmt(buying.price * qty)}</span> سکه
            </div>
            <div className="flex gap-2">
              <button className="btn-ghost flex-1" onClick={() => setBuying(null)}>انصراف</button>
              <button className="btn-primary flex-1" onClick={buy} disabled={busy}>تایید خرید</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
