import * as THREE from 'three'
import { mergeGeometries, mergeVertices } from 'three/examples/jsm/utils/BufferGeometryUtils.js'

/** icosphere with welded vertices → smooth shading */
function smoothIco(r: number, detail: number) {
  const g = new THREE.IcosahedronGeometry(r, detail)
  g.deleteAttribute('uv')
  g.deleteAttribute('normal')
  return mergeVertices(g, 1e-4)
}
import type { ItemKey } from './data'

/* ------------------------------------------------------------------ */
/* merged, vertex-coloured geometry helper                             */
/* ------------------------------------------------------------------ */
export function paint(geo: THREE.BufferGeometry, color: THREE.ColorRepresentation, m?: THREE.Matrix4) {
  let g = geo
  if (g.index) g = g.toNonIndexed()
  if (m) g.applyMatrix4(m)
  g.deleteAttribute('uv')
  const col = new THREE.Color(color)
  const arr = new Float32Array(g.attributes.position.count * 3)
  for (let i = 0; i < g.attributes.position.count; i++) {
    arr[i * 3] = col.r
    arr[i * 3 + 1] = col.g
    arr[i * 3 + 2] = col.b
  }
  g.setAttribute('color', new THREE.BufferAttribute(arr, 3))
  return g
}

const T = (x: number, y: number, z: number) => new THREE.Matrix4().makeTranslation(x, y, z)
const TS = (x: number, y: number, z: number, sx: number, sy: number, sz: number) =>
  new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion(), new THREE.Vector3(sx, sy, sz))

/** deterministic pseudo-random for model detail */
function jitterColor(hex: string, amount: number, seed: number) {
  const c = new THREE.Color(hex)
  const r = (Math.sin(seed * 12.9898) * 43758.5453) % 1
  c.offsetHSL(r * 0.02, r * amount * 0.5, r * amount * 0.5)
  return c
}

/* ------------------------------------------------------------------ */
/* vegetation                                                          */
/* ------------------------------------------------------------------ */
export function makeConiferGeometry() {
  const parts: THREE.BufferGeometry[] = []
  parts.push(paint(new THREE.CylinderGeometry(0.09, 0.15, 0.7, 5), '#4a3524', T(0, 0.35, 0)))
  const tiers = [
    { r: 1.0, h: 1.35, y: 0.55, c: '#2f5a33' },
    { r: 0.78, h: 1.25, y: 1.2, c: '#356638' },
    { r: 0.52, h: 1.1, y: 1.9, c: '#3b7040' },
    { r: 0.28, h: 0.7, y: 2.55, c: '#437a46' },
  ]
  tiers.forEach((t, i) => {
    parts.push(paint(new THREE.ConeGeometry(t.r, t.h, 7, 1), jitterColor(t.c, 0.5, i + 1), T(0, t.y + t.h / 2, 0)))
  })
  const g = mergeGeometries(parts)!
  parts.forEach((p) => p.dispose())
  return g
}

export function makeBroadleafGeometry() {
  const parts: THREE.BufferGeometry[] = []
  parts.push(paint(new THREE.CylinderGeometry(0.1, 0.17, 1.3, 5), '#5a4330', T(0, 0.65, 0)))
  const blobs = [
    { r: 1.05, x: 0, y: 2.0, z: 0, c: '#4f7d36' },
    { r: 0.8, x: 0.55, y: 1.65, z: 0.3, c: '#5a8a3c' },
    { r: 0.78, x: -0.5, y: 1.75, z: -0.35, c: '#477432' },
  ]
  blobs.forEach((b, i) => {
    const ico = smoothIco(b.r, 1)
    // squash + noisy surface for a leafy silhouette
    const pos = ico.attributes.position
    for (let k = 0; k < pos.count; k++) {
      const x = pos.getX(k)
      const y = pos.getY(k)
      const z = pos.getZ(k)
      const n = 1 + 0.16 * Math.sin(x * 5.1 + i) * Math.cos(z * 4.3 + y * 3.1)
      pos.setXYZ(k, x * n, y * n * 0.86, z * n)
    }
    ico.computeVertexNormals()
    parts.push(paint(ico, jitterColor(b.c, 0.6, i + 7), T(b.x, b.y, b.z)))
  })
  const g = mergeGeometries(parts)!
  parts.forEach((p) => p.dispose())
  return g
}

