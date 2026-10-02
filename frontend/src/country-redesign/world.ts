import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js'
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import { mulberry32, smoothstep } from './noise'
import {
  BIOMES,
  ITEM_BY_KEY,
  type CountryProfile,
  type Division,
  type ItemKey,
  type Placement,
} from './data'
import {
  N,
  SIZE,
  buildRoads,
  contour,
  findSite,
  flattenRegion,
  generateTerrain,
  gridToWorld,
  padRadius,
  sampleHeight,
  worldToGrid,
  type TerrainResult,
} from './terrain'
import {
  CLOUD_Y,
  applyAtmosphere,
  createCloudMaterial,
  createSharedUniforms,
  createSkyMaterial,
  createWaterMaterial,
  patchBuildingMaterial,
  patchTerrainMaterial,
  patchWindMaterial,
  type SkyState,
} from './shaders'
import {
  buildInstallation,
  buildLandmark,
  buildShip,
  createModelMats,
  makeBroadleafGeometry,
  makeConiferGeometry,
  makeShrubGeometry,
  paint,
  type ModelMats,
} from './models'

export type Selection = { type: 'division'; id: string } | { type: 'placement'; id: number } | null
export type Quality = 'high' | 'medium' | 'low'

export interface Layers {
  terrain: boolean
  divisions: boolean
  placements: boolean
  clouds: boolean
  border: boolean
}

export interface WorldCallbacks {
  onReady: (divisions: Division[]) => void
  onDivisions: (divisions: Division[]) => void
  onSelect: (sel: Selection) => void
  onPlaceRequest: (info: { item: ItemKey; x: number; z: number; nearest: Division[] }) => void
  onGhost: (v: { ok: boolean; reason: string } | null) => void
  onHour: (h: number) => void
  onFps: (fps: number) => void
}

interface Inst {
  x: number
  y: number
  z: number
  s: number
  r: number
}

interface VegSet {
  mesh: THREE.InstancedMesh
  inst: Inst[]
  total: number
}

interface RoadPath {
  pts: Float32Array // x,z pairs
  cum: Float32Array
  len: number
}

interface Car {
  road: number
  s: number
  speed: number
  dir: number
}

interface ShipState {
  obj: THREE.Group
  ax: number
  az: number
  bx: number
  bz: number
  t: number
  dir: number
  speed: number
  phase: number
}

interface LabelItem {
  el: HTMLElement
  pos: THREE.Vector3
  kind: 'division' | 'unit'
  ref: string
}

interface PlacedModel {
  id: number
  group: THREE.Group
  spin?: THREE.Object3D
  radius: number
  born: number
  x: number
  z: number
  label: LabelItem
}

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

function disposeTree(o: THREE.Object3D) {
  o.traverse((c) => {
    const m = c as THREE.Mesh
    if (m.geometry) m.geometry.dispose()
    const mat = (m as THREE.Mesh).material as THREE.Material | THREE.Material[] | undefined
    if (mat) {
      const list = Array.isArray(mat) ? mat : [mat]
      list.forEach((x) => x.dispose())
    }
  })
}

function glowTexture() {
  const cv = document.createElement('canvas')
  cv.width = cv.height = 128
  const g = cv.getContext('2d')!
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  grd.addColorStop(0, 'rgba(255,255,255,1)')
  grd.addColorStop(0.25, 'rgba(255,255,255,0.45)')
  grd.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = grd
  g.fillRect(0, 0, 128, 128)
  const t = new THREE.CanvasTexture(cv)
  t.colorSpace = THREE.SRGBColorSpace
  return t
}

function roadTexture() {
  const cv = document.createElement('canvas')
  cv.width = 128
  cv.height = 64
  const g = cv.getContext('2d')!
  g.fillStyle = '#323437'
  g.fillRect(0, 0, 128, 64)
  for (let i = 0; i < 700; i++) {
    g.fillStyle = `rgba(255,255,255,${Math.random() * 0.05})`
    g.fillRect(Math.random() * 128, Math.random() * 64, 2, 2)
  }
  g.fillStyle = 'rgba(210,210,200,0.8)'
  g.fillRect(0, 4, 128, 2)
  g.fillRect(0, 58, 128, 2)
  g.fillStyle = 'rgba(235,205,110,0.9)'
  g.fillRect(8, 31, 52, 2.5)
  const t = new THREE.CanvasTexture(cv)
  t.colorSpace = THREE.SRGBColorSpace
  t.wrapS = THREE.RepeatWrapping
  t.anisotropy = 8
  return t
}

function cityGroundTexture() {
  const cv = document.createElement('canvas')
  cv.width = cv.height = 512
  const g = cv.getContext('2d')!
  g.clearRect(0, 0, 512, 512)
  g.fillStyle = '#35373a'
  g.fillRect(0, 0, 512, 512)
  // blocks
  g.fillStyle = '#505357'
  const cell = 512 / 12
  for (let i = 0; i < 12; i++) {
    for (let j = 0; j < 12; j++) {
      g.fillRect(i * cell + 5, j * cell + 5, cell - 10, cell - 10)
    }
  }
  // avenues
  g.fillStyle = '#2b2d30'
  g.fillRect(256 - 14, 0, 28, 512)
  g.fillRect(0, 256 - 14, 512, 28)
  g.fillStyle = 'rgba(235,205,110,0.5)'
  for (let k = 0; k < 512; k += 24) {
    g.fillRect(254, k, 4, 12)
    g.fillRect(k, 254, 12, 4)
  }
  // soft alpha mask
  g.globalCompositeOperation = 'destination-in'
  const grd = g.createRadialGradient(256, 256, 120, 256, 256, 256)
  grd.addColorStop(0, 'rgba(0,0,0,1)')
  grd.addColorStop(0.75, 'rgba(0,0,0,0.85)')
  grd.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = grd
  g.fillRect(0, 0, 512, 512)
  const t = new THREE.CanvasTexture(cv)
  t.colorSpace = THREE.SRGBColorSpace
  t.anisotropy = 8
  return t
}

export class CountryWorld {
  private container: HTMLElement
  private cb: WorldCallbacks
  private renderer: THREE.WebGLRenderer
  private scene = new THREE.Scene()
  private camera: THREE.PerspectiveCamera
  private controls: OrbitControls
  private u = createSharedUniforms()
  private sky: SkyState = {
    sunDir: new THREE.Vector3(),
    elev: 0.5,
    lightDir: new THREE.Vector3(),
    lightColor: new THREE.Color(),
    lightIntensity: 3,
    hemiSky: new THREE.Color(),
    hemiGround: new THREE.Color(),
    hemiIntensity: 0.8,
    exposure: 0.9,
  }
  private sun: THREE.DirectionalLight
  private hemi: THREE.HemisphereLight
  private skyMesh: THREE.Mesh
  private cloudMesh: THREE.Mesh
  private labelLayer: HTMLDivElement
  private ro: ResizeObserver
  private mats: ModelMats
  private glowTex: THREE.Texture
  private roadTex: THREE.Texture
  private cityTex: THREE.Texture

  // dynamic world
  private worldGroup = new THREE.Group()
  private terrain!: TerrainResult
  private preset = BIOMES.temperate
  private profile: CountryProfile
  private terrainMesh!: THREE.Mesh
  private terrainGeo!: THREE.BufferGeometry
  private ctrlTex!: THREE.DataTexture
  private waterMesh!: THREE.Mesh
  private roadMask = new Uint8Array(N * N)
  private roadMesh: THREE.Mesh | null = null
  private roadPaths: RoadPath[] = []
  private gVeg = new THREE.Group()
  private gCities = new THREE.Group()
  private gRoads = new THREE.Group()
  private gPlace = new THREE.Group()
  private gLife = new THREE.Group()
  private gBorder = new THREE.Group()
  private veg: Record<'con' | 'bro' | 'shr', VegSet | null> = { con: null, bro: null, shr: null }
  private divisions: Division[] = []
  private cityGlow: { sprite: THREE.Sprite; base: number }[] = []
  private cityMarks: Record<string, { pad: number; anchor: THREE.Vector3 }> = {}
  private placed: PlacedModel[] = []
  private labels: LabelItem[] = []
  private ships: ShipState[] = []
  private cars: Car[] = []
  private carMesh: THREE.InstancedMesh | null = null
  private carLights: THREE.InstancedMesh | null = null
  private borderLines: LineSegments2[] = []
  private beacons: THREE.Material[] = []
  private nextPlacementId = 1

