import { Noise2D, mulberry32, clamp, smoothstep, mix } from './noise'
import { CITY_NAMES, PROVINCE_NAMES, type BiomePreset, type Division, type DivisionKind } from './data'

export const SIZE = 300
export const N = 301
export const CELL = SIZE / (N - 1)
export const H_MIN = -16
export const H_MAX = 48

export interface TerrainResult {
  heights: Float32Array
  slope: Float32Array
  moist: Float32Array
  water: Float32Array
  forest: Float32Array
  scrub: Float32Array
  divisions: Division[]
}

/* ------------------------------------------------------------------ */
/* small binary min-heap (key = priority)                              */
/* ------------------------------------------------------------------ */
class MinHeap {
  keys: Float64Array
  vals: Int32Array
  size = 0
  constructor(cap: number) {
    this.keys = new Float64Array(cap)
    this.vals = new Int32Array(cap)
  }
  push(k: number, v: number) {
    let i = this.size++
    while (i > 0) {
      const p = (i - 1) >> 1
      if (this.keys[p] <= k) break
      this.keys[i] = this.keys[p]
      this.vals[i] = this.vals[p]
      i = p
    }
    this.keys[i] = k
    this.vals[i] = v
  }
  popVal(): number {
    const top = this.vals[0]
    this.size--
    if (this.size > 0) {
      const k = this.keys[this.size]
      const v = this.vals[this.size]
      let i = 0
      for (;;) {
        let c = i * 2 + 1
        if (c >= this.size) break
        if (c + 1 < this.size && this.keys[c + 1] < this.keys[c]) c++
        if (this.keys[c] >= k) break
        this.keys[i] = this.keys[c]
        this.vals[i] = this.vals[c]
        i = c
      }
      this.keys[i] = k
      this.vals[i] = v
    }
    return top
  }
}

/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */
export const worldToGrid = (v: number) => (v / SIZE + 0.5) * (N - 1)
export const gridToWorld = (g: number) => (g / (N - 1) - 0.5) * SIZE

export function sampleHeight(h: Float32Array, x: number, z: number): number {
  const gx = clamp(worldToGrid(x), 0, N - 1.001)
  const gz = clamp(worldToGrid(z), 0, N - 1.001)
  const i = Math.floor(gx)
  const j = Math.floor(gz)
  const fx = gx - i
  const fz = gz - j
  const k = j * N + i
  return (
    h[k] * (1 - fx) * (1 - fz) + h[k + 1] * fx * (1 - fz) + h[k + N] * (1 - fx) * fz + h[k + N + 1] * fx * fz
  )
}

export function computeSlope(h: Float32Array): Float32Array {
  const s = new Float32Array(N * N)
  for (let j = 1; j < N - 1; j++) {
    for (let i = 1; i < N - 1; i++) {
      const k = j * N + i
      const dx = (h[k + 1] - h[k - 1]) / (2 * CELL)
      const dz = (h[k + N] - h[k - N]) / (2 * CELL)
      s[k] = Math.hypot(dx, dz)
    }
  }
  return s
}

function boxBlur(src: Float32Array, radius: number, passes = 1): Float32Array {
  let a = src
  let b = new Float32Array(src.length)
  for (let p = 0; p < passes; p++) {
    // horizontal
    for (let j = 0; j < N; j++) {
      let sum = 0
      const row = j * N
      for (let i = -radius; i <= radius; i++) sum += a[row + clamp(i, 0, N - 1)]
      for (let i = 0; i < N; i++) {
        b[row + i] = sum / (radius * 2 + 1)
        sum += a[row + clamp(i + radius + 1, 0, N - 1)] - a[row + clamp(i - radius, 0, N - 1)]
      }
    }
    // vertical
    const c = new Float32Array(src.length)
    for (let i = 0; i < N; i++) {
      let sum = 0
      for (let j = -radius; j <= radius; j++) sum += b[clamp(j, 0, N - 1) * N + i]
      for (let j = 0; j < N; j++) {
        c[j * N + i] = sum / (radius * 2 + 1)
        sum += b[clamp(j + radius + 1, 0, N - 1) * N + i] - b[clamp(j - radius, 0, N - 1) * N + i]
      }
    }
    a = c
    b = new Float32Array(src.length)
  }
  return a
}