export function makeShrubGeometry() {
  const parts: THREE.BufferGeometry[] = []
  const blobs = [
    { r: 0.55, x: 0, y: 0.35, z: 0, c: '#7b7a45' },
    { r: 0.4, x: 0.4, y: 0.28, z: 0.2, c: '#8a8650' },
    { r: 0.38, x: -0.35, y: 0.26, z: -0.2, c: '#6d7040' },
  ]
  blobs.forEach((b, i) => {
    const ico = smoothIco(b.r, 1)
    ico.computeVertexNormals()
    parts.push(paint(ico, jitterColor(b.c, 0.5, i + 3), TS(b.x, b.y, b.z, 1, 0.7, 1)))
  })
  const g = mergeGeometries(parts)!
  parts.forEach((p) => p.dispose())
  return g
}

/* ------------------------------------------------------------------ */
/* shared standard materials                                           */
/* ------------------------------------------------------------------ */
export interface ModelMats {
  olive: THREE.MeshStandardMaterial
  darkOlive: THREE.MeshStandardMaterial
  metal: THREE.MeshStandardMaterial
  steel: THREE.MeshStandardMaterial
  concrete: THREE.MeshStandardMaterial
  asphalt: THREE.MeshStandardMaterial
  white: THREE.MeshStandardMaterial
  red: THREE.MeshStandardMaterial
  glass: THREE.MeshStandardMaterial
  sand: THREE.MeshStandardMaterial
  grass: THREE.MeshStandardMaterial
  beacon: THREE.MeshStandardMaterial
  gold: THREE.MeshStandardMaterial
  runway: THREE.MeshStandardMaterial
}

export function createModelMats(): ModelMats {
  const m = (color: string, rough = 0.8, metal = 0.0) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal })
  const runwayTex = makeRunwayTexture()
  return {
    olive: m('#59663f', 0.85),
    darkOlive: m('#3b4630', 0.9),
    metal: m('#262a30', 0.5, 0.5),
    steel: m('#8a9097', 0.45, 0.6),
    concrete: m('#a09f98', 0.95),
    asphalt: m('#2a2c2f', 0.95),
    white: m('#e8eaec', 0.6),
    red: m('#b3322a', 0.6),
    glass: new THREE.MeshStandardMaterial({ color: '#1a2630', roughness: 0.08, metalness: 0.7 }),
    sand: m('#a89572', 0.95),
    grass: m('#566b36', 1),
    beacon: new THREE.MeshStandardMaterial({ color: '#ff3a2a', emissive: '#ff2200', emissiveIntensity: 2.2, roughness: 0.4 }),
    gold: m('#c9a45a', 0.35, 0.65),
    runway: new THREE.MeshStandardMaterial({ map: runwayTex, roughness: 0.92 }),
  }
}

function makeRunwayTexture() {
  const cv = document.createElement('canvas')
  cv.width = 1024
  cv.height = 128
  const g = cv.getContext('2d')!
  g.fillStyle = '#2c2e31'
  g.fillRect(0, 0, 1024, 128)
  // speckle
  for (let i = 0; i < 2600; i++) {
    g.fillStyle = `rgba(${90 + Math.random() * 60},${90 + Math.random() * 60},${90 + Math.random() * 60},${Math.random() * 0.08})`
    g.fillRect(Math.random() * 1024, Math.random() * 128, 2, 2)
  }
  g.fillStyle = '#e6e6e0'
  for (let x = 90; x < 940; x += 56) g.fillRect(x, 61, 32, 6)
  for (let k = 0; k < 6; k++) {
    g.fillRect(24, 22 + k * 14, 46, 6)
    g.fillRect(954, 22 + k * 14, 46, 6)
  }
  g.fillRect(8, 6, 1008, 3)
  g.fillRect(8, 119, 1008, 3)
  g.font = 'bold 34px sans-serif'
  g.save()
  g.translate(118, 64)
  g.rotate(Math.PI / 2)
  g.fillText('09', -18, 0)
  g.restore()
  g.save()
  g.translate(900, 64)
  g.rotate(-Math.PI / 2)
  g.fillText('27', -18, 0)
  g.restore()
  const tex = new THREE.CanvasTexture(cv)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = 8
  return tex
}

