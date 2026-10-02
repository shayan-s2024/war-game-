import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import * as THREE from 'three'
import { api } from '../lib/api'
import { fmt, timeAgo } from '../lib/utils'
import earthDayUrl from '../assets/earth/earth-day.jpg'
import earthNightUrl from '../assets/earth/earth-night.jpg'
import earthWaterUrl from '../assets/earth/earth-water.png'
import cloudsUrl from '../assets/earth/clouds.png'
import { HologramGrid, OrbitalRings, Starfield as CinematicStarfield } from './CinematicScene'

// ==================== انواع داده (از /api/world/ — Game Core) ====================
interface CountryW {
  name: string; command_name?: string; imaginary?: boolean; emoji: string; continent: string; population: number
  taken: boolean; lat: number | null; lon: number | null
  clat: number; clon: number
  owner?: { name: string; username: string; union: string | null; score: number } | null
}
interface ContinentW { key: string; name: string; flag: string; lat: number; lon: number }
interface UnionW { id: number; name: string; level: number; owner: string; members: number; treasury: number; countries: string[] }
interface BaseW { id: number; country: string; emoji: string; continent: string; owner: string; username: string; lat: number | null; lon: number | null; ready: boolean; lat_fallback: number; lon_fallback: number }
interface BattleW { id: number; summary: string; attacker: string; defender: string; country: string | null; emoji: string; lat: number | null; lon: number | null; continent: string | null; created_at: string }
export interface FleetW {
  id: number; player: string; username: string; status: 'outbound' | 'returning'; progress: number
  origin: { name: string | null; lat: number | null; lon: number | null; clat: number; clon: number }
  target: { name: string | null; lat: number | null; lon: number | null; clat: number; clon: number }
  ships: Record<string, number>; loot: number; summary: string
  arrive_at: string | null; return_at: string | null
}
export interface AdminPlayerW { id: number; name: string; username: string; country: string | null; lat: number | null; lon: number | null; clat: number; clon: number; credit: number; score: number; army: number; online: boolean }
export interface AdminTxW { id: number; player: string; amount: number; reason: string; created_at: string; lat: number | null; lon: number | null }
export interface AdminBlock { players: AdminPlayerW[]; transactions: AdminTxW[]; battles_24h: number; total_players: number; total_credit: number }
export interface PlacementW { id: number; item_key: string; qty: number; player: string; username: string; lat: number; lon: number }
export interface WorldState {
  countries: CountryW[]; continents: ContinentW[]; unions: UnionW[]
  bases: BaseW[]; battles: BattleW[]
  fleets?: FleetW[]
  placements?: PlacementW[]
  is_staff?: boolean
  admin?: AdminBlock
  stats: { countries_total: number; countries_taken: number; players: number; online: number; bases: number; unions: number; battles_recent: number }
  updated_at: string
}

type MapMode = 'political' | 'military' | 'alliance' | 'conflict' | 'admin'
type Quality = 'low' | 'medium' | 'high' | 'ultra'
type SunState = { myCountry: string | null }

const QUALITY: Record<Quality, { seg: number; stars: number; aa: boolean; clouds: boolean; atmo: boolean; dpr: number }> = {
  low: { seg: 32, stars: 0, aa: false, clouds: false, atmo: true, dpr: 1 },
  medium: { seg: 64, stars: 900, aa: false, clouds: true, atmo: true, dpr: 1.25 },
  high: { seg: 96, stars: 2200, aa: true, clouds: true, atmo: true, dpr: 1.5 },
  ultra: { seg: 128, stars: 3800, aa: true, clouds: true, atmo: true, dpr: 2 },
}
// اگر ماسک آب معکوس بود (خشکی براق) → 1
const WATER_INVERT = 0
const QUALITY_FA: Record<Quality, string> = { low: 'کم', medium: 'متوسط', high: 'زیاد', ultra: 'اولترا' }
const MODE_FA: Record<MapMode, string> = { political: '🗺 سیاسی', military: '⚙️ نظامی', alliance: '🤝 اتحادها', conflict: '⚔️ درگیری‌ها', admin: '🛡 ادمین' }
const CONT_FA: Record<string, string> = {
  asia: 'آسیا', europe: 'اروپا', africa: 'آفریقا', north_america: 'آمریکای شمالی',
  south_america: 'آمریکای جنوبی', oceania: 'اقیانوسیه',
}

// 🛡 مارکر تراکنش لحظه‌ای روی Globe — فقط در حالت ادمین
function TxMarker({ t }: { t: AdminTxW }) {
  if (t.lat == null || t.lon == null) return null
  const pos = latLonToVec3(t.lat, t.lon, 2.02)
  const neg = t.amount < 0
  const ring = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (ring.current) ring.current.scale.setScalar(1 + ((clock.elapsedTime * 1.2) % 1) * 1.2)
  })
  return (
    <group position={pos}>
      <mesh><sphereGeometry args={[0.011, 8, 8]} /><meshBasicMaterial color={neg ? '#f97316' : '#22c55e'} /></mesh>
      <mesh ref={ring}><sphereGeometry args={[0.012, 8, 8]} /><meshBasicMaterial color={neg ? '#f97316' : '#22c55e'} transparent opacity={0.3} /></mesh>
    </group>
  )
}

function latLonToVec3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  )
}
function hashPos(name: string, baseLat: number, baseLon: number): [number, number] {
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 997
  return [baseLat + ((h % 23) - 11), baseLon + ((Math.floor(h / 23) % 29) - 14)]
}

// ==================== 🌍 لایه مرزهای واقعی (GeoJSON → three.js) ====================
// بالاتر از لایه ابر (2.024) تا مرزها همیشه واضح بمانند
const GEO_R = 2.028

/** مساحت علامت‌دار — برای تشخیص winding */
function ringSignedArea(ring: number[][]): number {
  let a = 0
  for (let i = 0; i < ring.length; i++) {
    const p = ring[i], q = ring[(i + 1) % ring.length]
    a += p[0] * q[1] - q[0] * p[1]
  }
  return a / 2
}