/* ------------------------------------------------------------------ */
/* base landform                                                       */
/* ------------------------------------------------------------------ */
function baseHeights(n: Noise2D, preset: BiomePreset): Float32Array {
  const h = new Float32Array(N * N)
  const t = 0.68 - preset.mountainCover * 0.3
  for (let j = 0; j < N; j++) {
    const nz = (j / (N - 1)) * 2 - 1
    for (let i = 0; i < N; i++) {
      const nx = (i / (N - 1)) * 2 - 1
      const wx = nx + 0.24 * n.fbm(nx * 1.4 + 3.1, nz * 1.4 - 1.7, 3)
      const wz = nz + 0.24 * n.fbm(nx * 1.4 - 5.2, nz * 1.4 + 2.3, 3)
      const r = Math.hypot(wx * 0.95, wz * 1.08)
      const c = 0.92 - r * 1.3 + 0.32 * n.fbm(nx * 2.3 + 9, nz * 2.3 + 4, 4)

      let e: number
      if (c > 0) {
        const cn = smoothstep(0, 0.4, c)
        const beach = Math.pow(smoothstep(0, 0.05, c), 0.7) * 1.7
        const plains = (n.fbm(nx * 3 + 20, nz * 3 + 5, 5) * 0.5 + 0.5) * 6 * preset.plainAmp
        const hills = n.fbm(nx * 7.5, nz * 7.5, 4) * 2.4
        const mm = n.fbm(nx * 1.25 + 40 + wx * 0.4, nz * 1.25 - 12 + wz * 0.4, 3) * 0.5 + 0.5
        const mMask = smoothstep(t, t + 0.17, mm)
        const ridge = n.ridged(nx * 2.2 + 7, nz * 2.2 + 13, 6)
        const mountain = mMask * (3 + 36 * Math.pow(ridge, 1.45)) * preset.mountainAmp * cn
        const micro = n.fbm(nx * 30, nz * 30, 3) * 0.3 * cn
        e = beach + (plains + hills) * cn + mountain + micro
      } else {
        const shelf = -13 * smoothstep(0, -0.55, c)
        e = shelf + n.fbm(nx * 12, nz * 12, 3) * 0.35 * smoothstep(0, -0.2, c)
      }
      const edge = Math.max(Math.abs(nx), Math.abs(nz))
      e -= 26 * smoothstep(0.86, 1.0, edge)
      h[j * N + i] = e
    }
  }
  return h
}

