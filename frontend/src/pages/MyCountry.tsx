import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Html, OrbitControls } from '@react-three/drei'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api, errMsg } from '../lib/api'
import { fmt } from '../lib/utils'
import earthDayUrl from '../assets/earth/earth-day.jpg'
import earthNightUrl from '../assets/earth/earth-night.jpg'
import earthWaterUrl from '../assets/earth/earth-water.png'
import cloudsUrl from '../assets/earth/clouds.png'
import { HologramGrid, OrbitalRings } from '../components/CinematicScene'
import TerritoryMap2D from '../components/TerritoryMap2D'

interface WorldGeoFeature {
  type: 'Feature'
  properties?: { name?: string; db_name?: string | null }
  geometry?: {
    type: 'Polygon' | 'MultiPolygon'
    coordinates: number[][][] | number[][][][]
  } | null
}
interface WorldGeoJson { type: 'FeatureCollection'; features: WorldGeoFeature[] }

type GeoPart = { outer: number[][]; holes: number[][][]; bbox: [number, number, number, number] }
type HoverCountry = { key: string; name: string; emoji?: string; parts: GeoPart[] }

// ==================== تایپ‌ها (از /api/my-map/ — Game Core) ====================
interface GeoPoly { kind: 'real' | 'imaginary'; polygons: number[][][]; center: [number, number]; bbox: number[]; span_deg: number; area_km2: number }
interface Division { name: string; kind: 'capital' | 'province' | 'city'; lat: number; lon: number }
interface Profile { display_name: string; flag_emoji: string; map_color: string; capital_name: string; government: string; imaginary: boolean; divisions: Division[] }
interface Territory { name: string; emoji: string; lat: number | null; lon: number | null; clat: number; clon: number; geo: GeoPoly; divisions: Division[]; profile: Profile }
interface Placement { id: number; item_key: string; suffix: string; qty: number; lat: number; lon: number; city_name?: string }
interface InvItem { key: string; name: string; icon: string; qty: number }
interface Stats {
  treasury: number; population: number; score: number; daily_profit: number
  income: { mines: number; economic: number; total: number }
  assets: { mines: Record<string, number>; economic: Record<string, number>; buildings: Record<string, number> }
  army: { attack: number; defense: number; categories: Record<string, { count: number; quality: number }>; ready_fighters: number; ready_helicopters: number }
  bases: { id: number; country: string; ready: boolean; ground: number; air: number }[]
  fleets: { outbound: number; returning: number }
  status: { viruses: string[]; sanction: { active: boolean; penalty: number; until: string | null }; on_fire: boolean }
  recent_battles: string[]
  notifications: { title: string; kind: string; at: string }[]
  combat_ready: boolean
}
interface MyMapData { territory: Territory[]; placements: Placement[]; stats: Stats }

const CONT_FA: Record<string, string> = {
  asia: 'آسیا', europe: 'اروپا', africa: 'آفریقا', north_america: 'آمریکای شمالی',
  south_america: 'آمریکای جنوبی', oceania: 'اقیانوسیه',
}
const GOVS = ['جمهوری', 'پادشاهی', 'امارات', 'فدراسیون', 'جمهوری خلق', 'دولت شهری']

function llToVec3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta))
}

// ==================== ابزار هندسه (همان موتور GlobeMap) ====================
function ringSignedArea(ring: number[][]): number {
  let a = 0
  for (let i = 0; i < ring.length; i++) {
    const p = ring[i], q = ring[(i + 1) % ring.length]
    a += p[0] * q[1] - q[0] * p[1]
  }
  return a / 2
}
function densifyRing(ring: number[][], maxDeg = 2): number[][] {
  const out: number[][] = []
  for (let i = 0; i < ring.length; i++) {
    const p = ring[i], q = ring[(i + 1) % ring.length]
    out.push(p)
    const d = Math.hypot(q[0] - p[0], q[1] - p[1])
    const n = Math.floor(d / maxDeg)
    for (let k = 1; k < n; k++) out.push([p[0] + ((q[0] - p[0]) * k) / n, p[1] + ((q[1] - p[1]) * k) / n])
  }
  return out
}
function unwrapRing(ring: number[][]): number[][] {
  const out: number[][] = []
  let prev = 0
  for (const pt of ring) {
    let lon = pt[0]
    while (lon - prev > 180) lon -= 360
    while (lon - prev < -180) lon += 360
    prev = lon
    out.push([lon, pt[1]])
  }
  return out
}
function prepareRing(ring0: number[][]): number[][] | null {
  if (!ring0 || ring0.length < 3) return null
  const wound = ringSignedArea(ring0) < 0 ? [...ring0].reverse() : ring0
  return densifyRing(unwrapRing(wound))
}
/** مثلث‌بندی تخت و projection روی کره — همان موتور GlobeMap با شعاع دلخواه */
function sphereGeoFromRing(ring0: number[][], radius: number): THREE.BufferGeometry | null {
  const dense = prepareRing(ring0)
  if (!dense) return null
  const shape = new THREE.Shape()
  dense.forEach((pt, i) => { if (i === 0) shape.moveTo(pt[0], pt[1]); else shape.lineTo(pt[0], pt[1]) })
  shape.closePath()
  const geoBuf = new THREE.ShapeGeometry(shape)
  const pos = geoBuf.attributes.position as THREE.BufferAttribute
  for (let i = 0; i < pos.count; i++) {
    const v = llToVec3(pos.getY(i), pos.getX(i), radius)
    pos.setXYZ(i, v.x, v.y, v.z)
  }
  pos.needsUpdate = true
  return geoBuf
}
function ringToPoints(ring: number[][], radius: number): THREE.Vector3[] {
  const dense = prepareRing(ring)
  return dense ? dense.map((pt) => llToVec3(pt[1], pt[0], radius)) : []
}

function bboxForRing(ring: number[][]): [number, number, number, number] {
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity
  for (const [lon, lat] of ring) {
    minLon = Math.min(minLon, lon); minLat = Math.min(minLat, lat)
    maxLon = Math.max(maxLon, lon); maxLat = Math.max(maxLat, lat)
  }
  return [minLon, minLat, maxLon, maxLat]
}

function pointInRing(lon: number, lat: number, ring: number[][]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (((yi > lat) !== (yj > lat)) &&
      (lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-12) + xi)) inside = !inside
  }
  return inside
}

function pointInPart(lon: number, lat: number, part: GeoPart): boolean {
  const lonCandidates = [lon, lon + 360, lon - 360]
  for (const candidate of lonCandidates) {
    const [minLon, minLat, maxLon, maxLat] = part.bbox
    if (candidate < minLon || candidate > maxLon || lat < minLat || lat > maxLat) continue
    if (!pointInRing(candidate, lat, part.outer)) continue
    if (part.holes.some((hole) => pointInRing(candidate, lat, hole))) return false
    return true
  }
  return false
}