/** متراکم‌سازی یال‌های بلند — تا مثلث‌ها بعد از projection زیر سطح کره فرو نروند */
function densifyRing(ring: number[][], maxDeg = 5): number[][] {
  const out: number[][] = []
  for (let i = 0; i < ring.length; i++) {
    const p = ring[i]
    const q = ring[(i + 1) % ring.length]
    out.push(p)
    const d = Math.hypot(q[0] - p[0], q[1] - p[1])
    const n = Math.floor(d / maxDeg)
    for (let k = 1; k < n; k++) {
      out.push([p[0] + ((q[0] - p[0]) * k) / n, p[1] + ((q[1] - p[1]) * k) / n])
    }
  }
  return out
}

/** رینگ (lon,lat) → بردارهای سه‌بعدی برای خط ساحلی/مرز */
function latLonRingToPoints(ring: number[][], radius: number): THREE.Vector3[] {
  return ring.map((pt) => latLonToVec3(pt[1], pt[0], radius))
}

/** پیوسته‌سازی طول جغرافیایی — ضد خطای نصف‌النهار 180 (فیجی/روسیه/قطب) */
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

/** آماده‌سازی رینگ: winding + unwrap + densify */
function prepareRing(ring0: number[][]): number[][] | null {
  if (!ring0 || ring0.length < 3) return null
  const wound = ringSignedArea(ring0) < 0 ? [...ring0].reverse() : ring0
  return densifyRing(unwrapRing(wound))
}

/** مثلث‌بندی تخت (lon,lat) و بردن هر رأس روی کره — مرز واقعی بدون projection تخت */
function sphereGeoFromRing(ring0: number[][], radius: number = GEO_R): THREE.BufferGeometry | null {
  const dense = prepareRing(ring0)
  if (!dense) return null
  const shape = new THREE.Shape()
  dense.forEach((pt: number[], i: number) => {
    if (i === 0) shape.moveTo(pt[0], pt[1])
    else shape.lineTo(pt[0], pt[1])
  })
  shape.closePath()
  const geoBuf = new THREE.ShapeGeometry(shape)
  const pos = geoBuf.attributes.position as THREE.BufferAttribute
  for (let i = 0; i < pos.count; i++) {
    const v = latLonToVec3(pos.getY(i), pos.getX(i), radius) // shape.x=lon، shape.y=lat
    pos.setXYZ(i, v.x, v.y, v.z)
  }
  pos.needsUpdate = true
  return geoBuf
}

function GeoLayer({ world }: { world: WorldState }) {
  const [geo, setGeo] = useState<any>(null)
  useEffect(() => {
    api.get('/world/borders/').then(({ data }) => setGeo(data)).catch(() => {})
  }, [])
  const items = useMemo<{ fills: { key: string; geo: THREE.BufferGeometry; color: string }[]; edges: { key: string; geo: THREE.BufferGeometry; color: string }[] }>(() => {
    if (!geo?.features || !world) return { fills: [], edges: [] }
    const ownerMap: Record<string, unknown> = {}
    for (const c of world.countries) if (c.owner) ownerMap[c.name] = c.owner
    const fills: { key: string; geo: THREE.BufferGeometry; color: string }[] = []
    const edges: { key: string; geo: THREE.BufferGeometry; color: string }[] = []
    for (const f of geo.features) {
      const g = f.geometry
      if (!g) continue
      const db: string | null = f.properties?.db_name ?? null
      const taken = !!db && !!ownerMap[db]
      const fill = taken ? '#e8654f' : '#1f7a4d'
      const line = taken ? '#ffd9c9' : '#5eead4'
      const polys: number[][][][] = g.type === 'Polygon' ? [g.coordinates] : (g.coordinates || [])
      for (const poly of polys) {
        const ring = poly[0]
        const geoBuf = sphereGeoFromRing(ring)
        if (geoBuf) fills.push({ key: `${db || f.properties?.name || 'x'}_${fills.length}`, geo: geoBuf, color: fill })
        const dense = prepareRing(ring)
        const linePts = dense ? latLonRingToPoints(dense, GEO_R + 0.002) : []
        if (linePts.length >= 2) {
          const lg = new THREE.BufferGeometry().setFromPoints(linePts)
          edges.push({ key: `${db || f.properties?.name || 'x'}_e${edges.length}`, geo: lg, color: line })
        }
      }
    }
    return { fills, edges }
  }, [geo, world])
  if (!items.fills.length) return null
  return (
    <group>
      {items.fills.map((m) => (
        <mesh key={m.key} geometry={m.geo}>
          <meshBasicMaterial color={m.color} transparent opacity={0.2} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
      ))}
      {items.edges.map((m) => (
        <primitive key={m.key} object={new THREE.Line(m.geo, new THREE.LineBasicMaterial({ color: m.color, transparent: true, opacity: 0.75 }))} />
      ))}
    </group>
  )
}

// ==================== 🌍 Earth — شیدر روز/شب واقعی + specular اقیانوس ====================
// textureها: Blue Marble (NASA) + شب‌های شهری + ماسک آب — همه از npm pack (بدون دانلود مستقیم)
const EARTH_R = 2
// خورشید مشترک Earth + Atmosphere — هر فریم از دوربین محاسبه می‌شود (سمت دیده‌شده همیشه روز)
const SUN_DIR = new THREE.Vector3(1, 0.28, 0.6).normalize()

