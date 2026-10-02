import * as THREE from 'three'
import { smoothstep, mix } from './noise'

export const CLOUD_Y = 92

/* ------------------------------------------------------------------ */
/* shared GLSL                                                         */
/* ------------------------------------------------------------------ */
export const GLSL_NOISE = /* glsl */ `
float hash21(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
float vnoise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  f = f*f*(3.0-2.0*f);
  float a = hash21(i), b = hash21(i+vec2(1.0,0.0)), c = hash21(i+vec2(0.0,1.0)), d = hash21(i+vec2(1.0,1.0));
  return mix(mix(a,b,f.x), mix(c,d,f.x), f.y);
}
float fbm4(vec2 p){
  float s = 0.0, a = 0.5;
  for(int i=0;i<4;i++){ s += a*vnoise(p); p = p*2.03 + vec2(17.1,9.3); a *= 0.5; }
  return s;
}
float cloudDensity(vec2 p, float t, float cover){
  vec2 q = p*0.0105 + vec2(t*0.0042, t*0.0016);
  float n = fbm4(q)*0.72 + 0.28*fbm4(q*3.3+7.7);
  return smoothstep(cover, cover+0.24, n);
}
`

/* ------------------------------------------------------------------ */
/* shared uniforms (one set, referenced by every material)             */
/* ------------------------------------------------------------------ */
export interface SharedUniforms {
  uTime: { value: number }
  uNight: { value: number }
  uSunDir: { value: THREE.Vector3 }
  uSunCol: { value: THREE.Color }
  uZenith: { value: THREE.Color }
  uHorizon: { value: THREE.Color }
  uFogCol: { value: THREE.Color }
  uFogDensity: { value: number }
  uCover: { value: number }
  uCloudOn: { value: number }
  uSunset: { value: number }
  uDay: { value: number }
}

export function createSharedUniforms(): SharedUniforms {
  return {
    uTime: { value: 0 },
    uNight: { value: 0 },
    uSunDir: { value: new THREE.Vector3(0.5, 0.5, 0.5).normalize() },
    uSunCol: { value: new THREE.Color(1, 0.9, 0.7) },
    uZenith: { value: new THREE.Color(0.07, 0.2, 0.55) },
    uHorizon: { value: new THREE.Color(0.5, 0.65, 0.85) },
    uFogCol: { value: new THREE.Color(0.5, 0.65, 0.85) },
    uFogDensity: { value: 0.0016 },
    uCover: { value: 0.5 },
    uCloudOn: { value: 1 },
    uSunset: { value: 0 },
    uDay: { value: 1 },
  }
}

/* ------------------------------------------------------------------ */
/* atmosphere model                                                    */
/* ------------------------------------------------------------------ */
export interface SkyState {
  sunDir: THREE.Vector3
  elev: number
  lightDir: THREE.Vector3
  lightColor: THREE.Color
  lightIntensity: number
  hemiSky: THREE.Color
  hemiGround: THREE.Color
  hemiIntensity: number
  exposure: number
}

const c = (r: number, g: number, b: number) => new THREE.Color(r, g, b)
const lerpC = (out: THREE.Color, a: THREE.Color, b: THREE.Color, t: number) => out.copy(a).lerp(b, t)

const ZEN_DAY = c(0.06, 0.19, 0.55)
const ZEN_NIGHT = c(0.0015, 0.004, 0.014)
const ZEN_TW = c(0.05, 0.09, 0.25)
const HOR_DAY = c(0.5, 0.66, 0.86)
const HOR_NIGHT = c(0.008, 0.014, 0.034)
const HOR_TW = c(0.95, 0.4, 0.15)
const SUN_WHITE = c(1.0, 0.95, 0.85)
const SUN_ORANGE = c(1.0, 0.5, 0.2)
const MOON = c(0.42, 0.52, 0.9)
const NIGHT_AMB = c(0.05, 0.08, 0.17)
const NIGHT_GND = c(0.02, 0.025, 0.04)

