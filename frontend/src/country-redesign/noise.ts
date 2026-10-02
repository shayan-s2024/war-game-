// Seeded random + gradient noise helpers used by the terrain generator.

export function mulberry32(seed: number) {
  let a = seed | 0
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const fade = (t: number) => t * t * t * (t * (t * 6 - 15) + 10)
const lerp = (a: number, b: number, t: number) => a + (b - a) * t

export class Noise2D {
  private perm = new Uint16Array(512)
  private gx = new Float32Array(256)
  private gy = new Float32Array(256)

  constructor(seed: number) {
    const rnd = mulberry32(seed)
    const p = new Uint16Array(256)
    for (let i = 0; i < 256; i++) p[i] = i
    for (let i = 255; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1))
      const t = p[i]
      p[i] = p[j]
      p[j] = t
    }
    for (let i = 0; i < 512; i++) this.perm[i] = p[i & 255]
    for (let i = 0; i < 256; i++) {
      const a = rnd() * Math.PI * 2
      this.gx[i] = Math.cos(a)
      this.gy[i] = Math.sin(a)
    }
  }

  /** classic gradient noise, ~[-1, 1] */
  noise(x: number, y: number): number {
    const xi = Math.floor(x)
    const yi = Math.floor(y)
    const xf = x - xi
    const yf = y - yi
    const X = xi & 255
    const Y = yi & 255
    const g = (ix: number, iy: number, dx: number, dy: number) => {
      const h = this.perm[this.perm[ix & 255] + (iy & 255)] & 255
      return this.gx[h] * dx + this.gy[h] * dy
    }
    const u = fade(xf)
    const v = fade(yf)
    return (
      lerp(
        lerp(g(X, Y, xf, yf), g(X + 1, Y, xf - 1, yf), u),
        lerp(g(X, Y + 1, xf, yf - 1), g(X + 1, Y + 1, xf - 1, yf - 1), u),
        v,
      ) * 1.41
    )
  }

  /** noise that tiles with an integer period (for seamless textures) */
  tile(x: number, y: number, period: number): number {
    const xi = Math.floor(x)
    const yi = Math.floor(y)
    const xf = x - xi
    const yf = y - yi
    const wrap = (n: number) => ((n % period) + period) % period
    const g = (ix: number, iy: number, dx: number, dy: number) => {
      const h = this.perm[this.perm[wrap(ix) & 255] + (wrap(iy) & 255)] & 255
      return this.gx[h] * dx + this.gy[h] * dy
    }
    const u = fade(xf)
    const v = fade(yf)
    return (
      lerp(
        lerp(g(xi, yi, xf, yf), g(xi + 1, yi, xf - 1, yf), u),
        lerp(g(xi, yi + 1, xf, yf - 1), g(xi + 1, yi + 1, xf - 1, yf - 1), u),
        v,
      ) * 1.41
    )
  }

  fbm(x: number, y: number, oct = 5, lac = 2.0, gain = 0.5): number {
    let amp = 1
    let f = 1
    let sum = 0
    let norm = 0
    for (let i = 0; i < oct; i++) {
      sum += amp * this.noise(x * f, y * f)
      norm += amp
      amp *= gain
      f *= lac
    }
    return sum / norm
  }

  /** ridged multifractal, ~[0, 1] — sharp mountain crests */
  ridged(x: number, y: number, oct = 6): number {
    let amp = 0.5
    let f = 1
    let sum = 0
    let weight = 1
    for (let i = 0; i < oct; i++) {
      let n = 1 - Math.abs(this.noise(x * f, y * f))
      n = n * n
      n *= weight
      weight = Math.min(1, Math.max(0, n * 2))
      sum += n * amp
      amp *= 0.5
      f *= 2.03
    }
    return sum
  }
}

export const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v))
export const smoothstep = (e0: number, e1: number, x: number) => {
  const t = clamp((x - e0) / (e1 - e0), 0, 1)
  return t * t * (3 - 2 * t)
}
export const mix = lerp