/* ------------------------------------------------------------------ */
/* hydraulic erosion (particle based)                                  */
/* ------------------------------------------------------------------ */
function erode(h: Float32Array, rnd: () => number, droplets: number) {
  const radius = 2
  const brush: { o: number; dx: number; dy: number; w: number }[] = []
  let wsum = 0
  for (let dy = -radius; dy <= radius; dy++) {
    for (let dx = -radius; dx <= radius; dx++) {
      const d = Math.hypot(dx, dy)
      if (d < radius + 0.01) {
        const w = Math.max(0, 1 - d / (radius + 0.5))
        brush.push({ o: dy * N + dx, dx, dy, w })
        wsum += w
      }
    }
  }
  brush.forEach((b) => (b.w /= wsum))

  const inertia = 0.06
  const capFactor = 5
  const minSlope = 0.012
  const erodeSpeed = 0.28
  const depositSpeed = 0.3
  const evap = 0.012
  const gravity = 4.5
  const maxLife = 38

  for (let d = 0; d < droplets; d++) {
    let px = 3 + rnd() * (N - 7)
    let py = 3 + rnd() * (N - 7)
    if (h[Math.floor(py) * N + Math.floor(px)] < 1.2) continue
    let dirX = 0
    let dirY = 0
    let speed = 1
    let water = 1
    let sediment = 0
    for (let life = 0; life < maxLife; life++) {
      const nodeX = Math.floor(px)
      const nodeY = Math.floor(py)
      const idx = nodeY * N + nodeX
      const ox = px - nodeX
      const oy = py - nodeY
      const h00 = h[idx]
      const h10 = h[idx + 1]
      const h01 = h[idx + N]
      const h11 = h[idx + N + 1]
      const gradX = (h10 - h00) * (1 - oy) + (h11 - h01) * oy
      const gradY = (h01 - h00) * (1 - ox) + (h11 - h10) * ox
      const height = h00 * (1 - ox) * (1 - oy) + h10 * ox * (1 - oy) + h01 * (1 - ox) * oy + h11 * ox * oy

      dirX = dirX * inertia - gradX * (1 - inertia)
      dirY = dirY * inertia - gradY * (1 - inertia)
      const len = Math.hypot(dirX, dirY)
      if (len > 1e-9) {
        dirX /= len
        dirY /= len
      }
      px += dirX
      py += dirY
      if ((dirX === 0 && dirY === 0) || px < 3 || px >= N - 4 || py < 3 || py >= N - 4) break

      const ni = Math.floor(py) * N + Math.floor(px)
      const nox = px - Math.floor(px)
      const noy = py - Math.floor(py)
      const newHeight =
        h[ni] * (1 - nox) * (1 - noy) + h[ni + 1] * nox * (1 - noy) + h[ni + N] * (1 - nox) * noy + h[ni + N + 1] * nox * noy
      const deltaH = newHeight - height
      if (newHeight < 0.25) break

      const capacity = Math.max(-deltaH, minSlope) * speed * water * capFactor
      if (sediment > capacity || deltaH > 0) {
        const amount = deltaH > 0 ? Math.min(deltaH, sediment) : (sediment - capacity) * depositSpeed
        sediment -= amount
        h[idx] += amount * (1 - ox) * (1 - oy)
        h[idx + 1] += amount * ox * (1 - oy)
        h[idx + N] += amount * (1 - ox) * oy
        h[idx + N + 1] += amount * ox * oy
      } else {
        const amount = Math.min((capacity - sediment) * erodeSpeed, -deltaH)
        for (let b = 0; b < brush.length; b++) {
          const br = brush[b]
          const cx = nodeX + br.dx
          const cy = nodeY + br.dy
          if (cx < 0 || cy < 0 || cx >= N || cy >= N) continue
          const ci = idx + br.o
          const take = Math.min(h[ci], amount * br.w)
          h[ci] -= take
          sediment += take
        }
      }
      speed = Math.sqrt(Math.max(0, speed * speed + deltaH * gravity))
      water *= 1 - evap
    }
  }
}

/* ------------------------------------------------------------------ */
/* city sites                                                          */
/* ------------------------------------------------------------------ */
const SITE_PAD: Record<DivisionKind, number> = { capital: 19, province: 14, city: 10.5 }

export function findSite(
  h: Float32Array,
  existing: Division[],
  rnd: () => number,
  kind: DivisionKind,
  minDist: number,
): { x: number; z: number } | null {
  let best: { x: number; z: number; s: number } | null = null
  const R = SITE_PAD[kind]
  for (let t = 0; t < 2600; t++) {
    const x = (rnd() - 0.5) * SIZE * 0.86
    const z = (rnd() - 0.5) * SIZE * 0.86
    const e = sampleHeight(h, x, z)
    if (e < 1.7 || e > 9.5) continue
    let tooClose = false
    for (const d of existing) {
      if (Math.hypot(d.x - x, d.z - z) < minDist) {
        tooClose = true
        break
      }
    }
    if (tooClose) continue
    // local relief within pad radius
    let mn = e
    let mx = e
    for (let k = 0; k < 10; k++) {
      const a = (k / 10) * Math.PI * 2
      const hh = sampleHeight(h, x + Math.cos(a) * R * 0.8, z + Math.sin(a) * R * 0.8)
      if (hh < mn) mn = hh
      if (hh > mx) mx = hh
    }
    if (mn < 0.9) continue // no pad in the sea
    const relief = mx - mn
    if (relief > 4.2) continue
    // coastal bonus: look for open sea within ~26 units
    let coastal = 0
    for (let k = 0; k < 12; k++) {
      const a = (k / 12) * Math.PI * 2 + 0.3
      if (sampleHeight(h, x + Math.cos(a) * 26, z + Math.sin(a) * 26) < -0.5) coastal = 0.32
    }
    let s = 1 - (relief / 4.2) * 0.7 + coastal + rnd() * 0.3
    if (kind === 'capital') s -= Math.hypot(x, z) / 140
    if (!best || s > best.s) best = { x, z, s }
  }
  return best ? { x: best.x, z: best.z } : null
}