export function applyAtmosphere(hour: number, u: SharedUniforms, sky: SkyState, cloudy: number) {
  const a = ((hour - 6) / 12) * Math.PI
  sky.sunDir.set(Math.cos(a), Math.sin(a) * 0.82, 0.45).normalize()
  const s = sky.sunDir.y
  sky.elev = s
  const dayF = smoothstep(-0.08, 0.28, s)
  const tw = Math.exp(-Math.pow(s / 0.2, 2))

  u.uSunDir.value.copy(sky.sunDir)
  u.uDay.value = dayF
  u.uNight.value = 1 - smoothstep(-0.14, 0.1, s)
  u.uSunset.value = tw

  const zen = u.uZenith.value
  lerpC(zen, ZEN_NIGHT, ZEN_DAY, dayF)
  zen.lerp(ZEN_TW, tw * 0.55)
  const hor = u.uHorizon.value
  lerpC(hor, HOR_NIGHT, HOR_DAY, dayF)
  hor.lerp(HOR_TW, tw * 0.75)
  // overcast greys the sky
  const grey = c(0.38, 0.42, 0.48).multiplyScalar(0.2 + 0.8 * dayF)
  zen.lerp(grey, cloudy * 0.4)
  hor.lerp(grey, cloudy * 0.35)

  u.uFogCol.value.copy(hor).multiplyScalar(0.92)
  u.uFogDensity.value = 0.0015 + cloudy * 0.0006 + (1 - dayF) * 0.0002
  u.uCover.value = 0.62 - cloudy * 0.26

  lerpC(u.uSunCol.value, SUN_ORANGE, SUN_WHITE, smoothstep(0.04, 0.5, s))

  const sunI = 6.6 * smoothstep(-0.02, 0.22, s) * (1 - cloudy * 0.45)
  const moonI = 1.5 * smoothstep(0.06, -0.22, s)
  if (s > -0.03) {
    sky.lightDir.copy(sky.sunDir)
    sky.lightColor.copy(u.uSunCol.value)
    sky.lightIntensity = sunI + 0.001
  } else {
    sky.lightDir.copy(sky.sunDir).negate()
    sky.lightColor.copy(MOON)
    sky.lightIntensity = moonI
  }
  sky.hemiSky.copy(zen).lerp(hor, 0.35).multiplyScalar(1.15)
  sky.hemiSky.lerp(NIGHT_AMB, (1 - dayF) * 0.85)
  sky.hemiGround.set(0.2, 0.17, 0.12).multiplyScalar(0.25 + 0.75 * dayF)
  sky.hemiGround.lerp(NIGHT_GND, (1 - dayF) * 0.8)
  sky.hemiIntensity = 0.9 + 1.3 * dayF
  sky.exposure = mix(1.15, 0.85, dayF)
}

/* ------------------------------------------------------------------ */
/* terrain material                                                    */
/* ------------------------------------------------------------------ */
export function patchTerrainMaterial(
  mat: THREE.MeshStandardMaterial,
  u: SharedUniforms,
  ctrl: THREE.Texture,
  palette: Record<string, string>,
  snowLine: number,
) {
  const col = (hex: string) => new THREE.Color(hex)
  const own = {
    uCtrl: { value: ctrl },
    uGrassA: { value: col(palette.grassA) },
    uGrassB: { value: col(palette.grassB) },
    uDry: { value: col(palette.dry) },
    uForest: { value: col(palette.forestFloor) },
    uRockA: { value: col(palette.rockA) },
    uRockB: { value: col(palette.rockB) },
    uSand: { value: col(palette.sand) },
    uSnow: { value: col(palette.snow) },
    uSnowLine: { value: snowLine },
  }
  mat.userData.own = own
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, own, {
      uTime: u.uTime,
      uSunDir: u.uSunDir,
      uCover: u.uCover,
      uCloudOn: u.uCloudOn,
      uDay: u.uDay,
    })
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        `#include <common>
varying vec3 vWPos; varying vec3 vWNor; varying vec2 vCUv;`,
      )
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
vWPos = (modelMatrix * vec4(position, 1.0)).xyz;
vWNor = normalize(mat3(modelMatrix) * normal);
vCUv = uv;`,
      )
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
${GLSL_NOISE}
uniform sampler2D uCtrl;
uniform vec3 uGrassA, uGrassB, uDry, uForest, uRockA, uRockB, uSand, uSnow, uSunDir;
uniform float uSnowLine, uTime, uCover, uCloudOn, uDay;
varying vec3 vWPos; varying vec3 vWNor; varying vec2 vCUv;
float detailH(vec2 p){ return vnoise(p*1.9)*0.55 + vnoise(p*5.7)*0.3 + vnoise(p*15.0)*0.18; }`,
      )
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
vec4 ctrl = texture2D(uCtrl, vCUv);
float tForest = ctrl.r;
float tMoist = ctrl.g;
float tWater = ctrl.b;
float hgt = vWPos.y;
vec3 wN = normalize(vWNor);
float slp = 1.0 - wN.y;
vec2 wp = vWPos.xz;
float n1 = fbm4(wp*0.33);
float n2 = fbm4(wp*1.7 + 3.0);
float n3 = vnoise(wp*8.0);
float camD = length(cameraPosition - vWPos);