function featureParts(feature: WorldGeoFeature): GeoPart[] {
  const g = feature.geometry
  if (!g) return []
  const polys: number[][][][] = g.type === 'Polygon' ? [g.coordinates as number[][][]] : g.coordinates as number[][][][]
  return polys
    .filter((poly) => poly.length > 0 && poly[0]?.length >= 3)
    .map((poly) => {
      const outer = unwrapRing(poly[0])
      return { outer, holes: poly.slice(1).map(unwrapRing), bbox: bboxForRing(outer) }
    })
}

// ==================== 🎬 دوربین سینمایی — پرواز easing از فضا به کشور ====================
const EASE = {
  // easeInOutCubic + easeOutQuart برای فازهای مختلف پرواز
  inOut: (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  out: (t: number) => 1 - Math.pow(1 - t, 4),
}

type FlightPhase = 'orbit' | 'diving' | 'done'

function CameraFlight({ target, span, phase, skip, globeRef }: {
  target: [number, number] | null; span: number; phase: FlightPhase; skip: boolean; globeRef: { current: THREE.Group | null }
}) {
  const { camera } = useThree()
  const t = useRef(0)
  const start = useRef<THREE.Vector3 | null>(null)
  useFrame((_, delta) => {
    if (!target || phase !== 'diving') return
    if (!start.current) { start.current = camera.position.clone(); t.current = 0 }
    t.current = Math.min(1, t.current + (skip ? delta * 6 : delta / 3.2))
    const e = skip ? 1 : EASE.inOut(t.current)
    // مسیر: قوس بزرگ بالا رفتن (فضا) → شیرجه به کشور (بر اساس span واقعی جغرافیایی)
    const destLocal = llToVec3(target[0], target[1], 1.18 + Math.min(1.2, span * 0.05))
    const arcLocal = llToVec3(target[0], target[1], 1)
    const dest = globeRef.current ? globeRef.current.localToWorld(destLocal) : destLocal
    const arcTop = (globeRef.current ? globeRef.current.localToWorld(arcLocal) : arcLocal).normalize().multiplyScalar(4.6)
    const pos = new THREE.Vector3()
    if (e < 0.45) {
      // فاز ۱: چرخش در مدار و بالا رفتن
      const k = EASE.out(e / 0.45)
      pos.copy(start.current!).lerp(arcTop, k)
    } else {
      // فاز ۲: شیرجه منحنی به مقصد
      const k = EASE.inOut((e - 0.45) / 0.55)
      pos.copy(arcTop).lerp(dest, k)
    }
    // نوسان ملایم ابر/نفس در کل مسیر
    camera.position.copy(pos)
    camera.lookAt(0, 0, 0)
  })
  return null
}

// ==================== 🌍 مرزهای واقعی جهان روی همان Globe ====================
function WorldCountryLayer({ currentCountry, globeRef }: { currentCountry: string | null; globeRef: { current: THREE.Group | null } }) {
  const [worldGeo, setWorldGeo] = useState<WorldGeoJson | null>(null)
  const [hovered, setHovered] = useState<HoverCountry | null>(null)
  const { camera, gl } = useThree()
  const hoverScratch = useMemo(() => ({
    raycaster: new THREE.Raycaster(),
    pointer: new THREE.Vector2(),
    sphere: new THREE.Sphere(new THREE.Vector3(0, 0, 0), 1),
    hit: new THREE.Vector3(),
  }), [])

  useEffect(() => {
    let alive = true
    api.get('/world/borders/').then(({ data }) => {
      if (alive) setWorldGeo(data)
    }).catch(() => {})
    return () => { alive = false }
  }, [])

  const countries = useMemo<HoverCountry[]>(() => {
    if (!worldGeo?.features) return []
    return worldGeo.features.map((f, index) => ({
      key: `${f.properties?.db_name || f.properties?.name || 'country'}-${index}`,
      name: f.properties?.db_name || f.properties?.name || 'Unknown',
      parts: featureParts(f),
    })).filter((x) => x.parts.length > 0)
  }, [worldGeo])

  const findCountryAt = (lat: number, lon: number) => {
    for (const country of countries) {
      if (country.parts.some((part) => pointInPart(lon, lat, part))) return country
    }
    return null
  }

  useEffect(() => {
    if (!countries.length) return
    const canvas = gl.domElement
    const onMove = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect()
      hoverScratch.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      hoverScratch.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
      // The canvas ray is in world space. Convert the hit into the rotating globe's local space
      // so geographic longitude/latitude always stay aligned with the Earth texture.
      hoverScratch.raycaster.setFromCamera(hoverScratch.pointer, camera)
      if (!hoverScratch.raycaster.ray.intersectSphere(hoverScratch.sphere, hoverScratch.hit)) {
        setHovered(null)
        return
      }
      const localHit = hoverScratch.hit.clone()
      globeRef.current?.worldToLocal(localHit)
      localHit.normalize()
      const lat = 90 - (Math.acos(Math.max(-1, Math.min(1, localHit.y))) * 180) / Math.PI
      let lon = (Math.atan2(localHit.z, -localHit.x) * 180) / Math.PI - 180
      lon = ((lon + 540) % 360) - 180
      setHovered(findCountryAt(lat, lon))
    }
    const onLeave = () => setHovered(null)
    canvas.addEventListener('pointermove', onMove)
    canvas.addEventListener('pointerleave', onLeave)
    return () => {
      canvas.removeEventListener('pointermove', onMove)
      canvas.removeEventListener('pointerleave', onLeave)
    }
  }, [camera, countries, gl, globeRef, hoverScratch])

  const rendered = useMemo(() => {
    const normal: { key: string; geometry: THREE.BufferGeometry }[] = []
    const bold: { key: string; geometry: THREE.BufferGeometry }[] = []
    for (const country of countries) {
      const isBold = country.name === currentCountry || country.key === hovered?.key
      for (const [partIndex, part] of country.parts.entries()) {
        const rings = [part.outer, ...part.holes]
        for (const [ringIndex, ring] of rings.entries()) {
          const dense = densifyRing(ring, 2)
          if (dense.length < 2) continue
          const g = new THREE.BufferGeometry().setFromPoints(dense.map((pt) => llToVec3(pt[1], pt[0], isBold ? 1.010 : 1.003)))
          ;(isBold ? bold : normal).push({ key: `${country.key}-${partIndex}-${ringIndex}`, geometry: g })
        }
      }
    }
    return { normal, bold }
  }, [countries, currentCountry, hovered?.key])

  return (
    <>
      {rendered.normal.map((line) => (
        <primitive key={`n-${line.key}`} object={new THREE.Line(
          line.geometry,
          new THREE.LineBasicMaterial({ color: '#b9d3e8', transparent: true, opacity: 0.45, depthWrite: false }),
        )} />
      ))}
      {rendered.bold.map((line) => (
        <primitive key={`b-${line.key}`} object={new THREE.Line(
          line.geometry,
          new THREE.LineBasicMaterial({
            color: line.key.startsWith(`${hovered?.key}-`) ? '#fff1a8' : '#67d8ff',
            transparent: true, opacity: 0.98, depthWrite: false,
          }),
        )} />
      ))}
      {hovered && (
        <Html position={llToVec3(
          hovered.parts[0].outer.reduce((sum, p) => sum + p[1], 0) / Math.max(1, hovered.parts[0].outer.length),
          hovered.parts[0].outer.reduce((sum, p) => sum + p[0], 0) / Math.max(1, hovered.parts[0].outer.length),
          1.025,
        )} distanceFactor={8} center zIndexRange={[20, 0]}>
          <div className="pointer-events-none select-none whitespace-nowrap rounded-lg border border-gold-400/60 bg-night-950/95 px-2.5 py-1 text-[11px] font-black text-gold-200 shadow-xl backdrop-blur">
            🌍 {hovered.name}
          </div>
        </Html>
      )}
    </>
  )
}