  // interaction
  private raycaster = new THREE.Raycaster()
  private ring: THREE.Mesh
  private beam: THREE.Mesh
  private ghost: THREE.Group | null = null
  private ghostRing: THREE.Mesh | null = null
  private ghostMat = new THREE.MeshBasicMaterial({ color: '#46f09a', transparent: true, opacity: 0.5, depthWrite: false })
  private placingKey: ItemKey | null = null
  private ghostState: { ok: boolean; reason: string } | null = null
  private selected: Selection = null
  private hoverSel: Selection = null
  private pointerDirty = false
  private pointerXY = { x: 0, y: 0 }
  private downInfo: { x: number; y: number; t: number } | null = null
  private dragging = false

  // state
  private hour = 16.2
  private playing = false
  private cloudy = 0.18
  private layers: Layers = { terrain: true, divisions: true, placements: true, clouds: true, border: true }
  private quality: Quality = 'high'
  private flight: null | { t0: number; dur: number; fromT: THREE.Vector3; toT: THREE.Vector3; fromP: THREE.Vector3; toP: THREE.Vector3 } = null
  private raf = 0
  private lastT = 0
  private hourEmit = 0
  private fpsAcc = 0
  private fpsFrames = 0
  private shadowExt = 0
  private disposed = false

  constructor(container: HTMLElement, profile: CountryProfile, cb: WorldCallbacks) {
    this.container = container
    this.cb = cb
    this.profile = profile

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.domElement.style.display = 'block'
    this.renderer.domElement.style.touchAction = 'none'
    container.appendChild(this.renderer.domElement)

    this.scene.fog = new THREE.FogExp2(0x88aacc, 0.0016)
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.6, 5200)
    this.camera.position.set(0, 190, 250)

    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.07
    this.controls.maxPolarAngle = Math.PI / 2 - 0.02
    this.controls.minDistance = 10
    this.controls.maxDistance = 520
    this.controls.zoomToCursor = true
    this.controls.screenSpacePanning = false
    this.controls.autoRotateSpeed = 0.55
    this.controls.target.set(0, 0, 0)

    this.hemi = new THREE.HemisphereLight(0xaaccff, 0x554433, 0.8)
    this.scene.add(this.hemi)
    this.sun = new THREE.DirectionalLight(0xffffff, 3)
    this.sun.castShadow = true
    this.sun.shadow.bias = -0.0004
    this.sun.shadow.normalBias = 0.45
    this.sun.shadow.camera.near = 10
    this.sun.shadow.camera.far = 700
    this.scene.add(this.sun, this.sun.target)

    this.skyMesh = new THREE.Mesh(new THREE.SphereGeometry(3000, 40, 20), createSkyMaterial(this.u))
    this.skyMesh.frustumCulled = false
    this.skyMesh.renderOrder = -10
    this.scene.add(this.skyMesh)

    this.cloudMesh = new THREE.Mesh(new THREE.PlaneGeometry(2600, 2600, 1, 1), createCloudMaterial(this.u))
    this.cloudMesh.rotation.x = -Math.PI / 2
    this.cloudMesh.position.y = CLOUD_Y
    this.cloudMesh.renderOrder = 5
    this.cloudMesh.frustumCulled = false
    this.scene.add(this.cloudMesh)

    this.labelLayer = document.createElement('div')
    this.labelLayer.className = 'c3d-labels'
    container.appendChild(this.labelLayer)

    this.mats = createModelMats()
    this.beacons.push(this.mats.beacon)
    this.glowTex = glowTexture()
    this.roadTex = roadTexture()
    this.cityTex = cityGroundTexture()