export function flattenRegion(h: Float32Array, x: number, z: number, r: number, target?: number): number {
  let tgt = target
  if (tgt === undefined) {
    let sum = 0
    let cnt = 0
    for (let a = 0; a < 16; a++) {
      const ang = (a / 16) * Math.PI * 2
      for (const rr of [0, r * 0.3, r * 0.6]) {
        sum += sampleHeight(h, x + Math.cos(ang) * rr, z + Math.sin(ang) * rr)
        cnt++
      }
    }
    tgt = Math.max(1.5, sum / cnt)
  }
  const outer = r * 1.75
  const g0x = Math.max(0, Math.floor(worldToGrid(x - outer)))
  const g1x = Math.min(N - 1, Math.ceil(worldToGrid(x + outer)))
  const g0z = Math.max(0, Math.floor(worldToGrid(z - outer)))
  const g1z = Math.min(N - 1, Math.ceil(worldToGrid(z + outer)))
  for (let j = g0z; j <= g1z; j++) {
    for (let i = g0x; i <= g1x; i++) {
      const wx = gridToWorld(i)
      const wz = gridToWorld(j)
      const d = Math.hypot(wx - x, wz - z)
      if (d > outer) continue
      const w = 1 - smoothstep(r * 0.72, outer, d)
      const k = j * N + i
      h[k] = mix(h[k], tgt, w)
    }
  }
  return tgt
}

export const padRadius = (kind: DivisionKind) => SITE_PAD[kind]

function populationFor(kind: DivisionKind, rnd: () => number) {
  if (kind === 'capital') return Math.round(3_600_000 + rnd() * 1_400_000)
  if (kind === 'province') return Math.round(900_000 + rnd() * 1_500_000)
  return Math.round(180_000 + rnd() * 600_000)
}