// ==================== 🌍 کره جهانی — نقطه شروع سینمایی ====================
function GlobeScene({ spin, currentCountry, globeRef }: { spin: boolean; currentCountry: string | null; globeRef: { current: THREE.Group | null } }) {
  const mesh = useRef<THREE.Mesh>(null)
  const clouds = useRef<THREE.Mesh>(null)
  const [tex, setTex] = useState<{day: THREE.Texture; night: THREE.Texture; water: THREE.Texture; clouds: THREE.Texture} | null>(null)
  const [earthMat, setEarthMat] = useState<THREE.ShaderMaterial | null>(null)
  useEffect(() => {
    let alive = true
    const loader = new THREE.TextureLoader()
    Promise.all([loader.loadAsync(earthDayUrl), loader.loadAsync(earthNightUrl), loader.loadAsync(earthWaterUrl), loader.loadAsync(cloudsUrl)]).then(([day, night, water, cloud]) => {
      if (!alive) return
      for (const t of [day, night, water, cloud]) { t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8 }
      setTex({ day, night, water, clouds: cloud })
    }).catch(() => {})
    return () => { alive = false }
  }, [])
  useFrame((state, d) => {
    if (globeRef.current && spin) globeRef.current.rotation.y += d * 0.055
    if (clouds.current) clouds.current.rotation.y += d * 0.073
    if (earthMat) {
      const cam = state.camera.position.clone().normalize()
      earthMat.uniforms.sunDir.value.lerp(cam, 0.022).normalize()
    }
  })
  useEffect(() => {
    if (!tex) return
    const m = new THREE.ShaderMaterial({
      uniforms: { dayMap: { value: tex.day }, nightMap: { value: tex.night }, waterMap: { value: tex.water }, sunDir: { value: new THREE.Vector3(1, 0.25, 0.55).normalize() } },
      vertexShader: `varying vec3 vNormalW; varying vec2 vUv; void main(){ vUv=uv; vNormalW=normalize(mat3(modelMatrix)*normal); gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
      fragmentShader: `uniform sampler2D dayMap; uniform sampler2D nightMap; uniform sampler2D waterMap; uniform vec3 sunDir; varying vec3 vNormalW; varying vec2 vUv; void main(){ vec3 n=normalize(vNormalW); float ndl=dot(n,sunDir); float day=smoothstep(-0.1,0.28,ndl); vec3 d=texture2D(dayMap,vUv).rgb; vec3 night=texture2D(nightMap,vUv).rgb*1.18; float w=texture2D(waterMap,vUv).r; float spec=pow(max(dot(n,normalize(sunDir+normalize(cameraPosition))),0.0),38.0)*w*day; vec3 col=mix(night,d*1.08,day); col+=vec3(0.28,0.55,0.82)*spec*0.55; float rim=pow(1.0-max(dot(n,normalize(cameraPosition)),0.0),3.2); col+=vec3(0.12,0.38,0.7)*rim*0.34; gl_FragColor=vec4(col,1.0); #include <colorspace_fragment> }`,
    })
    setEarthMat(m)
    return () => { m.dispose(); setEarthMat((current) => current === m ? null : current) }
  }, [tex])
  return (
    <group ref={globeRef}>
      <mesh ref={mesh}>
        <sphereGeometry args={[0.995, 128, 128]} />
        {earthMat ? <primitive object={earthMat} attach="material" /> : <meshStandardMaterial color="#0b1c33" roughness={0.86} />}
      </mesh>
      {tex && <mesh ref={clouds} scale={1.012}>
        <sphereGeometry args={[0.995, 72, 72]} />
        <meshBasicMaterial map={tex.clouds} transparent opacity={0.18} depthWrite={false} />
      </mesh>}
      <mesh scale={1.065}>
        <sphereGeometry args={[0.995, 72, 72]} />
        <meshBasicMaterial color="#52b9ff" transparent opacity={0.075} side={THREE.BackSide} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      <OrbitalRings radius={1.05} color="#59d9ff" intensity={0.92} />
      <HologramGrid radius={1.08} />
      <WorldCountryLayer currentCountry={currentCountry} globeRef={globeRef} />
    </group>
  )
}

// ==================== 🗺 نمای کشور — لایه‌ها و تعامل ====================
type LayerKey = 'terrain' | 'divisions' | 'placements' | 'neighbors'

function ClickCatcher({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  // گارد درگ: کلیک واقعی ≠ چرخش OrbitControls (فاصله pointerdown تا click)
  const down = useRef<{ x: number; y: number } | null>(null)
  return (
    <mesh
      visible={false}
      onPointerDown={(e) => { down.current = { x: e.clientX ?? 0, y: e.clientY ?? 0 } }}
      onClick={(e) => {
        const d = down.current
        if (d && Math.hypot((e.clientX ?? 0) - d.x, (e.clientY ?? 0) - d.y) > 6) return
        const p = e.point.clone().normalize()
        const lat = 90 - (Math.acos(p.y) * 180) / Math.PI
        let lon = ((Math.atan2(p.z, -p.x) * 180) / Math.PI) - 180
        lon = ((lon + 540) % 360) - 180
        onPick(Number(lat.toFixed(2)), Number(lon.toFixed(2)))
      }}
    >
      <sphereGeometry args={[1.008, 48, 48]} />
      <meshBasicMaterial />
    </mesh>
  )
}

function CountryScene({ t, placements, layers, onPlace, color, onDivClick, hoveredDiv }: {
  t: Territory
  placements: Placement[]
  layers: Record<LayerKey, boolean>
  onPlace: (lat: number, lon: number) => void
  color: string
  onDivClick: (d: Division) => void
  hoveredDiv: Division | null
}) {
  const geo = t.geo
  const R = 1.0
  const polys = geo.polygons
  const fillGeos = useMemo(
    () => polys.map((p, i) => ({ i, geo: sphereGeoFromRing(p, R * 1.004) })).filter((x) => x.geo),
    [polys])
  const edgeLines = useMemo(
    () => polys.map((p, i) => ({ i, pts: ringToPoints(p, R * 1.008) })).filter((x) => x.pts.length > 1),
    [polys])
  const placingMode = layers.divisions === false // وقتی انتخاب سازه فعال است

  return (
    <group>
      <OrbitalRings radius={1.025} color={color} intensity={0.62} />
      <mesh scale={1.055}>
        <sphereGeometry args={[R, 72, 72]} />
        <meshBasicMaterial color={color} transparent opacity={0.05} side={THREE.BackSide} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      {/* زمین تیره (اقیانوس) */}
      <mesh>
        <sphereGeometry args={[R, 64, 64]} />
        <meshStandardMaterial color="#0a1830" roughness={0.95} />
      </mesh>
      {/* همسایه‌ها — خطوط محو قاره */}
      {layers.neighbors && (
        <mesh>
          <sphereGeometry args={[R * 1.001, 64, 64]} />
          <meshBasicMaterial color="#14365c" wireframe transparent opacity={0.08} />
        </mesh>
      )}
      {/* قلمرو کشور — fill طلایی/رنگی + خطوط ساحلی */}
      {fillGeos.map(({ i, geo: g }) => (
        <mesh key={i} geometry={g!}>
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35}
            transparent opacity={0.55} side={THREE.DoubleSide} />
        </mesh>
      ))}
      {edgeLines.map(({ i, pts }) => (
        <primitive key={i} object={new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(pts),
          new THREE.LineBasicMaterial({ color: '#ffd9a0', transparent: true, opacity: 0.9 }))} />
      ))}
      {/* تقسیمات (استان/شهر/پایتخت) — قابل کلیک */}
      {layers.divisions && t.divisions.map((d) => (
        <DivisionPin key={d.name} d={d} color={color} onClick={() => onDivClick(d)} hovered={hoveredDiv?.name === d.name} />
      ))}
      {/* سازه‌های جای‌گذاری‌شده */}
      {layers.placements && placements.map((p) => (
        <group key={p.id} position={llToVec3(p.lat, p.lon, R * 1.02)}>
          <mesh>
            <boxGeometry args={[0.022, 0.022, 0.022]} />
            <meshBasicMaterial color="#38bdf8" />
          </mesh>
          <Html distanceFactor={6} center zIndexRange={[10, 0]}>
            <div className="pointer-events-none whitespace-nowrap bg-night-900/95 border border-sky-500/40 rounded px-1.5 py-0.5 text-[9px] text-sky-200">
              📍 {p.item_key} ×{p.qty}
            </div>
          </Html>
        </group>
      ))}
      <ClickCatcher onPick={onPlace} />
      {placingMode && null}
    </group>
  )
}