vec3 grass = mix(uGrassA, uGrassB, smoothstep(0.25, 0.8, n1 + (n2-0.5)*0.35));
vec3 dryc = mix(uDry, uDry*0.84, n2);
vec3 ground = mix(dryc, grass, smoothstep(0.28, 0.62, tMoist + (n1-0.5)*0.32));
ground *= 0.86 + 0.28*n3;
ground = mix(ground, uForest*(0.8+0.4*n2), tForest*0.82);

float strata = 0.5 + 0.5*sin(hgt*3.4 + n1*5.0);
vec3 rock = mix(uRockA, uRockB, clamp(n2*0.8 + strata*0.35, 0.0, 1.0)) * (0.72 + 0.5*n3);
float rockAmt = smoothstep(0.17, 0.36, slp + (n2-0.5)*0.12) + smoothstep(13.0, 26.0, hgt)*0.35*(1.0-tForest);
rockAmt = clamp(rockAmt, 0.0, 1.0);
vec3 col = mix(ground, rock, rockAmt);

// beach / seabed
float sandAmt = (1.0 - smoothstep(0.35, 1.9, hgt + (n2-0.5)*0.9)) * (1.0 - rockAmt*0.7);
col = mix(col, uSand*(0.88+0.2*n3), sandAmt);
float wet = 1.0 - smoothstep(0.0, 0.55, hgt + (n3-0.5)*0.3);
col *= 1.0 - wet*0.28;
float deep = 1.0 - smoothstep(-7.0, 0.0, hgt);
col = mix(col, vec3(0.03, 0.09, 0.13), deep*0.85);

// snow
float snowLineN = uSnowLine + (n1-0.5)*6.0;
float snowAmt = smoothstep(snowLineN, snowLineN + 3.5, hgt) * (1.0 - smoothstep(0.34, 0.62, slp + (n2-0.5)*0.1));
col = mix(col, uSnow*(0.94+0.08*n3), snowAmt);
float tSnow = snowAmt;

// rivers & lakes
vec3 waterCol = mix(vec3(0.045,0.17,0.2), vec3(0.09,0.3,0.34), n2);
float wMask = smoothstep(0.28, 0.62, tWater);
col = mix(col, waterCol, wMask*(1.0 - snowAmt*0.0));
tWater = wMask;

// drifting cloud shadows
vec2 shP = wp + uSunDir.xz / max(uSunDir.y, 0.22) * ${CLOUD_Y.toFixed(1)};
float cs = cloudDensity(shP, uTime, uCover) * uCloudOn * uDay;
col *= 1.0 - cs*0.42;
// aerial perspective on forest floors keeps far hills soft
diffuseColor.rgb = col;`,
      )
      .replace(
        '#include <roughnessmap_fragment>',
        `#include <roughnessmap_fragment>
roughnessFactor = mix(roughnessFactor, 0.07, tWater*0.9);
roughnessFactor = mix(roughnessFactor, 0.62, tSnow);`,
      )
      .replace(
        '#include <normal_fragment_maps>',
        `#include <normal_fragment_maps>
{
  float fade = 1.0 - smoothstep(60.0, 230.0, camD);
  float amp = (0.55 + rockAmt*1.1) * fade * (1.0 - tWater);
  vec2 e = vec2(0.14, 0.0);
  float d0 = detailH(wp);
  float dx = detailH(wp + e.xy) - d0;
  float dz = detailH(wp + e.yx) - d0;
  // rivers get a flowing ripple instead
  float rip = (vnoise(wp*3.0 + vec2(uTime*0.4, 0.0)) - 0.5);
  vec3 nW = normalize(wN + vec3(-dx, 0.0, -dz) / e.x * amp * 0.2 + vec3(rip, 0.0, rip*0.6) * tWater * 0.12);
  normal = normalize((viewMatrix * vec4(nW, 0.0)).xyz);
}`,
      )
  }
  mat.customProgramCacheKey = () => 'terrain-v1'
}

/* ------------------------------------------------------------------ */
/* ocean                                                               */
/* ------------------------------------------------------------------ */
export function createWaterMaterial(u: SharedUniforms, ctrl: THREE.Texture, size: number, hMin: number, hRange: number) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: {
      ...u,
      uCtrl: { value: ctrl },
      uSize: { value: size },
      uHMin: { value: hMin },
      uHRange: { value: hRange },
    },
    vertexShader: /* glsl */ `