/* ------------------------------------------------------------------ */
/* main entry                                                          */
/* ------------------------------------------------------------------ */
export function generateTerrain(seed: number, preset: BiomePreset, capitalName: string): TerrainResult {
  const n = new Noise2D(seed)
  const rnd = mulberry32(seed * 7 + 13)

  const h = baseHeights(n, preset)
  erode(h, rnd, 120000)

  // gentle smoothing of the eroded land (removes single-cell spikes)
  const sm = boxBlur(h, 1, 1)
  for (let k = 0; k < h.length; k++) h[k] = h[k] > 0.2 ? mix(h[k], sm[k], 0.55) : h[k]

  // --- settlements ---------------------------------------------------
  const divisions: Division[] = []
  const wanted: { kind: DivisionKind; name: string; min: number }[] = [
    { kind: 'capital', name: capitalName, min: 0 },
    ...PROVINCE_NAMES.slice(0, 4).map((name) => ({ kind: 'province' as DivisionKind, name, min: 62 })),
    ...CITY_NAMES.slice(0, 3).map((name) => ({ kind: 'city' as DivisionKind, name, min: 42 })),
  ]
  wanted.forEach((w, idx) => {
    const site = findSite(h, divisions, rnd, w.kind, w.min) ?? findSite(h, divisions, rnd, w.kind, w.min * 0.5)
    if (!site) return
    divisions.push({
      id: `d${idx}`,
      name: w.name,
      kind: w.kind,
      x: site.x,
      z: site.z,
      radius: SITE_PAD[w.kind],
      population: populationFor(w.kind, rnd),
    })
    flattenRegion(h, site.x, site.z, SITE_PAD[w.kind])
  })

  // --- hydrology: priority-flood fill + flow accumulation ------------
  const total = N * N
  const filled = new Float32Array(h)
  const visited = new Uint8Array(total)
  const heap = new MinHeap(total + 8)
  for (let k = 0; k < total; k++) {
    const i = k % N
    const j = (k / N) | 0
    if (h[k] <= 0.1 || i === 0 || j === 0 || i === N - 1 || j === N - 1) {
      visited[k] = 1
      heap.push(h[k], k)
    }
  }
  const dx8 = [1, -1, 0, 0, 1, 1, -1, -1]
  const dz8 = [0, 0, 1, -1, 1, -1, 1, -1]
  while (heap.size > 0) {
    const k = heap.popVal()
    const i = k % N
    const j = (k / N) | 0
    for (let d = 0; d < 8; d++) {
      const ni = i + dx8[d]
      const nj = j + dz8[d]
      if (ni < 0 || nj < 0 || ni >= N || nj >= N) continue
      const nk = nj * N + ni
      if (visited[nk]) continue
      visited[nk] = 1
      filled[nk] = Math.max(h[nk], filled[k] + 0.0006)
      heap.push(filled[nk], nk)
    }
  }

  const recv = new Int32Array(total).fill(-1)
  for (let k = 0; k < total; k++) {
    if (h[k] <= 0.1) continue
    const i = k % N
    const j = (k / N) | 0
    let bestDrop = 0
    let bestK = -1
    for (let d = 0; d < 8; d++) {
      const ni = i + dx8[d]
      const nj = j + dz8[d]
      if (ni < 0 || nj < 0 || ni >= N || nj >= N) continue
      const nk = nj * N + ni
      const drop = (filled[k] - filled[nk]) / (d < 4 ? 1 : 1.4142)
      if (drop > bestDrop) {
        bestDrop = drop
        bestK = nk
      }
    }
    recv[k] = bestK
  }
  const order = new Uint32Array(total)
  for (let k = 0; k < total; k++) order[k] = k
  order.sort((a, b) => filled[b] - filled[a])
  const acc = new Float32Array(total).fill(1)
  for (let q = 0; q < total; q++) {
    const k = order[q]
    if (h[k] <= 0.1) continue
    const r = recv[k]
    if (r >= 0) acc[r] += acc[k]
  }

  const water = new Float32Array(total)
  // lakes: filled depressions
  for (let k = 0; k < total; k++) {
    if (h[k] <= 0.3) continue
    const depth = filled[k] - h[k]
    if (depth > 0.45) {
      water[k] = Math.max(water[k], smoothstep(0.4, 0.9, depth))
    }
  }
  for (let k = 0; k < total; k++) {
    if (water[k] > 0.5) h[k] = filled[k] - 0.38
  }
  // rivers: stamp soft discs, carve a channel
  const T = 260
  const carve = new Float32Array(total)
  for (let k = 0; k < total; k++) {
    if (h[k] <= 0.3 || acc[k] < T) continue
    const t = clamp(Math.log(acc[k] / T) / Math.log(70), 0, 1)
    const hw = 0.7 + 1.9 * t
    const cx = k % N
    const cz = (k / N) | 0
    const rr = Math.ceil(hw + 1)
    for (let dz = -rr; dz <= rr; dz++) {
      for (let dx = -rr; dx <= rr; dx++) {
        const x = cx + dx
        const z = cz + dz
        if (x < 0 || z < 0 || x >= N || z >= N) continue
        const d = Math.hypot(dx, dz)
        const w = 1 - smoothstep(hw * 0.55, hw + 0.9, d)
        if (w <= 0) continue
        const q = z * N + x
        if (w > water[q]) water[q] = w
        const cv = w * (0.45 + 1.1 * t)
        if (cv > carve[q]) carve[q] = cv
      }
    }
  }
  for (let k = 0; k < total; k++) if (carve[k] > 0 && h[k] > 0.3) h[k] = Math.max(0.28, h[k] - carve[k])
  const waterSoft = boxBlur(water, 1, 1)
  for (let k = 0; k < total; k++) water[k] = clamp(Math.max(water[k] * 0.9, waterSoft[k] * 1.5), 0, 1)

  // --- climate & vegetation ---------------------------------------------
  const slope = computeSlope(h)
  const wet = new Float32Array(total)
  for (let k = 0; k < total; k++) wet[k] = h[k] <= 0.05 || water[k] > 0.4 ? 1 : 0
  const near = boxBlur(wet, 9, 2)

  const moist = new Float32Array(total)
  const forest = new Float32Array(total)
  const scrub = new Float32Array(total)
  for (let j = 0; j < N; j++) {
    const nz = (j / (N - 1)) * 2 - 1
    for (let i = 0; i < N; i++) {
      const nx = (i / (N - 1)) * 2 - 1
      const k = j * N + i
      const e = h[k]
      const m = clamp(
        0.5 +
          0.42 * n.fbm(nx * 2.6 + 31, nz * 2.6 - 8, 4) +
          preset.moistureBias +
          near[k] * 0.6 -
          0.012 * Math.max(0, e - 12),
        0,
        1,
      )
      moist[k] = m
      const slopeTerm = 1 - smoothstep(0.5, 0.9, slope[k])
      const alt = 1 - smoothstep(preset.treeLine - 4, preset.treeLine, e)
      const low = smoothstep(1.3, 2.4, e)
      const patch = smoothstep(-0.28, 0.22, n.fbm(nx * 9 + 50, nz * 9 + 20, 3))
      const f = smoothstep(0.36, 0.62, m) * slopeTerm * alt * low * patch * preset.forest * (1 - clamp(water[k] * 2, 0, 1))
      forest[k] = f
      const sc =
        smoothstep(-0.1, 0.5, n.fbm(nx * 14 + 5, nz * 14 + 11, 3) + 0.2) *
        slopeTerm *
        low *
        (1 - alt * 0.0) *
        (1 - smoothstep(preset.treeLine, preset.treeLine + 5, e)) *
        preset.scrub *
        (1 - f) *
        (1 - clamp(water[k] * 2, 0, 1))
      scrub[k] = sc
    }
  }

  return { heights: h, slope, moist, water, forest, scrub, divisions }
}