function DivisionPin({ d, color, onClick, hovered }: { d: Division; color: string; onClick: () => void; hovered: boolean }) {
  const [h, setH] = useState(false)
  const isCap = d.kind === 'capital'
  return (
    <group position={llToVec3(d.lat, d.lon, 1.016)}>
      <mesh onClick={(e) => { e.stopPropagation(); onClick() }}
        onPointerOver={(e) => { e.stopPropagation(); setH(true) }}
        onPointerOut={() => setH(false)}
        scale={isCap ? 1.4 : 1}>
        {isCap ? <octahedronGeometry args={[0.016]} /> : <sphereGeometry args={[0.011, 8, 8]} />}
        <meshBasicMaterial color={isCap ? '#fbbf24' : color} />
      </mesh>
      {(h || hovered) && (
        <Html distanceFactor={6} center zIndexRange={[10, 0]}>
          <div className={`pointer-events-none whitespace-nowrap rounded px-1.5 py-0.5 text-[9px] font-bold bg-night-900/95 border ${isCap ? 'border-gold-500/50 text-gold-200' : 'border-white/20 text-slate-200'}`}>
            {isCap ? '★ ' : d.kind === 'province' ? '🏙 ' : '🏘 '}{d.name}
          </div>
        </Html>
      )}
    </group>
  )
}

// ==================== داشبورد — تب‌ها، همگی متصل به stats ====================
const ARMY_FA: Record<string, string> = {
  tank: 'تانک', fighter: 'جنگنده', helicopter: 'بالگرد', drone: 'پهپاد', navy: 'ناو',
  submarine: 'زیردریایی', missile: 'موشک', artillery: 'توپخانه', air_defense: 'پدافند', ground: 'نیروی زمینی',
}

function StatCard({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: 'gold' | 'sky' | 'red' | 'green' }) {
  const tones: Record<string, string> = {
    gold: 'border-gold-500/40 text-gold-300', sky: 'border-sky-500/40 text-sky-300',
    red: 'border-danger-500/40 text-danger-300', green: 'border-success-500/40 text-success-300',
  }
  return (
    <div className={`glass-card p-3 ${tones[tone || 'sky'] || tones.sky}`}>
      <div className="text-[10px] text-slate-500">{label}</div>
      <div className="text-lg font-black">{value}</div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  )
}