varying vec3 vWPos;
void main(){
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vWPos = wp.xyz;
  gl_Position = projectionMatrix * viewMatrix * wp;
}`,
    fragmentShader: /* glsl */ `
${GLSL_NOISE}
uniform float uTime, uNight, uFogDensity, uSize, uHMin, uHRange, uDay;
uniform vec3 uSunDir, uSunCol, uZenith, uHorizon, uFogCol;
uniform sampler2D uCtrl;
varying vec3 vWPos;

vec3 skyCol(vec3 d){
  float t = pow(clamp(d.y, 0.0, 1.0), 0.45);
  vec3 c = mix(uHorizon, uZenith, t);
  float s = max(dot(d, uSunDir), 0.0);
  c += uSunCol * (pow(s, 900.0)*10.0 + pow(s, 9.0)*0.22) * smoothstep(-0.1, 0.1, uSunDir.y);
  return c;
}
vec2 waves(vec2 p, float t){
  vec2 g = vec2(0.0);
  for(int i=0;i<6;i++){
    float fi = float(i);
    float a = fi*1.37 + 0.4;
    vec2 dir = vec2(cos(a), sin(a));
    float k = 0.32*pow(1.62, fi);
    float ph = dot(dir, p)*k + t*(0.7 + 0.22*fi*0.9) + fi*2.0;
    g += dir * cos(ph) * (0.19/(1.0 + fi*0.85)) ;
  }
  return g;
}
void main(){
  vec2 uv = vWPos.xz / uSize + 0.5;
  float inside = step(0.0, uv.x)*step(uv.x, 1.0)*step(0.0, uv.y)*step(uv.y, 1.0);
  float hh = mix(-20.0, texture2D(uCtrl, clamp(uv, 0.0, 1.0)).a + 0.0 * (uHRange + uHMin), inside);
  float depth = max(vWPos.y - hh, 0.0);

  float camDist = length(cameraPosition - vWPos);
  vec2 g = waves(vWPos.xz, uTime) * (1.0 - smoothstep(120.0, 700.0, camDist)*0.75);
  vec3 n = normalize(vec3(-g.x, 1.0, -g.y));
  vec3 V = normalize(cameraPosition - vWPos);
  float NdV = max(dot(n, V), 0.0);
  float fres = 0.025 + 0.975*pow(1.0 - NdV, 5.0);

  float absorb = 1.0 - exp(-depth*0.32);
  vec3 shallow = vec3(0.07, 0.34, 0.36);
  vec3 deepc = vec3(0.004, 0.035, 0.085);
  vec3 body = mix(shallow, deepc, smoothstep(0.0, 1.0, absorb));
  body *= 0.12 + 0.88*uDay;

  vec3 R = reflect(-V, n);
  R.y = abs(R.y);
  vec3 refl = skyCol(normalize(R));
  vec3 col = mix(body, refl, clamp(fres, 0.0, 1.0));

  vec3 Hh = normalize(uSunDir + V);
  float spec = pow(max(dot(n, Hh), 0.0), 380.0) * 6.0 * smoothstep(-0.05, 0.12, uSunDir.y);
  col += uSunCol * spec;

  // shoreline foam
  float shore = 1.0 - smoothstep(0.0, 1.05, depth);
  float wv = 0.5 + 0.5*sin(uTime*1.15 - depth*8.0 + fbm4(vWPos.xz*0.55)*7.0);
  float foam = shore * smoothstep(0.42, 0.95, wv * (fbm4(vWPos.xz*2.4 + uTime*0.05) + 0.42));
  foam += (1.0 - smoothstep(0.0, 0.14, depth)) * 0.7;
  foam = clamp(foam, 0.0, 1.0);
  col = mix(col, vec3(0.92, 0.96, 0.98) * (0.2 + 0.8*uDay + 0.0), foam*0.85);

  float alpha = smoothstep(0.0, 0.55, depth) * (0.62 + 0.36*absorb);
  alpha = clamp(alpha + foam*0.6, 0.0, 1.0);
  if(depth <= 0.0) alpha = 0.0;

  float fogF = 1.0 - exp(-uFogDensity*uFogDensity*camDist*camDist);
  col = mix(col, uFogCol, fogF);
  gl_FragColor = vec4(col, alpha);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`,
  })
}

/* ------------------------------------------------------------------ */
/* sky dome                                                            */
/* ------------------------------------------------------------------ */
export function createSkyMaterial(u: SharedUniforms) {
  return new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: { ...u },
    vertexShader: /* glsl */ `
varying vec3 vDir;
void main(){
  vDir = normalize(position);
  vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  gl_Position = p.xyww;
}`,
    fragmentShader: /* glsl */ `
${GLSL_NOISE}
uniform vec3 uSunDir, uSunCol, uZenith, uHorizon;
uniform float uNight, uSunset, uTime;
varying vec3 vDir;
float hash31(vec3 p){ p = fract(p*0.3183099 + 0.1); p *= 17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
void main(){
  vec3 d = normalize(vDir);
  float h = d.y;
  vec3 col = mix(uHorizon, uZenith, pow(clamp(h, 0.0, 1.0), 0.5));
  col = mix(col, uHorizon*0.55, 1.0 - smoothstep(-0.25, 0.0, h));
  float s = dot(d, uSunDir);
  float haze = exp(-abs(h)*5.5);
  vec2 sunH = normalize(uSunDir.xz + 1e-4);
  float sideSun = pow(max(dot(normalize(d.xz + 1e-4), sunH), 0.0), 3.0);
  col += vec3(1.0, 0.42, 0.14) * haze * sideSun * uSunset * 0.9;
  float vis = smoothstep(-0.12, 0.03, uSunDir.y);
  col += uSunCol * (smoothstep(0.99955, 0.9999, s)*18.0 + pow(max(s,0.0), 48.0)*0.5 + pow(max(s,0.0), 6.0)*0.14) * vis;
  // moon + stars
  vec3 md = -uSunDir;
  float ms = dot(d, md);
  float moon = smoothstep(0.9993, 0.9997, ms);
  col += vec3(0.75, 0.82, 1.0) * moon * 1.6 * uNight;
  col += vec3(0.25, 0.3, 0.5) * pow(max(ms, 0.0), 40.0) * 0.25 * uNight;
  vec3 q = floor(d*260.0);
  float st = step(0.9965, hash31(q));
  float tw = 0.65 + 0.35*sin(uTime*2.0 + hash31(q+3.0)*30.0);
  col += vec3(0.9,0.95,1.0) * st * tw * uNight * smoothstep(0.0, 0.2, h) * 1.1;
  gl_FragColor = vec4(col, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`,
  })
}

/* ------------------------------------------------------------------ */
/* cloud layer                                                         */
/* ------------------------------------------------------------------ */
export function createCloudMaterial(u: SharedUniforms) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: { ...u, uY: { value: CLOUD_Y } },
    vertexShader: /* glsl */ `
varying vec3 vWPos;
void main(){
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vWPos = wp.xyz;
  gl_Position = projectionMatrix * viewMatrix * wp;
}`,
    fragmentShader: /* glsl */ `
${GLSL_NOISE}
uniform float uTime, uCover, uCloudOn, uFogDensity, uDay, uSunset, uY, uNight;
uniform vec3 uSunDir, uSunCol, uHorizon, uFogCol;
varying vec3 vWPos;
void main(){
  float d = cloudDensity(vWPos.xz, uTime, uCover);
  if(d < 0.01 || uCloudOn < 0.5) discard;
  vec2 toSun = normalize(uSunDir.xz + 1e-4) * 7.0;
  float d2 = cloudDensity(vWPos.xz + toSun, uTime, uCover);
  float lit = clamp(1.0 - (d2 - d)*1.8 - d*0.35, 0.0, 1.0);
  vec3 litCol = mix(vec3(0.98,0.98,1.0), uSunCol, 0.35 + uSunset*0.5);
  vec3 darkCol = mix(vec3(0.42,0.46,0.56), uHorizon*0.7, 0.25);
  vec3 col = mix(darkCol, litCol, lit) * (0.06 + 0.94*uDay) + vec3(0.03,0.035,0.06)*uNight;
  float camDist = length(cameraPosition - vWPos);
  float near = smoothstep(8.0, 55.0, abs(cameraPosition.y - uY));
  float alpha = d * 0.9 * near;
  alpha *= 1.0 - smoothstep(650.0, 1250.0, length(vWPos.xz - cameraPosition.xz));
  float fogF = 1.0 - exp(-uFogDensity*uFogDensity*camDist*camDist);
  col = mix(col, uFogCol, fogF);
  alpha *= 1.0 - fogF*0.55;
  gl_FragColor = vec4(col, alpha);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`,
  })
}

/* ------------------------------------------------------------------ */
/* instanced buildings: procedural facades + night windows             */
/* ------------------------------------------------------------------ */
export function patchBuildingMaterial(mat: THREE.MeshStandardMaterial, u: SharedUniforms) {
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uNight = u.uNight
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        `#include <common>
varying vec3 vBWPos; varying vec3 vBNor; varying float vBSeed; varying float vBTop;`,
      )
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
vec4 bw = instanceMatrix * vec4(transformed, 1.0);
vBWPos = (modelMatrix * bw).xyz;
vBNor = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * normal);
vBSeed = fract(sin(dot(instanceMatrix[3].xz, vec2(12.9898, 78.233))) * 43758.5453);
vBTop = transformed.y;`,
      )
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
uniform float uNight;
varying vec3 vBWPos; varying vec3 vBNor; varying float vBSeed; varying float vBTop;
float bh(vec2 p){ p = fract(p*vec2(443.897, 441.423)); p += dot(p, p.yx+19.19); return fract((p.x+p.y)*p.x); }`,
      )
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
float wallF = 1.0 - step(0.5, abs(vBNor.y));
vec3 tng = vec3(-vBNor.z, 0.0, vBNor.x);
float along = dot(vBWPos, tng);
vec2 cellP = vec2(along / 0.62, vBWPos.y / 0.7);
vec2 cid = floor(cellP);
vec2 cf = fract(cellP);
float winM = step(0.2, cf.x) * step(cf.x, 0.8) * step(0.22, cf.y) * step(cf.y, 0.78) * wallF * step(1.0, vBWPos.y - 0.0);
float lit = step(0.52, bh(cid + vBSeed*91.0));
vec3 glass = mix(vec3(0.06,0.09,0.13), vec3(0.2,0.27,0.34), bh(cid*1.7 + vBSeed));
diffuseColor.rgb = mix(diffuseColor.rgb, glass, winM*0.88);
float winMask = winM;`,
      )
      .replace(
        '#include <roughnessmap_fragment>',
        `#include <roughnessmap_fragment>
roughnessFactor = mix(roughnessFactor, 0.16, winMask);`,
      )
      .replace(
        '#include <emissivemap_fragment>',
        `#include <emissivemap_fragment>
totalEmissiveRadiance += vec3(1.0, 0.76, 0.42) * lit * winMask * uNight * 1.35;`,
      )
  }
  mat.customProgramCacheKey = () => 'building-v1'
}

/* ------------------------------------------------------------------ */
/* wind sway for instanced vegetation                                  */
/* ------------------------------------------------------------------ */
export function patchWindMaterial(mat: THREE.MeshStandardMaterial, u: SharedUniforms, strength: number) {
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = u.uTime
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\nuniform float uTime;`)
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
{
  vec4 ip = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
  float ph = uTime*1.7 + ip.x*0.31 + ip.z*0.27;
  float hh = max(position.y, 0.0);
  transformed.x += sin(ph) * ${strength.toFixed(3)} * hh * hh * 0.12;
  transformed.z += cos(ph*0.87 + 1.3) * ${strength.toFixed(3)} * hh * hh * 0.09;
}`,
      )
  }
  mat.customProgramCacheKey = () => 'wind-' + strength.toFixed(3)
}