/* ------------------------------------------------------------------ */
/* little builders                                                     */
/* ------------------------------------------------------------------ */
function mesh(geo: THREE.BufferGeometry, mat: THREE.Material, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geo, mat)
  m.position.set(x, y, z)
  m.castShadow = true
  m.receiveShadow = true
  return m
}
const box = (w: number, h: number, d: number) => new THREE.BoxGeometry(w, h, d)
const cyl = (rt: number, rb: number, h: number, s = 12) => new THREE.CylinderGeometry(rt, rb, h, s)

function makeTank(mats: ModelMats, scale = 1) {
  const g = new THREE.Group()
  g.add(mesh(box(1.7, 0.36, 0.95), mats.darkOlive, 0, 0.32, 0))
  g.add(mesh(box(1.85, 0.3, 0.26), mats.metal, 0, 0.18, 0.55))
  g.add(mesh(box(1.85, 0.3, 0.26), mats.metal, 0, 0.18, -0.55))
  g.add(mesh(box(0.4, 0.2, 0.9), mats.darkOlive, 0.75, 0.55, 0))
  const turret = new THREE.Group()
  turret.position.set(-0.1, 0.62, 0)
  turret.add(mesh(box(0.85, 0.28, 0.72), mats.olive, 0, 0.12, 0))
  turret.add(mesh(cyl(0.05, 0.06, 1.35, 8), mats.metal, 1.05, 0.14, 0).rotateZ(Math.PI / 2))
  turret.add(mesh(cyl(0.12, 0.12, 0.2, 8), mats.metal, -0.15, 0.34, 0.14))
  g.add(turret)
  g.scale.setScalar(scale)
  return g
}

function makeTruck(mats: ModelMats, color: THREE.Material, scale = 1) {
  const g = new THREE.Group()
  g.add(mesh(box(0.55, 0.42, 0.62), color, 0.75, 0.42, 0))
  g.add(mesh(box(0.2, 0.2, 0.55), mats.glass, 1.0, 0.52, 0))
  g.add(mesh(box(1.5, 0.34, 0.66), mats.darkOlive, -0.1, 0.35, 0))
  g.add(mesh(box(1.45, 0.5, 0.62), color, -0.1, 0.77, 0))
  for (const x of [-0.65, -0.1, 0.8]) for (const z of [-0.34, 0.34]) g.add(mesh(cyl(0.17, 0.17, 0.12, 10), mats.metal, x, 0.17, z).rotateX(Math.PI / 2))
  g.scale.setScalar(scale)
  return g
}

function makeHowitzer(mats: ModelMats) {
  const g = new THREE.Group()
  g.add(mesh(box(1.6, 0.34, 0.9), mats.olive, 0, 0.3, 0))
  g.add(mesh(box(1.7, 0.28, 0.24), mats.metal, 0, 0.16, 0.52))
  g.add(mesh(box(1.7, 0.28, 0.24), mats.metal, 0, 0.16, -0.52))
  const t = new THREE.Group()
  t.position.set(-0.15, 0.62, 0)
  t.add(mesh(box(1.0, 0.5, 0.8), mats.darkOlive, 0, 0.2, 0))
  const barrel = mesh(cyl(0.065, 0.075, 2.3, 8), mats.metal, 1.3, 0.55, 0)
  barrel.rotation.z = Math.PI / 2 - 0.5
  barrel.position.set(1.0, 0.65, 0)
  t.add(barrel)
  t.add(mesh(cyl(0.12, 0.12, 0.28, 8), mats.metal, 0.3, 0.5, 0).rotateZ(Math.PI / 2 - 0.5))
  g.add(t)
  return g
}

function makeJet(mats: ModelMats, hex = '#8b929a') {
  const g = new THREE.Group()
  const body = new THREE.MeshStandardMaterial({ color: hex, roughness: 0.4, metalness: 0.55 })
  const fus = mesh(cyl(0.17, 0.22, 2.6, 10), body, 0, 0.5, 0)
  fus.rotation.z = Math.PI / 2
  g.add(fus)
  const nose = mesh(new THREE.ConeGeometry(0.17, 0.85, 10), body, 1.7, 0.5, 0)
  nose.rotation.z = -Math.PI / 2
  g.add(nose)
  const shape = new THREE.Shape()
  shape.moveTo(0.9, 0)
  shape.lineTo(-0.5, 1.45)
  shape.lineTo(-0.9, 1.45)
  shape.lineTo(-0.9, -1.45)
  shape.lineTo(-0.5, -1.45)
  shape.closePath()
  const wg = new THREE.ExtrudeGeometry(shape, { depth: 0.05, bevelEnabled: false })
  wg.rotateX(-Math.PI / 2)
  g.add(mesh(wg, body, 0, 0.42, 0))
  for (const s of [-1, 1]) {
    const fin = mesh(box(0.55, 0.5, 0.04), body, -1.15, 0.85, s * 0.17)
    fin.rotation.x = s * 0.18
    g.add(fin)
  }
  const canopy = mesh(new THREE.SphereGeometry(0.2, 10, 8), mats.glass, 0.65, 0.68, 0)
  canopy.scale.set(2, 0.7, 0.8)
  g.add(canopy)
  g.add(mesh(cyl(0.12, 0.14, 0.5, 8), mats.metal, -1.4, 0.5, 0).rotateZ(Math.PI / 2))
  g.scale.setScalar(0.95)
  return g
}