/* ------------------------------------------------------------------ */
/* roads                                                               */
/* ------------------------------------------------------------------ */
export function buildRoads(h: Float32Array, divisions: Division[]): number[][] {
  const STEP = 3
  const M = Math.floor((N - 1) / STEP) + 1
  const cost = (a: number, b: number, d: number) => {
    const ha = h[a]
    const hb = h[b]
    if (ha < 0.45 || hb < 0.45) return Infinity
    const s = Math.abs(hb - ha) / (d * CELL)
    return d * CELL * (1 + 22 * s * s + 4 * s)
  }
  const nodeIdx = (i: number, j: number) => (j * STEP) * N + i * STEP

  const route = (a: Division, b: Division): number[] | null => {
    const sx = clamp(Math.round(worldToGrid(a.x) / STEP), 0, M - 1)
    const sz = clamp(Math.round(worldToGrid(a.z) / STEP), 0, M - 1)
    const tx = clamp(Math.round(worldToGrid(b.x) / STEP), 0, M - 1)
    const tz = clamp(Math.round(worldToGrid(b.z) / STEP), 0, M - 1)
    const dist = new Float32Array(M * M).fill(Infinity)
    const prev = new Int32Array(M * M).fill(-1)
    const heap = new MinHeap(M * M * 9 + 16)
    const s = sz * M + sx
    dist[s] = 0
    heap.push(0, s)
    while (heap.size > 0) {
      const u = heap.popVal()
      const ux = u % M
      const uz = (u / M) | 0
      if (ux === tx && uz === tz) break
      for (let d = 0; d < 8; d++) {
        const vx = ux + [1, -1, 0, 0, 1, 1, -1, -1][d]
        const vz = uz + [0, 0, 1, -1, 1, -1, 1, -1][d]
        if (vx < 0 || vz < 0 || vx >= M || vz >= M) continue
        const v = vz * M + vx
        const c = cost(nodeIdx(ux, uz), nodeIdx(vx, vz), d < 4 ? STEP : STEP * 1.4142)
        const nd = dist[u] + c
        if (nd < dist[v]) {
          dist[v] = nd
          prev[v] = u
          heap.push(nd, v)
        }
      }
    }
    const t = tz * M + tx
    if (!isFinite(dist[t])) return null
    const pts: number[][] = []
    for (let cur = t; cur !== -1; cur = prev[cur]) {
      const cx = cur % M
      const cz = (cur / M) | 0
      pts.push([gridToWorld(cx * STEP), gridToWorld(cz * STEP)])
    }
    pts.reverse()
    pts[0] = [a.x, a.z]
    pts[pts.length - 1] = [b.x, b.z]
    // Chaikin smoothing
    let line = pts
    for (let it = 0; it < 3; it++) {
      const out: number[][] = [line[0]]
      for (let i = 0; i < line.length - 1; i++) {
        const p = line[i]
        const q = line[i + 1]
        out.push([p[0] * 0.75 + q[0] * 0.25, p[1] * 0.75 + q[1] * 0.25])
        out.push([p[0] * 0.25 + q[0] * 0.75, p[1] * 0.25 + q[1] * 0.75])
      }
      out.push(line[line.length - 1])
      line = out
    }
    // resample ~1.1 units
    const res: number[] = [line[0][0], line[0][1]]
    let acc = 0
    for (let i = 1; i < line.length; i++) {
      const dx = line[i][0] - line[i - 1][0]
      const dz = line[i][1] - line[i - 1][1]
      acc += Math.hypot(dx, dz)
      if (acc >= 1.1) {
        res.push(line[i][0], line[i][1])
        acc = 0
      }
    }
    res.push(line[line.length - 1][0], line[line.length - 1][1])
    return res
  }

  // MST (Prim) + a few extra links between near neighbours
  const roads: number[][] = []
  const inTree = new Set<number>([0])
  const edges = new Set<string>()
  while (inTree.size < divisions.length) {
    let bi = -1
    let bj = -1
    let bd = Infinity
    inTree.forEach((i) => {
      for (let j = 0; j < divisions.length; j++) {
        if (inTree.has(j)) continue
        const d = Math.hypot(divisions[i].x - divisions[j].x, divisions[i].z - divisions[j].z)
        if (d < bd) {
          bd = d
          bi = i
          bj = j
        }
      }
    })
    if (bj < 0) break
    inTree.add(bj)
    edges.add(`${Math.min(bi, bj)}-${Math.max(bi, bj)}`)
  }
  for (let i = 0; i < divisions.length; i++) {
    let bj = -1
    let bd = Infinity
    for (let j = 0; j < divisions.length; j++) {
      if (i === j || edges.has(`${Math.min(i, j)}-${Math.max(i, j)}`)) continue
      const d = Math.hypot(divisions[i].x - divisions[j].x, divisions[i].z - divisions[j].z)
      if (d < bd) {
        bd = d
        bj = j
      }
    }
    if (bj >= 0 && bd < 95 && edges.size < divisions.length + 3) edges.add(`${Math.min(i, bj)}-${Math.max(i, bj)}`)
  }
  edges.forEach((e) => {
    const [a, b] = e.split('-').map(Number)
    const r = route(divisions[a], divisions[b])
    if (r) roads.push(r)
  })
  return roads
}

