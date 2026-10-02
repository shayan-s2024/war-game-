import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export function OrbitalRings({ radius = 2.06, color = '#52d8ff', intensity = 1 }: {
  radius?: number; color?: string; intensity?: number
}) {
  const a = useRef<THREE.Group>(null)
  const b = useRef<THREE.Group>(null)
  const c = useRef<THREE.Group>(null)
  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    if (a.current) {
      a.current.rotation.x = Math.sin(t * 0.17) * 0.28
      a.current.rotation.y = t * 0.08
    }
    if (b.current) {
      b.current.rotation.x = Math.PI * 0.52 + Math.cos(t * 0.13) * 0.16
      b.current.rotation.z = -t * 0.045
    }
    if (c.current) {
      c.current.rotation.x = Math.PI * 0.2 + Math.sin(t * 0.11) * 0.22
      c.current.rotation.y = t * 0.028
      c.current.scale.setScalar(1 + Math.sin(t * 1.1) * 0.008)
    }
  })
  return (
    <group>
      <group ref={a}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[radius, 0.0045, 8, 160]} />
          <meshBasicMaterial color={color} transparent opacity={0.26 * intensity} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
      </group>
      <group ref={b}>
        <mesh>
          <torusGeometry args={[radius * 1.045, 0.0028, 8, 160]} />
          <meshBasicMaterial color="#f7c65f" transparent opacity={0.18 * intensity} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
      </group>
      <group ref={c}>
        <mesh rotation={[Math.PI / 2, 0.35, 0]}>
          <torusGeometry args={[radius * 1.075, 0.0017, 6, 140]} />
          <meshBasicMaterial color="#8aa8ff" transparent opacity={0.15 * intensity} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
      </group>
    </group>
  )
}

export function Starfield({ count = 1400, radius = 26 }: { count?: number; radius?: number }) {
  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const c = new THREE.Color()
    for (let i = 0; i < count; i++) {
      const r = radius * (0.82 + Math.random() * 0.55)
      const u = Math.random() * 2 - 1
      const a = Math.random() * Math.PI * 2
      const s = Math.sqrt(1 - u * u)
      positions[i * 3] = r * s * Math.cos(a)
      positions[i * 3 + 1] = r * u
      positions[i * 3 + 2] = r * s * Math.sin(a)
      const k = Math.random()
      c.set(k < 0.72 ? '#d8e6ff' : k < 0.92 ? '#8ac6ff' : '#ffe2a6')
      const b = 0.24 + Math.pow(Math.random(), 2.6) * 0.76
      colors[i * 3] = c.r * b; colors[i * 3 + 1] = c.g * b; colors[i * 3 + 2] = c.b * b
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [count, radius])
  const ref = useRef<THREE.Points>(null)
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.006
  })
  return (
    <points ref={ref} geometry={geometry}>
      <pointsMaterial size={0.055} vertexColors sizeAttenuation transparent opacity={0.78} depthWrite={false} />
    </points>
  )
}

export function HologramGrid({ radius = 2.095 }: { radius?: number }) {
  const ref = useRef<THREE.Group>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.elapsedTime * 0.012
    ref.current.rotation.z = Math.sin(clock.elapsedTime * 0.18) * 0.025
  })
  return (
    <group ref={ref}>
      <mesh>
        <sphereGeometry args={[radius, 40, 24]} />
        <meshBasicMaterial color="#53c7ff" transparent opacity={0.028} wireframe depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh scale={1.004}>
        <sphereGeometry args={[radius, 24, 12]} />
        <meshBasicMaterial color="#f3bf5e" transparent opacity={0.018} wireframe depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  )
}