/* ------------------------------------------------------------------ */
/* installations                                                       */
/* ------------------------------------------------------------------ */
export interface BuiltModel {
  group: THREE.Group
  spin?: THREE.Object3D
  radius: number
}

export function buildInstallation(key: ItemKey, mats: ModelMats): BuiltModel {
  const g = new THREE.Group()
  let spin: THREE.Object3D | undefined
  let radius = 4

  if (key === 'radar') {
    radius = 3.6
    g.add(mesh(cyl(3.5, 3.6, 0.16, 28), mats.concrete, 0, 0.08, 0))
    g.add(mesh(box(2.4, 1.3, 2.4), mats.concrete, 0, 0.8, 0))
    g.add(mesh(box(2.5, 0.14, 2.5), mats.darkOlive, 0, 1.5, 0))
    g.add(mesh(cyl(0.38, 0.55, 3.2, 12), mats.steel, 0, 3.0, 0))
    const head = new THREE.Group()
    head.position.set(0, 4.8, 0)
    const dish = mesh(new THREE.SphereGeometry(1.9, 24, 8, 0, Math.PI * 2, 0, Math.PI / 3.1), mats.white, 0, 0, 0)
    dish.rotation.x = Math.PI / 2
    dish.rotation.z = 0
    dish.scale.set(1.8, 0.45, 1)
    dish.position.set(0.1, 0, 0)
    ;(dish.material as THREE.Material).side = THREE.DoubleSide
    head.add(dish)
    head.add(mesh(cyl(0.05, 0.05, 1.7, 6), mats.steel, 0.9, 0, 0).rotateZ(Math.PI / 2))
    head.add(mesh(new THREE.SphereGeometry(0.14, 8, 8), mats.red, 1.8, 0, 0))
    head.add(mesh(box(0.9, 0.7, 0.8), mats.steel, -0.2, -0.1, 0))
    g.add(head)
    g.add(mesh(new THREE.SphereGeometry(0.1, 8, 8), mats.beacon, 0, 5.9, 0))
    spin = head
    // generator & fence posts
    g.add(mesh(box(1.1, 0.7, 0.8), mats.olive, 2.6, 0.5, 1.8))
    for (let i = 0; i < 16; i++) {
      const a = (i / 16) * Math.PI * 2
      g.add(mesh(cyl(0.035, 0.035, 0.55, 5), mats.steel, Math.cos(a) * 3.4, 0.4, Math.sin(a) * 3.4))
    }
  }

  if (key === 'sam') {
    radius = 4.2
    g.add(mesh(cyl(4.1, 4.2, 0.14, 28), mats.concrete, 0, 0.07, 0))
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2 + Math.PI / 4
      const l = new THREE.Group()
      l.position.set(Math.cos(a) * 2.3, 0.14, Math.sin(a) * 2.3)
      l.rotation.y = -a + Math.PI / 2
      l.add(mesh(box(1.1, 0.4, 1.9), mats.darkOlive, 0, 0.35, 0))
      const rack = new THREE.Group()
      rack.position.set(0, 0.8, -0.2)
      rack.rotation.x = -0.95
      rack.add(mesh(box(0.9, 0.2, 2.9), mats.olive, 0, 0, 0.5))
      for (const sx of [-0.22, 0.22]) {
        rack.add(mesh(cyl(0.15, 0.15, 2.9, 10), mats.steel, sx, 0.2, 0.5).rotateX(Math.PI / 2))
        const tip = mesh(new THREE.ConeGeometry(0.15, 0.5, 10), mats.white, sx, 0.2, 2.2)
        tip.rotation.x = Math.PI / 2
        rack.add(tip)
      }
      l.add(rack)
      g.add(l)
    }
    const cmd = makeTruck(mats, mats.olive, 1.2)
    cmd.position.set(0, 0.14, 0)
    cmd.rotation.y = 0.4
    g.add(cmd)
    const spinG = new THREE.Group()
    spinG.position.set(0, 1.9, 0)
    const dish = mesh(new THREE.SphereGeometry(0.6, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2.5), mats.white, 0, 0, 0)
    dish.rotation.x = Math.PI / 2.2
    spinG.add(dish)
    cmd.add(spinG)
    spin = spinG
    g.add(mesh(new THREE.SphereGeometry(0.08, 8, 8), mats.beacon, 0, 2.2, 0))
  }

  if (key === 'airbase') {
    radius = 9.5
    const rw = new THREE.Mesh(box(17, 0.07, 2.4), mats.runway)
    rw.position.set(0, 0.04, 0)
    rw.receiveShadow = true
    g.add(rw)
    g.add(mesh(box(13, 0.06, 0.7), mats.asphalt, -0.5, 0.035, 3.0))
    g.add(mesh(box(9, 0.07, 3.6), mats.concrete, 1.5, 0.04, 5.0))
    // hangars
    for (let i = 0; i < 2; i++) {
      // half-barrel hangar: arch in the XY plane, running along Z
      const grp = new THREE.Group()
      const barrel = new THREE.Mesh(
        new THREE.CylinderGeometry(1.4, 1.4, 3.0, 14, 1, false, Math.PI / 2, Math.PI),
        mats.steel,
      )
      barrel.rotation.set(Math.PI / 2, 0, 0)
      barrel.scale.set(1, 1, 0.8)
      barrel.castShadow = true
      barrel.receiveShadow = true
      grp.add(barrel)
      grp.add(mesh(box(2.8, 0.9, 0.12), mats.darkOlive, 0, 0.45, -1.5))
      grp.position.set(-2.4 + i * 3.4, 0.07, 7.9)
      grp.rotation.y = Math.PI
      g.add(grp)
    }
    // tower
    g.add(mesh(box(0.9, 2.2, 0.9), mats.concrete, 6.2, 1.1, 3.4))
    g.add(mesh(box(1.4, 0.55, 1.4), mats.glass, 6.2, 2.45, 3.4))
    g.add(mesh(box(1.6, 0.1, 1.6), mats.concrete, 6.2, 2.78, 3.4))
    g.add(mesh(cyl(0.03, 0.03, 0.8, 5), mats.steel, 6.2, 3.2, 3.4))
    g.add(mesh(new THREE.SphereGeometry(0.07, 8, 8), mats.beacon, 6.2, 3.62, 3.4))
    // aircraft on the apron
    const jets: [number, number, number][] = [
      [-0.4, 5.1, 0.4],
      [1.5, 5.4, -0.2],
      [3.6, 5.0, 0.15],
      [5.4, 5.5, -0.35],
    ]
    jets.forEach(([x, z, r], i) => {
      const j = makeJet(mats, i % 2 ? '#7d858d' : '#939aa1')
      j.position.set(x, 0.1, z)
      j.rotation.y = r
      g.add(j)
    })
    // a jet lined up on the runway
    const rj = makeJet(mats, '#8d949b')
    rj.position.set(-5.5, 0.1, 0.0)
    g.add(rj)
    // fuel tanks
    for (let i = 0; i < 3; i++) g.add(mesh(cyl(0.55, 0.55, 1.5, 14), mats.white, -7.2, 0.8, 4.6 + i * 1.3).rotateX(Math.PI / 2))
  }

  if (key === 'armor') {
    radius = 4.6
    g.add(mesh(cyl(4.5, 4.6, 0.06, 26), mats.sand, 0, 0.03, 0))
    for (let r = 0; r < 2; r++) {
      for (let c = 0; c < 3; c++) {
        if (r === 1 && c === 2) continue
        const t = makeTank(mats, 1.05)
        t.position.set(-2.4 + c * 2.4 + (r ? 1.1 : 0), 0.05, -1.6 + r * 2.1)
        t.rotation.y = (Math.sin(r * 4 + c * 2) * 0.12)
        g.add(t)
      }
    }
    const tr = makeTruck(mats, mats.olive, 1.1)
    tr.position.set(-2.2, 0.05, 3.1)
    tr.rotation.y = 0.1
    g.add(tr)
    const tr2 = makeTruck(mats, mats.darkOlive, 1.1)
    tr2.position.set(0.5, 0.05, 3.3)
    tr2.rotation.y = -0.08
    g.add(tr2)
    // camouflage net
    const net = mesh(box(3.2, 0.06, 2.0), mats.darkOlive, 3.0, 1.1, 3.0)
    net.rotation.z = 0.06
    g.add(net)
    for (const [x, z] of [[1.5, 2.1], [4.5, 2.1], [1.5, 3.9], [4.5, 3.9]]) g.add(mesh(cyl(0.04, 0.04, 1.1, 5), mats.steel, x, 0.55, z))
  }

  if (key === 'artillery') {
    radius = 4.8
    g.add(mesh(cyl(4.6, 4.7, 0.06, 26), mats.sand, 0, 0.03, 0))
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2 + 0.4
      const h = makeHowitzer(mats)
      h.position.set(Math.cos(a) * 2.3, 0.05, Math.sin(a) * 2.3)
      h.rotation.y = -a + Math.PI / 2 + 0.2
      g.add(h)
      // sandbag berm
      for (let k = 0; k < 7; k++) {
        const b = -0.9 + k * 0.3
        const ang = a + 0.0
        const bx = Math.cos(ang) * 3.5 + Math.cos(ang + Math.PI / 2) * b * 1.2
        const bz = Math.sin(ang) * 3.5 + Math.sin(ang + Math.PI / 2) * b * 1.2
        const bag = mesh(box(0.5, 0.32, 0.4), mats.sand, bx, 0.2, bz)
        bag.rotation.y = -ang
        g.add(bag)
      }
    }
    const am = makeTruck(mats, mats.olive, 1.0)
    am.position.set(0, 0.05, 0)
    g.add(am)
  }

  if (key === 'silo') {
    radius = 3.8
    g.add(mesh(cyl(3.6, 3.7, 0.18, 28), mats.concrete, 0, 0.09, 0))
    g.add(mesh(cyl(1.5, 1.5, 0.22, 28), mats.metal, 0, 0.17, 0))
    // open blast doors
    const d1 = mesh(box(1.6, 0.14, 1.7), mats.steel, -1.25, 0.9, 0)
    d1.rotation.z = 0.95
    const d2 = mesh(box(1.6, 0.14, 1.7), mats.steel, 1.25, 0.9, 0)
    d2.rotation.z = -0.95
    g.add(d1, d2)
    const missile = new THREE.Group()
    missile.add(mesh(cyl(0.33, 0.33, 3.6, 14), mats.white, 0, 2.1, 0))
    missile.add(mesh(cyl(0.34, 0.34, 0.5, 14), mats.red, 0, 2.7, 0))
    missile.add(mesh(new THREE.ConeGeometry(0.33, 1.1, 14), mats.white, 0, 4.45, 0))
    for (let i = 0; i < 4; i++) {
      const f = mesh(box(0.7, 0.9, 0.05), mats.steel, 0, 0.55, 0)
      f.rotation.y = (i * Math.PI) / 2
      f.position.set(Math.cos((i * Math.PI) / 2) * 0.4, 0.55, Math.sin((i * Math.PI) / 2) * 0.4)
      missile.add(f)
    }
    g.add(missile)
    // control bunker
    const mound = mesh(new THREE.SphereGeometry(1.5, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), mats.grass, 3.3, 0.1, 2.2)
    mound.scale.set(1.2, 0.7, 1)
    g.add(mound)
    g.add(mesh(box(1.1, 0.55, 0.15), mats.concrete, 3.3, 0.42, 1.25))
    g.add(mesh(new THREE.SphereGeometry(0.09, 8, 8), mats.beacon, -3.0, 0.9, -2.6))
    g.add(mesh(cyl(0.05, 0.05, 0.9, 5), mats.steel, -3.0, 0.45, -2.6))
    // security fence
    for (let i = 0; i < 20; i++) {
      const a = (i / 20) * Math.PI * 2
      g.add(mesh(cyl(0.03, 0.03, 0.65, 5), mats.steel, Math.cos(a) * 3.7, 0.45, Math.sin(a) * 3.7))
    }
  }

  g.traverse((o) => {
    if ((o as THREE.Mesh).isMesh) {
      o.castShadow = true
      o.receiveShadow = true
    }
  })
  return { group: g, spin, radius }
}