/* ------------------------------------------------------------------ */
/* contour (marching squares) → [x0,z0,x1,z1,...]                      */
/* ------------------------------------------------------------------ */
export function contour(h: Float32Array, level: number, step = 2): number[] {
  const out: number[] = []
  for (let j = 0; j < N - step; j += step) {
    for (let i = 0; i < N - step; i += step) {
      const a = h[j * N + i]
      const b = h[j * N + i + step]
      const c = h[(j + step) * N + i + step]
      const d = h[(j + step) * N + i]
      const idx = (a > level ? 1 : 0) | (b > level ? 2 : 0) | (c > level ? 4 : 0) | (d > level ? 8 : 0)
      if (idx === 0 || idx === 15) continue
      const x0 = gridToWorld(i)
      const x1 = gridToWorld(i + step)
      const z0 = gridToWorld(j)
      const z1 = gridToWorld(j + step)
      const t = (p: number, q: number) => (level - p) / (q - p)
      const top = () => [mix(x0, x1, t(a, b)), z0]
      const right = () => [x1, mix(z0, z1, t(b, c))]
      const bottom = () => [mix(x0, x1, t(d, c)), z1]
      const left = () => [x0, mix(z0, z1, t(a, d))]
      const seg = (p: number[], q: number[]) => out.push(p[0], p[1], q[0], q[1])
      switch (idx) {
        case 1:
        case 14:
          seg(left(), top())
          break
        case 2:
        case 13:
          seg(top(), right())
          break
        case 3:
        case 12:
          seg(left(), right())
          break
        case 4:
        case 11:
          seg(right(), bottom())
          break
        case 5:
          seg(left(), top())
          seg(right(), bottom())
          break
        case 6:
        case 9:
          seg(top(), bottom())
          break
        case 7:
        case 8:
          seg(left(), bottom())
          break
        case 10:
          seg(top(), right())
          seg(left(), bottom())
          break
      }
    }
  }
  return out
}
