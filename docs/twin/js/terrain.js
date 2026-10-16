// Bharat-Bot twin: the street surface, rebuilt in the browser with sim/world.py's arithmetic (potholes, water, the speed
// breaker, the broken road edge), from the numbers in data/street.json. Coordinates here are the simulation's: metres,
// x along the street, y to the left, z up. In three.js that is (x, z, -y).
import * as THREE from 'three';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const smoothstep = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };

// world._hash2 / vnoise: the same 32-bit integer hash, so the noise matches Python bit for bit
function hash2(ix, iy, seed) {
  let h = (Math.imul(ix, 374761393) + Math.imul(iy, 668265263) + Math.imul(seed, 1442695041)) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0;
  return ((h ^ (h >>> 16)) & 0xFFFFFF) / 0xFFFFFF;
}
function vnoise(x, y, scale, seed) {
  x /= scale; y /= scale;
  const ix = Math.floor(x), iy = Math.floor(y);
  const fx = x - ix, fy = y - iy;
  const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
  const a = hash2(ix, iy, seed), b = hash2(ix + 1, iy, seed), c = hash2(ix, iy + 1, seed), d = hash2(ix + 1, iy + 1, seed);
  return (a + (b - a) * sx) * (1 - sy) + (c + (d - c) * sx) * sy;
}

class Pothole {
  constructor(p) {
    Object.assign(this, p);
    this.c = Math.cos(p.rot); this.s = Math.sin(p.rot);
  }
  depthAt(x, y) {                       // world.Pothole.depth_at (0 outside its reach box)
    const dx = x - this.cx, dy = y - this.cy;
    if (Math.abs(dx) >= this.reach || Math.abs(dy) >= this.reach) return 0;
    const u = (dx * this.c + dy * this.s) / this.rx, v = (-dx * this.s + dy * this.c) / this.ry;
    const th = Math.atan2(v, u);
    const wob = 1 + 0.16 * Math.sin(3 * th + this.ph[0]) + 0.08 * Math.sin(5 * th + this.ph[1]) + 0.04 * Math.sin(9 * th + this.ph[2]);
    const rn = Math.hypot(u, v) / wob;
    const wall = 1 - smoothstep(0.78, 1.0, rn);
    const floor = 0.88 + 0.12 * clamp(1 - rn * rn, 0, 1);
    const lip = 0.010 * Math.exp(-(((rn - 1.08) / 0.07) ** 2));
    return this.depth * wall * floor - lip;
  }
  rimRadius(th) {                       // distance from the centre to the rim along world angle th
    const a = th - this.rot, u = Math.cos(a) / this.rx, v = Math.sin(a) / this.ry;
    const t = Math.atan2(v, u);
    return (1 + 0.16 * Math.sin(3 * t + this.ph[0]) + 0.08 * Math.sin(5 * t + this.ph[1]) + 0.04 * Math.sin(9 * t + this.ph[2])) / Math.hypot(u, v);
  }
}

export class Street {
  constructor(d) {
    this.d = d;
    this.half = d.roadHalf;
    this.asphalt = d.roadHalf - 0.16;    // nearer the centre than this the road mask is exactly 1 (world._ASPHALT)
    this.potholes = d.potholes.map((p) => new Pothole(p));
    this.wet = this.potholes.filter((p) => p.water > 0);
    this.sb = d.speedBreaker;
  }
  roadMask(x, y) {
    const edge = this.half + 0.05 + 0.22 * (vnoise(x, y, 0.45, 5) - 0.5) + 0.12 * (vnoise(x, y, 1.7, 6) - 0.5);
    return 1 - smoothstep(edge - 0.03, edge + 0.03, Math.abs(y));
  }
  potholeDepth(x, y) {
    let d = 0;
    for (const p of this.potholes) d = Math.max(d, p.depthAt(x, y));
    return d;
  }
  breaker(x, y) {
    const d = Math.abs(x - this.sb.x0);
    if (d >= this.sb.width / 2) return 0;
    const taper = 1 - smoothstep(this.half - 0.4, this.half - 0.05, Math.abs(y));
    return this.sb.height * Math.cos(Math.PI * d / this.sb.width) ** 2 * taper;
  }
  height(x, y) {                         // world.terrain_height
    const ay = Math.abs(y);
    const road = 0.025 * (1 - Math.min(1, ay / this.half) ** 2) + 0.004 * (vnoise(x, y, 0.6, 3) - 0.5);
    let z = road;
    if (ay >= this.asphalt) {
      const t = clamp((ay - this.half) / 1.3, 0, 1);
      const dirt = -0.035 + 0.085 * t + 0.025 * (vnoise(x, y, 0.5, 7) - 0.5) + 0.04 * (vnoise(x, y, 2.2, 9) - 0.5);
      const m = this.roadMask(x, y);
      z = road * m + dirt * (1 - m);
    }
    for (const p of this.potholes) z -= p.depthAt(x, y);
    return z + this.breaker(x, y);
  }
  waterDepth(x, y, z = null) {           // world.water_depth
    let out = 0;
    for (const p of this.wet) {
      if (Math.abs(x - p.cx) >= p.reach || Math.abs(y - p.cy) >= p.reach) continue;
      if (z === null) z = this.height(x, y);
      out = Math.max(out, p.level - z);
    }
    return Math.max(0, out);
  }
  // Python's own numbers at a few hundred points (street.json "checks"): the largest difference, in metres
  selfCheck() {
    let worst = 0;
    for (const [x, y, z, w, m, pd] of this.d.checks) {
      worst = Math.max(worst, Math.abs(this.height(x, y) - z), Math.abs(this.waterDepth(x, y) - w),
        Math.abs(this.roadMask(x, y) - m), Math.abs(this.potholeDepth(x, y) - pd));
    }
    return worst;
  }