function makeEarthMaterial(waterTex: THREE.Texture | null, dayTex: THREE.Texture, nightTex: THREE.Texture) {
  return new THREE.ShaderMaterial({
    uniforms: {
      dayMap: { value: dayTex },
      nightMap: { value: nightTex },
      waterMap: { value: waterTex },
      sunDir: { value: SUN_DIR },
      waterInvert: { value: WATER_INVERT },
      nightBoost: { value: 1.35 },
    },
    vertexShader: /* glsl */ `
      varying vec3 vNormalW;
      varying vec2 vUv;
      void main() {
        vUv = uv;
        vNormalW = normalize(mat3(modelMatrix) * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D dayMap, nightMap, waterMap;
      uniform vec3 sunDir;
      uniform float waterInvert, nightBoost;
      varying vec3 vNormalW;
      varying vec2 vUv;
      void main() {
        vec3 n = normalize(vNormalW);
        float ndl = dot(n, sunDir);
        // ترمیناتور نرم (طول روز/شب واقعی)
        float dayAmt = smoothstep(-0.12, 0.25, ndl);
        vec3 dayCol = texture2D(dayMap, vUv).rgb;
        vec3 nightCol = texture2D(nightMap, vUv).rgb * nightBoost;
        // سمت شب: خطوط ساحلی کم‌نور + شهرها
        vec3 col = mix(nightCol * 0.9, dayCol * 1.08, dayAmt);
        // specular خورشید فقط روی آب (ماسک real) — برق اقیانوس
        float w = mix(texture2D(waterMap, vUv).r, 1.0 - texture2D(waterMap, vUv).r, waterInvert);
        vec3 viewDir = normalize(cameraPosition - (modelMatrix * vec4(0.0,0.0,0.0,1.0)).xyz);
        vec3 h = normalize(sunDir + viewDir);
        float spec = pow(max(dot(n, h), 0.0), 42.0) * w * dayAmt;
        col += vec3(0.45, 0.62, 0.75) * spec * 0.55;
        // گرمای لبه ترمیناتور (طلوع/غروب) — نوار نارنجی خیلی ظریف
        float term = smoothstep(0.22, 0.0, abs(ndl)) * dayAmt;
        col += vec3(0.30, 0.14, 0.02) * term * 0.6;
        gl_FragColor = vec4(col, 1.0);
        #include <colorspace_fragment>
      }`,
  })
}

function Earth({ quality, rotate, sun }: {
  quality: Quality; rotate: boolean; sun: SunState
}) {
  const cfg = QUALITY[quality]
  const earth = useRef<THREE.Group>(null)
  const clouds = useRef<THREE.Mesh>(null)
  const [texs, setTexs] = useState<{ day: THREE.Texture; night: THREE.Texture; water: THREE.Texture; clouds: THREE.Texture } | null>(null)
  const matRef = useRef<THREE.ShaderMaterial | null>(null)

  useEffect(() => {
    const loader = new THREE.TextureLoader()
    let alive = true
    Promise.all([
      loader.loadAsync(earthDayUrl),
      loader.loadAsync(earthNightUrl),
      loader.loadAsync(earthWaterUrl),
      loader.loadAsync(cloudsUrl),
    ]).then(([day, night, water, cl]) => {
      if (!alive) return
      for (const t of [day, night, water, cl]) { t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8 }
      setTexs({ day, night, water, clouds: cl })
    }).catch(() => {})
    return () => { alive = false }
  }, [])

  const earthMat = useMemo(() => {
    if (!texs) return null
    const m = makeEarthMaterial(texs.water, texs.day, texs.night)
    matRef.current = m
    return m
  }, [texs])

  // خورشید همیشه کمی بالاتر و چپِ دوربین — نیم‌کره قابل‌مشاهده روشن، ترمیناتور در لبه
  useFrame((state, delta) => {
    if (earth.current && rotate) earth.current.rotation.y += delta * 0.04
    if (clouds.current && rotate) clouds.current.rotation.y += delta * 0.055
    const camDir = state.camera.position.clone().normalize()
    SUN_DIR.copy(camDir).applyAxisAngle(new THREE.Vector3(0, 1, 0), 0.55)
    SUN_DIR.y += 0.18
    SUN_DIR.normalize()
  })

  const cloudSeg = Math.max(32, cfg.seg / 2)
  return (
    <>
      <group ref={earth} rotation={[0, 0, 0]}>
        <mesh>
          <sphereGeometry args={[EARTH_R, cfg.seg, cfg.seg]} />
          {earthMat ? <primitive object={earthMat} attach="material" /> : <meshStandardMaterial color="#0b2038" roughness={0.9} />}
        </mesh>
      </group>
      {/* لایه ابر واقعی — texture NASA، مستقل و کندتر از زمین */}
      {cfg.clouds && texs && (
        <mesh ref={clouds}>
          <sphereGeometry args={[EARTH_R * 1.012, cloudSeg, cloudSeg]} />
          <meshStandardMaterial alphaMap={texs.clouds} map={texs.clouds} transparent opacity={0.34} depthWrite={false} color="#ffffff" roughness={1} />
        </mesh>
      )}
      {/* highlight کشور خودم — ring نرم */}
      {sun.myCountry && <MyCountryRing name={sun.myCountry} />}
    </>
  )
}

// ==================== 🌫 جو — شیدر Fresnel دو لایه (ریم داخلی + هاله بیرونی) ====================
function Atmosphere({ quality }: { quality: Quality }) {
  const cfg = QUALITY[quality]
  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: { sunDir: { value: SUN_DIR } },
    vertexShader: /* glsl */ `
      varying vec3 vNormalW;
      varying vec3 vViewDir;
      void main() {
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vNormalW = normalize(mat3(modelMatrix) * normal);
        vViewDir = normalize(cameraPosition - wp.xyz);
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 sunDir;
      varying vec3 vNormalW;
      varying vec3 vViewDir;
      void main() {
        float f = pow(1.0 - abs(dot(normalize(vNormalW), normalize(vViewDir))), 3.2);
        // سمت خورشید آبی روشن‌تر — سمت شب تیره‌تر
        float lit = max(dot(normalize(vNormalW), normalize(sunDir)), 0.0);
        vec3 col = mix(vec3(0.05, 0.12, 0.30), vec3(0.35, 0.65, 1.0), lit);
        float a = f * (0.28 + lit * 0.42);
        gl_FragColor = vec4(col, a);
        #include <colorspace_fragment>
      }`,
    transparent: true,
    side: THREE.BackSide,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), [])
  return (
    <mesh scale={1.065}>
      <sphereGeometry args={[EARTH_R, Math.max(48, cfg.seg), Math.max(48, cfg.seg)]} />
      <primitive object={mat} attach="material" />
    </mesh>
  )
}

