import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CountryWorld, type Layers, type Quality, type Selection } from './world'
import {
  BIOMES,
  CITY_NAMES,
  DEFAULT_PROFILE,
  DEMO_STATS,
  INVENTORY,
  ITEM_BY_KEY,
  type CountryProfile,
  type Division,
  type ItemKey,
  type Placement,
  type Stats,
} from './data'
import { ArmyPanel, CustomizePanel, EconomyPanel, StatusPanel, fmt, fmtCompact } from './panels'
import { api, errMsg } from '../lib/api'

type Tab = 'economy' | 'army' | 'status' | 'customize'

const initialInv = () => Object.fromEntries(INVENTORY.map((i) => [i.key, i.qty])) as Record<ItemKey, number>

const KIND_FA: Record<Division['kind'], string> = { capital: 'پایتخت', province: 'استان', city: 'شهر' }
const KIND_ICON: Record<Division['kind'], string> = { capital: '★', province: '◆', city: '●' }

const BONUS: Record<ItemKey, { atk: number; def: number }> = {
  radar: { atk: 0, def: 150 },
  sam: { atk: 0, def: 420 },
  airbase: { atk: 300, def: 120 },
  armor: { atk: 380, def: 200 },
  artillery: { atk: 340, def: 40 },
  silo: { atk: 900, def: 0 },
}

const clock = (h: number) => {
  const hh = Math.floor(h) % 24
  const mm = Math.floor((h % 1) * 60)
  return new Intl.NumberFormat('fa-IR', { minimumIntegerDigits: 2, useGrouping: false }).format(hh) + ':' + new Intl.NumberFormat('fa-IR', { minimumIntegerDigits: 2, useGrouping: false }).format(mm)
}

const dayLabel = (h: number) => (h < 5 || h >= 20 ? 'شب' : h < 7.5 ? 'سپیده‌دم' : h < 11 ? 'صبح' : h < 15 ? 'ظهر' : h < 18 ? 'عصر' : 'غروب')