  // ── the road-surface mesh: fine across the carriageway, coarser out to the shop fronts and at the street's ends ──
  buildMesh(fine = 0.075) {
    const span = (segs) => {
      const out = [];
      for (const [a, b, step] of segs) for (let v = a; v < b - 1e-9; v += step) out.push(+v.toFixed(4));
      return out;
    };
    const B = this.d.buildY;
    const xs = span([[this.d.x0, -4, 0.4], [-4, 74, fine], [74, this.d.x1 + 1e-6, 0.4]]);
    xs.push(this.d.x1);
    const ys = span([[-B, -3.8, 0.25], [-3.8, 4.0, fine], [4.0, B + 1e-6, 0.2]]);
    ys.push(B);
    const nx = xs.length, ny = ys.length, n = nx * ny;
    const pos = new Float32Array(n * 3), zone = new Float32Array(n * 3);
    let k = 0;
    for (let i = 0; i < nx; i++) {
      const x = xs[i];
      for (let j = 0; j < ny; j++, k++) {
        const y = ys[j];
        const z = this.height(x, y);
        pos[k * 3] = x; pos[k * 3 + 1] = z; pos[k * 3 + 2] = -y;
        // zones, as build_terrain() paints them: pothole floor, wet (water + a damp ring), dirt shoulder
        const pot = clamp(this.potholeDepth(x, y) / 0.05, 0, 1);
        let wet = clamp(this.waterDepth(x, y, z) / 0.004, 0, 1);
        for (const p of this.wet) {
          if (Math.abs(x - p.cx) < p.reach + 0.3 && Math.abs(y - p.cy) < p.reach + 0.3) wet = Math.max(wet, clamp(1 - (z - p.level) / 0.03, 0, 1) * 0.8);
        }
        const dirt = Math.abs(y) < this.asphalt ? 0 : 1 - this.roadMask(x, y);
        zone[k * 3] = pot; zone[k * 3 + 1] = wet; zone[k * 3 + 2] = dirt;
      }
    }
    const idx = new Uint32Array((nx - 1) * (ny - 1) * 6);
    k = 0;
    for (let i = 0; i < nx - 1; i++) {
      for (let j = 0; j < ny - 1; j++) {
        const a = i * ny + j, b = (i + 1) * ny + j, c = (i + 1) * ny + j + 1, d = i * ny + j + 1;
        idx[k++] = a; idx[k++] = d; idx[k++] = b;
        idx[k++] = b; idx[k++] = d; idx[k++] = c;
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('zone', new THREE.BufferAttribute(zone, 3));
    g.setIndex(new THREE.BufferAttribute(idx, 1));
    g.computeVertexNormals();
    g.computeBoundingSphere();
    return g;
  }
}

// ── materials ────────────────────────────────────────────────────────────────────────────────────────────────────
const NOISE = /* glsl */`
float bbHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123); }
float bbNoise(vec2 p) {
  vec2 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
  return mix(mix(bbHash(i), bbHash(i + vec2(1, 0)), u.x), mix(bbHash(i + vec2(0, 1)), bbHash(i + vec2(1, 1)), u.x), u.y);
}
float bbFbm(vec2 p) { return 0.55 * bbNoise(p) + 0.3 * bbNoise(p * 2.03 + 7.1) + 0.15 * bbNoise(p * 4.1 + 3.7); }
vec2 bbRot(vec2 p, float a) { float c = cos(a), s = sin(a); return vec2(c * p.x - s * p.y, s * p.x + c * p.y); }
`;

// environment.mat_terrain_textured in GLSL: cracked asphalt with dusty patches toward the edges, red laterite shoulders,
// mud in the potholes, darker and glossy where it is wet; the breaker's older, paler surface
export function terrainMaterial(tex, breakerX) {
  const m = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9, metalness: 0 });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, { tA: { value: tex.asphalt }, tAN: { value: tex.asphaltN }, tR: { value: tex.damaged },
      tD: { value: tex.dirt }, tDN: { value: tex.dirtN }, tM: { value: tex.mud }, uSB: { value: breakerX } });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec3 zone;\nvarying vec3 vZone;\nvarying vec3 vWP;\nvarying vec3 vWN;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvZone = zone;\nvWP = (modelMatrix * vec4(position, 1.0)).xyz;\nvWN = normalize(mat3(modelMatrix) * normal);');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