function MyCountryRing({ name }: { name: string }) {
  // نشانگر کشور خود بازیکن در موقعیتش (fallback: قاره)
  const [pos, setPos] = useState<THREE.Vector3 | null>(null)
  useEffect(() => {
    api.get('/dashboard/').then(({ data }) => {
      const cont = data.player?.continent
      if (cont) {
        api.get('/world/').then(({ data: w }) => {
          const c = w.continents.find((x: ContinentW) => x.key === cont)
          if (c) setPos(latLonToVec3(c.lat, c.lon, 2.05))
        }).catch(() => {})
      }
    }).catch(() => {})
  }, [name])
  if (!pos) return null
  return (
    <mesh position={pos}>
      <sphereGeometry args={[0.03, 12, 12]} />
      <meshBasicMaterial color="#fbbf24" transparent opacity={0.9} />
    </mesh>
  )
}

function Stars({ count }: { count: number }) {
  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const c = new THREE.Color()
    for (let i = 0; i < count; i++) {
      // کره ستاره‌ای واقعی — پخش روی پوسته کروی (نه مکعب)
      const r = 24 + Math.random() * 26
      const th = Math.random() * Math.PI * 2
      const ph = Math.acos(2 * Math.random() - 1)
      positions[i * 3] = r * Math.sin(ph) * Math.cos(th)
      positions[i * 3 + 1] = r * Math.cos(ph)
      positions[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th)
      // رنگ واقعی ستاره‌ها: سفید/آبی/کهربایی + قدر متنوع
      const k = Math.random()
      c.set(k < 0.72 ? '#cfd8ea' : k < 0.9 ? '#a8c4f0' : '#f0d9a8')
      const br = 0.35 + Math.pow(Math.random(), 2.4) * 0.65
      colors[i * 3] = c.r * br; colors[i * 3 + 1] = c.g * br; colors[i * 3 + 2] = c.b * br
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [count])
  return <points geometry={geometry}><pointsMaterial size={0.075} vertexColors sizeAttenuation transparent opacity={0.95} depthWrite={false} /></points>
}

// ==================== دوربین: Focus نرم + Reset ====================
function CameraRig({ target, dist }: { target: THREE.Vector3 | null; dist: number }) {
  const { camera } = useThree()
  useFrame(() => {
    if (target) {
      const goal = target.clone().normalize().multiplyScalar(dist)
      camera.position.lerp(goal, 0.07)
    }
  })
  return null
}

// ==================== Markerها (Instancing سبک با mesh های مشترک) ====================
function CountryMarker({ c, mode, myUnion, onSelect, isSelected }: {
  c: CountryW; mode: MapMode; myUnion: string | null
  onSelect: (c: CountryW) => void; isSelected: boolean
}) {
  const [hovered, setHovered] = useState(false)
  const lat = c.lat ?? c.clat
  const lon = c.lon ?? c.clon
  const pos = useMemo(() => latLonToVec3(lat, lon, 2.015), [lat, lon])

  // رنگ بر اساس Map Mode — دولت‌محور و خوانا
  let color = c.taken ? '#e8654f' : '#37b26c'                       // political: آزاد/صاحب‌دار
  if (mode === 'alliance') {
    color = c.owner?.union ? (c.owner.union === myUnion ? '#38bdf8' : '#a78bfa') : '#475569'
  } else if (mode === 'military') {
    color = c.owner ? '#f59e0b' : '#334155'
  } else if (mode === 'conflict') {
    color = c.taken ? '#ef4444' : '#14532d'
  }
  if (isSelected) color = '#fbbf24'
  const scale = isSelected ? 1.9 : hovered ? 1.5 : 1
  const size = c.taken ? 0.017 : 0.012

  return (
    <mesh position={pos} scale={scale}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
      onPointerOut={() => setHovered(false)}
      onClick={(e) => { e.stopPropagation(); onSelect(c) }}>
      <sphereGeometry args={[size, 8, 8]} />
      <meshBasicMaterial color={color} />
      {hovered && !isSelected && (
        <Html distanceFactor={7} center zIndexRange={[10, 0]}>
          <div className="pointer-events-none select-none whitespace-nowrap bg-night-900/95 border border-white/15 rounded-lg px-2.5 py-1 text-[11px] font-bold text-slate-100 shadow-xl backdrop-blur">
            {c.emoji} {c.name}
            <span className={`mr-2 text-[10px] ${c.owner ? 'text-danger-400' : 'text-success-400'}`}>
              {c.owner ? c.owner.name : 'آزاد'}
            </span>
          </div>
        </Html>
      )}
    </mesh>
  )
}

function BaseMarker({ b, onSelect }: { b: BaseW; onSelect: (b: BaseW) => void }) {
  const [hovered, setHovered] = useState(false)
  const pos = useMemo(() => {
    const lat = b.lat ?? b.lat_fallback, lon = b.lon ?? b.lon_fallback
    return latLonToVec3(lat, lon, 2.03)
  }, [b])
  const pulse = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (pulse.current) {
      const s = 1 + Math.sin(clock.elapsedTime * 3) * 0.25
      pulse.current.scale.setScalar(b.ready ? s : 0.8)
    }
  })
  return (
    <group position={pos}>
      <mesh
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
        onPointerOut={() => setHovered(false)}
        onClick={(e) => { e.stopPropagation(); onSelect(b) }}>
        <boxGeometry args={[0.03, 0.03, 0.03]} />
        <meshBasicMaterial color={b.ready ? '#38bdf8' : '#94a3b8'} />
      </mesh>
      <mesh ref={pulse} scale={1}>
        <sphereGeometry args={[0.028, 8, 8]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.25} />
      </mesh>
      {hovered && (
        <Html distanceFactor={7} center>
          <div className="pointer-events-none whitespace-nowrap bg-night-900/95 border border-sky-500/40 rounded-lg px-2 py-1 text-[10px] text-sky-200 font-bold">
            🏕 {b.country} — {b.owner}{b.ready ? '' : ' (در حال ساخت)'}
          </div>
        </Html>
      )}
    </group>
  )
}