function ArmyPanel({ stats }: { stats: Stats }) {
  const data = Object.entries(stats.army.categories).map(([k, v]) => ({
    name: ARMY_FA[k] || k, count: v.count, quality: v.quality,
  }))
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="⚔️ قدرت حمله" value={fmt(stats.army.attack)} tone="red" />
        <StatCard label="🛡 دفاع" value={fmt(stats.army.defense)} tone="green" />
        <StatCard label="✈️ جنگنده آماده (با خلبان)" value={fmt(stats.army.ready_fighters)} />
        <StatCard label="🚁 بالگرد آماده" value={fmt(stats.army.ready_helicopters)} />
      </div>
      {data.length > 0 ? (
        <div className="glass-card p-3">
          <div className="text-xs font-bold text-slate-300 mb-2">ترکیب نیروها</div>
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={data} layout="vertical" margin={{ left: 8, right: 12 }}>
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" width={80} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid #334155', borderRadius: 8, fontSize: 11 }}
                formatter={(v: number) => fmt(v)} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {data.map((d, i) => <Cell key={i} fill={d.quality >= 1.2 ? '#f59e0b' : d.quality >= 0.8 ? '#38bdf8' : '#64748b'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="text-[10px] text-slate-500 mt-1">● طلایی: کیفیت ≥ ۱.۲ · آبی: ≥ ۰.۸ · خاکستری: کمتر</div>
        </div>
      ) : (
        <div className="glass-card p-4 text-center text-xs text-slate-500">هنوز نیرویی ندارید — از <a href="/shop" className="text-primary-400 underline">فروشگاه</a> خرید کنید</div>
      )}
    </div>
  )
}

function EconomyPanel({ stats, color }: { stats: Stats; color: string }) {
  const m = stats.assets.mines
  const e = stats.assets.economic
  const rows = [
    ...Object.entries(m).map(([k, v]) => ({ key: k, kind: 'معدن', qty: v })),
    ...Object.entries(e).map(([k, v]) => ({ key: k, kind: 'شرکت', qty: v })),
  ]
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <StatCard label="💰 خزانه" value={fmt(stats.treasury)} tone="gold" />
        <StatCard label="📈 سود روزانه" value={fmt(stats.daily_profit)} tone="green" />
        <StatCard label="👥 جمعیت" value={fmt(stats.population)} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="⛏️ درآمد معادن" value={fmt(stats.income.mines)} />
        <StatCard label="🏢 درآمد شرکت‌ها" value={fmt(stats.income.economic)} />
      </div>
      {rows.length > 0 && (
        <div className="glass-card p-3 space-y-1">
          <div className="text-xs font-bold text-slate-300 mb-1">دارایی‌های اقتصادی</div>
          {rows.map((r) => (
            <div key={r.key} className="flex items-center justify-between bg-white/5 rounded-lg px-2.5 py-1.5 text-xs">
              <span className="truncate text-slate-300">{r.key} <span className="text-[10px] text-slate-600">({r.kind})</span></span>
              <span className="font-bold" style={{ color }}>×{fmt(r.qty)}</span>
            </div>
          ))}
        </div>
      )}
      <div className="glass-card p-3 text-xs space-y-1">
        <div className="flex justify-between"><span className="text-slate-500">امتیاز کشور</span><span className="font-bold">{fmt(stats.score)}</span></div>
        <div className="flex justify-between"><span className="text-slate-500">⚔️ ناوگان دریایی</span><span className="font-bold">{fmt(stats.fleets.outbound)} در مسیر · {fmt(stats.fleets.returning)} برگشت</span></div>
        <div className="flex justify-between"><span className="text-slate-500">🏕 پایگاه‌ها</span><span className="font-bold">{fmt(stats.bases.length)}</span></div>
      </div>
    </div>
  )
}

function StatusPanel({ stats }: { stats: Stats }) {
  const st = stats.status
  return (
    <div className="space-y-3">
      {(st.viruses.length > 0 || st.sanction.active || st.on_fire) && (
        <div className="glass-card p-3 space-y-1.5 !border-danger-500/40">
          <div className="text-xs font-black text-danger-300">⚠️ وضعیت‌های فعال</div>
          {st.viruses.map((v) => <div key={v} className="text-xs text-danger-200">🦠 ویروس {v} فعال است</div>)}
          {st.sanction.active && <div className="text-xs text-danger-200">🚫 تحریم فعال — جریمه {fmt(st.sanction.penalty)}٪ روی قیمت خرید</div>}
          {st.on_fire && <div className="text-xs text-danger-200">🔥 کشور زیر آتش است — تولید و درآمد آسیب دیده</div>}
        </div>
      )}
      <div className="glass-card p-3">
        <div className="text-xs font-bold text-slate-300 mb-1.5">🏕 پایگاه‌ها ({fmt(stats.bases.length)})</div>
        {stats.bases.length === 0 && <div className="text-xs text-slate-500">پایگاهی ندارید</div>}
        <div className="space-y-1">
          {stats.bases.map((b) => (
            <div key={b.id} className="flex items-center justify-between bg-white/5 rounded-lg px-2.5 py-1.5 text-xs">
              <span>{b.ready ? '✅' : '⏳'} {b.country}</span>
              <span className="text-[10px] text-slate-500">🥷 {fmt(b.ground)} · ✈️ {fmt(b.air)}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="glass-card p-3">
        <div className="text-xs font-bold text-slate-300 mb-1.5">⚔️ آخرین نبردها</div>
        {stats.recent_battles.length === 0 && <div className="text-xs text-slate-500">نبردی ثبت نشده</div>}
        <div className="space-y-1">
          {stats.recent_battles.map((b, i) => (
            <div key={i} className="text-[11px] text-slate-400 border-r-2 border-danger-500/30 pr-2 py-0.5 leading-5">{b}</div>
          ))}
        </div>
      </div>
      <div className="glass-card p-3">
        <div className="text-xs font-bold text-slate-300 mb-1.5">🔔 اعلان‌ها</div>
        {stats.notifications.length === 0 && <div className="text-xs text-slate-500">اعلانی نیست</div>}
        <div className="space-y-1">
          {stats.notifications.map((n, i) => (
            <div key={i} className="text-[11px] text-slate-400 truncate">· {n.title}</div>
          ))}
        </div>
      </div>
    </div>
  )
}

function CustomizePanel({ t, onSave, msg }: {
  t: Territory
  onSave: (fields: Record<string, string>) => void
  msg: string
}) {
  const p = t.profile
  const [name, setName] = useState(p.display_name)
  const [color, setColor] = useState(p.map_color)
  const [gov, setGov] = useState(p.government)
  const [capital, setCapital] = useState(p.capital_name)
  const [flag, setFlag] = useState(p.flag_emoji)
  useEffect(() => { setName(p.display_name); setColor(p.map_color); setGov(p.government); setCapital(p.capital_name); setFlag(p.flag_emoji) }, [t.name])
  const dirty = name !== p.display_name || color !== p.map_color || gov !== p.government || capital !== p.capital_name || flag !== p.flag_emoji
  return (
    <div className="space-y-3">
      <div className="glass-card p-3 space-y-2">
        <div className="text-xs font-bold text-slate-300">🎨 هویت کشور {p.imaginary && <span className="text-[10px] text-gold-400">· قلمرو خیالی</span>}</div>
        <label className="block text-[11px] text-slate-500">نام نمایشی کشور
          <input value={name} onChange={(e) => setName(e.target.value)} dir="rtl" maxLength={64}
            className="w-full mt-0.5 bg-night-900/80 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-primary-500/50" />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="block text-[11px] text-slate-500">پرچم (ایموجی)
            <input value={flag} onChange={(e) => setFlag(e.target.value)} dir="ltr" maxLength={8}
              className="w-full mt-0.5 bg-night-900/80 border border-white/10 rounded-lg px-2.5 py-1.5 text-lg text-center focus:outline-none focus:border-primary-500/50" />
          </label>
          <label className="block text-[11px] text-slate-500">رنگ نقشه
            <input type="color" value={/^#[0-9a-fA-F]{6}$/.test(color) ? color : '#38bdf8'} onChange={(e) => setColor(e.target.value)}
              className="w-full mt-0.5 h-9 bg-night-900/80 border border-white/10 rounded-lg cursor-pointer" />
          </label>
        </div>
        <label className="block text-[11px] text-slate-500">پایتخت (نام)
          <input value={capital} onChange={(e) => setCapital(e.target.value)} dir="rtl" maxLength={64}
            className="w-full mt-0.5 bg-night-900/80 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-primary-500/50" />
        </label>
        <label className="block text-[11px] text-slate-500">نوع حکومت
          <select value={gov} onChange={(e) => setGov(e.target.value)}
            className="w-full mt-0.5 bg-night-900/80 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none">
            {GOVS.map((g) => <option key={g} value={g} className="bg-night-900">{g}</option>)}
          </select>
        </label>
        <button onClick={() => onSave({ display_name: name, map_color: color, government: gov, capital_name: capital, flag_emoji: flag })}
          disabled={!dirty}
          className={`w-full !py-2 text-xs font-black rounded-lg transition ${dirty ? 'btn-primary' : 'bg-white/5 text-slate-600 cursor-not-allowed'}`}>
          {dirty ? '💾 ذخیره هویت کشور' : '✓ ذخیره شده'}
        </button>
        {msg && <div className="text-[11px] text-gold-300 text-center">{msg}</div>}
      </div>
      <div className="glass-card p-3">
        <div className="text-xs font-bold text-slate-300 mb-1.5">🗂 تقسیمات کشوری (سرور-پایدار)</div>
        <div className="space-y-1 max-h-52 overflow-y-auto">
          {t.divisions.map((d) => (
            <div key={d.name} className="flex items-center justify-between bg-white/5 rounded-lg px-2.5 py-1.5 text-xs">
              <span className="text-slate-300">{d.kind === 'capital' ? '★ ' : d.kind === 'province' ? '🏙 ' : '🏘 '}{d.name}</span>
              <span className="text-[10px] text-slate-600">{d.lat}, {d.lon}</span>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-slate-600 mt-2">موقعیت تقسیمات از هندسه واقعی/تولیدشده کشور برمی‌آید و بین بارگذاری‌ها ثابت است (seed-پایدار).</p>
      </div>
    </div>
  )
}

// ==================== صفحه اصلی ====================
type Tab = 'economy' | 'army' | 'status' | 'customize'

/** موقعیت دوربین رو به مرکز واقعی قلمرو (lat/lon از Game Core) */
function camPosFor(t: Territory): [number, number, number] {
  const [lat, lon] = t.geo.center
  return llToVec3(lat, lon, 2.6).toArray() as [number, number, number]
}

export default function MyCountry() {
  const [data, setData] = useState<MyMapData | null>(null)
  const [inv, setInv] = useState<Record<string, InvItem[]>>({})
  const [error, setError] = useState('')
  // سینما
  const [phase, setPhase] = useState<'orbit' | 'diving' | 'done'>('orbit')
  const [reducedMotion, setReducedMotion] = useState(false)
  const [skipHint, setSkipHint] = useState(false)
  const target = useRef<{ lat: number; lon: number; span: number } | null>(null)
  // نمای کشور
  const [activeIdx, setActiveIdx] = useState(0)
  const [tab, setTab] = useState<Tab>('economy')
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({ terrain: true, divisions: true, placements: true, neighbors: true })
  const [placing, setPlacing] = useState<(InvItem & { suffix: string }) | null>(null)
  const [cityPickerOpen, setCityPickerOpen] = useState(false)
  const [cityFormOpen, setCityFormOpen] = useState(false)
  const [cityDraft, setCityDraft] = useState('')
  const [cityBusy, setCityBusy] = useState(false)
  const [hoveredDiv, setHoveredDiv] = useState<Division | null>(null)
  const [msg, setMsg] = useState('')
  const [profileMsg, setProfileMsg] = useState('')
  // کره اصلی / نمای کشور
  const [globeMode, setGlobeMode] = useState<'globe' | 'country'>('country')
  const [buildMenuOpen, setBuildMenuOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data: mapData } = await api.get('/my-map/')
      setData(mapData)
      if (mapData.territory?.length) {
        const t0 = mapData.territory[0]
        target.current = { lat: t0.geo.center[0], lon: t0.geo.center[1], span: t0.geo.span_deg }
      }
      api.get('/equipment/').then(({ data: equipment }) => setInv(equipment.categories || {})).catch(() => {})
    } catch (e) {
      const response = (e as { response?: { status?: number } }).response
      setError(response ? errMsg(e) : 'Could not connect to the game server. Start the backend and retry.')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    void load()
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReducedMotion(mq.matches)
  }, [])

  const t = data?.territory[activeIdx]
  const stats = data?.stats
  const globeRef = useRef<THREE.Group>(null)

  // شروع انیمیشن ورود پس از لود
  useEffect(() => {
    if (globeMode === 'globe' && data && data.territory.length > 0 && phase === 'orbit') {
      setSkipHint(true)
      const delay = reducedMotion ? 0 : 400
      const tm = setTimeout(() => { setPhase('diving') }, delay)
      return () => clearTimeout(tm)
    }
  }, [globeMode, data, phase, reducedMotion])

  // پایان انیمیشن — وقتی دوربین به مقصد رسید (تایمر بر اساس مدت پرواز)
  useEffect(() => {
    if (phase !== 'diving') return
    const dur = reducedMotion ? 200 : 3400
    const tm = setTimeout(() => { setPhase('done'); setGlobeMode('country'); setSkipHint(false) }, dur)
    return () => clearTimeout(tm)
  }, [phase, reducedMotion])

  const place = async (city: Division) => {
    if (!placing) return
    try {
      const { data: res } = await api.post('/my-map/', {
        lat: city.lat, lon: city.lon, city_name: city.name,
        item_key: placing.key, suffix: placing.suffix, qty: 1,
      })
      setData((prev) => (prev ? { ...prev, placements: res.placements } : prev))
      setMsg(`${placing.name} ? ${city.name}`)
      setPlacing(null)
      setCityPickerOpen(false)
      setTimeout(() => setMsg(''), 3500)
    } catch (e) { setMsg(errMsg(e)); setTimeout(() => setMsg(''), 3500) }
  }
  const addCity = async () => {
    const name = cityDraft.trim()
    if (!t || !name || cityBusy) return
    setCityBusy(true)
    try {
      const { data: res } = await api.post('/my-map/country-profile/', { country: t.name, add_city: name })
      setData((prev) => prev ? {
        ...prev,
        territory: prev.territory.map((country) => country.name === res.country
          ? { ...country, divisions: res.profile.divisions, profile: { ...country.profile, ...res.profile } }
          : country),
      } : prev)
      setCityDraft('')
      setCityFormOpen(false)
      setMsg(`??? ?${name}? ?? ???? ????? ??`)
      setTimeout(() => setMsg(''), 3000)
    } catch (e) { setMsg(errMsg(e)); setTimeout(() => setMsg(''), 4000) }
    finally { setCityBusy(false) }
  }
  const removePlacement = async (id: number) => {
    try {
      const { data: res } = await api.delete('/my-map/', { data: { id } })
      setData((prev) => (prev ? { ...prev, placements: res.placements } : prev))
    } catch (e) { setMsg('❌ ' + errMsg(e)); setTimeout(() => setMsg(''), 3000) }
  }
  const saveProfile = async (fields: Record<string, string>) => {
    if (!t) return
    try {
      const { data: res } = await api.post('/my-map/country-profile/', { country: t.name, ...fields })
      setProfileMsg('✅ ذخیره شد')
      setTimeout(() => setProfileMsg(''), 2500)
      setData((prev) => {
        if (!prev) return prev
        const ter = [...prev.territory]
        const idx = ter.findIndex((x) => x.name === res.country)
        if (idx >= 0) ter[idx] = { ...ter[idx], divisions: res.profile.divisions || ter[idx].divisions, profile: { ...ter[idx].profile, ...res.profile } }
        return { ...prev, territory: ter }
      })
    } catch (e) { setProfileMsg('❌ ' + errMsg(e)); setTimeout(() => setProfileMsg(''), 3000) }
  }

  const placeable = useMemo(() => [
    ...(inv.building || []).map((i) => ({ ...i, suffix: 'count' })),
    ...(inv.mine || []).map((i) => ({ ...i, suffix: 'count' })),
    ...(inv.economic || []).map((i) => ({ ...i, suffix: 'count' })),
    ...(inv.defense || []).map((i) => ({ ...i, suffix: 'air_defense_count' })),
  ].map((item) => ({ ...item, qty: Math.max(0, item.qty - (data?.placements || [])
    .filter((placement) => placement.item_key === item.key && placement.suffix === item.suffix)
    .reduce((sum, placement) => sum + placement.qty, 0)) })).filter((i) => i.qty > 0), [inv, data?.placements])
  const cityChoices = useMemo(() => (t?.divisions || []).filter((d) => d.kind === 'city' || d.kind === 'capital'), [t])
  const customCityCount = useMemo(() => (t?.divisions || []).filter((d) => (d as Division & { custom?: boolean }).custom).length, [t])

  if (loading) return <div className="glass-card p-8 text-center text-slate-400">Loading your country map...</div>
  if (error) return <div className="glass-card p-8 text-center text-danger-300"><p>{error}</p><button className="btn-ghost mt-4" onClick={() => void load()}>Retry</button></div>

  // ===== نما ۱: کره سینمایی (orbit + diving) =====
  if (globeMode === 'globe') {
    return (
      <div className="relative w-full h-[80vh] min-h-[520px]">
        <div className="absolute inset-0 pointer-events-none cinematic-vignette" /><Canvas data-my-country-globe camera={{ position: [0, 0.6, 3.4], fov: 45 }} dpr={[1, 1.75]} gl={{ antialias: true }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[4, 2.5, 5]} intensity={1.6} color="#fdf6e3" />
          <directionalLight position={[-5, -2, -4]} intensity={0.25} color="#1e40af" />
          <GlobeScene spin={phase === 'orbit'} currentCountry={t?.name ?? null} globeRef={globeRef} />
          <CameraFlight target={target.current ? [target.current.lat, target.current.lon] : null}
            span={target.current?.span || 5} phase={phase} skip={reducedMotion}
            globeRef={globeRef} />
        </Canvas>
        {/* HUD سینمایی */}
        <div className="absolute top-5 inset-x-0 flex flex-col items-center gap-2 pointer-events-none z-10">
          <div className="cinematic-hud px-5 py-3 text-center">
            <div className="text-sm font-black text-gold-300">
              {phase === 'orbit' ? '🌍 در حال چرخش به سمت قلمرو شما…' : '🛬 در حال ورود به کشور…'}
            </div>
            {t && <div className="text-[11px] text-slate-400 mt-0.5">{t.emoji} {t.profile.display_name} · {t.geo.kind === 'imaginary' ? 'قلمرو خیالی' : 'کشور واقعی'}</div>}
          </div>
          {skipHint && phase === 'diving' && !reducedMotion && (
            <button onClick={() => { setPhase('done'); setGlobeMode('country'); setSkipHint(false) }}
              className="pointer-events-auto btn-ghost !py-1 !px-3 text-[11px] animate-pulse">
              ⏭ رد کردن انیمیشن
            </button>
          )}
        </div>
      </div>
    )
  }

  if (!t || !stats) return <div className="glass-card p-8 text-center text-slate-500">…</div>

  // ===== نما ۲: کشور + داشبورد =====
  const color = t.profile.map_color || '#38bdf8'
  return (
    <div className="space-y-4">
      {/* هدر کشور — بازگشت به کره + سوییچ قلمرو */}
      <div className="glass-card p-4 depth-card">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-3xl">{t.profile.flag_emoji || t.emoji}</span>
            <div>
              <div className="section-title !mb-0">{t.profile.display_name}
                {t.profile.imaginary && <span className="text-[10px] text-gold-400 mr-2">قلمرو خیالی</span>}
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {t.profile.government} · پایتخت: {t.profile.capital_name} · {fmt(t.geo.area_km2)} km²
                {data.territory.length > 1 && ` · قلمرو ${activeIdx + 1} از ${fmt(data.territory.length)}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            {data.territory.length > 1 && data.territory.map((x, i) => (
              <button key={x.name} onClick={() => setActiveIdx(i)}
                className={`px-2 py-1 rounded-md text-[10px] font-bold ${i === activeIdx ? 'bg-primary-500 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}>
                {x.emoji} {x.name}
              </button>
            ))}
            <button onClick={() => { setGlobeMode('globe'); setPhase('orbit') }}
              className="btn-ghost !py-1.5 !px-3 text-[11px]">🌍 بازگشت به کره</button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* نقشه کشور */}
        <div className="glass-card territory-map-card overflow-hidden relative lg:col-span-2">
          <TerritoryMap2D name={t.name} color={color} geo={t.geo} divisions={t.divisions}
            placements={data.placements} layers={layers} placing={false}
            onPlace={() => {}} onDivisionClick={(division) => {
              setHoveredDiv(division)
              setMsg(`${division.kind}: ${division.name}`)
              setTimeout(() => setMsg(''), 2600)
            }} />
          <div className="territory-map-layer-controls" dir="rtl">
            {([['terrain', '\u0639\u0648\u0627\u0631\u0636'], ['divisions', '\u0634\u0647\u0631\u0647\u0627'], ['placements', '\u0633\u0627\u0632\u0647\u200c\u0647\u0627']] as [LayerKey, string][]).map(([k, label]) => (
              <button key={k} type="button" onClick={() => setLayers((l) => ({ ...l, [k]: !l[k] }))}
                className={layers[k] ? 'is-active' : ''}>{label}</button>
            ))}
          </div>
          <div className="territory-map-build" dir="rtl">
            <button type="button" onClick={() => { setBuildMenuOpen((open) => !open); if (placing) setPlacing(null) }}
              className={`territory-map-build-toggle ${placing ? 'is-active' : ''}`}>
              {placing ? `\u062c\u0627\u06cc\u200c\u06af\u0630\u0627\u0631\u06cc ${placing.name}` : '\u0633\u0627\u062e\u062a\u200c\u0648\u0633\u0627\u0632'}
            </button>
            {buildMenuOpen && (
              <div className="territory-map-build-menu">
                <strong>{'\u0633\u0627\u0632\u0647 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646'}</strong>
                {placeable.length === 0 ? <p>{'\u0633\u0627\u0632\u0647\u200c\u0627\u06cc \u0628\u0631\u0627\u06cc \u0633\u0627\u062e\u062a \u0646\u062f\u0627\u0631\u06cc\u062f. \u0627\u0648\u0644 \u0627\u0632 \u0641\u0631\u0648\u0634\u06af\u0627\u0647 \u0628\u062e\u0631\u06cc\u062f.'}</p> : placeable.map((item) => (
                  <button type="button" key={item.key} onClick={() => { setPlacing(item); setCityPickerOpen(true); setBuildMenuOpen(false) }}>
                    <span className="territory-map-inventory-icon">{item.icon}</span><span>{item.name}</span><b>?{fmt(item.qty)}</b>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="territory-map-city-actions" dir="rtl">
            <button type="button" onClick={() => setCityFormOpen(true)} disabled={customCityCount >= 10}>
              <span>+</span> {'\u0627\u0641\u0632\u0648\u062f\u0646 \u0634\u0647\u0631'} <b>{customCityCount}/10</b>
            </button>
          </div>
          {cityFormOpen && (
            <div className="territory-map-modal-backdrop" dir="rtl" onMouseDown={(e) => { if (e.target === e.currentTarget) setCityFormOpen(false) }}>
              <form className="territory-map-city-modal" onSubmit={(e) => { e.preventDefault(); void addCity() }}>
                <div className="territory-map-modal-icon">{'\u2316'}</div>
                <strong>{'\u0633\u0627\u062e\u062a \u0634\u0647\u0631 \u062a\u0627\u0632\u0647'}</strong>
                <p>{'\u0645\u062e\u062a\u0635\u0627\u062a \u0634\u0647\u0631 \u062f\u0631 \u0642\u0644\u0645\u0631\u0648 \u062e\u0648\u062f\u062a \u062e\u0648\u062f\u06a9\u0627\u0631 \u067e\u06cc\u062f\u0627 \u0645\u06cc\u200c\u0634\u0648\u062f. \u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u06cc \u062a\u0627 \u06f1\u06f0 \u0634\u0647\u0631 \u0633\u0641\u0627\u0631\u0634\u06cc \u0627\u0636\u0627\u0641\u0647 \u06a9\u0646\u06cc.'}</p>
                <input autoFocus maxLength={48} value={cityDraft} onChange={(e) => setCityDraft(e.target.value)} placeholder={'\u0646\u0627\u0645 \u0634\u0647\u0631 \u062f\u0644\u062e\u0648\u0627\u0647'} dir="rtl" />
                <div className="territory-map-modal-actions">
                  <button type="button" onClick={() => setCityFormOpen(false)}>{'\u0627\u0646\u0635\u0631\u0627\u0641'}</button>
                  <button type="submit" disabled={!cityDraft.trim() || cityBusy || customCityCount >= 10}>{cityBusy ? '\u062f\u0631 \u062d\u0627\u0644 \u0633\u0627\u062e\u062a...' : '\u0627\u0641\u0632\u0648\u062f\u0646 \u0634\u0647\u0631'}</button>
                </div>
              </form>
            </div>
          )}
          {cityPickerOpen && placing && (
            <div className="territory-map-city-picker" dir="rtl">
              <div><strong>{'\u0627\u0646\u062a\u062e\u0627\u0628 \u0634\u0647\u0631'}</strong><button type="button" aria-label="Close" onClick={() => { setCityPickerOpen(false); setPlacing(null) }}>&times;</button></div>
              <p>{placing.name} {'\u0631\u0627 \u062f\u0631 \u06a9\u062f\u0627\u0645 \u0634\u0647\u0631 \u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u06cc \u0628\u0633\u0627\u0632\u06cc\u061f'}</p>
              <section>{cityChoices.map((city) => (
                <button type="button" key={`${city.kind}-${city.name}`} onClick={() => void place(city)}>
                  <span className="territory-map-city-pin">{city.kind === 'capital' ? '\u2726' : '\u2316'}</span>
                  <span>{city.name}<small>{city.kind === 'capital' ? '\u067e\u0627\u06cc\u062a\u062e\u062a' : '\u0634\u0647\u0631'}</small></span>
                  <b>{'\u0628\u0633\u0627\u0632 \u2190'}</b>
                </button>
              ))}</section>
              {cityChoices.length === 0 && <small>{'\u0627\u0628\u062a\u062f\u0627 \u06cc\u06a9 \u0634\u0647\u0631 \u0628\u0647 \u0642\u0644\u0645\u0631\u0648\u062a \u0627\u0636\u0627\u0641\u0647 \u06a9\u0646.'}</small>}
            </div>
          )}
          {msg && <div className="territory-map-toast" dir="rtl">{msg}</div>}
          {data.placements.length > 0 && (
            <div className="territory-map-placement-list" dir="rtl">
              <strong>{'\u0633\u0627\u0632\u0647\u200c\u0647\u0627\u06cc \u0646\u0635\u0628\u200c\u0634\u062f\u0647'} <span>{fmt(data.placements.length)}</span></strong>
              {data.placements.map((p) => (
                <div key={p.id}><span>{p.item_key} {"\u00D7"}{p.qty}{p.city_name ? ` \u00B7 ${p.city_name}` : ''}</span><button type="button" aria-label={`Remove ${p.item_key}`} onClick={() => removePlacement(p.id)}>{"\u00D7"}</button></div>
              ))}
            </div>
          )}
        </div>

        {/* داشبورد */}
        <div className="glass-card p-4 space-y-3">
          <div className="flex gap-1 flex-wrap">
            {([['economy', '💰 اقتصاد'], ['army', '⚔️ ارتش'], ['status', '📡 وضعیت'], ['customize', '🎨 شخصی‌سازی']] as [Tab, string][]).map(([k, label]) => (
              <button key={k} onClick={() => setTab(k)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition ${tab === k ? 'bg-primary-500 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}>
                {label}
              </button>
            ))}
          </div>
          <div className="animate-glow">
            {tab === 'economy' && <EconomyPanel stats={stats} color={color} />}
            {tab === 'army' && <ArmyPanel stats={stats} />}
            {tab === 'status' && <StatusPanel stats={stats} />}
            {tab === 'customize' && <CustomizePanel t={t} onSave={saveProfile} msg={profileMsg} />}
          </div>
        </div>
      </div>
    </div>
  )
}