/* ------------------------------------------------------------------ */
/* city landmarks                                                      */
/* ------------------------------------------------------------------ */
export function buildLandmark(kind: 'capital' | 'province' | 'city', mats: ModelMats): THREE.Group {
  const g = new THREE.Group()
  if (kind === 'capital') {
    // broadcast tower
    g.add(mesh(cyl(0.9, 1.4, 1.2, 16), mats.concrete, 0, 0.6, 0))
    g.add(mesh(cyl(0.34, 0.6, 11, 14), mats.concrete, 0, 6.6, 0))
    const pod = mesh(new THREE.SphereGeometry(1.25, 18, 12), mats.steel, 0, 11.2, 0)
    pod.scale.set(1, 0.55, 1)
    g.add(pod)
    g.add(mesh(cyl(1.3, 1.3, 0.24, 18), mats.glass, 0, 11.2, 0))
    g.add(mesh(cyl(0.05, 0.16, 5, 8), mats.steel, 0, 14.0, 0))
    g.add(mesh(new THREE.SphereGeometry(0.16, 8, 8), mats.beacon, 0, 16.6, 0))
    // parliament dome
    const dome = new THREE.Group()
    dome.position.set(6.2, 0, 2.2)
    dome.add(mesh(box(5.2, 1.2, 3.2), mats.concrete, 0, 0.6, 0))
    dome.add(mesh(cyl(1.2, 1.3, 0.9, 20), mats.concrete, 0, 1.65, 0))
    dome.add(mesh(new THREE.SphereGeometry(1.2, 22, 12, 0, Math.PI * 2, 0, Math.PI / 2), mats.gold, 0, 2.1, 0))
    for (let i = 0; i < 8; i++) dome.add(mesh(cyl(0.1, 0.1, 1.2, 6), mats.white, -2.1 + i * 0.6, 0.6, 1.7))
    g.add(dome)
    // skyscraper cluster accent
    g.add(mesh(box(1.5, 8.5, 1.5), mats.glass, -5.5, 4.25, -1.8))
    g.add(mesh(box(1.4, 6.0, 1.4), mats.glass, -7.2, 3.0, 0.6))
  } else if (kind === 'province') {
    const dome = new THREE.Group()
    dome.add(mesh(box(3.2, 0.9, 2.4), mats.concrete, 0, 0.45, 0))
    dome.add(mesh(cyl(0.9, 1.0, 0.6, 18), mats.concrete, 0, 1.2, 0))
    dome.add(mesh(new THREE.SphereGeometry(0.9, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), mats.gold, 0, 1.5, 0))
    dome.position.set(3.8, 0, 1.6)
    g.add(dome)
    g.add(mesh(cyl(0.3, 0.45, 5, 10), mats.concrete, -4.6, 2.5, -2.6))
    g.add(mesh(cyl(0.32, 0.32, 0.5, 10), mats.red, -4.6, 4.7, -2.6))
    g.add(mesh(new THREE.SphereGeometry(0.1, 8, 8), mats.beacon, -4.6, 5.2, -2.6))
  } else {
    g.add(mesh(cyl(0.9, 0.9, 1.2, 14), mats.steel, -3.8, 3.4, 2.4))
    g.add(mesh(new THREE.ConeGeometry(0.95, 0.5, 14), mats.steel, -3.8, 4.25, 2.4))
    for (const [x, z] of [[-0.5, -0.5], [0.5, -0.5], [-0.5, 0.5], [0.5, 0.5]]) g.add(mesh(cyl(0.05, 0.05, 2.8, 5), mats.steel, -3.8 + x, 1.4, 2.4 + z))
    g.add(mesh(cyl(0.22, 0.28, 3.0, 8), mats.concrete, 4.2, 1.5, -2.4))
  }
  return g
}