function BattleMarker({ b, onSelect }: { b: BattleW; onSelect: (b: BattleW) => void }) {
  const [hovered, setHovered] = useState(false)
  const pos = useMemo(() => {
    if (b.lat != null && b.lon != null) return latLonToVec3(b.lat, b.lon, 2.05)
    return null
  }, [b])
  if (!pos) return null
  const ring = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (ring.current) ring.current.scale.setScalar(1 + ((clock.elapsedTime * 0.8) % 1) * 1.6)
  })
  return (
    <group position={pos}>
      <mesh onClick={(e) => { e.stopPropagation(); onSelect(b) }}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
        onPointerOut={() => setHovered(false)}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshBasicMaterial color="#ef4444" />
      </mesh>
      <mesh ref={ring}>
        <sphereGeometry args={[0.022, 10, 10]} />
        <meshBasicMaterial color="#ef4444" transparent opacity={0.3} />
      </mesh>
      {hovered && (
        <Html distanceFactor={7} center>
          <div className="pointer-events-none whitespace-nowrap bg-night-900/95 border border-danger-500/50 rounded-lg px-2 py-1 text-[10px] text-danger-200 font-bold max-w-52 truncate">
            ⚔ {b.summary}
          </div>
        </Html>
      )}
    </group>
  )
}

// ==================== ⚓ ناوگان متحرک — موقعیت زنده بین مبدأ و هدف (slerp) ====================
// slerp بین دو بردار واحد — مسیر بزرگ‌دایره‌ای روی سطح کره
function slerpV(a: THREE.Vector3, b: THREE.Vector3, t: number): THREE.Vector3 {
  const omega = a.angleTo(b)
  const so = Math.sin(omega)
  if (so < 1e-4) return a.clone() // نقطه مقابل/یکسان — ثابت
  const s1 = Math.sin((1 - t) * omega) / so
  const s2 = Math.sin(t * omega) / so
  return a.clone().multiplyScalar(s1).add(b.clone().multiplyScalar(s2)).normalize()
}

function FleetMarker({ f, onSelect }: { f: FleetW; onSelect: (f: FleetW) => void }) {
  const oLat = f.origin.lat ?? f.origin.clat
  const oLon = f.origin.lon ?? f.origin.clon
  const tLat = f.target.lat ?? f.target.clat
  const tLon = f.target.lon ?? f.target.clon
  const a = useMemo(() => latLonToVec3(oLat, oLon, 1).normalize(), [oLat, oLon])
  const b = useMemo(() => latLonToVec3(tLat, tLon, 1).normalize(), [tLat, tLon])
  const [hovered, setHovered] = useState(false)
  const grp = useRef<THREE.Group>(null)
  const p = useRef(0)
  useFrame(({ clock }, delta) => {
    if (!grp.current) return
    // progress واقعی سرور + interpolate نرم بین poll ها — برگشت معکوس حرکت می‌کند
    const target = f.status === 'returning' ? 1 - f.progress : f.progress
    p.current = p.current + (target - p.current) * Math.min(1, delta * 3)
    const pos = slerpV(a, b, Math.min(1, Math.max(0, p.current))).multiplyScalar(2.025)
    grp.current.position.copy(pos)
    // جهت‌گیری شعاعی (بالای سطح) + تکان خوردن ملایم موج
    grp.current.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), pos.clone().normalize())
    grp.current.rotateY(clock.elapsedTime * 0.8)
  })
  const ret = f.status === 'returning'
  return (
    <group ref={grp}>
      <mesh onClick={(e) => { e.stopPropagation(); onSelect(f) }}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
        onPointerOut={() => setHovered(false)}>
        <coneGeometry args={[0.015, 0.045, 6]} />
        <meshBasicMaterial color={ret ? '#22d3ee' : '#fbbf24'} />
      </mesh>
      <mesh position={[0, 0.045, 0]}>
        <sphereGeometry args={[0.013, 8, 8]} />
        <meshBasicMaterial color={ret ? '#22d3ee' : '#fbbf24'} transparent opacity={0.35} />
      </mesh>
      {hovered && (
        <Html distanceFactor={7} center zIndexRange={[10, 0]}>
          <div className="pointer-events-none whitespace-nowrap bg-night-900/95 border border-gold-500/40 rounded-lg px-2 py-1 text-[10px] font-bold text-gold-200 shadow-xl">
            {ret ? '🏠' : '⚓'} {f.player}: {f.origin.name} → {f.target.name} ({Math.round(f.progress * 100)}٪)
          </div>
        </Html>
      )}
    </group>
  )
}

// ==================== 📍 نشانگر سازه جای‌گذاری‌شده (نقشه شخصی → Globe جهانی) ====================
function PlacementPin({ p }: { p: PlacementW }) {
  const pos = useMemo(() => latLonToVec3(p.lat, p.lon, 2.02), [p.lat, p.lon])
  const [hovered, setHovered] = useState(false)
  return (
    <group position={pos}>
      <mesh onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
        onPointerOut={() => setHovered(false)}>
        <octahedronGeometry args={[0.014]} />
        <meshBasicMaterial color="#38bdf8" />
      </mesh>
      {hovered && (
        <Html distanceFactor={7} center zIndexRange={[10, 0]}>
          <div className="pointer-events-none whitespace-nowrap bg-night-900/95 border border-sky-500/40 rounded-lg px-2 py-1 text-[10px] font-bold text-sky-200">
            📍 {p.item_key} ×{p.qty} — {p.player}
          </div>
        </Html>
      )}
    </group>
  )
}

// ==================== Union خلاصه (Alliance Mode) — حلقه رنگی قاره‌ای ====================
function UnionBadge({ unions }: { unions: UnionW[] }) {
  return null // اعضا با رنگ اتحاد روی مارکرها نمایش داده می‌شوند؛ پنل اتحاد 2D است
}