uniform sampler2D tA, tAN, tR, tD, tDN, tM; uniform float uSB;
varying vec3 vZone; varying vec3 vWP; varying vec3 vWN;
${NOISE}
vec3 bbCol; float bbRough; vec3 bbN;`)
      .replace('#include <map_fragment>', `
vec2 P = vec2(vWP.x, -vWP.z);
float pot = vZone.x, wet = vZone.y, dirt = vZone.z;
vec2 ua = P / 3.0, ud = bbRot(P, 0.4) / 2.0, um = bbRot(P, 0.9) / 1.5, ur = bbRot(P, 1.3) / 2.2;
vec3 asph = texture2D(tA, ua).rgb;
float dust = clamp(0.65 * smoothstep(0.48, 0.66, bbFbm(P * 0.35)) + 0.45 * clamp((abs(P.y) - 2.4) / 1.1, 0.0, 1.0), 0.0, 1.0);
vec3 road = mix(asph, texture2D(tR, ur).rgb, dust) * 0.78;
float sb = clamp(mix(0.7, 0.0, (abs(P.x - uSB) - 0.42) / 0.1), 0.0, 0.7);
road = mix(road, vec3(0.24, 0.22, 0.2), sb);
vec3 col = mix(road, texture2D(tD, ud).rgb, dirt);
col = mix(col, texture2D(tM, um).rgb, pot * 0.95);
col = mix(col, col * 0.45, wet * 0.85);
diffuseColor.rgb *= col;
bbRough = mix(mix(0.86, 0.95, dirt), 0.12, wet);
vec3 nA = texture2D(tAN, ua).xyz * 2.0 - 1.0, nD = texture2D(tDN, ud).xyz * 2.0 - 1.0;
vec3 nt = normalize(mix(nA * vec3(0.8, 0.8, 1.0), nD, dirt));
nt.xy *= 1.0 - wet * 0.8;
vec3 Nw = normalize(vWN), Tw = normalize(vec3(1.0, 0.0, 0.0) - Nw * Nw.x), Bw = cross(Nw, Tw);
bbN = normalize((viewMatrix * vec4(normalize(Tw * nt.x + Bw * nt.y + Nw * nt.z), 0.0)).xyz);`)
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = bbRough;')
      .replace('#include <normal_fragment_maps>', 'normal = bbN;');
  };
  m.customProgramCacheKey = () => 'bb-terrain';
  return m;
}

// environment.mat_wall: the object's colour on photographed plaster, grimy toward the ground, with stains
export function wallMaterial(plaster) {
  const m = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.88, metalness: 0, vertexColors: true });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.tP = { value: plaster };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWP;\nvarying vec3 vWN;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWP = (modelMatrix * vec4(position, 1.0)).xyz;\nvWN = normalize(mat3(modelMatrix) * normal);');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\nuniform sampler2D tP;\nvarying vec3 vWP;\nvarying vec3 vWN;\n${NOISE}`)
      .replace('#include <map_fragment>', `
vec3 an = abs(normalize(vWN));
vec2 uv = an.y > max(an.x, an.z) ? vWP.xz : (an.x > an.z ? vWP.zy : vWP.xy);
vec3 pl = texture2D(tP, uv * 0.5).rgb;
float low = clamp(mix(0.42, 0.0, vWP.y / 1.4), 0.0, 0.42);
float stain = (bbFbm(vec2(vWP.x + vWP.z, vWP.y) * 1.6) - 0.42) * 0.9;
float grime = clamp(low + stain, 0.0, 1.0);
diffuseColor.rgb = mix(diffuseColor.rgb * pl * 1.25, vec3(0.18, 0.15, 0.12), grime);`);
  };
  m.customProgramCacheKey = () => 'bb-wall';
  return m;
}

// environment/bpy_utils mat_water: muddy standing water with a slow ripple
export function waterMaterial() {
  const m = new THREE.MeshStandardMaterial({ color: new THREE.Color(0.075, 0.06, 0.042), roughness: 0.04, metalness: 0,
    envMapIntensity: 1.4, transparent: true, opacity: 0.93, polygonOffset: true, polygonOffsetFactor: -2 });
  const time = { value: 0 };
  m.userData.time = time;
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uT = time;
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWP;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWP = (modelMatrix * vec4(position, 1.0)).xyz;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\nuniform float uT;\nvarying vec3 vWP;\n${NOISE}`)
      .replace('#include <normal_fragment_maps>', `
vec2 q = vWP.xz * 9.0;
float e = 0.06;
float h0 = bbFbm(q + uT * 0.35), hx = bbFbm(q + vec2(e, 0.0) + uT * 0.35), hz = bbFbm(q + vec2(0.0, e) + uT * 0.35);
vec3 nW = normalize(vec3(-(hx - h0) / e * 0.05, 1.0, -(hz - h0) / e * 0.05));
normal = normalize((viewMatrix * vec4(nW, 0.0)).xyz);`);
  };
  m.customProgramCacheKey = () => 'bb-water';
  return m;
}
