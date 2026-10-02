import { useEffect, useState } from 'react'
import { BIOMES, GOVS, type BiomeId, type CountryProfile, type Stats } from './data'

export const fmt = (n: number) => new Intl.NumberFormat('fa-IR').format(Math.round(n))
export const fmtCompact = (n: number) => {
  if (n >= 1e9) return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 1 }).format(n / 1e9) + ' میلیارد'
  if (n >= 1e6) return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 1 }).format(n / 1e6) + ' میلیون'
  if (n >= 1e3) return new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 1 }).format(n / 1e3) + ' هزار'
  return fmt(n)
}

function Stat({ icon, label, value, tone }: { icon: string; label: string; value: string; tone?: 'gold' | 'cyan' | 'danger' }) {
  return (
    <div className="stat-tile">
      <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
        <span>{icon}</span>
        {label}
      </div>
      <div className={`mt-1 text-lg font-black tabular-nums ${tone === 'gold' ? 'text-[var(--gold)]' : tone === 'danger' ? 'text-[var(--danger)]' : 'text-[var(--cyan)]'}`}>{value}</div>
    </div>
  )
}

function Bar({ value, max = 100, color = 'var(--cyan)' }: { value: number; max?: number; color?: string }) {
  return (
    <div className="h-1.5 rounded-full bg-white/8 overflow-hidden">
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(100, (value / max) * 100)}%`, background: color }} />
    </div>
  )
}

export function EconomyPanel({ stats, color }: { stats: Stats; color: string }) {
  const days = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']
  const base = stats.income.total
  const series = days.map((_, i) => base * (0.82 + 0.1 * Math.sin(i * 1.3 + 0.6) + i * 0.025))
  const maxV = Math.max(...series)
  const share = stats.income.total ? (stats.income.mines / stats.income.total) * 100 : 0
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <Stat icon="💰" label="خزانه" value={fmtCompact(stats.treasury)} tone="gold" />
        <Stat icon="📈" label="سود روزانه" value={fmtCompact(stats.daily_profit)} />
        <Stat icon="👥" label="جمعیت" value={fmtCompact(stats.population)} />
        <Stat icon="🏆" label="امتیاز" value={fmt(stats.score)} tone="gold" />
      </div>

      <div>
        <div className="section-sub">درآمد هفتگی</div>
        <div className="flex items-end gap-1.5 h-24 mt-2">
          {series.map((v, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div
                className="w-full rounded-t-md transition-all duration-700"
                style={{
                  height: `${(v / maxV) * 100}%`,
                  background: `linear-gradient(180deg, ${color}, rgba(255,255,255,0.06))`,
                  boxShadow: `0 0 14px ${color}33`,
                }}
              />
              <span className="text-[10px] text-slate-500">{days[i]}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex justify-between text-xs text-slate-400 mb-1.5">
          <span>⛏️ معادن {fmtCompact(stats.income.mines)}</span>
          <span>🏭 اقتصادی {fmtCompact(stats.income.economic)}</span>
        </div>
        <Bar value={share} color="linear-gradient(90deg, var(--gold), var(--cyan))" />
      </div>

      {(['mines', 'economic', 'buildings'] as const).map((k) => (
        <div key={k}>
          <div className="section-sub">{k === 'mines' ? 'معادن' : k === 'economic' ? 'زیرساخت اقتصادی' : 'ساختمان‌ها'}</div>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {Object.entries(stats.assets[k]).map(([name, n]) => (
              <span key={name} className="chip-sm">
                {name} <b className="text-[var(--cyan)]">×{fmt(n)}</b>
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export function ArmyPanel({ stats, bonus }: { stats: Stats; bonus: { atk: number; def: number } }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <Stat icon="💥" label="قدرت حمله" value={fmt(stats.army.attack)} tone="danger" />
        <Stat icon="🛡" label="قدرت دفاع" value={fmt(stats.army.defense)} />
      </div>
      {(bonus.atk > 0 || bonus.def > 0) && (
        <div className="rounded-xl border border-[var(--gold)]/25 bg-[var(--gold)]/5 px-3 py-2 text-xs text-[var(--gold)]">
          سازه‌های مستقرشده در نقشه: حمله +{fmt(bonus.atk)} · دفاع +{fmt(bonus.def)}
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        <Stat icon="✈️" label="جنگنده آماده" value={fmt(stats.army.ready_fighters)} />
        <Stat icon="🚁" label="بالگرد آماده" value={fmt(stats.army.ready_helicopters)} />
      </div>
      <div className="space-y-3">
        {Object.entries(stats.army.categories).map(([name, c]) => (
          <div key={name}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-200">{name}</span>
              <span className="text-slate-400">
                {fmt(c.count)} · کیفیت {fmt(c.quality)}٪
              </span>
            </div>
            <Bar value={c.quality} color={c.quality > 80 ? 'var(--cyan)' : c.quality > 65 ? 'var(--gold)' : 'var(--danger)'} />
          </div>
        ))}
      </div>
      <div>
        <div className="section-sub">پایگاه‌ها</div>
        <div className="mt-2 space-y-1.5">
          {stats.bases.map((b) => (
            <div key={b.id} className="flex items-center justify-between rounded-lg bg-white/4 border border-white/6 px-3 py-2 text-xs">
              <span className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${b.ready ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-amber-400'}`} />
                {b.country}
              </span>
              <span className="text-slate-400">
                زمینی {fmt(b.ground)} · هوایی {fmt(b.air)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function StatusPanel({ stats }: { stats: Stats }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <div className="stat-tile">
          <div className="text-[11px] text-slate-400">آمادگی رزمی</div>
          <div className={`mt-1 font-black ${stats.combat_ready ? 'text-emerald-300' : 'text-amber-300'}`}>{stats.combat_ready ? '● آماده نبرد' : '● در حال بازسازی'}</div>
        </div>
        <div className="stat-tile">
          <div className="text-[11px] text-slate-400">ناوگان</div>
          <div className="mt-1 font-black text-[var(--cyan)]">
            {fmt(stats.fleets.outbound)} اعزامی · {fmt(stats.fleets.returning)} بازگشتی
          </div>
        </div>
        <div className="stat-tile">
          <div className="text-[11px] text-slate-400">تحریم</div>
          <div className="mt-1 font-black">{stats.status.sanction.active ? `فعال (−${fmt(stats.status.sanction.penalty)}٪)` : 'ندارد'}</div>
        </div>
        <div className="stat-tile">
          <div className="text-[11px] text-slate-400">ویروس / آتش‌سوزی</div>
          <div className="mt-1 font-black">{stats.status.viruses.length === 0 && !stats.status.on_fire ? 'سالم' : 'هشدار'}</div>
        </div>
      </div>
      <div>
        <div className="section-sub">نبردهای اخیر</div>
        <div className="mt-2 space-y-1.5">
          {stats.recent_battles.map((b, i) => (
            <div key={i} className="text-xs rounded-lg bg-white/4 border border-white/6 px-3 py-2">
              ⚔️ {b}
            </div>
          ))}
        </div>
      </div>
      <div>
        <div className="section-sub">اعلان‌ها</div>
        <div className="mt-2 space-y-1.5">
          {stats.notifications.map((n, i) => (
            <div key={i} className="flex justify-between gap-2 text-xs rounded-lg bg-white/4 border border-white/6 px-3 py-2">
              <span>🔔 {n.title}</span>
              <span className="text-slate-500 shrink-0">{n.at}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const FLAGS = ['🇮🇷', '🇹🇷', '🇪🇬', '🇸🇦', '🇮🇶', '🇵🇰', '🇦🇿', '🇦🇲', '🇰🇿', '🇯🇵', '🇨🇭', '🇳🇴', '🇧🇷', '🇨🇦', '🏴', '🚩']
const COLORS = ['#55d6ff', '#f1c86d', '#ff6c6c', '#6ee7a8', '#c084fc', '#fb923c', '#f472b6', '#e5e7eb']

export function CustomizePanel({
  profile,
  onSave,
  busy,
}: {
  profile: CountryProfile
  onSave: (p: CountryProfile) => void
  busy: boolean
}) {
  const [draft, setDraft] = useState(profile)
  useEffect(() => setDraft(profile), [profile])
  const set = <K extends keyof CountryProfile>(k: K, v: CountryProfile[K]) => setDraft((d) => ({ ...d, [k]: v }))
  const terrainChanged = draft.biome !== profile.biome || draft.seed !== profile.seed
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault()
        onSave({ ...draft, display_name: draft.display_name.trim() || profile.display_name, capital_name: draft.capital_name.trim() || profile.capital_name })
      }}
    >
      <label className="block">
        <span className="section-sub">نام کشور</span>
        <input className="input-dark mt-1.5" value={draft.display_name} maxLength={28} onChange={(e) => set('display_name', e.target.value)} />
      </label>
      <label className="block">
        <span className="section-sub">نام پایتخت</span>
        <input className="input-dark mt-1.5" value={draft.capital_name} maxLength={20} onChange={(e) => set('capital_name', e.target.value)} />
      </label>
      <div>
        <span className="section-sub">پرچم</span>
        <div className="flex flex-wrap gap-1.5 mt-1.5">
          {FLAGS.map((f) => (
            <button type="button" key={f} onClick={() => set('flag_emoji', f)} className={`swatch-btn ${draft.flag_emoji === f ? 'on' : ''}`}>
              {f}
            </button>
          ))}
        </div>
      </div>
      <div>
        <span className="section-sub">رنگ قلمرو (مرز سه‌بعدی)</span>
        <div className="flex flex-wrap items-center gap-2 mt-1.5">
          {COLORS.map((c) => (
            <button type="button" key={c} onClick={() => set('map_color', c)} className={`w-7 h-7 rounded-full border-2 transition ${draft.map_color === c ? 'border-white scale-110' : 'border-white/15'}`} style={{ background: c, boxShadow: draft.map_color === c ? `0 0 14px ${c}` : 'none' }} aria-label={c} />
          ))}
          <input type="color" value={draft.map_color} onChange={(e) => set('map_color', e.target.value)} className="w-8 h-8 bg-transparent rounded cursor-pointer" />
        </div>
      </div>
      <label className="block">
        <span className="section-sub">نوع حکومت</span>
        <select className="input-dark mt-1.5" value={draft.government} onChange={(e) => set('government', e.target.value)}>
          {GOVS.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </label>

      <div>
        <span className="section-sub">اقلیم و سرزمین</span>
        <div className="grid gap-2 mt-1.5">
          {(Object.keys(BIOMES) as BiomeId[]).map((id) => (
            <button
              type="button"
              key={id}
              onClick={() => set('biome', id)}
              className={`text-right rounded-xl border px-3 py-2.5 transition ${draft.biome === id ? 'border-[var(--cyan)]/60 bg-[var(--cyan)]/10' : 'border-white/8 bg-white/3 hover:bg-white/6'}`}
            >
              <div className="flex items-center gap-2 text-sm font-bold">
                <span className="flex gap-0.5">
                  {[BIOMES[id].palette.grassA, BIOMES[id].palette.rockA, BIOMES[id].palette.snow].map((c, i) => (
                    <i key={i} className="w-3 h-3 rounded-full inline-block" style={{ background: c }} />
                  ))}
                </span>
                {BIOMES[id].label}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">{BIOMES[id].desc}</div>
            </button>
          ))}
        </div>
        <div className="flex gap-2 mt-2">
          <input type="number" className="input-dark" value={draft.seed} onChange={(e) => set('seed', Math.max(1, Math.min(999999, Number(e.target.value) || 1)))} />
          <button type="button" className="btn-ghost shrink-0" onClick={() => set('seed', Math.floor(Math.random() * 99999) + 1)}>
            🎲 تصادفی
          </button>
        </div>
        {terrainChanged && <p className="text-[11px] text-amber-300 mt-1.5">با ذخیره، سرزمین از نو ساخته می‌شود و سازه‌های نصب‌شده به انبار برمی‌گردند.</p>}
      </div>

      <button className="btn-primary w-full" disabled={busy}>
        {busy ? 'در حال ساخت سرزمین…' : '💾 ذخیره'}
      </button>
    </form>
  )
}