// ==================== کامپوننت اصلی ====================
export default function GlobeMap({ world, onSelectCountry, onSelectBase, onSelectBattle, compact, focusName }: {
  world: WorldState | null
  onSelectCountry?: (c: CountryW) => void
  onSelectBase?: (b: BaseW) => void
  onSelectBattle?: (b: BattleW) => void
  compact?: boolean
  focusName?: string | null
}) {
  const [quality, setQuality] = useState<Quality>(() => {
    const saved = localStorage.getItem('globe_quality') as Quality | null
    return saved || (window.innerWidth < 768 ? 'medium' : 'high')
  })
  const [mode, setMode] = useState<MapMode>('political')
  const [autoRotate, setAutoRotate] = useState(true)
  const [selected, setSelected] = useState<CountryW | null>(null)
  const [selectedBase, setSelectedBase] = useState<BaseW | null>(null)
  const [selectedBattle, setSelectedBattle] = useState<BattleW | null>(null)
  const [selectedFleet, setSelectedFleet] = useState<FleetW | null>(null)
  const [myUnion, setMyUnion] = useState<string | null>(null)
  const [myCountry, setMyCountry] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [cameraTarget, setCameraTarget] = useState<THREE.Vector3 | null>(null)
  const [camDist, setCamDist] = useState(5)
  const cfg = QUALITY[quality]
  const focusTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    api.get('/dashboard/').then(({ data }) => {
      setMyUnion(data.player ? null : null)
    }).catch(() => {})
    api.get('/unions/').then(({ data }) => {
      setMyUnion(data.my_union?.name || null)
    }).catch(() => {})
  }, [])

  // focus از بیرون (پروفایل/لینک) — ?focus=نام کشور
  useEffect(() => {
    if (focusName && world) {
      const c = world.countries.find((x) => x.name === focusName)
      if (c) focusOn(c.lat ?? c.clat, c.lon ?? c.clon)
    }
  }, [focusName, world])

  const posOf = useCallback((lat: number, lon: number) => latLonToVec3(lat, lon, 2), [])

  const focusOn = useCallback((lat: number, lon: number) => {
    setCameraTarget(posOf(lat, lon))
    setAutoRotate(false)
    if (focusTimer.current) clearTimeout(focusTimer.current)
    focusTimer.current = setTimeout(() => setCameraTarget(null), 2500)
  }, [posOf])

  const selectCountry = (c: CountryW) => {
    setSelected(c); setSelectedBase(null); setSelectedBattle(null)
    focusOn(c.lat ?? c.clat, c.lon ?? c.clon)
    onSelectCountry?.(c)
  }
  const selectBase = (b: BaseW) => {
    setSelectedBase(b); setSelected(null); setSelectedBattle(null)
    onSelectBase?.(b)
  }
  const selectBattle = (b: BattleW) => {
    setSelectedBattle(b); setSelected(null); setSelectedBase(null)
    onSelectBattle?.(b)
  }

  // 🔍 Search — کشور/بازیکن/اتحاد/پایگاه
  const results = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q || !world) return []
    const out: { type: string; label: string; sub: string; lat: number; lon: number; action: () => void }[] = []
    for (const c of world.countries) {
      if (c.name.toLowerCase().includes(q)) {
        out.push({ type: 'کشور', label: `${c.emoji} ${c.name}`, sub: c.owner ? c.owner.name : 'آزاد', lat: c.lat ?? c.clat, lon: c.lon ?? c.clon, action: () => selectCountry(c) })
      }
    }
    for (const c of world.countries) {
      if (c.owner && c.owner.name.toLowerCase().includes(q)) {
        out.push({ type: 'بازیکن', label: `👤 ${c.owner.name}`, sub: c.name, lat: c.lat ?? c.clat, lon: c.lon ?? c.clon, action: () => selectCountry(c) })
      }
    }
    for (const u of world.unions) {
      if (u.name.toLowerCase().includes(q)) {
        out.push({ type: 'اتحاد', label: `🤝 ${u.name}`, sub: `${u.members} عضو`, lat: 0, lon: 0, action: () => { setMode('alliance'); setSelected(null) } })
      }
    }
    for (const b of world.bases) {
      if (b.country.toLowerCase().includes(q) || b.owner.toLowerCase().includes(q)) {
        out.push({ type: 'پایگاه', label: `🏕 ${b.country}`, sub: b.owner, lat: b.lat ?? b.lat_fallback, lon: b.lon ?? b.lon_fallback, action: () => selectBase(b) })
      }
    }
    return out.slice(0, 8)
  }, [search, world])

  const myPos = () => {
    api.get('/dashboard/').then(({ data }) => {
      const cont = data.player?.continent
      if (world && cont) {
        const c = world.continents.find((x) => x.key === cont)
        if (c) focusOn(c.lat, c.lon)
      }
    }).catch(() => {})
  }

  const showBases = mode === 'military' || mode === 'political'
  const showBattles = mode === 'conflict' || mode === 'military' || mode === 'political' || mode === 'admin'
  const showAdmin = mode === 'admin' && !!world?.is_staff && !!world.admin
  // LOD/Clustering: در کیفیت پایین هر ۳ کشور، در zoom دور مارکرهای کوچک‌تر
  const step = quality === 'low' ? 3 : 1
  const countries = world ? world.countries.filter((_, i) => i % step === 0) : []

  return (
    <div className="relative w-full h-full globe-stage">
      <div className="globe-corner-glow globe-corner-glow-a" />
      <div className="globe-corner-glow globe-corner-glow-b" />
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }} gl={{ antialias: cfg.aa, powerPreference: 'high-performance' }} dpr={[1, cfg.dpr]}>
        <ambientLight intensity={0.22} />
        <hemisphereLight args={['#8acbff', '#020611', 0.34]} />
        <directionalLight position={[6, 2, 4]} intensity={1.55} color="#fff3da" castShadow />
        <directionalLight position={[-6, -2, -4]} intensity={0.38} color="#2349a5" />
        <pointLight position={[-4, 2.5, 5]} intensity={1.1} distance={12} color="#37c8ff" />
        <CinematicStarfield count={quality === 'ultra' ? 1800 : quality === 'high' ? 1200 : cfg.stars} radius={26} />
        <Stars count={Math.min(cfg.stars, 900)} />
        <Earth quality={quality} rotate={autoRotate} sun={{ myCountry }} />
        {quality !== 'low' && <Atmosphere quality={quality} />}
        {quality !== 'low' && <GeoLayer world={world!} />}
        {countries.map((c) => (
          <CountryMarker key={c.name} c={c} mode={mode} myUnion={myUnion} onSelect={selectCountry} isSelected={selected?.name === c.name} />
        ))}
        {showBases && world?.bases.map((b) => <BaseMarker key={b.id} b={b} onSelect={selectBase} />)}
        {showBattles && world?.battles.map((b) => <BattleMarker key={b.id} b={b} onSelect={selectBattle} />)}
        {world?.fleets?.map((f) => <FleetMarker key={f.id} f={f} onSelect={(ff) => { setSelectedFleet(ff) }} />)}
        {mode === 'admin' && world?.admin?.transactions.map((t) => <TxMarker key={t.id} t={t} />)}
        {quality !== 'low' && world?.placements?.map((p) => <PlacementPin key={p.id} p={p} />)}
        <OrbitControls enablePan={false} minDistance={2.6} maxDistance={9} enableDamping dampingFactor={0.07} rotateSpeed={0.55} zoomSpeed={0.9} />
        <CameraRig target={cameraTarget} dist={camDist} />
      </Canvas>

      {/* ===== Top: World Status Bar ===== */}
      {!compact && world && (
        <div className="absolute top-3 inset-x-3 flex flex-wrap items-center gap-1.5 justify-center pointer-events-none z-10">
          <span className="hud-chip !py-1 !px-2 text-[10px]">🗺 {fmt(world.stats.countries_total)}</span>
          <span className="hud-chip !py-1 !px-2 text-[10px]">👑 {fmt(world.stats.countries_taken)}</span>
          <span className="hud-chip !py-1 !px-2 text-[10px]">👥 {fmt(world.stats.players)}</span>
          <span className="hud-chip !py-1 !px-2 text-[10px] !border-success-500/30">🟢 {fmt(world.stats.online)}</span>
          <span className="hud-chip !py-1 !px-2 text-[10px]">🏕 {fmt(world.stats.bases)}</span>
          <span className="hud-chip !py-1 !px-2 text-[10px]">🤝 {fmt(world.stats.unions)}</span>
          {world.fleets && world.fleets.length > 0 && (
            <span className="hud-chip !py-1 !px-2 text-[10px] !border-gold-500/30">⚓ {fmt(world.fleets.length)}</span>
          )}
        </div>
      )}

      {/* ===== Left: Map Modes + Quality ===== */}
      <div className="absolute top-14 right-3 flex flex-col gap-1.5 items-start z-10 depth-control-panel">
        {(Object.keys(MODE_FA) as MapMode[])
          .filter((m) => m !== 'admin' || world?.is_staff)
          .map((m) => (
          <button key={m} onClick={() => setMode(m)}
            className={`hud-button px-2 py-1.5 rounded-lg text-[10px] font-bold transition ${mode === m ? 'bg-primary-500 text-white' : 'bg-night-900/80 text-slate-400 hover:bg-white/10'}`}>
            {MODE_FA[m]}
          </button>
        ))}
      </div>

      {/* ===== Right: quality + controls ===== */}
      <div className="absolute top-14 left-3 flex flex-col gap-1.5 items-end z-10 depth-control-panel">
        <div className="flex gap-1">
          {(['low', 'medium', 'high', 'ultra'] as Quality[]).map((q) => (
            <button key={q} onClick={() => { setQuality(q); localStorage.setItem('globe_quality', q) }}
              className={`hud-button px-2 py-1 rounded-md text-[9px] font-bold ${quality === q ? 'bg-primary-500 text-white' : 'bg-night-900/80 text-slate-400'}`}>
              {QUALITY_FA[q]}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          <button onClick={() => setCamDist(3)} className="px-2 py-0.5 rounded text-[10px] bg-night-900/80 text-slate-300 hover:bg-white/10">➕</button>
          <button onClick={() => setCamDist(7)} className="px-2 py-0.5 rounded text-[10px] bg-night-900/80 text-slate-300 hover:bg-white/10">➖</button>
        </div>
        <div className="flex gap-1">
          <button onClick={myPos} className="px-2 py-0.5 rounded text-[10px] bg-gold-500/20 text-gold-300 hover:bg-gold-500/30">📍 من</button>
          <button onClick={() => { setCameraTarget(new THREE.Vector3(0, 0, 2)); setCamDist(5); setTimeout(() => setCameraTarget(null), 100); setAutoRotate(true); setSelected(null); setSelectedBase(null); setSelectedBattle(null) }}
            className="px-2 py-0.5 rounded text-[10px] bg-night-900/80 text-slate-300 hover:bg-white/10">🏠</button>
        </div>
      </div>

      {/* ===== Search ===== */}
      {!compact && (
        <div className="absolute bottom-2 inset-x-2 flex justify-center">
          <div className="relative w-full max-w-xs">
            <input value={search} onChange={(e) => setSearch(e.target.value)} dir="rtl"
              placeholder="🔍 جستجو: کشور، بازیکن، اتحاد، پایگاه..."
              className="w-full bg-night-900/90 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500/50" />
            {results.length > 0 && (
              <div className="absolute bottom-full mb-1 w-full bg-night-900/95 border border-white/10 rounded-xl overflow-hidden shadow-2xl">
                {results.map((r, i) => (
                  <button key={i} onClick={() => { r.action(); setSearch('') }}
                    className="w-full text-right px-3 py-2 text-xs hover:bg-white/10 flex items-center justify-between">
                    <span className="font-bold">{r.label}</span>
                    <span className="text-[10px] text-slate-500">{r.type} · {r.sub}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== Country Panel (2D overlay — بدون خروج از Globe) ===== */}
      {selected && (
        <div className="absolute top-14 left-2 w-64 glass-card p-3 space-y-2 animate-glow">
          <div className="flex items-center justify-between">
            <div className="font-black">{selected.emoji} {selected.name}</div>
            <button className="text-slate-500 text-xs" onClick={() => setSelected(null)}>✕</button>
          </div>
          <div className="text-xs space-y-1">
            {selected.command_name && <Row k="فرمان" v={`/${selected.command_name}`} />}
            <Row k="قاره" v={CONT_FA[selected.continent] || selected.continent} />
            <Row k="جمعیت" v={`${fmt(selected.population)} میلیون`} />
            <Row k="وضعیت" v={selected.owner ? '👑 صاحب‌دار' : '✅ آزاد'} />
            {selected.owner && <Row k="فرمانده" v={selected.owner.name} />}
            {selected.owner?.union && <Row k="اتحاد" v={selected.owner.union} />}
            {selected.owner && <Row k="امتیاز" v={fmt(selected.owner.score)} />}
          </div>
          {selected.owner && (
            <a href={`/players/${selected.owner.username}`} className="btn-ghost w-full !py-1.5 text-xs block text-center">
              👤 پروفایل فرمانده
            </a>
          )}
        </div>
      )}

      {/* ===== Base Panel ===== */}
      {selectedBase && (
        <div className="absolute top-14 left-2 w-64 glass-card p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="font-black">🏕 پایگاه {selectedBase.country}</div>
            <button className="text-slate-500 text-xs" onClick={() => setSelectedBase(null)}>✕</button>
          </div>
          <div className="text-xs space-y-1">
            <Row k="فرمانده" v={selectedBase.owner} />
            <Row k="وضعیت" v={selectedBase.ready ? '✅ آماده عملیات' : '⏳ در حال ساخت'} />
            <Row k="قاره" v={CONT_FA[selectedBase.continent] || selectedBase.continent} />
          </div>
          <a href={`/players/${selectedBase.username}`} className="btn-ghost w-full !py-1.5 text-xs block text-center">👤 پروفایل مالک</a>
        </div>
      )}

      {/* ===== 🛡 Admin Panel — پخش زنده لحظه‌ای (فقط برای staff) ===== */}
      {showAdmin && world!.admin && (
        <div className="absolute top-14 left-2 w-72 glass-card p-3 space-y-2 !border-danger-500/40 max-h-[80%] overflow-y-auto">
          <div className="flex items-center justify-between">
            <div className="font-black text-danger-300">🛡 دید لحظه‌ای ادمین</div>
            <span className="text-[10px] text-slate-500">{fmt(world!.admin.total_players)} فرمانده</span>
          </div>
          <div className="flex gap-2 text-[10px]">
            <span className="stat-chip !py-0.5 !px-2">⚔️ {fmt(world!.admin.battles_24h)}/۲۴ساعت</span>
            <span className="stat-chip !py-0.5 !px-2">💰 {fmt(world!.admin.total_credit)}</span>
          </div>
          <div className="text-[10px] text-slate-500">👥 بازیکنان (کلیک = فوکوس)</div>
          <div className="space-y-0.5">
            {world!.admin.players.map((p) => (
              <button key={p.id} onClick={() => { focusOn(p.lat ?? p.clat, p.lon ?? p.clon) }}
                className="w-full flex items-center justify-between px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-[11px]">
                <span className="truncate">{p.online ? '🟢' : '⚪'} {p.name}</span>
                <span className="text-slate-500 text-[10px]">💰{fmt(p.credit)} · ⚡{fmt(p.army)}</span>
              </button>
            ))}
          </div>
          <div className="text-[10px] text-slate-500">💰 آخرین تراکنش‌ها (روی کره هم پین‌شدند)</div>
          <div className="space-y-0.5">
            {world!.admin.transactions.slice(0, 10).map((t) => (
              <div key={t.id} className="flex items-center justify-between px-2 py-0.5 text-[10px] text-slate-400">
                <span className="truncate">{t.player}</span>
                <span className={t.amount < 0 ? 'text-orange-400' : 'text-success-400'}>{t.amount > 0 ? '+' : ''}{fmt(t.amount)}</span>
                <span className="text-slate-600">{timeAgo(t.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===== Fleet Panel ===== */}
      {selectedFleet && (
        <div className="absolute top-14 left-2 w-72 glass-card p-3 space-y-2 !border-gold-500/40">
          <div className="flex items-center justify-between">
            <div className="font-black text-gold-300">⚓ مأموریت دریایی</div>
            <button className="text-slate-500 text-xs" onClick={() => setSelectedFleet(null)}>✕</button>
          </div>
          <div className="text-xs space-y-1">
            <Row k="فرمانده" v={selectedFleet.player} />
            <Row k="مسیر" v={`${selectedFleet.origin.name || '؟'} → ${selectedFleet.target.name || '؟'}`} />
            <Row k="وضعیت" v={selectedFleet.status === 'outbound' ? '🚢 در مسیر' : '🏠 در حال بازگشت'} />
            <Row k="پیشرفت" v={`${Math.round(selectedFleet.progress * 100)}٪`} />
            <Row k="شناورها" v={Object.entries(selectedFleet.ships).map(([k, v]) => `${v}×${k}`).join('، ') || '—'} />
            {selectedFleet.loot > 0 && <Row k="غنیمت" v={fmt(selectedFleet.loot)} />}
            {selectedFleet.summary && <Row k="نبرد" v={selectedFleet.summary.slice(0, 60)} />}
          </div>
        </div>
      )}

      {/* ===== Battle Panel ===== */}
      {selectedBattle && (
        <div className="absolute top-14 left-2 w-72 glass-card p-3 space-y-2 !border-danger-500/40">
          <div className="flex items-center justify-between">
            <div className="font-black text-danger-400">⚔️ رویداد نبرد</div>
            <button className="text-slate-500 text-xs" onClick={() => setSelectedBattle(null)}>✕</button>
          </div>
          <p className="text-xs text-slate-200">{selectedBattle.summary}</p>
          <div className="text-xs space-y-1">
            <Row k="مهاجم" v={selectedBattle.attacker} />
            <Row k="مدافع" v={selectedBattle.defender} />
            <Row k="زمان" v={timeAgo(selectedBattle.created_at)} />
          </div>
        </div>
      )}

      {/* ===== Legend ===== */}
      {!compact && (
        <div className="absolute bottom-2 left-2 hidden sm:flex gap-2 text-[10px] text-slate-400">
          {mode === 'political' && (<>
            <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-[#37b26c] inline-block" /> آزاد</span>
            <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-[#e8654f] inline-block" /> صاحب‌دار</span>
            <span className="flex items-center gap-1"><i className="w-2 h-2 bg-[#38bdf8] inline-block rotate-45" /> پایگاه</span>
          </>)}
          {mode === 'alliance' && (<>
            <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-[#38bdf8] inline-block" /> اتحاد من</span>
            <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-[#a78bfa] inline-block" /> اتحاد دیگر</span>
          </>)}
          {mode === 'conflict' && (<>
            <span className="flex items-center gap-1"><i className="w-2 h-2 rounded-full bg-[#ef4444] inline-block" /> نبرد فعال</span>
          </>)}
        </div>
      )}
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-500">{k}</span>
      <span className="font-bold text-slate-200 truncate max-w-36">{v}</span>
    </div>
  )
}
