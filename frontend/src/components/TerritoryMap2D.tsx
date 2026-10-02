import { useMemo, useRef, useState } from 'react'

type Division = { name: string; kind: 'capital' | 'province' | 'city'; lat: number; lon: number }
type Geo = { polygons: number[][][]; center: [number, number] }
type Placement = { id: number; item_key: string; suffix: string; qty: number; lat: number; lon: number; city_name?: string }
type ProjectedPoint = { x: number; y: number }
type ProjectedMap = {
  paths: string[]
  rings: ProjectedPoint[][]
  centerLat: number
  centerLon: number
  midX: number
  midY: number
  scale: number
  width: number
  height: number
}

const MAP_W = 1000
const MAP_H = 760
const wrapLon = (lon: number, center: number) => center + ((((lon - center) % 360) + 540) % 360) - 180

function projectMap(geo: Geo, name: string): ProjectedMap | null {
  const validRings = (geo.polygons || []).filter((ring) => Array.isArray(ring) && ring.length >= 3)
  if (!validRings.length) return null
  const coords = validRings.flat().filter((p) => Number.isFinite(p?.[0]) && Number.isFinite(p?.[1]))
  if (!coords.length) return null
  const sin = coords.reduce((sum, p) => sum + Math.sin((p[0] * Math.PI) / 180), 0)
  const cos = coords.reduce((sum, p) => sum + Math.cos((p[0] * Math.PI) / 180), 0)
  const centerLon = Math.atan2(sin, cos) * 180 / Math.PI
  const centerLat = Math.max(-78, Math.min(78, geo.center?.[0] ?? coords.reduce((sum, p) => sum + p[1], 0) / coords.length))
  const lonScale = Math.max(0.2, Math.cos(centerLat * Math.PI / 180))
  const raw = validRings.map((ring) => ring.map(([lon, lat]) => ({
    x: (wrapLon(lon, centerLon) - centerLon) * lonScale,
    y: -(lat - centerLat),
  })))
  const all = raw.flat()
  const minX = Math.min(...all.map((p) => p.x)), maxX = Math.max(...all.map((p) => p.x))
  const minY = Math.min(...all.map((p) => p.y)), maxY = Math.max(...all.map((p) => p.y))
  const worldW = Math.max(maxX - minX, 0.25), worldH = Math.max(maxY - minY, 0.25)
  const fitScale = Math.min(900 / worldW, 660 / worldH)
  const midX = (minX + maxX) / 2, midY = (minY + maxY) / 2
  const rings = raw.map((ring) => ring.map((p) => ({
    x: MAP_W / 2 + (p.x - midX) * fitScale,
    y: MAP_H / 2 + (p.y - midY) * fitScale,
  })))
  const paths = rings.map((ring) => ring.map((p, i) => {
    return `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`
  }).join(' ') + ' Z')
  return { paths, rings, centerLat, centerLon, midX, midY, scale: fitScale, width: worldW, height: worldH }
}


function clipVoronoiCell(polygon: ProjectedPoint[], site: ProjectedPoint, other: ProjectedPoint): ProjectedPoint[] {
  const a = 2 * (other.x - site.x), b = 2 * (other.y - site.y)
  const c = other.x * other.x + other.y * other.y - site.x * site.x - site.y * site.y
  const result: ProjectedPoint[] = []
  if (polygon.length < 3) return result
  for (let i = 0; i < polygon.length; i++) {
    const current = polygon[i], previous = polygon[(i + polygon.length - 1) % polygon.length]
    const dc = a * current.x + b * current.y - c
    const dp = a * previous.x + b * previous.y - c
    const currentInside = dc <= 1e-7, previousInside = dp <= 1e-7
    if (currentInside !== previousInside) {
      const t = dp / (dp - dc)
      result.push({ x: previous.x + (current.x - previous.x) * t, y: previous.y + (current.y - previous.y) * t })
    }
    if (currentInside) result.push(current)
  }
  return result
}

