import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api, errMsg } from '../lib/api'
import { CONTINENT_LABELS, fmt, timeAgo } from '../lib/utils'
import type { BaseInfo, ContinentInfo, CountryInfo } from '../lib/types'

interface BasesData {
  my_bases: BaseInfo[]
  world_bases: BaseInfo[]
  permission_requests_in: { id: number; requester: string; country: string; expires_at: string }[]
  permission_requests_out: { id: number; country: string; status: string; expires_at: string }[]
  price: number
  build_seconds: number
}

export default function BasesPage() {
  const [data, setData] = useState<BasesData | null>(null)
  const [continents, setContinents] = useState<ContinentInfo[]>([])
  const [countries, setCountries] = useState<Record<string, CountryInfo[]>>({})
  const [continent, setContinent] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = () => api.get('/bases/').then(({ data }) => setData(data))
  useEffect(() => {
    load()
    api.get('/countries/').then(({ data }) => {
      setContinents(data.continents)
      setCountries(data.countries)
    })
  }, [])

  const build = async (country: string) => {
    setBusy(true)
    try {
      const { data: res } = await api.post('/bases/', { action: 'build', country })
      if (res.ok) {
        toast.success(res.pending_permission
          ? '📨 درخواست مجوز برای مالک کشور ارسال شد (۵ دقیقه اعتبار)'
          : '🏗️ ساخت پایگاه شروع شد — ۳۰ دقیقه طول می‌کشد')
        load()
      } else toast.error(res.error)
    } catch (e) { toast.error(errMsg(e)) } finally { setBusy(false) }
  }

  const respond = async (id: number, approve: boolean) => {
    try {
      await api.post('/bases/', { action: approve ? 'approve_permission' : 'deny_permission', request_id: id })
      toast.success(approve ? '✅ مجوز داده شد' : '❌ رد شد')
      load()
    } catch (e) { toast.error(errMsg(e)) }
  }

  return (
    <div className="space-y-4">
      <div className="glass-card p-4">
        <h1 className="section-title text-xl">🏕️ پایگاه‌های نظامی</h1>
        <p className="text-slate-400 text-sm mt-1">
          پایگاه در قاره دیگر = باز شدن برد حملات به آن قاره. هزینه: {fmt(data?.price || 20000)} سکه | ساخت: ۳۰ دقیقه
        </p>
      </div>

      {/* درخواست‌های ورودی */}
      {data?.permission_requests_in.length ? (
        <div className="glass-card p-4 !border-gold-500/40 space-y-2">
          <div className="section-title text-gold-400">📥 درخواست ساخت پایگاه در کشور شما</div>
          {data.permission_requests_in.map((r) => (
            <div key={r.id} className="flex items-center justify-between bg-white/5 rounded-xl px-4 py-3">
              <span className="text-sm"><b>{r.requester}</b> می‌خواهد در <b>{r.country}</b> پایگاه بسازد</span>
              <div className="flex gap-1">
                <button className="btn-primary !px-3 !py-1 text-xs" onClick={() => respond(r.id, true)}>✅ اجازه</button>
                <button className="btn-ghost !px-3 !py-1 text-xs" onClick={() => respond(r.id, false)}>❌ رد</button>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* پایگاه‌های من */}
      <div className="glass-card p-4">
        <div className="section-title mb-3">🏕️ پایگاه‌های من ({data?.my_bases.length || 0})</div>
        {data?.my_bases.length === 0 && <p className="text-slate-500 text-sm">هنوز پایگاهی ندارید.</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {data?.my_bases.map((b) => (
            <div key={b.id} className={`rounded-xl px-4 py-3 flex items-center justify-between ${b.is_ready ? 'bg-success-500/10' : 'bg-gold-500/10'}`}>
              <div>
                <div className="font-bold">{b.country_emoji} {b.country}</div>
                <div className="text-xs text-slate-400">{b.is_ready ? '✅ آماده عملیات' : `⏳ در حال ساخت — ${new Date(b.ready_at).toLocaleTimeString('fa-IR')}`}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ساخت پایگاه جدید */}
      <div className="glass-card p-4">
        <div className="section-title mb-3">🏗️ ساخت پایگاه جدید</div>
        {!continent ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {continents.map((c) => (
              <button key={c.key} onClick={() => setContinent(c.key)} className="btn-ghost">
                {c.flag} {c.name}
              </button>
            ))}
          </div>
        ) : (
          <>
            <button className="btn-ghost mb-3 text-sm" onClick={() => setContinent(null)}>🔙 بازگشت به قاره‌ها</button>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 max-h-72 overflow-y-auto">
              {(countries[continent] || []).map((c) => (
                <button key={c.name} disabled={busy} onClick={() => build(c.name)}
                  className="text-right px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm transition">
                  {c.emoji} {c.name}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* پایگاه‌های جهان */}
      <div className="glass-card p-4">
        <div className="section-title mb-3">🌍 پایگاه‌های فعال جهان</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-60 overflow-y-auto">
          {data?.world_bases.map((b) => (
            <div key={b.id} className="bg-white/5 rounded-lg px-3 py-2 text-sm flex justify-between">
              <span>{b.country_emoji} {b.country}</span>
              <span className="text-xs text-slate-500">{b.owner_name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
