import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api, errMsg } from '../lib/api'
import { CATEGORY_LABELS, fmt } from '../lib/utils'
import { useGameStore } from '../store/gameStore'
import type { UnionInfo } from '../lib/types'
import type { ShopItem } from '../lib/types'

export default function UnionsPage() {
  const { fetchDashboard, dashboard } = useGameStore()
  const [data, setData] = useState<{ unions: UnionInfo[]; my_union: UnionInfo | null; pending_requests: any[] } | null>(null)
  const [metric, setMetric] = useState<'name' | 'wealth' | 'production' | 'power'>('name')
  const [createName, setCreateName] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [amount, setAmount] = useState(0)
  const [donateTo, setDonateTo] = useState<number | null>(null)
  const [donateAmount, setDonateAmount] = useState(0)
  // اهدای تجهیز
  const [itemTo, setItemTo] = useState<{ id: number; name: string } | null>(null)
  const [equipCatalog, setEquipCatalog] = useState<Record<string, ShopItem[]>>({})
  const [equipCategory, setEquipCategory] = useState<string | null>(null)
  const [equipItem, setEquipItem] = useState<ShopItem | null>(null)
  const [equipQty, setEquipQty] = useState(1)
  const [busy, setBusy] = useState(false)

  const load = () => api.get('/unions/', { params: { metric } }).then(({ data }) => setData(data))
  useEffect(() => { load() }, [metric])

  const act = async (payload: Record<string, unknown>, successMsg?: string) => {
    setBusy(true)
    try {
      const { data: res } = await api.post('/unions/', payload)
      if (res.ok) {
        if (successMsg) toast.success(successMsg)
        load()
        fetchDashboard()
        return true
      }
      toast.error(res.error)
      return false
    } catch (e) {
      toast.error(errMsg(e))
      return false
    } finally { setBusy(false) }
  }

  const my = data?.my_union

  const openItemDonation = async (m: { id: number; name: string }) => {
    setItemTo(m)
    setEquipCategory(null)
    setEquipItem(null)
    if (Object.keys(equipCatalog).length === 0) {
      try {
        const { data: cat } = await api.get('/shop/catalog/')
        setEquipCatalog(cat.categories)
      } catch { /* ignore */ }
    }
  }

  const sendItemDonation = async () => {
    if (!itemTo || !equipItem || !my) return
    const ok = await act({
      action: 'donate_item', union_id: my.id, recipient_id: itemTo.id,
      category: equipCategory, item: equipItem.key, count: equipQty,
    }, `📦 ${equipQty} عدد ${equipItem.name} اهدا شد`)
    if (ok) { setItemTo(null); setEquipItem(null); setEquipQty(1) }
  }

  return (
    <div className="space-y-4">
      <div className="glass-card p-4 flex items-center justify-between">
        <h1 className="section-title text-xl">🤝 اتحادها</h1>
        {!my && <button className="btn-primary !py-2" onClick={() => setShowCreate(true)}>🆕 ساخت اتحاد</button>}
      </div>

      {/* اتحاد من */}
      {my && (
        <div className="glass-card p-4 space-y-3 !border-primary-500/30">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-black">🏛 {my.name}</div>
              <div className="text-xs text-slate-400">🆔 {my.union_id} | 👑 {my.owner_name}</div>
            </div>
            <div className="text-left">
              <div className="text-gold-400 font-black">⭐ لول {my.level}</div>
              <div className="text-xs text-slate-400">👥 {my.members_count}/{my.capacity}</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <span className="stat-chip">🏦 خزانه: <b>{fmt(my.treasury)}</b></span>
            <span className="stat-chip">🎁 سقف اهدا: {fmt(my.donation_limit)}</span>
            <span className="stat-chip">📦 سقف تجهیز: ۱۰۰</span>
          </div>

          {/* درخواست‌ها (مالک) */}
          {my.is_owner && data!.pending_requests.length > 0 && (
            <div className="bg-gold-500/10 border border-gold-500/30 rounded-xl p-3">
              <div className="font-bold text-sm text-gold-400 mb-2">📥 درخواست‌های عضویت ({data!.pending_requests.length})</div>
              {data!.pending_requests.map((r) => (
                <div key={r.id} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2 mb-1 text-sm">
                  <span>{r.name} — {r.country}</span>
                  <div className="flex gap-1">
                    <button className="btn-primary !px-3 !py-1 text-xs" onClick={() => act({ action: 'approve', request_id: r.id }, 'تایید شد')}>✅</button>
                    <button className="btn-ghost !px-3 !py-1 text-xs" onClick={() => act({ action: 'reject', request_id: r.id }, 'رد شد')}>❌</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* خزانه (مالک) */}
          {my.is_owner && (
            <div className="bg-white/5 rounded-xl p-3 space-y-2">
              <div className="font-bold text-sm">🏦 مدیریت خزانه</div>
              <div className="flex gap-2">
                <input type="number" className="input-dark" placeholder="مقدار سکه" value={amount || ''} onChange={(e) => setAmount(+e.target.value)} />
                <button className="btn-primary !px-4" disabled={busy} onClick={() => act({ action: 'deposit', union_id: my.id, amount }, 'واریز شد')}>واریز</button>
                <button className="btn-ghost !px-4" disabled={busy} onClick={() => act({ action: 'withdraw', union_id: my.id, amount }, 'برداشت شد')}>برداشت</button>
              </div>
              <div className="flex gap-2">
                <button className="btn-primary !px-4 text-sm" disabled={busy}
                  onClick={() => act({ action: 'upgrade', union_id: my.id }, 'اتحاد ارتقا یافت!')}>
                  ⬆️ ارتقا ({fmt(50000 * my.level)} سکه)
                </button>
                <button className="btn-danger !px-4 text-sm" disabled={busy}
                  onClick={() => { if (confirm('اتحاد حذف شود؟')) act({ action: 'delete', union_id: my.id }, 'حذف شد') }}>
                  🗑 حذف اتحاد
                </button>
              </div>
            </div>
          )}

          {/* اهدای تجهیز */}
          {my.members.length > 1 && (
            <div className="bg-white/5 rounded-xl p-3 space-y-2">
              <div className="font-bold text-sm">📦 اهدای تجهیزات (سقف ۱۰۰ عدد — هر ۴۸ ساعت)</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {my.members.filter((m) => m.id !== (dashboard?.player?.id ?? -1)).map((m) => (
                  <button key={m.id} onClick={() => openItemDonation(m)}
                    className={`p-2 rounded-lg text-sm text-right transition ${itemTo?.id === m.id ? 'bg-gold-500/20 border border-gold-500/40' : 'bg-white/5'}`}>
                    📦 {m.name}
                  </button>
                ))}
              </div>
              {itemTo && (
                <div className="space-y-2 bg-night-900/60 rounded-xl p-3">
                  <div className="text-xs text-slate-400">اهداد به: <b className="text-slate-200">{itemTo.name}</b></div>
                  {!equipCategory ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                      {Object.keys(equipCatalog).filter((c) => equipCatalog[c].some((i) => (i.count ?? 0) > 0 || true)).slice(0, 9).map((c) => (
                        <button key={c} className="btn-ghost !py-1.5 text-xs" onClick={() => setEquipCategory(c)}>
                          {CATEGORY_LABELS[c] || c}
                        </button>
                      ))}
                    </div>
                  ) : !equipItem ? (
                    <div className="grid grid-cols-2 gap-1.5 max-h-48 overflow-y-auto">
                      {(equipCatalog[equipCategory] || []).map((i) => (
                        <button key={i.key} className="btn-ghost !py-1.5 text-xs" onClick={() => setEquipItem(i)}>
                          {i.icon} {i.name}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex gap-2 items-center">
                      <input type="number" min={1} max={100} className="input-dark" value={equipQty}
                        onChange={(e) => setEquipQty(Math.max(1, Math.min(100, +e.target.value)))} />
                      <button className="btn-primary !px-4" disabled={busy} onClick={sendItemDonation}>اهدا</button>
                      <button className="btn-ghost !px-3" onClick={() => setEquipItem(null)}>🔙</button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* اهدا */}
          {my.members.length > 1 && (
            <div className="bg-white/5 rounded-xl p-3 space-y-2">
              <div className="font-bold text-sm">🎁 اهدای سکه به هم‌اتحدی (هر ۴۸ ساعت یک‌بار)</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {my.members.filter((m) => m.id !== (dashboard?.player?.id ?? -1)).map((m) => (
                  <button key={m.id} onClick={() => setDonateTo(donateTo === m.id ? null : m.id)}
                    className={`p-2 rounded-lg text-sm text-right transition ${donateTo === m.id ? 'bg-primary-500/20 border border-primary-500/40' : 'bg-white/5'}`}>
                    {m.name}
                    <span className="block text-xs text-slate-500">🏆 {fmt(m.score)}</span>
                  </button>
                ))}
              </div>
              {donateTo && (
                <div className="flex gap-2">
                  <input type="number" className="input-dark" placeholder="سکه" value={donateAmount || ''} onChange={(e) => setDonateAmount(+e.target.value)} />
                  <button className="btn-primary !px-4" disabled={busy}
                    onClick={() => act({ action: 'donate_credit', union_id: my.id, recipient_id: donateTo, amount: donateAmount }, 'اهدا شد 🎁')}>
                    اهدا
                  </button>
                </div>
              )}
            </div>
          )}

          {/* اعضا */}
          <div>
            <div className="font-bold text-sm mb-2">👥 اعضا</div>
            <div className="space-y-1">
              {my.members.map((m) => (
                <div key={m.id} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2 text-sm">
                  <span>{m.name} <span className="text-slate-500 text-xs">{m.country}</span></span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs">🏆 {fmt(m.score)}</span>
                    {my.is_owner && m.id !== my.owner_id && (
                      <button className="text-danger-400 text-xs" onClick={() => { if (confirm('اخراج شود؟')) act({ action: 'kick', union_id: my.id, member_id: m.id }, 'اخراج شد') }}>اخراج</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button className="btn-ghost w-full" disabled={busy} onClick={() => act({ action: 'leave', union_id: my.id }, 'خارج شدید')}>
            🚪 خروج از اتحاد
          </button>
        </div>
      )}

      {/* رتبه‌بندی */}
      <div className="glass-card p-4">
        <div className="flex gap-2 mb-3 overflow-x-auto">
          {([['name', 'همه'], ['wealth', '💰 ثروت'], ['production', '🏭 تولید'], ['power', '⚔️ قدرت']] as const).map(([k, label]) => (
            <button key={k} onClick={() => setMetric(k)}
              className={`px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition ${metric === k ? 'bg-primary-500/20 text-primary-300' : 'bg-white/5 text-slate-400'}`}>
              {label}
            </button>
          ))}
        </div>
        <div className="space-y-1.5">
          {data?.unions.length === 0 && <p className="text-slate-500 text-sm">هنوز اتحادی وجود ندارد.</p>}
          {data?.unions.map((u) => (
            <div key={u.id} className="flex items-center justify-between bg-white/5 rounded-xl px-4 py-3">
              <div>
                <span className="font-bold">{u.name}</span>
                <span className="text-xs text-slate-500 block">👑 {u.owner_name}</span>
              </div>
              <div className="text-left text-sm">
                <div>⭐ {u.level} | 👥 {u.members_count}/{u.capacity}</div>
                <div className="text-gold-400 text-xs">🏦 {fmt(u.treasury)}</div>
              </div>
              {!my && (
                <button className="btn-ghost !py-1 text-xs" onClick={() => act({ action: 'join_request', union_id: u.id }, 'درخواست ارسال شد')}>
                  درخواست
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ساخت اتحاد */}
      {showCreate && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setShowCreate(false)}>
          <div className="glass-card p-6 w-full max-w-sm space-y-3" onClick={(e) => e.stopPropagation()}>
            <h3 className="section-title text-lg">🆕 ساخت اتحاد</h3>
            <input className="input-dark" placeholder="نام اتحاد (۳ تا ۲۰ کاراکتر)" value={createName} onChange={(e) => setCreateName(e.target.value)} />
            <div className="flex gap-2">
              <button className="btn-ghost flex-1" onClick={() => setShowCreate(false)}>انصراف</button>
              <button className="btn-primary flex-1" disabled={busy || createName.trim().length < 3}
                onClick={async () => { if (await act({ action: 'create', name: createName.trim() }, 'اتحاد ساخته شد!')) setShowCreate(false) }}>
                ساخت
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