/* ------------------------------------------------------------------ */
/* ships                                                               */
/* ------------------------------------------------------------------ */
export function buildShip(type: 'cargo' | 'frigate', seed: number): THREE.Group {
  const g = new THREE.Group()
  const hullMat = new THREE.MeshStandardMaterial({ color: type === 'cargo' ? '#2b3a4a' : '#7d858b', roughness: 0.6, metalness: 0.3 })
  const shape = new THREE.Shape()
  const L = type === 'cargo' ? 4.2 : 3.4
  const W = type === 'cargo' ? 0.75 : 0.5
  shape.moveTo(L, 0)
  shape.quadraticCurveTo(L * 0.75, W, L * 0.35, W)
  shape.lineTo(-L * 0.92, W)
  shape.lineTo(-L, W * 0.7)
  shape.lineTo(-L, -W * 0.7)
  shape.lineTo(-L * 0.92, -W)
  shape.lineTo(L * 0.35, -W)
  shape.quadraticCurveTo(L * 0.75, -W, L, 0)
  const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.55, bevelEnabled: false })
  geo.rotateX(-Math.PI / 2)
  const hull = mesh(geo, hullMat, 0, -0.2, 0)
  g.add(hull)
  const rnd = (n: number) => Math.abs(Math.sin(seed * 91.7 + n * 17.3))
  if (type === 'cargo') {
    g.add(mesh(box(0.9, 0.9, 1.1), mats_white(), -L * 0.7, 0.8, 0))
    g.add(mesh(box(0.55, 0.25, 0.5), mats_white(), -L * 0.7, 1.4, 0))
    g.add(mesh(cyl(0.12, 0.14, 0.5, 8), new THREE.MeshStandardMaterial({ color: '#b3322a' }), -L * 0.82, 1.3, 0))
    const colors = ['#b5472f', '#2f6aa0', '#d1a43b', '#4e8a5a', '#8e8e8e', '#a33b52']
    for (let i = 0; i < 6; i++) {
      for (let j = 0; j < 2; j++) {
        const h = 1 + Math.floor(rnd(i * 2 + j) * 3)
        for (let k = 0; k < h; k++) {
          const c = new THREE.MeshStandardMaterial({ color: colors[Math.floor(rnd(i + j * 7 + k * 3) * colors.length)], roughness: 0.7 })
          g.add(mesh(box(0.8, 0.28, 0.5), c, -L * 0.3 + i * 0.95 - 0.5, 0.48 + k * 0.29, (j - 0.5) * 0.56))
        }
      }
    }
  } else {
    g.add(mesh(box(1.5, 0.55, 0.55), hullMat, -0.3, 0.6, 0))
    g.add(mesh(box(0.7, 0.45, 0.42), hullMat, -0.2, 1.1, 0))
    g.add(mesh(cyl(0.03, 0.04, 1.1, 6), hullMat, -0.2, 1.7, 0))
    g.add(mesh(cyl(0.14, 0.18, 0.4, 8), hullMat, -1.1, 0.95, 0))
    const gun = mesh(cyl(0.04, 0.05, 0.8, 6), hullMat, L * 0.55 + 0.4, 0.78, 0)
    gun.rotation.z = Math.PI / 2
    g.add(gun)
    g.add(mesh(new THREE.SphereGeometry(0.17, 8, 8), hullMat, L * 0.55, 0.62, 0))
    const dish = mesh(new THREE.SphereGeometry(0.22, 8, 6, 0, Math.PI * 2, 0, Math.PI / 2), hullMat, -0.2, 1.95, 0)
    g.add(dish)
  }
  // wake
  const wake = new THREE.Mesh(
    new THREE.PlaneGeometry(L * 2.6, 0.5 + W * 2.2),
    new THREE.MeshBasicMaterial({ map: wakeTexture(), transparent: true, depthWrite: false, opacity: 0.8 }),
  )
  wake.rotation.x = -Math.PI / 2
  wake.position.set(-L * 1.7, 0.06, 0)
  wake.renderOrder = 3
  g.add(wake)
  return g
}

let _white: THREE.MeshStandardMaterial | null = null
function mats_white() {
  if (!_white) _white = new THREE.MeshStandardMaterial({ color: '#e5e7ea', roughness: 0.6 })
  return _white
}

let _wake: THREE.CanvasTexture | null = null
function wakeTexture() {
  if (_wake) return _wake
  const cv = document.createElement('canvas')
  cv.width = 256
  cv.height = 64
  const g = cv.getContext('2d')!
  const grd = g.createLinearGradient(256, 0, 0, 0)
  grd.addColorStop(0, 'rgba(255,255,255,0.85)')
  grd.addColorStop(0.35, 'rgba(255,255,255,0.35)')
  grd.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = grd
  g.beginPath()
  g.moveTo(256, 32)
  g.lineTo(0, 0)
  g.lineTo(0, 64)
  g.closePath()
  g.fill()
  _wake = new THREE.CanvasTexture(cv)
  _wake.colorSpace = THREE.SRGBColorSpace
  return _wake
}