export default function CountryPage() {
  const stageRef = useRef<HTMLDivElement>(null)
  const worldRef = useRef<CountryWorld | null>(null)
  const toastTimer = useRef<number>(0)

  const [profile, setProfile] = useState<CountryProfile>(DEFAULT_PROFILE)
  const profileRef = useRef(profile)
  profileRef.current = profile

  const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading')
  const [regen, setRegen] = useState(false)
  const [divisions, setDivisions] = useState<Division[]>([])
  const [placements, setPlacements] = useState<Placement[]>([])
  const [inv, setInv] = useState<Record<ItemKey, number>>(initialInv)
  const [layers, setLayers] = useState<Layers>({ terrain: true, divisions: true, placements: true, clouds: true, border: true })
  const [hour, setHour] = useState(16.2)
  const [playing, setPlaying] = useState(false)
  const [cloud, setCloud] = useState(0.18)
  const [quality, setQuality] = useState<Quality>('high')
  const [spin, setSpin] = useState(false)
  const [selection, setSelection] = useState<Selection>(null)
  const [buildOpen, setBuildOpen] = useState(false)
  const [placingKey, setPlacingKey] = useState<ItemKey | null>(null)
  const [ghost, setGhost] = useState<{ ok: boolean; reason: string } | null>(null)
  const [pending, setPending] = useState<{ item: ItemKey; x: number; z: number; nearest: Division[] } | null>(null)
  const [cityFormOpen, setCityFormOpen] = useState(false)
  const [cityDraft, setCityDraft] = useState('')
  const [listOpen, setListOpen] = useState(true)
  const [msg, setMsg] = useState('')
  const [fps, setFps] = useState(0)
  const [tab, setTab] = useState<Tab>('economy')
  const [toolsOpen, setToolsOpen] = useState(true)
  const [ownedCountries, setOwnedCountries] = useState<any[]>([])
  const [activeCountry, setActiveCountry] = useState<any>(null)
  const [liveStats, setLiveStats] = useState<Stats | null>(null)
  const [itemBindings, setItemBindings] = useState<Partial<Record<ItemKey, { key: string; suffix: string; qty: number }[]>>>({})
  const [serverPlacements, setServerPlacements] = useState<any[]>([])

  const flash = useCallback((t: string) => {
    setMsg(t)
    window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setMsg(''), 3200)
  }, [])

  useEffect(() => {
    let alive = true
    Promise.all([api.get('/my-map/'), api.get('/equipment/')]).then(([mapResponse, equipmentResponse]) => {
      if (!alive) return
      const map = mapResponse.data
      const countries = map.territory || []
      setOwnedCountries(countries)
      setServerPlacements(map.placements || [])
      const current = countries[0]
      if (current) {
        setActiveCountry(current)
        const seed = String(current.name).split('').reduce((n, c) => (n * 31 + c.charCodeAt(0)) >>> 0, 1)
        const next = { ...DEFAULT_PROFILE, display_name: current.profile.display_name, flag_emoji: current.profile.flag_emoji || current.emoji,
          map_color: current.profile.map_color, capital_name: current.profile.capital_name, government: current.profile.government, seed }
        setProfile(next)
      }
      const s = map.stats
      if (s) setLiveStats({ ...DEMO_STATS, treasury: s.treasury, population: s.population, score: s.score, daily_profit: s.daily_profit,
        income: s.income, assets: s.assets, army: { ...DEMO_STATS.army, ...s.army }, bases: s.bases,
        fleets: s.fleets, status: s.status, recent_battles: s.recent_battles, notifications: s.notifications, combat_ready: s.combat_ready })
      const categories = equipmentResponse.data.categories || {}
      const specs: Record<ItemKey, [string, string]> = {
        radar: ['mine', 'count'], sam: ['air_defense', 'air_defense_count'], airbase: ['building', 'count'],
        armor: ['economic', 'count'], artillery: ['artillery', 'artillery_count'], silo: ['missile', 'missile_count'],
      }
      const bindings: Partial<Record<ItemKey, { key: string; suffix: string; qty: number }[]>> = {}
      const nextInv = { ...initialInv() }
      for (const item of INVENTORY) {
        const [category, suffix] = specs[item.key]
        const available = (categories[category] || []) as { key: string; qty: number }[]
        bindings[item.key] = available.map((entry) => ({ ...entry, suffix }))
        nextInv[item.key] = available.reduce((sum, entry) => sum + entry.qty, 0)
      }
      setItemBindings(bindings)
      setInv(nextInv)
    }).catch((error) => flash(`خطا در دریافت اطلاعات کشور: ${errMsg(error)}`))
    return () => { alive = false }
  }, [flash])

  useEffect(() => {
    if (!activeCountry || phase !== 'ready') return
    const next = { ...profile, display_name: activeCountry.profile.display_name,
      flag_emoji: activeCountry.profile.flag_emoji || activeCountry.emoji,
      map_color: activeCountry.profile.map_color, capital_name: activeCountry.profile.capital_name,
      government: activeCountry.profile.government }
    setProfile(next)
    void worldRef.current?.regenerate(next).then(() => {
      if (activeCountry.divisions?.length) worldRef.current?.setDivisionNames(activeCountry.divisions)
      const cityNames = new Set((activeCountry.divisions || []).map((division: any) => division.name))
      const worldDivisions = worldRef.current?.getDivisions() || []
      const restored: Placement[] = []
      for (const saved of serverPlacements) {
        if (!saved.city_name || !cityNames.has(saved.city_name)) continue
        const model = (Object.keys(itemBindings) as ItemKey[]).find((key) =>
          itemBindings[key]?.some((binding) => `${binding.key}_${binding.suffix}` === saved.item_key))
        const city = worldDivisions.find((division) => division.name === saved.city_name)
        if (!model || !city) continue
        restored.push(worldRef.current!.addPlacement({ id: saved.id, item_key: model, qty: saved.qty,
          x: city.x, z: city.z, city_name: city.name }))
      }
      setPlacements(restored)
    })
  // The selected game's country is the only trigger; visual profile edits are handled by saveProfile.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCountry?.name, phase])

  /* ------------------------- world lifecycle ------------------------ */
  useEffect(() => {
    const el = stageRef.current
    if (!el) return
    let world: CountryWorld
    try {
      world = new CountryWorld(el, profileRef.current, {
        onReady: (d) => {
          setDivisions(d)
          setPhase('ready')
        },
        onDivisions: (d) => setDivisions(d),
        onSelect: (s) => {
          setSelection(s)
          worldRef.current?.select(s)
        },
        onPlaceRequest: (info) => setPending(info),
        onGhost: (g) => setGhost(g),
        onHour: (h) => setHour(h),
        onFps: (f) => setFps(f),
      })
    } catch (e) {
      console.error(e)
      setPhase('error')
      return
    }
    worldRef.current = world
    world.init().catch((e) => {
      console.error(e)
      setPhase('error')
    })
    return () => {
      world.dispose()
      worldRef.current = null
    }
  }, [])

  useEffect(() => worldRef.current?.setLayers(layers), [layers, phase])
  useEffect(() => worldRef.current?.setHour(hour), [hour, phase])
  useEffect(() => worldRef.current?.setPlaying(playing), [playing])
  useEffect(() => worldRef.current?.setCloudiness(cloud), [cloud])
  useEffect(() => worldRef.current?.setQuality(quality), [quality, phase])
  useEffect(() => worldRef.current?.setAutoRotate(spin), [spin])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (pending) setPending(null)
      else if (cityFormOpen) setCityFormOpen(false)
      else if (placingKey) cancelPlacing()
      else if (selection) {
        setSelection(null)
        worldRef.current?.select(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending, cityFormOpen, placingKey, selection])

  /* ------------------------------ actions --------------------------- */
  const cancelPlacing = () => {
    worldRef.current?.startPlacing(null)
    setPlacingKey(null)
    setGhost(null)
  }

  const beginPlacing = (key: ItemKey) => {
    if (inv[key] <= 0) {
      flash('موجودی این سازه تمام شده است. از فروشگاه بخرید.')
      return
    }
    setBuildOpen(false)
    setSelection(null)
    worldRef.current?.select(null)
    worldRef.current?.startPlacing(key)
    setPlacingKey(key)
  }

  const confirmPlacement = (city: Division) => {
    const world = worldRef.current
    if (!world || !pending) return
    const binding = itemBindings[pending.item]?.find((item) => item.qty > 0)
    const serverCity = activeCountry?.divisions?.find((item: any) => item.name === city.name)
    if (!binding || !activeCountry || !serverCity) { flash('این سازه در موجودی قابل‌استقرار نیست.'); return }
    api.post('/my-map/', { lat: serverCity.lat, lon: serverCity.lon, city_name: city.name,
      item_key: binding.key, suffix: binding.suffix, qty: 1 }).then(({ data: response }) => {
      const saved = response.placements?.find((item: any) => item.item_key === `${binding.key}_${binding.suffix}` && item.city_name === city.name)
      const p = world.addPlacement({ id: saved?.id, item_key: pending.item, qty: 1, x: pending.x, z: pending.z, city_name: city.name })
      setPlacements((prev) => [...prev, p])
      setInv((prev) => ({ ...prev, [pending.item]: Math.max(0, prev[pending.item] - 1) }))
      setItemBindings((prev) => ({ ...prev, [pending.item]: prev[pending.item]?.map((item) => item === binding ? { ...item, qty: item.qty - 1 } : item) }))
      flash(`${ITEM_BY_KEY[pending.item].name} در ${city.name} مستقر شد`)
      setPending(null)
      cancelPlacing()
      setSelection({ type: 'placement', id: p.id })
      world.select({ type: 'placement', id: p.id })
    }).catch((error) => flash(errMsg(error)))
  }

  const removePlacement = (id: number) => {
    const p = placements.find((x) => x.id === id)
    if (!p) return
    api.delete('/my-map/', { data: { id } }).catch((error) => flash(errMsg(error)))
    worldRef.current?.removePlacement(id)
    setPlacements((prev) => prev.filter((x) => x.id !== id))
    setInv((prev) => ({ ...prev, [p.item_key]: prev[p.item_key] + 1 }))
    setSelection(null)
    flash('سازه به انبار بازگشت')
  }

  const submitCity = () => {
    const customCount = divisions.filter((d) => d.custom).length
    const name = cityDraft.trim() || CITY_NAMES[(3 + customCount) % CITY_NAMES.length] + ' ' + new Intl.NumberFormat('fa-IR').format(customCount + 1)
    if (activeCountry) {
      api.post('/my-map/country-profile/', { country: activeCountry.name, add_city: name }).then(({ data: response }) => {
        const d = worldRef.current?.addCity(name)
        if (!d) { flash('جای مناسبی برای شهر تازه پیدا نشد.'); return }
        const updated = { ...activeCountry, divisions: response.profile.divisions }
        setActiveCountry(updated)
        setOwnedCountries((items) => items.map((country) => country.name === updated.name ? updated : country))
      worldRef.current?.setDivisionNames(response.profile.divisions)
        flash(`شهر «${name}» ساخته و ذخیره شد`)
      }).catch((error) => flash(errMsg(error)))
      setCityDraft('')
      setCityFormOpen(false)
      return
    }
    const d = worldRef.current?.addCity(name)
    if (!d) flash('جای مناسبی برای شهر تازه پیدا نشد (حداکثر ۱۰ شهر سفارشی).')
    else {
      flash(`شهر «${d.name}» ساخته شد`)
      setSelection({ type: 'division', id: d.id })
      worldRef.current?.select({ type: 'division', id: d.id })
    }
    setCityDraft('')
    setCityFormOpen(false)
  }

  const saveProfile = async (next: CountryProfile) => {
    const terrainChanged = next.biome !== profile.biome || next.seed !== profile.seed
    if (activeCountry) {
      try {
        await api.post('/my-map/country-profile/', { country: activeCountry.name, display_name: next.display_name,
          flag_emoji: next.flag_emoji, map_color: next.map_color, capital_name: next.capital_name, government: next.government })
        const updated = { ...activeCountry, profile: { ...activeCountry.profile, display_name: next.display_name,
          flag_emoji: next.flag_emoji, map_color: next.map_color, capital_name: next.capital_name, government: next.government } }
        setActiveCountry(updated)
        setOwnedCountries((items) => items.map((country) => country.name === updated.name ? updated : country))
      } catch (error) { flash(`ذخیره انجام نشد: ${errMsg(error)}`); return }
    }
    setProfile(next)
    const world = worldRef.current
    if (!world) return
    if (!terrainChanged) {
      world.setProfileVisual(next)
      flash('تنظیمات کشور ذخیره شد')
      return
    }
    setRegen(true)
    setSelection(null)
    cancelPlacing()
    await world.regenerate(next)
    setPlacements([])
    setInv(initialInv())
    setRegen(false)
    flash('سرزمین تازه ساخته شد')
  }

  const goto = (id: string) => {
    setSelection({ type: 'division', id })
    worldRef.current?.select({ type: 'division', id })
    worldRef.current?.flyToDivision(id)
  }

  const bonus = useMemo(() => {
    let atk = 0
    let def = 0
    placements.forEach((p) => {
      atk += BONUS[p.item_key].atk
      def += BONUS[p.item_key].def
    })
    return { atk, def }
  }, [placements])

  const stats: Stats = useMemo(
    () => ({ ...DEMO_STATS, army: { ...DEMO_STATS.army, attack: DEMO_STATS.army.attack + bonus.atk, defense: DEMO_STATS.army.defense + bonus.def } }),
    [bonus],
  )
  const visibleStats = liveStats || stats

  const selDivision = selection?.type === 'division' ? divisions.find((d) => d.id === selection.id) : undefined
  const selPlacement = selection?.type === 'placement' ? placements.find((p) => p.id === selection.id) : undefined
  const biome = BIOMES[profile.biome]
  const layerDefs: [keyof Layers, string, string][] = [
    ['terrain', '🌲', 'عوارض'],
    ['divisions', '🏙️', 'شهرها'],
    ['placements', '🏗️', 'سازه‌ها'],
    ['border', '🧭', 'مرز'],
    ['clouds', '☁️', 'ابرها'],
  ]

  const presets: [number, string, string][] = [
    [6.3, '🌅', 'سپیده‌دم'],
    [12, '☀️', 'ظهر'],
    [17.6, '🌇', 'غروب'],
    [23, '🌙', 'شب'],
  ]

  return (
    <div className="space-y-4" dir="rtl">
      {/* ----------------------------- header ---------------------------- */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-3">
          <div className="flag-orb" style={{ boxShadow: `0 0 24px ${profile.map_color}55, inset 0 0 0 1px ${profile.map_color}66` }}>
            {profile.flag_emoji}
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-black leading-tight">{profile.display_name}</h1>
            <p className="text-xs text-slate-400">
              {profile.government} · پایتخت {profile.capital_name} · {biome.label}
            </p>
          </div>
        </div>
        <div className="mr-auto flex flex-wrap gap-2 text-xs">
          <span className="stat-chip">🏙️ <b className="resource-value">{fmt(divisions.length)}</b> شهر</span>
          <span className="stat-chip">🏗️ <b className="resource-value">{fmt(placements.length)}</b> سازه</span>
          <span className="stat-chip">💥 <b className="resource-value">{fmt(visibleStats.army.attack)}</b></span>
          <span className="stat-chip">🛡 <b className="resource-value">{fmt(visibleStats.army.defense)}</b></span>
          <span className="stat-chip text-slate-400 hidden sm:flex">⚡ {fmt(fps)} فریم</span>
        </div>
        {ownedCountries.length > 1 && (
          <select className="input-dark !w-auto min-w-44 text-sm" value={activeCountry?.name || ''} onChange={(event) => {
            const country = ownedCountries.find((item) => item.name === event.target.value)
            if (!country) return
            setActiveCountry(country)
            const seed = String(country.name).split('').reduce((n, c) => (n * 31 + c.charCodeAt(0)) >>> 0, 1)
            const next = { ...profile, display_name: country.profile.display_name, flag_emoji: country.profile.flag_emoji || country.emoji,
              map_color: country.profile.map_color, capital_name: country.profile.capital_name, government: country.profile.government, seed }
            setProfile(next)
            setDivisions(country.divisions || [])
            setPlacements([])
            setPhase('ready')
          }} aria-label="انتخاب کشور">
            {ownedCountries.map((country) => <option key={country.name} value={country.name}>{country.emoji} {country.name}</option>)}
          </select>
        )}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        {/* ------------------------------ stage ------------------------------ */}
        <div className="glass-card stage-card relative overflow-hidden h-[72vh] min-h-[540px] xl:h-[calc(100vh-190px)]">
          <div ref={stageRef} className="absolute inset-0 stage-canvas" />

          {/* top-right: layers */}
          <div className="absolute top-3 right-3 flex flex-wrap gap-1.5 max-w-[70%] pointer-events-auto">
            {layerDefs.map(([k, icon, label]) => (
              <button key={k} onClick={() => setLayers((l) => ({ ...l, [k]: !l[k] }))} className={`hud-pill ${layers[k] ? 'on' : ''}`}>
                <span>{icon}</span>
                {label}
              </button>
            ))}
          </div>

          {/* top-left: camera tools */}
          <div className="absolute top-3 left-3 flex flex-col gap-1.5 pointer-events-auto items-start">
            <button onClick={() => setToolsOpen((o) => !o)} className="hud-pill on">
              🎥 دوربین
            </button>
            {toolsOpen && (
              <div className="hud-panel p-2 flex flex-col gap-1.5 w-40">
                <button className="hud-btn" onClick={() => worldRef.current?.resetView()}>
                  🌍 نمای کلی
                </button>
                <button className={`hud-btn ${spin ? 'active' : ''}`} onClick={() => setSpin((s) => !s)}>
                  🎬 چرخش سینمایی
                </button>
                <div className="flex gap-1">
                  {(['low', 'medium', 'high'] as Quality[]).map((q) => (
                    <button key={q} className={`hud-btn flex-1 ${quality === q ? 'active' : ''}`} onClick={() => setQuality(q)}>
                      {q === 'low' ? 'کم' : q === 'medium' ? 'متوسط' : 'بالا'}
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-slate-500 leading-relaxed">کشیدن: چرخش · راست‌کلیک: جابه‌جایی · چرخ ماوس: زوم</p>
              </div>
            )}
          </div>

          {/* left: divisions & structures list */}
          <div className="absolute top-[3.6rem] right-3 pointer-events-auto hidden md:block w-56">
            <button className="hud-pill on mb-1.5" onClick={() => setListOpen((o) => !o)}>
              {listOpen ? '▾' : '▸'} شهرها و سازه‌ها
            </button>
            {listOpen && (
              <div className="hud-panel p-1.5 max-h-[34vh] overflow-y-auto space-y-0.5">
                {divisions.map((d) => (
                  <button key={d.id} onClick={() => goto(d.id)} className={`list-row ${selDivision?.id === d.id ? 'on' : ''}`}>
                    <span className={`kind-dot ${d.kind}`}>{KIND_ICON[d.kind]}</span>
                    <span className="flex-1 text-right truncate">{d.name}</span>
                    <span className="text-[10px] text-slate-500">{KIND_FA[d.kind]}</span>
                  </button>
                ))}
                {placements.length > 0 && <div className="text-[10px] text-slate-500 px-2 pt-2">سازه‌های نصب‌شده {fmt(placements.length)}</div>}
                {placements.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setSelection({ type: 'placement', id: p.id })
                      worldRef.current?.select({ type: 'placement', id: p.id })
                      worldRef.current?.flyToPlacement(p.id)
                    }}
                    className={`list-row ${selPlacement?.id === p.id ? 'on' : ''}`}
                  >
                    <span>{ITEM_BY_KEY[p.item_key].icon}</span>
                    <span className="flex-1 text-right truncate">{ITEM_BY_KEY[p.item_key].name}</span>
                    <span className="text-[10px] text-slate-500 truncate max-w-[60px]">{p.city_name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* bottom-left: selection card */}
          {(selDivision || selPlacement) && (
            <div className="absolute bottom-[10.6rem] left-3 w-64 hud-panel p-3 pointer-events-auto info-card" dir="rtl">
              {selDivision && (
                <>
                  <div className="flex items-center gap-2">
                    <span className={`kind-dot big ${selDivision.kind}`}>{KIND_ICON[selDivision.kind]}</span>
                    <div className="flex-1">
                      <div className="font-black">{selDivision.name}</div>
                      <div className="text-[11px] text-slate-400">{KIND_FA[selDivision.kind]}</div>
                    </div>
                    <button className="text-slate-500 hover:text-white" onClick={() => { setSelection(null); worldRef.current?.select(null) }} aria-label="بستن">✕</button>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                    <div className="stat-tile !p-2">
                      <div className="text-slate-400">جمعیت</div>
                      <b className="text-[var(--cyan)]">{fmtCompact(selDivision.population)}</b>
                    </div>
                    <div className="stat-tile !p-2">
                      <div className="text-slate-400">سازه‌ها</div>
                      <b className="text-[var(--gold)]">{fmt(placements.filter((p) => p.city_name === selDivision.name).length)}</b>
                    </div>
                  </div>
                  <button className="btn-ghost w-full mt-3 !py-1.5 text-xs" onClick={() => worldRef.current?.flyToDivision(selDivision.id)}>
                    ✈️ پرواز به شهر
                  </button>
                </>
              )}
              {selPlacement && (
                <>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{ITEM_BY_KEY[selPlacement.item_key].icon}</span>
                    <div className="flex-1">
                      <div className="font-black">{ITEM_BY_KEY[selPlacement.item_key].name}</div>
                      <div className="text-[11px] text-slate-400">{selPlacement.city_name ? `مستقر در ${selPlacement.city_name}` : 'مستقر در قلمرو'}</div>
                    </div>
                    <button className="text-slate-500 hover:text-white" onClick={() => { setSelection(null); worldRef.current?.select(null) }} aria-label="بستن">✕</button>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">{ITEM_BY_KEY[selPlacement.item_key].desc}</p>
                  <p className="text-xs mt-2 text-[var(--gold)]">
                    اثر: حمله +{fmt(BONUS[selPlacement.item_key].atk)} · دفاع +{fmt(BONUS[selPlacement.item_key].def)}
                  </p>
                  <div className="flex gap-2 mt-3">
                    <button className="btn-ghost flex-1 !py-1.5 text-xs" onClick={() => worldRef.current?.flyToPlacement(selPlacement.id)}>
                      🎯 نمایش
                    </button>
                    <button className="btn-danger flex-1 !py-1.5 text-xs" onClick={() => removePlacement(selPlacement.id)}>
                      🗑 برگرداندن
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* bottom: time of day */}
          <div className="absolute bottom-3 right-3 left-3 sm:left-auto sm:w-[380px] hud-panel p-2.5 pointer-events-auto sm:mr-0" dir="rtl">
            <div className="flex items-center gap-2">
              <button className={`hud-btn !w-9 !h-9 !p-0 ${playing ? 'active' : ''}`} onClick={() => setPlaying((p) => !p)} aria-label="چرخهٔ شبانه‌روز">
                {playing ? '⏸' : '▶'}
              </button>
              <div className="flex-1">
                <div className="flex justify-between text-[11px] text-slate-400 mb-0.5">
                  <span>{dayLabel(hour)}</span>
                  <b className="text-slate-100 tabular-nums">{clock(hour)}</b>
                </div>
                <input type="range" min={0} max={24} step={0.05} value={hour} onChange={(e) => setHour(Number(e.target.value))} className="w-full range-hud" />
              </div>
            </div>
            <div className="flex items-center gap-1.5 mt-2">
              {presets.map(([h, ic, l]) => (
                <button key={l} className="hud-btn flex-1 !px-1 !py-1 text-[11px]" onClick={() => setHour(h)}>
                  {ic} {l}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-2 text-[11px] text-slate-400">
              <span>☀️</span>
              <input type="range" min={0} max={1} step={0.02} value={cloud} onChange={(e) => setCloud(Number(e.target.value))} className="flex-1 range-hud" aria-label="ابرناکی" />
              <span>⛈️</span>
            </div>
          </div>

          {/* bottom-left: build */}
          <div className="absolute bottom-3 left-3 pointer-events-auto hidden sm:flex flex-col items-start gap-2" dir="rtl">
            {buildOpen && (
              <div className="hud-panel p-2 w-64 space-y-1">
                <div className="text-xs font-black px-1 pb-1">سازه انتخاب کن</div>
                {INVENTORY.map((it) => (
                  <button key={it.key} disabled={inv[it.key] <= 0} onClick={() => beginPlacing(it.key)} className="build-row">
                    <span className="text-xl">{it.icon}</span>
                    <span className="flex-1 text-right">
                      <b className="block text-[13px]">{it.name}</b>
                      <small className="text-slate-400">{it.desc}</small>
                    </span>
                    <span className="qty">×{fmt(inv[it.key])}</span>
                  </button>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <button className={`btn-primary !py-2 !px-3 text-sm ${buildOpen ? 'brightness-125' : ''}`} onClick={() => {
                  setBuildOpen((o) => !o)
                  if (placingKey) cancelPlacing()
                  setSelection(null)
                  worldRef.current?.select(null)
                }}>
                🏗️ ساخت
              </button>
              <button className="btn-ghost !py-2 !px-3 text-sm" onClick={() => setCityFormOpen(true)}>
                ⌖ شهر تازه
              </button>
            </div>
          </div>

          {/* mobile build row */}
          <div className="absolute top-[3.6rem] left-3 sm:hidden pointer-events-auto flex gap-2">
            <button className="hud-pill on" onClick={() => setBuildOpen((o) => !o)}>🏗️ ساخت</button>
            <button className="hud-pill on" onClick={() => setCityFormOpen(true)}>⌖ شهر</button>
          </div>
          {buildOpen && (
            <div className="absolute top-24 left-3 right-3 sm:hidden hud-panel p-2 space-y-1 pointer-events-auto z-20">
              {INVENTORY.map((it) => (
                <button key={it.key} disabled={inv[it.key] <= 0} onClick={() => beginPlacing(it.key)} className="build-row">
                  <span className="text-xl">{it.icon}</span>
                  <span className="flex-1 text-right text-[13px] font-bold">{it.name}</span>
                  <span className="qty">×{fmt(inv[it.key])}</span>
                </button>
              ))}
            </div>
          )}

          {/* placing hint */}
          {placingKey && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 pointer-events-none z-10">
              <div className={`hud-panel px-4 py-2 text-center text-xs ${ghost && !ghost.ok ? 'border-red-400/40' : 'border-emerald-400/40'}`}>
                <div className="font-black">
                  {ITEM_BY_KEY[placingKey].icon} {ITEM_BY_KEY[placingKey].name}
                </div>
                <div className={ghost?.ok === false ? 'text-red-300' : 'text-emerald-300'}>{ghost ? ghost.reason : 'نشان‌گر را روی خشکی ببرید'}</div>
                <div className="text-slate-400 mt-0.5">کلیک: استقرار · راست‌کلیک یا Esc: لغو</div>
              </div>
            </div>
          )}

          {/* toast */}
          {msg && (
            <div className="absolute top-14 left-1/2 -translate-x-1/2 z-30 pointer-events-none">
              <div className="hud-panel px-4 py-2 text-sm font-bold toast-in">{msg}</div>
            </div>
          )}

          {/* city form modal */}
          {cityFormOpen && (
            <div className="modal-backdrop" dir="rtl" onMouseDown={(e) => e.target === e.currentTarget && setCityFormOpen(false)}>
              <form
                className="modal-card"
                onSubmit={(e) => {
                  e.preventDefault()
                  submitCity()
                }}
              >
                <div className="text-3xl text-[var(--cyan)]">⌖</div>
                <strong className="text-lg">ساخت شهر تازه</strong>
                <p className="text-xs text-slate-400 leading-6">مختصات شهر در قلمرو خودت خودکار و روی بهترین زمین هموار پیدا می‌شود؛ جاده‌ها هم به‌روز می‌شوند. می‌توانی تا ۱۰ شهر سفارشی اضافه کنی.</p>
                <input className="input-dark" autoFocus value={cityDraft} onChange={(e) => setCityDraft(e.target.value)} placeholder="نام شهر دلخواه" maxLength={22} />
                <div className="flex gap-2">
                  <button className="btn-primary flex-1">ساخت شهر</button>
                  <button type="button" className="btn-ghost" onClick={() => setCityFormOpen(false)}>
                    انصراف
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* city picker */}
          {pending && (
            <div className="modal-backdrop" dir="rtl" onMouseDown={(e) => e.target === e.currentTarget && setPending(null)}>
              <div className="modal-card">
                <strong className="text-lg">انتخاب شهر</strong>
                <p className="text-xs text-slate-400">
                  {ITEM_BY_KEY[pending.item].icon} {ITEM_BY_KEY[pending.item].name} را زیر نظر کدام شهر مستقر کنیم؟
                </p>
                <div className="space-y-1.5 max-h-60 overflow-y-auto">
                  {pending.nearest.map((c, i) => (
                    <button key={c.id} className={`list-row !py-2.5 ${i === 0 ? 'on' : ''}`} onClick={() => confirmPlacement(c)}>
                      <span className={`kind-dot ${c.kind}`}>{KIND_ICON[c.kind]}</span>
                      <span className="flex-1 text-right font-bold">{c.name}</span>
                      {i === 0 && <span className="text-[10px] text-emerald-300">نزدیک‌ترین</span>}
                    </button>
                  ))}
                </div>
                <button className="btn-ghost" onClick={() => setPending(null)}>
                  بازگشت به نقشه
                </button>
              </div>
            </div>
          )}

          {/* loading / regen / error */}
          {(phase === 'loading' || regen) && phase !== 'error' && (
            <div className="loader-overlay">
              <div className="loader-orb" />
              <div className="font-black mt-5">{regen ? 'در حال ساخت سرزمین تازه…' : 'در حال شکل‌دادن به سرزمین…'}</div>
              <div className="text-xs text-slate-400 mt-1.5">فرسایش کوه‌ها · جریان رودها · کاشت جنگل · ساخت شهرها</div>
            </div>
          )}
          {phase === 'error' && (
            <div className="loader-overlay">
              <div className="text-5xl">🛰️</div>
              <div className="font-black mt-4">نمایش سه‌بعدی روی این دستگاه فعال نشد</div>
              <div className="text-xs text-slate-400 mt-1.5">لطفاً WebGL2 را در مرورگر فعال کنید یا مرورگر دیگری را امتحان کنید.</div>
            </div>
          )}
        </div>

        {/* ---------------------------- side panel --------------------------- */}
        <div className="glass-card p-4 space-y-3 xl:max-h-[calc(100vh-190px)] xl:overflow-y-auto">
          <div className="grid grid-cols-4 gap-1 p-1 rounded-xl bg-black/30 border border-white/6">
            {(
              [
                ['economy', '💰 اقتصاد'],
                ['army', '⚔️ ارتش'],
                ['status', '📡 وضعیت'],
                ['customize', '🎨 سفارشی'],
              ] as [Tab, string][]
            ).map(([k, label]) => (
              <button key={k} onClick={() => setTab(k)} className={`tab-btn ${tab === k ? 'on' : ''}`}>
                {label}
              </button>
            ))}
          </div>
          <div key={tab} className="panel-in">
            {tab === 'economy' && <EconomyPanel stats={visibleStats} color={profile.map_color} />}
            {tab === 'army' && <ArmyPanel stats={visibleStats} bonus={bonus} />}
            {tab === 'status' && <StatusPanel stats={visibleStats} />}
            {tab === 'customize' && <CustomizePanel profile={profile} onSave={saveProfile} busy={regen} />}
          </div>
        </div>
      </div>
    </div>
  )
}