function siteMapPath(ring: ProjectedPoint[], sites: ProjectedPoint[]): string[] {
  return sites.flatMap((site, index) => {
    let cell = ring
    for (let j = 0; j < sites.length && cell.length >= 3; j++) {
      if (j !== index) cell = clipVoronoiCell(cell, site, sites[j])
    }
    return cell.length >= 3 ? [cell.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ') + ' Z'] : []
  })
}

const STRUCTURE_GLYPHS: Record<string, string> = {
  emerald: '\u{1F48E}', iron: '\u26CF', silver: '\u{1F948}', bronze: '\u{1F949}', diamond: '\u{1F4A0}', gold: '\u{1FA99}',
  factory: '\u{1F3ED}', oil_company: '\u{1F6E2}', industrial_company: '\u{1F3E2}',
  airport: '\u2708\uFE0F', dock: '\u2693', barracks: '\u{1F6E1}\uFE0F', metro: '\u{1F687}',
  normal_hospital: '\u271A', professional_hospital: '\u271A', normal: '\u{1F6E1}\uFE0F', base: '\u{1F3D5}\uFE0F', base_camp: '\u{1F3D5}\uFE0F', military_base: '\u{1F3D5}\uFE0F', airbase: '\u2708\uFE0F', air_base: '\u2708\uFE0F',
  sling: '\u{1F3F9}', patriot: '\u{1F6E1}\uFE0F', s400: '\u{1F6E1}\uFE0F', iron_dome: '\u{1F6E1}\uFE0F',
}
const STRUCTURE_TINTS: Record<string, string> = {
  emerald: '#63e6be', iron: '#aebdca', silver: '#d6e1ea', bronze: '#d99a65', diamond: '#89c8ff', gold: '#ffd36c',
  factory: '#f1b75c', oil_company: '#aeb7cc', industrial_company: '#82d9e5',
  airport: '#70c7ff', dock: '#5cded3', barracks: '#f38585', metro: '#b4a4ff', normal_hospital: '#ff7d95', professional_hospital: '#ff7d95', base: '#e7b86d', base_camp: '#e7b86d', military_base: '#e7b86d', airbase: '#70c7ff', air_base: '#70c7ff', normal: '#f38585', sling: '#f38585', patriot: '#f38585', s400: '#f38585', iron_dome: '#f38585',
}

function StructureMarker({ itemKey, x, y, cityName }: { itemKey: string; x: number; y: number; cityName: string }) {
  const tint = STRUCTURE_TINTS[itemKey] || '#f3c86f'
  return <g transform={`translate(${x} ${y})`} className="territory-map-building" aria-label={`${itemKey} ? ${cityName}`}>
    <circle r="23" fill={tint} opacity=".12" filter="url(#territory-glow)" />
    <rect x="-17" y="-20" width="34" height="34" rx="12" fill="#081520" stroke={tint} strokeWidth="1.6" />
    <text x="0" y="3" textAnchor="middle" dominantBaseline="middle" fill={tint} fontFamily="Segoe UI Emoji, Apple Color Emoji, sans-serif" fontSize="17">{STRUCTURE_GLYPHS[itemKey] || '\u{1F3D7}\uFE0F'}</text>
    <circle cx="12" cy="-15" r="3" fill={tint} stroke="#071522" strokeWidth="1" />
  </g>
}

function pointInRing(lon: number, lat: number, ring: number[][]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j]
    if (((yi > lat) !== (yj > lat)) && lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-12) + xi) inside = !inside
  }
  return inside
}

function placeOnMap(lat: number, lon: number, map: ProjectedMap): ProjectedPoint {
  const x = (wrapLon(lon, map.centerLon) - map.centerLon) * Math.max(0.2, Math.cos(map.centerLat * Math.PI / 180))
  const y = -(lat - map.centerLat)
  return { x: MAP_W / 2 + (x - map.midX) * map.scale, y: MAP_H / 2 + (y - map.midY) * map.scale }
}