    // selection ring + beam
    this.ring = new THREE.Mesh(
      new THREE.RingGeometry(0.94, 1, 96),
      new THREE.MeshBasicMaterial({ color: '#55d6ff', transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }),
    )
    this.ring.rotation.x = -Math.PI / 2
    this.ring.visible = false
    this.ring.renderOrder = 8
    this.scene.add(this.ring)
    this.beam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.16, 0.16, 40, 12, 1, true),
      new THREE.MeshBasicMaterial({ color: '#f1c86d', transparent: true, opacity: 0.35, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false }),
    )
    this.beam.visible = false
    this.beam.renderOrder = 8
    this.scene.add(this.beam)

    this.scene.add(this.worldGroup)
    this.gVeg.name = 'veg'
    this.worldGroup.add(this.gVeg, this.gCities, this.gRoads, this.gPlace, this.gLife, this.gBorder)

    const el = this.renderer.domElement
    el.addEventListener('pointermove', this.onMove)
    el.addEventListener('pointerdown', this.onDown)
    window.addEventListener('pointerup', this.onUp)
    el.addEventListener('contextmenu', this.onContext)
    this.ro = new ResizeObserver(() => this.resize())
    this.ro.observe(container)
    this.resize()
    this.setQuality('high')
    this.updateAtmosphere()
  }

  /* ================================================================ */
  /* public API                                                       */
  /* ================================================================ */
  async init() {
    await new Promise((r) => setTimeout(r, 40))
    if (this.disposed) return
    this.build()
    if (this.disposed) return
    this.lastT = performance.now()
    this.loop()
    this.cb.onReady(this.divisions.slice())
  }

  getDivisions() {
    return this.divisions.slice()
  }

  setDivisionNames(items: { name: string; kind: Division['kind']; population?: number; custom?: boolean }[]) {
    const generated = this.divisions.slice()
    const used = new Set<string>()
    const mapped: Division[] = []
    items.forEach((item, index) => {
      const candidate = generated.find((d) => !used.has(d.id) && d.kind === item.kind) ?? generated[index] ?? generated[0]
      if (!candidate) return
      used.add(candidate.id)
      mapped.push({ ...candidate, name: item.name, kind: item.kind,
        population: item.population ?? candidate.population, custom: item.custom })
    })
    this.divisions = mapped
    this.rebuildRoads()
    this.rebuildCities()
    this.cb.onDivisions(this.divisions.slice())
  }

  async regenerate(profile: CountryProfile) {
    this.profile = profile
    this.cb.onGhost(null)
    this.startPlacing(null)
    this.select(null)
    await new Promise((r) => setTimeout(r, 40))
    if (this.disposed) return
    this.build()
    this.cb.onDivisions(this.divisions.slice())
  }

  setProfileVisual(profile: CountryProfile) {
    this.profile = profile
    this.borderLines.forEach((l, i) => {
      const m = l.material as LineMaterial
      m.color.set(profile.map_color)
      m.opacity = i === 0 ? 0.95 : 0.22
    })
    const cap = this.divisions.find((d) => d.kind === 'capital')
    if (cap && cap.name !== profile.capital_name) {
      cap.name = profile.capital_name
      const lab = this.labels.find((l) => l.kind === 'division' && l.ref === cap.id)
      if (lab) lab.el.querySelector('.nm')!.textContent = cap.name
      this.cb.onDivisions(this.divisions.slice())
    }
  }

  setLayers(l: Layers) {
    this.layers = l
    this.gVeg.visible = l.terrain
    this.gCities.visible = l.divisions
    this.gRoads.visible = l.divisions
    this.gLife.visible = l.divisions
    this.gPlace.visible = l.placements
    this.gBorder.visible = l.border
    this.cloudMesh.visible = l.clouds
    this.u.uCloudOn.value = l.clouds ? 1 : 0
  }

  setHour(h: number) {
    this.hour = ((h % 24) + 24) % 24
    this.updateAtmosphere()
  }

  setPlaying(p: boolean) {
    this.playing = p
  }

  setCloudiness(v: number) {
    this.cloudy = v
    this.updateAtmosphere()
  }

  setAutoRotate(b: boolean) {
    this.controls.autoRotate = b
  }

  setQuality(q: Quality) {
    this.quality = q
    const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
    this.renderer.setPixelRatio(Math.min(dpr, q === 'high' ? 2 : q === 'medium' ? 1.5 : 1))
    const size = q === 'high' ? 4096 : q === 'medium' ? 2048 : 1024
    if (this.sun.shadow.mapSize.x !== size) {
      this.sun.shadow.mapSize.set(size, size)
      this.sun.shadow.map?.dispose()
      this.sun.shadow.map = null
    }
    this.renderer.shadowMap.enabled = q !== 'low'
    this.scene.traverse((o) => {
      const m = (o as THREE.Mesh).material as THREE.Material | THREE.Material[] | undefined
      if (m) (Array.isArray(m) ? m : [m]).forEach((x) => (x.needsUpdate = true))
    })
    const frac = q === 'high' ? 1 : q === 'medium' ? 0.6 : 0.3
    ;(['con', 'bro', 'shr'] as const).forEach((k) => {
      const v = this.veg[k]
      if (v) v.mesh.count = Math.floor(v.total * frac)
    })
    this.resize()
  }

  startPlacing(key: ItemKey | null) {
    this.placingKey = key
    if (this.ghost) {
      this.scene.remove(this.ghost)
      disposeTree(this.ghost)
      this.ghost = null
    }
    if (this.ghostRing) {
      this.scene.remove(this.ghostRing)
      this.ghostRing.geometry.dispose()
      this.ghostRing = null
    }
    this.ghostState = null
    if (key) {
      const m = buildInstallation(key, this.mats)
      m.group.traverse((o) => {
        const mesh = o as THREE.Mesh
        if (mesh.isMesh) {
          mesh.material = this.ghostMat
          mesh.castShadow = false
          mesh.receiveShadow = false
        }
      })
      m.group.visible = false
      this.ghost = m.group
      this.ghost.userData.radius = m.radius
      this.scene.add(this.ghost)
      this.ghostRing = new THREE.Mesh(
        new THREE.RingGeometry(m.radius * 0.96, m.radius * 1.04, 64),
        new THREE.MeshBasicMaterial({ color: '#46f09a', transparent: true, opacity: 0.85, side: THREE.DoubleSide, depthWrite: false, fog: false }),
      )
      this.ghostRing.rotation.x = -Math.PI / 2
      this.ghostRing.visible = false
      this.ghostRing.renderOrder = 9
      this.scene.add(this.ghostRing)
      this.renderer.domElement.style.cursor = 'crosshair'
    } else {
      this.renderer.domElement.style.cursor = 'grab'
      this.cb.onGhost(null)
    }
  }

  select(sel: Selection) {
    this.selected = sel
    this.refreshRing()
  }

  flyToDivision(id: string) {
    const d = this.divisions.find((x) => x.id === id)
    if (d) this.flyTo(d.x, d.z, 62)
  }

  flyToPlacement(id: number) {
    const p = this.placed.find((x) => x.id === id)
    if (p) this.flyTo(p.x, p.z, 38)
  }

  resetView() {
    this.flyTo(0, 0, 330, 0.62)
  }

  addCity(name: string): Division | null {
    const custom = this.divisions.filter((d) => d.custom).length
    if (custom >= 10) return null
    const rnd = mulberry32((Date.now() & 0xfffff) + custom * 17)
    const h = this.terrain.heights
    const site = findSite(h, this.divisions, rnd, 'city', 34) ?? findSite(h, this.divisions, rnd, 'city', 22)
    if (!site) return null
    const d: Division = {
      id: `c${Date.now()}`,
      name,
      kind: 'city',
      x: site.x,
      z: site.z,
      radius: padRadius('city'),
      population: Math.round(90_000 + rnd() * 240_000),
      custom: true,
    }
    flattenRegion(h, d.x, d.z, d.radius)
    this.syncTerrainGeometry()
    this.removeVegetation(d.x, d.z, d.radius * 1.5)
    this.divisions.push(d)
    this.rebuildRoads()
    this.rebuildCities()
    this.cb.onDivisions(this.divisions.slice())
    this.flyTo(d.x, d.z, 55)
    return d
  }

  addPlacement(p: Omit<Placement, 'id'> & { id?: number }): Placement {
    const placement: Placement = { ...p, id: p.id ?? this.nextPlacementId++ } as Placement
    const built = buildInstallation(placement.item_key, this.mats)
    const h = this.terrain.heights
    flattenRegion(h, placement.x, placement.z, built.radius * 1.05)
    this.syncTerrainGeometry()
    this.removeVegetation(placement.x, placement.z, built.radius * 1.7)
    const y = sampleHeight(h, placement.x, placement.z)
    built.group.position.set(placement.x, y + 0.02, placement.z)
    built.group.rotation.y = ((placement.id * 2.399) % (Math.PI * 2)) * 0.15
    built.group.scale.setScalar(0.001)
    this.gPlace.add(built.group)

    const item = ITEM_BY_KEY[placement.item_key]
    const el = this.makeLabel(`${item.icon} ${item.name}`, 'unit', () => this.cb.onSelect({ type: 'placement', id: placement.id }))
    const label: LabelItem = { el, pos: new THREE.Vector3(placement.x, y + 7, placement.z), kind: 'unit', ref: String(placement.id) }
    this.labels.push(label)
    this.placed.push({ id: placement.id, group: built.group, spin: built.spin, radius: built.radius, born: performance.now(), x: placement.x, z: placement.z, label })
    return placement
  }

  removePlacement(id: number) {
    const i = this.placed.findIndex((p) => p.id === id)
    if (i < 0) return
    const p = this.placed[i]
    this.gPlace.remove(p.group)
    disposeTree(p.group)
    p.label.el.remove()
    this.labels = this.labels.filter((l) => l !== p.label)
    this.placed.splice(i, 1)
    if (this.selected && this.selected.type === 'placement' && this.selected.id === id) this.select(null)
  }

  /** is a spot valid for the currently-selected installation? */
  validateSpot(x: number, z: number, radius: number): { ok: boolean; reason: string } {
    const h = this.terrain.heights
    if (Math.abs(x) > SIZE / 2 - 8 || Math.abs(z) > SIZE / 2 - 8) return { ok: false, reason: 'خارج از قلمرو' }
    const e = sampleHeight(h, x, z)
    if (e < 1.3) return { ok: false, reason: 'اینجا خشکی نیست' }
    let mn = e
    let mx = e
    for (let k = 0; k < 10; k++) {
      const a = (k / 10) * Math.PI * 2
      const hh = sampleHeight(h, x + Math.cos(a) * radius * 0.9, z + Math.sin(a) * radius * 0.9)
      mn = Math.min(mn, hh)
      mx = Math.max(mx, hh)
    }
    if (mn < 0.9) return { ok: false, reason: 'نزدیک آب است' }
    if (mx - mn > 7.5) return { ok: false, reason: 'شیب زمین زیاد است' }
    const gi = Math.round(worldToGrid(x))
    const gj = Math.round(worldToGrid(z))
    if (this.terrain.water[gj * N + gi] > 0.4) return { ok: false, reason: 'روی رودخانه یا دریاچه' }
    for (const d of this.divisions) {
      if (Math.hypot(d.x - x, d.z - z) < d.radius * 1.12 + radius * 0.55) return { ok: false, reason: 'داخل محدودهٔ شهر' }
    }
    for (const p of this.placed) {
      if (Math.hypot(p.x - x, p.z - z) < p.radius + radius) return { ok: false, reason: 'با سازهٔ دیگر تداخل دارد' }
    }
    return { ok: true, reason: 'محل مناسب است' }
  }

  dispose() {
    this.disposed = true
    cancelAnimationFrame(this.raf)
    const el = this.renderer.domElement
    el.removeEventListener('pointermove', this.onMove)
    el.removeEventListener('pointerdown', this.onDown)
    window.removeEventListener('pointerup', this.onUp)
    el.removeEventListener('contextmenu', this.onContext)
    this.ro.disconnect()
    this.controls.dispose()
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh
      if (m.geometry) m.geometry.dispose()
      const mat = m.material as THREE.Material | THREE.Material[] | undefined
      if (mat) (Array.isArray(mat) ? mat : [mat]).forEach((x) => x.dispose())
    })
    this.ctrlTex?.dispose()
    this.glowTex.dispose()
    this.roadTex.dispose()
    this.cityTex.dispose()
    this.renderer.dispose()
    this.renderer.forceContextLoss()
    el.remove()
    this.labelLayer.remove()
  }

  /* ================================================================ */
  /* building the world                                               */
  /* ================================================================ */
  private clearWorld() {
    ;[this.gVeg, this.gCities, this.gRoads, this.gPlace, this.gLife, this.gBorder].forEach((g) => {
      for (const c of [...g.children]) {
        g.remove(c)
        disposeTree(c)
      }
    })
    if (this.terrainMesh) {
      this.worldGroup.remove(this.terrainMesh)
      this.terrainGeo.dispose()
      ;(this.terrainMesh.material as THREE.Material).dispose()
    }
    if (this.waterMesh) {
      this.worldGroup.remove(this.waterMesh)
      this.waterMesh.geometry.dispose()
      ;(this.waterMesh.material as THREE.Material).dispose()
    }
    this.ctrlTex?.dispose()
    this.labels.forEach((l) => l.el.remove())
    this.labels = []
    this.placed = []
    this.ships = []
    this.cars = []
    this.carMesh = null
    this.carLights = null
    this.roadMesh = null
    this.borderLines = []
    this.veg = { con: null, bro: null, shr: null }
    this.cityGlow = []
    this.cityMarks = {}
  }

  private build() {
    this.clearWorld()
    this.preset = BIOMES[this.profile.biome]
    this.terrain = generateTerrain(this.profile.seed, this.preset, this.profile.capital_name)
    this.divisions = this.terrain.divisions.map((d) => ({ ...d }))
    this.buildTerrain()
    this.buildWater()
    this.rebuildRoads(true)
    this.buildVegetation()
    this.rebuildCities()
    this.buildBorder()
    this.buildShips()
    this.setLayers(this.layers)
    this.setQuality(this.quality)
    this.resetViewInstant()
  }

  private resetViewInstant() {
    this.camera.position.set(0, 175, 245)
    this.controls.target.set(0, 0, 0)
    this.controls.update()
  }

  private buildTerrain() {
    const h = this.terrain.heights
    const t = this.terrain
    const pos = new Float32Array(N * N * 3)
    const uv = new Float32Array(N * N * 2)
    for (let j = 0; j < N; j++) {
      for (let i = 0; i < N; i++) {
        const k = j * N + i
        pos[k * 3] = gridToWorld(i)
        pos[k * 3 + 1] = h[k]
        pos[k * 3 + 2] = gridToWorld(j)
        uv[k * 2] = i / (N - 1)
        uv[k * 2 + 1] = j / (N - 1)
      }
    }
    const idx = new Uint32Array((N - 1) * (N - 1) * 6)
    let q = 0
    for (let j = 0; j < N - 1; j++) {
      for (let i = 0; i < N - 1; i++) {
        const a = j * N + i
        const b = a + 1
        const c = a + N
        const d = c + 1
        idx[q++] = a
        idx[q++] = c
        idx[q++] = b
        idx[q++] = b
        idx[q++] = c
        idx[q++] = d
      }
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
    geo.setIndex(new THREE.BufferAttribute(idx, 1))
    geo.computeVertexNormals()
    geo.computeBoundingSphere()
    geo.computeBoundingBox()
    this.terrainGeo = geo

    // control texture: forest, moisture, water, height (half float)
    const data = new Uint16Array(N * N * 4)
    for (let k = 0; k < N * N; k++) {
      data[k * 4] = THREE.DataUtils.toHalfFloat(t.forest[k])
      data[k * 4 + 1] = THREE.DataUtils.toHalfFloat(t.moist[k])
      data[k * 4 + 2] = THREE.DataUtils.toHalfFloat(t.water[k])
      data[k * 4 + 3] = THREE.DataUtils.toHalfFloat(h[k])
    }
    const tex = new THREE.DataTexture(data, N, N, THREE.RGBAFormat, THREE.HalfFloatType)
    tex.minFilter = THREE.LinearFilter
    tex.magFilter = THREE.LinearFilter
    tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping
    tex.generateMipmaps = false
    tex.needsUpdate = true
    this.ctrlTex = tex

    const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.96, metalness: 0 })
    patchTerrainMaterial(mat, this.u, tex, this.preset.palette, this.preset.snowLine)
    const mesh = new THREE.Mesh(geo, mat)
    mesh.castShadow = true
    mesh.receiveShadow = true
    this.terrainMesh = mesh
    this.worldGroup.add(mesh)
  }

  private syncTerrainGeometry() {
    const h = this.terrain.heights
    const pos = this.terrainGeo.attributes.position as THREE.BufferAttribute
    for (let k = 0; k < N * N; k++) pos.setY(k, h[k])
    pos.needsUpdate = true
    this.terrainGeo.computeVertexNormals()
    this.terrainGeo.computeBoundingSphere()
  }

  private buildWater() {
    const mat = createWaterMaterial(this.u, this.ctrlTex, SIZE, 0, 1)
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(7000, 7000, 1, 1), mat)
    mesh.rotation.x = -Math.PI / 2
    mesh.position.y = 0.02
    mesh.renderOrder = 2
    mesh.frustumCulled = false
    this.waterMesh = mesh
    this.worldGroup.add(mesh)
  }

  /* ---------------------------- roads & traffic --------------------- */
  private rebuildRoads(initial = false) {
    if (this.roadMesh) {
      this.gRoads.remove(this.roadMesh)
      this.roadMesh.geometry.dispose()
      this.roadMesh = null
    }
    if (this.carMesh) {
      this.gLife.remove(this.carMesh)
      this.carMesh.geometry.dispose()
      this.carMesh = null
    }
    if (this.carLights) {
      this.gLife.remove(this.carLights)
      this.carLights.geometry.dispose()
      this.carLights = null
    }
    const h = this.terrain.heights
    const roads = buildRoads(h, this.divisions)
    this.roadMask.fill(0)
    this.roadPaths = []

    const positions: number[] = []
    const uvs: number[] = []
    const indices: number[] = []
    const W = 0.95
    roads.forEach((r) => {
      const m = r.length / 2
      if (m < 3) return
      const cum = new Float32Array(m)
      for (let k = 1; k < m; k++) cum[k] = cum[k - 1] + Math.hypot(r[k * 2] - r[k * 2 - 2], r[k * 2 + 1] - r[k * 2 - 1])
      this.roadPaths.push({ pts: Float32Array.from(r), cum, len: cum[m - 1] })
      const base = positions.length / 3
      for (let k = 0; k < m; k++) {
        const x = r[k * 2]
        const z = r[k * 2 + 1]
        const k0 = Math.max(0, k - 1)
        const k1 = Math.min(m - 1, k + 1)
        let tx = r[k1 * 2] - r[k0 * 2]
        let tz = r[k1 * 2 + 1] - r[k0 * 2 + 1]
        const l = Math.hypot(tx, tz) || 1
        tx /= l
        tz /= l
        const nx = -tz
        const nz = tx
        const lx = x + nx * W * 0.5
        const lz = z + nz * W * 0.5
        const rx = x - nx * W * 0.5
        const rz = z - nz * W * 0.5
        positions.push(lx, sampleHeight(h, lx, lz) + 0.1, lz, rx, sampleHeight(h, rx, rz) + 0.1, rz)
        uvs.push(cum[k] / 4.2, 0, cum[k] / 4.2, 1)
        if (k < m - 1) {
          const a = base + k * 2
          indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3)
        }
        // mask for vegetation
        const gi = Math.round(worldToGrid(x))
        const gj = Math.round(worldToGrid(z))
        for (let dz = -2; dz <= 2; dz++) {
          for (let dx = -2; dx <= 2; dx++) {
            const ci = gi + dx
            const cj = gj + dz
            if (ci >= 0 && cj >= 0 && ci < N && cj < N) this.roadMask[cj * N + ci] = 1
          }
        }
      }
    })
    if (positions.length) {
      const geo = new THREE.BufferGeometry()
      geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
      geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2))
      geo.setIndex(indices)
      geo.computeVertexNormals()
      const mat = new THREE.MeshStandardMaterial({
        map: this.roadTex,
        roughness: 0.93,
        polygonOffset: true,
        polygonOffsetFactor: -3,
        polygonOffsetUnits: -3,
      })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.receiveShadow = true
      mesh.frustumCulled = false
      this.roadMesh = mesh
      this.gRoads.add(mesh)
    }

    // vehicles
    this.cars = []
    const rnd = mulberry32(this.profile.seed + 404)
    this.roadPaths.forEach((rp, ri) => {
      const n = Math.max(2, Math.floor(rp.len / 11))
      for (let i = 0; i < n; i++) {
        this.cars.push({ road: ri, s: rnd() * rp.len, speed: 3.2 + rnd() * 3.6, dir: rnd() < 0.5 ? 1 : -1 })
      }
    })
    if (this.cars.length) {
      const body = paint(new THREE.BoxGeometry(0.7, 0.24, 0.34), '#ffffff', new THREE.Matrix4().makeTranslation(0, 0.16, 0))
      const cabin = paint(new THREE.BoxGeometry(0.34, 0.18, 0.3), '#1a2026', new THREE.Matrix4().makeTranslation(-0.05, 0.34, 0))
      const geo = mergeGeometries([body, cabin])!
      const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.45, metalness: 0.3 })
      const mesh = new THREE.InstancedMesh(geo, mat, this.cars.length)
      mesh.frustumCulled = false
      mesh.castShadow = true
      const palette = ['#d8d8d8', '#b02a2a', '#2b4a7a', '#202225', '#d2b24a', '#e9e9e9', '#4a7a52']
      this.cars.forEach((_, i) => mesh.setColorAt(i, new THREE.Color(palette[Math.floor(rnd() * palette.length)])))
      this.carMesh = mesh
      const lg = new THREE.BoxGeometry(0.08, 0.07, 0.3)
      lg.translate(0.36, 0.18, 0)
      const lm = new THREE.InstancedMesh(lg, new THREE.MeshBasicMaterial({ color: new THREE.Color(3.2, 2.7, 1.6), fog: false }), this.cars.length)
      lm.frustumCulled = false
      lm.visible = false
      this.carLights = lm
      this.gLife.add(mesh, lm)
    }
    if (!initial) this.pruneVegetationByRoads()
  }

  /* ---------------------------- vegetation -------------------------- */
  private buildVegetation() {
    const t = this.terrain
    const h = t.heights
    const rnd = mulberry32(this.profile.seed * 3 + 1)
    const con: Inst[] = []
    const bro: Inst[] = []
    const shr: Inst[] = []
    const step = 1.3
    const preset = this.preset
    for (let gz = -146; gz <= 146; gz += step) {
      for (let gx = -146; gx <= 146; gx += step) {
        const x = gx + (rnd() - 0.5) * step * 0.95
        const z = gz + (rnd() - 0.5) * step * 0.95
        const ci = Math.round(worldToGrid(x))
        const cj = Math.round(worldToGrid(z))
        if (ci < 0 || cj < 0 || ci >= N || cj >= N) continue
        const k = cj * N + ci
        if (this.roadMask[k]) continue
        const f = t.forest[k]
        const sc = t.scrub[k]
        if (f < 0.03 && sc < 0.04) continue
        const e = sampleHeight(h, x, z)
        if (e < 1.0) continue
        let nearCity = false
        for (const d of this.divisions) {
          if (Math.hypot(d.x - x, d.z - z) < d.radius * 1.2) {
            nearCity = true
            break
          }
        }
        if (nearCity) continue
        if (rnd() < Math.pow(f, 0.85)) {
          const conProb = Math.min(1, preset.coniferRatio + smoothstep(8, 17, e) * 0.55)
          if (rnd() < conProb) {
            con.push({ x, y: e - 0.05, z, s: (0.85 + rnd() * 0.8) * (1 - 0.3 * smoothstep(10, 19, e)), r: rnd() * 6.28 })
          } else {
            bro.push({ x, y: e - 0.05, z, s: 0.8 + rnd() * 0.75, r: rnd() * 6.28 })
          }
        } else if (rnd() < sc * 0.75) {
          shr.push({ x, y: e - 0.03, z, s: 0.7 + rnd() * 0.9, r: rnd() * 6.28 })
        }
      }
    }
    const shuffle = (a: Inst[]) => {
      for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(rnd() * (i + 1))
        const t2 = a[i]
        a[i] = a[j]
        a[j] = t2
      }
      return a.slice(0, 16000)
    }
    const make = (list: Inst[], geo: THREE.BufferGeometry, wind: number, key: 'con' | 'bro' | 'shr') => {
      if (list.length === 0) return
      const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0 })
      patchWindMaterial(mat, this.u, wind)
      const mesh = new THREE.InstancedMesh(geo, mat, list.length)
      mesh.frustumCulled = false
      mesh.castShadow = true
      mesh.receiveShadow = true
      const m4 = new THREE.Matrix4()
      const q = new THREE.Quaternion()
      const c = new THREE.Color()
      list.forEach((it, i) => {
        q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), it.r)
        m4.compose(new THREE.Vector3(it.x, it.y, it.z), q, new THREE.Vector3(it.s, it.s * (0.9 + (it.r % 1) * 0.3), it.s))
        mesh.setMatrixAt(i, m4)
        const v = 0.78 + ((it.r * 7.13) % 1) * 0.42
        c.setRGB(v * (0.95 + ((it.r * 3.1) % 1) * 0.1), v, v * (0.9 + ((it.r * 5.7) % 1) * 0.15))
        mesh.setColorAt(i, c)
      })
      mesh.instanceMatrix.needsUpdate = true
      this.gVeg.add(mesh)
      this.veg[key] = { mesh, inst: list, total: list.length }
    }
    make(shuffle(con), makeConiferGeometry(), 0.55, 'con')
    make(shuffle(bro), makeBroadleafGeometry(), 0.8, 'bro')
    make(shuffle(shr), makeShrubGeometry(), 0.12, 'shr')
  }

  private removeVegetation(x: number, z: number, r: number) {
    const zero = new THREE.Matrix4().makeScale(0, 0, 0)
    ;(['con', 'bro', 'shr'] as const).forEach((k) => {
      const v = this.veg[k]
      if (!v) return
      let dirty = false
      v.inst.forEach((it, i) => {
        if (it.s > 0 && Math.hypot(it.x - x, it.z - z) < r) {
          it.s = 0
          v.mesh.setMatrixAt(i, zero)
          dirty = true
        }
      })
      if (dirty) v.mesh.instanceMatrix.needsUpdate = true
    })
  }

  private pruneVegetationByRoads() {
    const zero = new THREE.Matrix4().makeScale(0, 0, 0)
    ;(['con', 'bro', 'shr'] as const).forEach((k) => {
      const v = this.veg[k]
      if (!v) return
      let dirty = false
      v.inst.forEach((it, i) => {
        if (it.s <= 0) return
        const ci = Math.round(worldToGrid(it.x))
        const cj = Math.round(worldToGrid(it.z))
        if (this.roadMask[cj * N + ci]) {
          it.s = 0
          v.mesh.setMatrixAt(i, zero)
          dirty = true
        }
      })
      if (dirty) v.mesh.instanceMatrix.needsUpdate = true
    })
  }

  /* ---------------------------- cities ----------------------------- */
  private rebuildCities() {
    for (const c of [...this.gCities.children]) {
      this.gCities.remove(c)
      disposeTree(c)
    }
    this.labels = this.labels.filter((l) => {
      if (l.kind === 'division') {
        l.el.remove()
        return false
      }
      return true
    })
    this.cityGlow = []
    this.cityMarks = {}

    const h = this.terrain.heights
    const water = this.terrain.water
    const rnd = mulberry32(this.profile.seed * 5 + 77)
    const concretes = ['#b9b4aa', '#a5a29b', '#cfc8b8', '#8f9399', '#b8a98f', '#c7c3bc', '#d6d0c2']
    const glassy = ['#7e8a96', '#6c7a88', '#9aa5ae', '#5f6d7c']
    type B = { m: THREE.Matrix4; c: THREE.Color }
    const list: B[] = []
    const q = new THREE.Quaternion()
    const yAxis = new THREE.Vector3(0, 1, 0)

    this.divisions.forEach((d, di) => {
      const ang = ((di * 1.37 + 0.4) % (Math.PI / 2)) - Math.PI / 4
      const cs = Math.cos(ang)
      const sn = Math.sin(ang)
      const padH = sampleHeight(h, d.x, d.z)
      const R = d.radius * 0.74
      const cell = 1.75
      const core = d.kind === 'capital' ? 7.5 : d.kind === 'province' ? 4.4 : 2.4
      const clear: [number, number, number][] =
        d.kind === 'capital'
          ? [[0, 0, 3.2], [6.2, 2.2, 3.3], [-5.5, -1.8, 1.4], [-7.2, 0.6, 1.4]]
          : d.kind === 'province'
            ? [[3.8, 1.6, 2.4], [-4.6, -2.6, 1.2]]
            : [[-3.8, 2.4, 1.5], [4.2, -2.4, 1]]
      const toWorld = (lx: number, lz: number) => ({ x: d.x + lx * cs + lz * sn, z: d.z - lx * sn + lz * cs })

      // urban ground disc
      const disc = new THREE.Mesh(
        new THREE.CircleGeometry(R * 1.12, 48),
        new THREE.MeshStandardMaterial({ map: this.cityTex, transparent: true, roughness: 0.95, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }),
      )
      disc.rotation.order = 'YXZ'
      disc.rotation.set(-Math.PI / 2, ang, 0)
      disc.position.set(d.x, padH + 0.06, d.z)
      disc.receiveShadow = true
      disc.renderOrder = 1
      this.gCities.add(disc)

      const span = Math.ceil(R / cell)
      for (let gi = -span; gi <= span; gi++) {
        for (let gj = -span; gj <= span; gj++) {
          const lx = gi * cell
          const lz = gj * cell
          const r = Math.hypot(lx, lz) / R
          if (r > 1) continue
          if (Math.abs(lx) < 0.75 || Math.abs(lz) < 0.75) continue
          const prob = 0.94 - 0.5 * Math.pow(r, 1.6)
          if (rnd() > prob) continue
          let blocked = false
          for (const [cx, cz, cr] of clear) {
            if (Math.hypot(lx - cx, lz - cz) < cr + 0.9) {
              blocked = true
              break
            }
          }
          if (blocked) continue
          const w = cell * (0.5 + rnd() * 0.32)
          const dd = cell * (0.5 + rnd() * 0.32)
          const wp = toWorld(lx + (rnd() - 0.5) * 0.15, lz + (rnd() - 0.5) * 0.15)
          const gi2 = Math.round(worldToGrid(wp.x))
          const gj2 = Math.round(worldToGrid(wp.z))
          if (gi2 < 0 || gj2 < 0 || gi2 >= N || gj2 >= N) continue
          if (water[gj2 * N + gi2] > 0.3) continue
          let mn = Infinity
          let mx = -Infinity
          for (const [ox, oz] of [[0, 0], [w / 2, dd / 2], [-w / 2, dd / 2], [w / 2, -dd / 2], [-w / 2, -dd / 2]]) {
            const hh = sampleHeight(h, wp.x + ox * cs + oz * sn, wp.z - ox * sn + oz * cs)
            mn = Math.min(mn, hh)
            mx = Math.max(mx, hh)
          }
          if (mn < 0.8) continue
          const centre = Math.pow(1 - r, 2.2)
          let height = 0.55 + rnd() * 0.9 + core * centre * (0.45 + rnd() * 0.95)
          // residential outskirts: low, wide
          if (r > 0.72) height = 0.5 + rnd() * 0.5
          const base = mn - 0.25
          height += mx - base
          const tall = height > 4.2
          const col = new THREE.Color(tall ? glassy[Math.floor(rnd() * glassy.length)] : concretes[Math.floor(rnd() * concretes.length)])
          col.offsetHSL(0, 0, (rnd() - 0.5) * 0.06)
          const m = new THREE.Matrix4()
          q.setFromAxisAngle(yAxis, ang)
          m.compose(new THREE.Vector3(wp.x, base, wp.z), q, new THREE.Vector3(w, height, dd))
          list.push({ m, c: col })
        }
      }

      // landmark
      const lm = buildLandmark(d.kind, this.mats)
      lm.position.set(d.x, padH, d.z)
      lm.rotation.y = ang
      this.gCities.add(lm)

      // night glow
      const spr = new THREE.Sprite(
        new THREE.SpriteMaterial({ map: this.glowTex, color: '#ffb25c', blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, opacity: 0, fog: false }),
      )
      const gs = R * (d.kind === 'capital' ? 4.8 : d.kind === 'province' ? 3.9 : 3.0)
      spr.scale.set(gs, gs * 0.55, 1)
      spr.position.set(d.x, padH + 2.2, d.z)
      this.gCities.add(spr)
      this.cityGlow.push({ sprite: spr, base: d.kind === 'capital' ? 0.62 : 0.45 })

      const anchor = new THREE.Vector3(d.x, padH + (d.kind === 'capital' ? 18.5 : 8.5), d.z)
      this.cityMarks[d.id] = { pad: padH, anchor }
      const flag = d.kind === 'capital' ? '★' : d.kind === 'province' ? '◆' : '●'
      const el = this.makeLabel('', 'division ' + d.kind, () => this.cb.onSelect({ type: 'division', id: d.id }))
      el.innerHTML = `<span class="ic">${flag}</span><span class="nm"></span>`
      el.querySelector('.nm')!.textContent = d.name
      this.labels.push({ el, pos: anchor, kind: 'division', ref: d.id })
    })

    const count = Math.max(1, list.length)
    const geo = new THREE.BoxGeometry(1, 1, 1)
    geo.translate(0, 0.5, 0)
    const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.82, metalness: 0.06 })
    patchBuildingMaterial(mat, this.u)
    const mesh = new THREE.InstancedMesh(geo, mat, count)
    mesh.frustumCulled = false
    mesh.castShadow = true
    mesh.receiveShadow = true
    if (list.length === 0) mesh.setMatrixAt(0, new THREE.Matrix4().makeScale(0, 0, 0))
    list.forEach((b, i) => {
      mesh.setMatrixAt(i, b.m)
      mesh.setColorAt(i, b.c)
    })
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
    this.gCities.add(mesh)
    this.gCities.visible = this.layers.divisions
    this.refreshRing()
  }

  /* ---------------------------- border ----------------------------- */
  private buildBorder() {
    const seg = contour(this.terrain.heights, -2.6, 2)
    if (seg.length < 4) return
    const arr = new Float32Array((seg.length / 4) * 6)
    for (let i = 0, o = 0; i < seg.length; i += 4) {
      arr[o++] = seg[i]
      arr[o++] = 0.45
      arr[o++] = seg[i + 1]
      arr[o++] = seg[i + 2]
      arr[o++] = 0.45
      arr[o++] = seg[i + 3]
    }
    const make = (width: number, opacity: number) => {
      const geo = new LineSegmentsGeometry()
      geo.setPositions(arr)
      const mat = new LineMaterial({ color: new THREE.Color(this.profile.map_color).getHex(), linewidth: width, transparent: true, opacity, depthWrite: false })
      mat.resolution.set(this.container.clientWidth, this.container.clientHeight)
      const line = new LineSegments2(geo, mat)
      line.frustumCulled = false
      line.renderOrder = 6
      this.gBorder.add(line)
      this.borderLines.push(line)
    }
    make(2.2, 0.95)
    make(9, 0.2)
  }

  /* ---------------------------- ships ------------------------------ */
  private buildShips() {
    const h = this.terrain.heights
    const rnd = mulberry32(this.profile.seed + 909)
    let tries = 0
    while (this.ships.length < 6 && tries++ < 600) {
      const ax = (rnd() - 0.5) * 270
      const az = (rnd() - 0.5) * 270
      const a = rnd() * Math.PI * 2
      const L = 34 + rnd() * 30
      const bx = ax + Math.cos(a) * L
      const bz = az + Math.sin(a) * L
      if (Math.abs(bx) > 140 || Math.abs(bz) > 140) continue
      let ok = true
      for (let k = 0; k <= 24; k++) {
        const t = k / 24
        if (sampleHeight(h, ax + (bx - ax) * t, az + (bz - az) * t) > -3.2) {
          ok = false
          break
        }
      }
      if (!ok) continue
      const type = this.ships.length % 3 === 2 ? 'frigate' : 'cargo'
      const obj = buildShip(type, rnd() * 100)
      obj.scale.setScalar(type === 'cargo' ? 1.15 : 1.0)
      this.gLife.add(obj)
      this.ships.push({ obj, ax, az, bx, bz, t: rnd(), dir: 1, speed: (type === 'cargo' ? 1.9 : 3.0) / L, phase: rnd() * 10 })
    }
  }

  /* ================================================================ */
  /* interaction                                                      */
  /* ================================================================ */
  private onMove = (e: PointerEvent) => {
    this.pointerXY = { x: e.clientX, y: e.clientY }
    this.pointerDirty = true
  }
  private onDown = (e: PointerEvent) => {
    this.downInfo = { x: e.clientX, y: e.clientY, t: performance.now() }
    this.dragging = true
  }
  private onUp = (e: PointerEvent) => {
    this.dragging = false
    const d = this.downInfo
    this.downInfo = null
    if (!d || e.button !== 0) return
    if (e.target !== this.renderer.domElement) return
    if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 6 || performance.now() - d.t > 450) return
    this.handleClick(e.clientX, e.clientY)
  }
  private onContext = (e: Event) => {
    if (this.placingKey) {
      e.preventDefault()
      this.startPlacing(null)
    }
  }

  private pickGround(cx: number, cy: number): THREE.Vector3 | null {
    if (!this.terrain) return null
    const rect = this.renderer.domElement.getBoundingClientRect()
    const ndc = new THREE.Vector2(((cx - rect.left) / rect.width) * 2 - 1, -((cy - rect.top) / rect.height) * 2 + 1)
    this.raycaster.setFromCamera(ndc, this.camera)
    const o = this.raycaster.ray.origin
    const d = this.raycaster.ray.direction
    const h = this.terrain.heights
    const ground = (x: number, z: number) =>
      Math.abs(x) < SIZE / 2 - 0.01 && Math.abs(z) < SIZE / 2 - 0.01 ? Math.max(sampleHeight(h, x, z), 0) : 0
    let prevT = 0
    let t = 0
    let step = 0.8
    while (t < 2200) {
      const y = o.y + d.y * t
      if (y < ground(o.x + d.x * t, o.z + d.z * t)) {
        let a = prevT
        let b = t
        for (let i = 0; i < 16; i++) {
          const m = (a + b) / 2
          if (o.y + d.y * m < ground(o.x + d.x * m, o.z + d.z * m)) b = m
          else a = m
        }
        return new THREE.Vector3(o.x + d.x * b, o.y + d.y * b, o.z + d.z * b)
      }
      prevT = t
      t += step
      step = Math.min(step * 1.012, 3.2)
      if (d.y > 0 && y > 400) break
    }
    return null
  }

  private selectionAt(p: THREE.Vector3): Selection {
    let best: Selection = null
    let bd = Infinity
    for (const pl of this.placed) {
      const dd = Math.hypot(pl.x - p.x, pl.z - p.z)
      if (dd < pl.radius * 1.05 && dd < bd) {
        bd = dd
        best = { type: 'placement', id: pl.id }
      }
    }
    if (best) return best
    for (const d of this.divisions) {
      const dd = Math.hypot(d.x - p.x, d.z - p.z)
      if (dd < d.radius * 0.95 && dd < bd) {
        bd = dd
        best = { type: 'division', id: d.id }
      }
    }
    return best
  }

  private nearestDivisions(x: number, z: number) {
    return [...this.divisions].sort((a, b) => Math.hypot(a.x - x, a.z - z) - Math.hypot(b.x - x, b.z - z))
  }

  private handleClick(cx: number, cy: number) {
    const p = this.pickGround(cx, cy)
    if (this.placingKey) {
      if (!p || !this.ghost) return
      const radius = this.ghost.userData.radius as number
      const v = this.validateSpot(p.x, p.z, radius)
      if (!v.ok) {
        this.cb.onGhost(v)
        return
      }
      const key = this.placingKey
      this.cb.onPlaceRequest({ item: key, x: p.x, z: p.z, nearest: this.nearestDivisions(p.x, p.z) })
      return
    }
    const sel = p ? this.selectionAt(p) : null
    this.select(sel)
    this.cb.onSelect(sel)
  }

  private processHover() {
    if (!this.pointerDirty || this.dragging || !this.terrain) return
    this.pointerDirty = false
    const p = this.pickGround(this.pointerXY.x, this.pointerXY.y)
    if (this.placingKey && this.ghost && this.ghostRing) {
      if (!p) {
        this.ghost.visible = false
        this.ghostRing.visible = false
        return
      }
      const radius = this.ghost.userData.radius as number
      const y = Math.max(sampleHeight(this.terrain.heights, p.x, p.z), 0.2)
      this.ghost.visible = true
      this.ghost.position.set(p.x, y + 0.1, p.z)
      this.ghostRing.visible = true
      this.ghostRing.position.set(p.x, y + 0.25, p.z)
      const v = this.validateSpot(p.x, p.z, radius)
      this.ghostMat.color.set(v.ok ? '#46f09a' : '#ff5c5c')
      ;(this.ghostRing.material as THREE.MeshBasicMaterial).color.set(v.ok ? '#46f09a' : '#ff5c5c')
      if (!this.ghostState || this.ghostState.ok !== v.ok || this.ghostState.reason !== v.reason) {
        this.ghostState = v
        this.cb.onGhost(v)
      }
      return
    }
    const sel = p ? this.selectionAt(p) : null
    const same = JSON.stringify(sel) === JSON.stringify(this.hoverSel)
    if (!same) {
      this.hoverSel = sel
      this.renderer.domElement.style.cursor = sel ? 'pointer' : 'grab'
    }
  }

  private refreshRing() {
    const sel = this.selected
    if (!sel) {
      this.ring.visible = false
      this.beam.visible = false
      return
    }
    let x = 0
    let z = 0
    let r = 6
    let color = '#55d6ff'
    if (sel.type === 'division') {
      const d = this.divisions.find((v) => v.id === sel.id)
      if (!d) {
        this.ring.visible = false
        this.beam.visible = false
        return
      }
      x = d.x
      z = d.z
      r = d.radius * 0.82
      color = d.kind === 'capital' ? '#f1c86d' : '#55d6ff'
    } else {
      const p = this.placed.find((v) => v.id === sel.id)
      if (!p) {
        this.ring.visible = false
        this.beam.visible = false
        return
      }
      x = p.x
      z = p.z
      r = p.radius * 1.15
      color = '#ff8a5c'
    }
    const y = sampleHeight(this.terrain.heights, x, z)
    ;(this.ring.material as THREE.MeshBasicMaterial).color.set(color)
    ;(this.beam.material as THREE.MeshBasicMaterial).color.set(color)
    this.ring.position.set(x, y + 0.3, z)
    this.ring.scale.setScalar(r)
    this.ring.visible = true
    this.beam.position.set(x, y + 20, z)
    this.beam.visible = true
  }

  private makeLabel(text: string, cls: string, onClick: () => void) {
    const el = document.createElement('div')
    el.className = 'c3d-label ' + cls
    el.textContent = text
    el.addEventListener('click', (e) => {
      e.stopPropagation()
      onClick()
    })
    this.labelLayer.appendChild(el)
    return el
  }

  private flyTo(x: number, z: number, dist: number, polar = 0.9) {
    const gy = Math.max(sampleHeight(this.terrain.heights, x, z), 0)
    const toT = new THREE.Vector3(x, gy, z)
    const off = new THREE.Vector3().subVectors(this.camera.position, this.controls.target)
    const az = Math.atan2(off.x, off.z)
    const toP = new THREE.Vector3(
      x + Math.sin(az) * Math.sin(polar) * dist,
      gy + Math.cos(polar) * dist,
      z + Math.cos(az) * Math.sin(polar) * dist,
    )
    this.flight = {
      t0: performance.now(),
      dur: 1500,
      fromT: this.controls.target.clone(),
      toT,
      fromP: this.camera.position.clone(),
      toP,
    }
  }

  /* ================================================================ */
  /* frame loop                                                       */
  /* ================================================================ */
  private resize() {
    const w = Math.max(1, this.container.clientWidth)
    const h = Math.max(1, this.container.clientHeight)
    this.renderer.setSize(w, h)
    this.camera.aspect = w / h
    this.camera.updateProjectionMatrix()
    this.borderLines.forEach((l) => (l.material as LineMaterial).resolution.set(w, h))
  }

  private updateAtmosphere() {
    applyAtmosphere(this.hour, this.u, this.sky, this.cloudy)
    this.sun.color.copy(this.sky.lightColor)
    this.sun.intensity = this.sky.lightIntensity
    this.hemi.color.copy(this.sky.hemiSky)
    this.hemi.groundColor.copy(this.sky.hemiGround)
    this.hemi.intensity = this.sky.hemiIntensity
    this.renderer.toneMappingExposure = this.sky.exposure
    const fog = this.scene.fog as THREE.FogExp2
    fog.color.copy(this.u.uFogCol.value)
    fog.density = this.u.uFogDensity.value
  }

  private loop = () => {
    if (this.disposed) return
    this.raf = requestAnimationFrame(this.loop)
    const now = performance.now()
    const dt = Math.min(0.05, (now - this.lastT) / 1000)
    this.lastT = now
    this.u.uTime.value += dt

    if (this.playing) {
      this.hour = (this.hour + dt * 0.35) % 24
      this.updateAtmosphere()
      this.hourEmit += dt
      if (this.hourEmit > 0.25) {
        this.hourEmit = 0
        this.cb.onHour(this.hour)
      }
    }

    // camera flight
    if (this.flight) {
      const f = this.flight
      const k = Math.min(1, (now - f.t0) / f.dur)
      const e = ease(k)
      this.controls.target.lerpVectors(f.fromT, f.toT, e)
      this.camera.position.lerpVectors(f.fromP, f.toP, e)
      // arc up slightly mid-flight
      this.camera.position.y += Math.sin(k * Math.PI) * 18
      if (k >= 1) this.flight = null
    }
    this.controls.target.x = Math.max(-150, Math.min(150, this.controls.target.x))
    this.controls.target.z = Math.max(-150, Math.min(150, this.controls.target.z))
    this.controls.update()

    // keep camera above the ground
    if (this.terrain) {
      const cp = this.camera.position
      if (Math.abs(cp.x) < SIZE / 2 && Math.abs(cp.z) < SIZE / 2) {
        const gh = Math.max(sampleHeight(this.terrain.heights, cp.x, cp.z), 0) + 3
        if (cp.y < gh) cp.y = gh
      } else if (cp.y < 3) cp.y = 3
    }

    this.skyMesh.position.copy(this.camera.position)
    this.updateLight()
    this.processHover()
    this.animate(dt, now)
    this.updateLabels()

    this.renderer.render(this.scene, this.camera)

    this.fpsAcc += dt
    this.fpsFrames++
    if (this.fpsAcc > 1) {
      this.cb.onFps(Math.round(this.fpsFrames / this.fpsAcc))
      this.fpsAcc = 0
      this.fpsFrames = 0
    }
  }

  private updateLight() {
    const tgt = this.controls.target
    const dist = this.camera.position.distanceTo(tgt)
    const ext = Math.round(Math.min(200, Math.max(30, dist * 0.62)) / 8) * 8
    const cam = this.sun.shadow.camera
    if (ext !== this.shadowExt) {
      this.shadowExt = ext
      cam.left = -ext
      cam.right = ext
      cam.top = ext
      cam.bottom = -ext
      cam.near = 5
      cam.far = 640
      cam.updateProjectionMatrix()
    }
    const texel = (ext * 2) / this.sun.shadow.mapSize.x
    const sx = Math.round(tgt.x / (texel * 6)) * texel * 6
    const sz = Math.round(tgt.z / (texel * 6)) * texel * 6
    this.sun.target.position.set(sx, 0, sz)
    this.sun.position.set(sx + this.sky.lightDir.x * 320, this.sky.lightDir.y * 320, sz + this.sky.lightDir.z * 320)
    this.sun.target.updateMatrixWorld()
  }

  private animate(dt: number, now: number) {
    const t = this.u.uTime.value
    // beacons
    this.mats.beacon.emissiveIntensity = 1.0 + 1.6 * (0.5 + 0.5 * Math.sin(t * 4.2))

    // night-time elements
    const night = this.u.uNight.value
    this.cityGlow.forEach((g) => ((g.sprite.material as THREE.SpriteMaterial).opacity = g.base * night * (this.layers.divisions ? 1 : 0)))
    if (this.carLights) this.carLights.visible = night > 0.2

    // placements
    for (const p of this.placed) {
      const k = Math.min(1, (now - p.born) / 900)
      const e = 1 - Math.pow(1 - k, 3)
      const overshoot = k < 1 ? 1 + Math.sin(k * Math.PI) * 0.06 : 1
      p.group.scale.setScalar(Math.max(0.001, e * overshoot))
      if (p.spin) p.spin.rotation.y += dt * 1.1
    }
    // selection ring pulse
    if (this.ring.visible) {
      const s = this.selected
      let base = 6
      if (s?.type === 'division') base = (this.divisions.find((d) => d.id === s.id)?.radius ?? 8) * 0.82
      else if (s?.type === 'placement') base = (this.placed.find((p) => p.id === s.id)?.radius ?? 5) * 1.15
      this.ring.scale.setScalar(base * (1 + 0.025 * Math.sin(t * 3)))
      ;(this.ring.material as THREE.MeshBasicMaterial).opacity = 0.65 + 0.3 * Math.sin(t * 3)
      this.beam.rotation.y += dt * 0.6
    }
    if (this.ghost && this.ghost.visible) {
      this.ghostMat.opacity = 0.42 + 0.14 * Math.sin(t * 5)
    }

    // ships
    for (const s of this.ships) {
      s.t += s.dir * s.speed * dt
      if (s.t > 1) {
        s.t = 1
        s.dir = -1
      } else if (s.t < 0) {
        s.t = 0
        s.dir = 1
      }
      const x = s.ax + (s.bx - s.ax) * s.t
      const z = s.az + (s.bz - s.az) * s.t
      const dx = (s.bx - s.ax) * s.dir
      const dz = (s.bz - s.az) * s.dir
      const heading = Math.atan2(-dz, dx)
      s.obj.position.set(x, 0.02 + Math.sin(t * 1.3 + s.phase) * 0.05, z)
      s.obj.rotation.set(Math.sin(t * 0.9 + s.phase) * 0.015, heading, Math.sin(t * 1.1 + s.phase) * 0.02)
    }

    // cars
    if (this.carMesh && this.layers.divisions) {
      const h = this.terrain.heights
      const m4 = new THREE.Matrix4()
      const q = new THREE.Quaternion()
      const up = new THREE.Vector3(0, 1, 0)
      const one = new THREE.Vector3(1, 1, 1)
      const pv = new THREE.Vector3()
      for (let i = 0; i < this.cars.length; i++) {
        const c = this.cars[i]
        const rp = this.roadPaths[c.road]
        c.s += c.dir * c.speed * dt
        if (c.s > rp.len) c.s -= rp.len
        if (c.s < 0) c.s += rp.len
        // locate segment
        let lo = 0
        let hi = rp.cum.length - 1
        while (hi - lo > 1) {
          const mid = (lo + hi) >> 1
          if (rp.cum[mid] <= c.s) lo = mid
          else hi = mid
        }
        const segLen = rp.cum[hi] - rp.cum[lo] || 1
        const f = (c.s - rp.cum[lo]) / segLen
        const x0 = rp.pts[lo * 2]
        const z0 = rp.pts[lo * 2 + 1]
        const x1 = rp.pts[hi * 2]
        const z1 = rp.pts[hi * 2 + 1]
        let tx = (x1 - x0) / segLen
        let tz = (z1 - z0) / segLen
        const lane = 0.21 * c.dir
        let x = x0 + (x1 - x0) * f + -tz * lane
        let z = z0 + (z1 - z0) * f + tx * lane
        const y = sampleHeight(h, x, z) + 0.17
        if (c.dir < 0) {
          tx = -tx
          tz = -tz
        }
        if (!isFinite(x)) x = 0
        if (!isFinite(z)) z = 0
        q.setFromAxisAngle(up, Math.atan2(-tz, tx))
        pv.set(x, y, z)
        m4.compose(pv, q, one)
        this.carMesh.setMatrixAt(i, m4)
        this.carLights?.setMatrixAt(i, m4)
      }
      this.carMesh.instanceMatrix.needsUpdate = true
      if (this.carLights) this.carLights.instanceMatrix.needsUpdate = true
    }
  }

  private updateLabels() {
    const w = this.container.clientWidth
    const h = this.container.clientHeight
    const camPos = this.camera.position
    const v = new THREE.Vector3()
    for (const l of this.labels) {
      const visibleLayer = l.kind === 'division' ? this.layers.divisions : this.layers.placements
      v.copy(l.pos).project(this.camera)
      const dist = camPos.distanceTo(l.pos)
      const maxD = l.kind === 'division' ? 900 : 190
      if (!visibleLayer || v.z > 1 || v.z < -1 || Math.abs(v.x) > 1.15 || Math.abs(v.y) > 1.15 || dist > maxD) {
        l.el.style.display = 'none'
        continue
      }
      l.el.style.display = ''
      const x = (v.x * 0.5 + 0.5) * w
      const y = (-v.y * 0.5 + 0.5) * h
      const sc = l.kind === 'division' ? Math.max(0.78, Math.min(1.12, 190 / dist + 0.4)) : 1
      l.el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -100%) scale(${sc.toFixed(3)})`
      const isSel =
        this.selected &&
        ((this.selected.type === 'division' && l.kind === 'division' && this.selected.id === l.ref) ||
          (this.selected.type === 'placement' && l.kind === 'unit' && String(this.selected.id) === l.ref))
      l.el.classList.toggle('sel', !!isSel)
      l.el.style.opacity = String(l.kind === 'unit' ? Math.max(0.25, 1 - dist / maxD) : 1)
    }
  }
}