export default function TerritoryMap2D({
  name, color, geo, divisions, placements, layers, placing, onPlace, onDivisionClick,
}: {
  name: string
  color: string
  geo: Geo
  divisions: Division[]
  placements: Placement[]
  layers: Record<string, boolean>
  placing: boolean
  onPlace: (lat: number, lon: number) => void
  onDivisionClick: (division: Division) => void
}) {
  const map = useMemo(() => projectMap(geo, name), [geo, name])
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [hovered, setHovered] = useState<string | null>(null)
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null)
  const moved = useRef(false)

  if (!map) return <div className="territory-map-empty">مرزهای این قلمرو هنوز در دسترس نیست.</div>

  const onPointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    moved.current = false
    if (placing || event.button !== 0) return
    event.currentTarget.setPointerCapture(event.pointerId)
    drag.current = { x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y }
  }
  const onPointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const start = drag.current
    if (!start) return
    const rect = event.currentTarget.getBoundingClientRect()
    const dx = (event.clientX - start.x) * MAP_W / rect.width
    const dy = (event.clientY - start.y) * MAP_H / rect.height
    if (Math.abs(dx) + Math.abs(dy) > 3) moved.current = true
    setPan({ x: start.panX + dx, y: start.panY + dy })
  }
  const onPointerUp = (event: React.PointerEvent<SVGSVGElement>) => {
    drag.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const onMapClick = (event: React.MouseEvent<SVGSVGElement>) => {
    if (!placing || moved.current) return
    const rect = event.currentTarget.getBoundingClientRect()
    const sx = (event.clientX - rect.left) * MAP_W / rect.width
    const sy = (event.clientY - rect.top) * MAP_H / rect.height
    const x = (sx - MAP_W / 2 - pan.x) / zoom + MAP_W / 2
    const y = (sy - MAP_H / 2 - pan.y) / zoom + MAP_H / 2
    const worldX = (x - MAP_W / 2) / map.scale + map.midX
    const worldY = (y - MAP_H / 2) / map.scale + map.midY
    const lat = map.centerLat - worldY
    const lon = wrapLon(map.centerLon + worldX / Math.max(0.2, Math.cos(map.centerLat * Math.PI / 180)), 0)
    onPlace(lat, lon)
  }
  const zoomBy = (amount: number) => setZoom((value) => Math.max(1, Math.min(4, Number((value + amount).toFixed(2)))))

  return (
    <div className="territory-map-shell" data-territory-map>
      <div className="territory-map-toolbar" dir="rtl">
        <div className="territory-map-heading">
          <span className="territory-map-live-dot" />
          <span>نقشهٔ قلمرو</span>
          <span className="territory-map-coordinate">{placing ? 'حالت ساخت‌وساز فعال' : 'نمای دوبعدی · قابل پیمایش'}</span>
        </div>
        <div className="territory-map-controls" aria-label="کنترل نقشه">
          <button type="button" aria-label="بزرگ‌نمایی" onClick={() => zoomBy(0.25)}>＋</button>
          <span>{Math.round(zoom * 100)}٪</span>
          <button type="button" aria-label="کوچک‌نمایی" onClick={() => zoomBy(-0.25)}>−</button>
          <button type="button" aria-label="بازنشانی نقشه" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }) }}>⌖</button>
        </div>
      </div>
      <svg
        className={`territory-map-svg ${placing ? 'is-placing' : ''}`}
        viewBox={`0 0 ${MAP_W} ${MAP_H}`}
        role="img"
        aria-label={`نقشه دوبعدی ${name}`}
        style={{ touchAction: 'none' }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onClick={onMapClick}
      >
        <defs>
          <linearGradient id="territory-land" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor={color} stopOpacity=".68" />
            <stop offset=".56" stopColor={color} stopOpacity=".34" />
            <stop offset="1" stopColor="#102c37" stopOpacity=".82" />
          </linearGradient>
          <pattern id="territory-grid" width="36" height="36" patternUnits="userSpaceOnUse">
            <path d="M 36 0 L 0 0 0 36" fill="none" stroke="#8ac6d8" strokeOpacity=".08" strokeWidth="1" />
            <circle cx="0" cy="0" r="1.3" fill="#8ac6d8" fillOpacity=".2" />
          </pattern>
          <filter id="territory-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="7" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <clipPath id="territory-clip"><path d={map.paths.join(' ')} /></clipPath>
        </defs>
        <rect width={MAP_W} height={MAP_H} fill="#071522" />
        <rect width={MAP_W} height={MAP_H} fill="url(#territory-grid)" />
        <g opacity=".2" stroke="#8fb4c7" strokeWidth="1" fill="none">
          {Array.from({ length: 5 }, (_, i) => <path key={`lat-${i}`} d={`M 0 ${90 + i * 105} H ${MAP_W}`} />)}
          {Array.from({ length: 8 }, (_, i) => <path key={`lon-${i}`} d={`M ${80 + i * 120} 0 V ${MAP_H}`} />)}
        </g>
        <g transform={`translate(${MAP_W / 2 + pan.x} ${MAP_H / 2 + pan.y}) scale(${zoom}) translate(${-MAP_W / 2} ${-MAP_H / 2})`}>
          {map.paths.map((path, index) => (
            <g key={`${name}-${index}`}>
              <path d={path} fill="none" stroke={color} strokeOpacity=".3" strokeWidth="20" filter="url(#territory-glow)" />
              <path d={path} fill="url(#territory-land)" stroke="#c9f5ff" strokeOpacity=".82" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
              <path d={path} fill="none" stroke={color} strokeOpacity=".42" strokeWidth=".7" strokeDasharray="3 5" vectorEffect="non-scaling-stroke" />
            </g>
          ))}
          {layers.divisions && (() => {
            const citySites = divisions.filter((d) => d.kind === 'city' || d.kind === 'capital')
              .map((d) => placeOnMap(d.lat, d.lon, map))
            return <g className="territory-map-city-borders" fill="none" stroke="#b8e3f1" strokeOpacity=".34" strokeWidth=".85" vectorEffect="non-scaling-stroke">
              {map.rings.flatMap((ring, i) => siteMapPath(ring, citySites).map((d, j) => <path key={`${i}-${j}`} d={d} />))}
            </g>
          })()}
          {layers.terrain && <g clipPath="url(#territory-clip)" opacity=".45" fill="none" stroke="#d5edf2" strokeOpacity=".18" strokeWidth="1.2">
            <ellipse cx="500" cy="300" rx="135" ry="64" />
            <ellipse cx="500" cy="300" rx="210" ry="104" />
            <ellipse cx="500" cy="300" rx="290" ry="148" />
          </g>}
          {layers.divisions && divisions.map((division) => {
            const p = placeOnMap(division.lat, division.lon, map)
            const isCapital = division.kind === 'capital'
            return (
              <g key={`${division.kind}-${division.name}`} transform={`translate(${p.x} ${p.y})`} className="territory-map-marker" role="button" tabIndex={0}
                aria-label={division.name} onPointerDown={(event) => event.stopPropagation()}
                onClick={(event) => { event.stopPropagation(); onDivisionClick(division) }}
                onPointerEnter={() => setHovered(division.name)} onPointerLeave={() => setHovered(null)}>
                <circle r={isCapital ? 12 : 8} fill={color} fillOpacity=".18" />
                <circle r={isCapital ? 5 : 3.3} fill={isCapital ? '#ffd789' : '#d3f7ff'} stroke="#071522" strokeWidth="2" />
                <text x="0" y={isCapital ? -16 : -11} textAnchor="middle" direction="rtl" className="territory-map-label" opacity={hovered === division.name || isCapital ? 1 : .74}>{division.name}</text>
              </g>
            )
          })}
          {layers.placements && (() => {
            const visible = placements.filter((placement) => (geo.polygons || []).some((ring) =>
              pointInRing(wrapLon(placement.lon, map.centerLon), placement.lat, ring)))
            const stacks = new Map<string, number>()
            const offsets: ProjectedPoint[] = [
              { x: 0, y: 0 }, { x: 23, y: 0 }, { x: 0, y: 23 }, { x: -23, y: 0 },
              { x: 0, y: -23 }, { x: 23, y: 23 }, { x: -23, y: 23 }, { x: 23, y: -23 }, { x: -23, y: -23 },
            ]
            return visible.map((placement) => {
              const p = placeOnMap(placement.lat, placement.lon, map)
              const stackKey = placement.city_name || `${placement.lat.toFixed(4)}:${placement.lon.toFixed(4)}`
              const stackIndex = stacks.get(stackKey) || 0
              stacks.set(stackKey, stackIndex + 1)
              const offset = offsets[stackIndex % offsets.length]
              return <StructureMarker key={placement.id} itemKey={placement.item_key}
                x={p.x + offset.x} y={p.y + offset.y} cityName={placement.city_name || ''} />
            })
          })()}
        </g>
        <text x="28" y="566" className="territory-map-scale">شبکهٔ جغرافیایی · مرز قلمرو برجسته</text>
        <text x="972" y="42" textAnchor="end" className="territory-map-north">N ↑</text>
      </svg>
      <div className="territory-map-legend" dir="rtl">
        <span><i className="legend-capital" /> پایتخت</span>
        <span><i className="legend-division" /> شهر و استان</span>
        <span><i className="legend-building" /> سازه‌ها ({placements.length})</span>
        <span className="territory-map-hint">برای جابه‌جایی بکشید · با دکمه‌ها بزرگ‌نمایی کنید</span>
      </div>
    </div>
  )
}
