// Bharat-Bot twin: everything that moves (the two robots, the food parcel, three street dogs, the cow, the thief, the
// customer, two passers-by and the auto-rickshaw), posed every frame from a simulation run the way sim/build_scene.py
// keys them in Blender. Axes: Blender (x, y, z) is three.js (x, z, -y); a Blender XYZ rotation (rx, ry, rz) is the
// three.js Euler (rx, rz, -ry) in 'YZX' order.
import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';

const TAU = Math.PI * 2;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

// build_scene.MODE_GROUP / MODE_COLOURS: the robot's status lights by state
const MODE_GROUP = { 'DOG HOTSPOT': 'caution', 'DOG FREEZE': 'caution', CREEP: 'caution', YIELD: 'caution', 'PERSON IN PATH': 'caution',
  BLOCKED: 'caution', TAMPER: 'caution', ALARM: 'alarm', STUCK: 'alarm', STOLEN: 'alarm', DELIVERING: 'deliver', DELIVERED: 'done' };
const MODE_COLOURS = { go: [0.1, 1.0, 0.55], caution: [1.0, 0.5, 0.03], alarm: [1.0, 0.03, 0.02], deliver: [0.15, 0.55, 1.0], done: [0.2, 1.0, 0.2] };
const LED_GAIN = 14;

function ledify(obj) {
  const mats = [];
  obj.traverse((m) => {
    if (!m.isMesh) return;
    const mat = new THREE.MeshStandardMaterial({ color: 0x050506, roughness: 0.3, metalness: 0, emissive: 0xffffff, emissiveIntensity: 0 });
    m.material = mat;
    m.userData.led = true;
    mats.push(mat);
  });
  return { obj, set(rgb, a) { for (const m of mats) { m.emissive.setRGB(rgb[0], rgb[1], rgb[2]); m.emissiveIntensity = a * LED_GAIN; } } };
}

function shadows(root, cast = true) {
  root.traverse((o) => { if (o.isMesh) { o.castShadow = cast; o.receiveShadow = true; } });
}

// ── robots ──────────────────────────────────────────────────────────────────────────────────────────────────────
export class RobotRig {
  constructor(root, kind) {
    this.root = root;
    this.kind = kind;
    const P = kind === 'bharat' ? 'BharatBot' : 'StdBot';
    this.prefix = P;
    const by = (n) => root.getObjectByName(n);
    this.hinge = by(`${P}_lidhinge`);
    const wheels = root.children.filter((o) => o.name.startsWith(`${P}_wheel`));
    const front = (a, b) => b.position.x - a.position.x;
    this.wheels = [...wheels.filter((w) => w.position.z < 0).sort(front), ...wheels.filter((w) => w.position.z > 0).sort(front)];
    this.wheelRest = this.wheels.map((w) => w.position.clone());
    // own material per mesh, so lighting up one part (explode view) never lights up another
    root.traverse((m) => { if (m.isMesh) m.material = m.material.clone(); });
    this.arms = [];
    for (const side of [1, -1]) {
      for (const nm of ['rf', 'rb', 'bf', 'bb']) {
        const o = by(`${P}_arm_${nm}${side > 0 ? 'L' : 'R'}`);
        if (o) this.arms.push([side, nm, o]);
      }
    }
    this.lidar = by(`${P}_lidar`);
    this.flag = by(`${P}_flag`);
    this.leds = {};
    for (const k of ['eyes', 'status', 'headlight', 'taillight']) {
      const o = by(`${P}_${k}`);
      if (o) this.leds[k] = ledify(o);
    }
    this.siren = by(`${P}_part_siren`);
    this.sirenMats = [];
    this.siren?.traverse((m) => {
      if (m.isMesh && m.material.name === 'SirenRed') {
        m.material = m.material.clone();
        m.material.emissive = new THREE.Color(1, 0.05, 0.03);
        this.sirenMats.push(m.material);
      }
    });
    this.r = kind === 'bharat' ? 0.16 : 0.09;
    this.top = 0.40;
    shadows(root);
    root.traverse((o) => { o.userData.robot = kind; });
  }

  pose(run, u, t) {
    const R = run.R;
    const L = (a) => run.lerp(a, u);
    this.root.visible = run.at(R.vis, u) > 0;
    this.root.position.set(L(R.x), L(R.z), -L(R.y));
    this.root.rotation.set(L(R.roll), L(R.h), L(R.pitch), 'YZX');
    this.hinge.rotation.z = L(R.lid) * 1.75 + Math.abs(L(R.lidj));
    const sL = L(R.spinL), sR = L(R.spinR);
    const dz = [0, 1, 2, 3, 4, 5].map((i) => L(R[`dz${i}`]));
    this.wheels.forEach((w, i) => { w.rotation.z = -(i < 3 ? sL : sR); w.position.set(this.wheelRest[i].x, dz[i], this.wheelRest[i].z); });
    for (const [side, nm, ob] of this.arms) {          // rocker-bogie bars between pivot, bogie joint and wheel hubs
      const o = side > 0 ? 0 : 3;
      const P = [0.06, 0.10], B = [-0.19, (dz[o + 1] + dz[o + 2]) / 2 + 0.07];
      const [A, C] = { rf: [P, [0.38, dz[o]]], rb: [P, B], bf: [B, [0, dz[o + 1]]], bb: [B, [-0.38, dz[o + 2]]] }[nm];
      ob.position.set((A[0] + C[0]) / 2, (A[1] + C[1]) / 2, -side * 0.30);
      ob.rotation.set(0, 0, -Math.atan2(-(C[1] - A[1]), C[0] - A[0]));
      ob.scale.set(Math.hypot(C[0] - A[0], C[1] - A[1]), 1, 1);
    }
    const v = L(R.v);
    if (this.lidar) this.lidar.rotation.y = t * TAU * 0.9;
    if (this.flag) this.flag.rotation.y = 0.25 * Math.sin(t * 7) + 0.6 * clamp(v, 0, 2) / 2;
    // lights: status strip by state, face lights dim around dogs, red/blue strobe in an alarm, brake lights
    const mode = run.at(R.mode, u);
    const alarm = run.at(R.alarm, u) > 0;
    const strobe = Math.floor(t * 8) % 2 === 0;
    const red = MODE_COLOURS.alarm;
    const { eyes, status, headlight, taillight } = this.leds;
    if (status) status.set(alarm ? (strobe ? red : [0.1, 0.2, 1.0]) : MODE_COLOURS[MODE_GROUP[mode] || 'go'], alarm ? 0.9 : 0.35);
    if (eyes) {
      const done = mode === 'DELIVERED';
      let c = [0.1, 0.85, 1.0], a = mode === 'DOG FREEZE' || mode === 'CREEP' ? 0.07 : 0.28;
      if (alarm) { c = red; a = strobe ? 0.7 : 0.1; }
      if (done) c = MODE_COLOURS.done;
      eyes.set(c, a);
      eyes.obj.scale.y = (t % 4.3) < 0.12 && !done ? 0.15 : 1;
    }
    const i = run.idx(u);
    const braking = i > 0 && R.v[i] - R.v[i - 1] < -0.012;
    if (taillight) taillight.set([1.0, 0.04, 0.02], braking || alarm ? 0.7 : 0.14);
    if (headlight) headlight.set([1.0, 0.95, 0.85], alarm ? (strobe ? 0.9 : 0) : 0.14);
    for (const m of this.sirenMats) m.emissiveIntensity = alarm && strobe ? 6 : 0;
    return { alarm, strobe, mode };
  }
}

// ── people: build_scene.animate_person ─────────────────────────────────────────────────────────────────────────
export class PersonRig {
  constructor(root) {
    this.root = root;
    const n = root.name;
    const by = (k) => root.getObjectByName(`${n}_${k}`);
    this.hip = by('hip');
    this.legs = [by('legL'), by('legR')];
    this.arms = [by('armL'), by('armR')];
    this.phone = by('phone');
    shadows(root);
  }
  pose(x, y, gz, h, ph, arm, grab, phone, wave, vs, vis, t) {
    this.root.visible = vis > 0.5;
    if (!this.root.visible) return;
    this.root.position.set(x, gz, -y);
    this.root.rotation.set(0, h, 0);
    const A = clamp(vs / 1.3, 0, 1) * (vs > 3 ? 0.75 : 0.48);
    const lean = 0.25 * arm + 0.6 * grab + (vs > 3 ? 0.25 : 0);
    this.hip.position.y = 0.92 - 0.22 * grab - 0.05 * arm + 0.03 * Math.abs(Math.cos(ph)) * A;
    this.hip.rotation.set(0, 0, -lean);
    [1, -1].forEach((sgn, k) => { this.legs[k].rotation.z = -(sgn * A * Math.sin(ph) - 0.35 * grab); });
    [1, -1].forEach((sgn, k) => {
      let ry = -0.8 * sgn * A * Math.sin(ph) * (1 - clamp(arm + grab, 0, 1)) - 1.15 * arm - 0.55 * grab;
      let rx = 0;
      if (sgn < 0) {
        ry = (ry * (1 - phone) - 1.25 * phone) * (1 - wave);
        rx = (-2.5 + 0.35 * Math.sin(t * 13)) * wave;
      }
      this.arms[k].rotation.set(rx, 0, -ry, 'YZX');
    });
    this.phone.scale.setScalar(Math.max(phone, 0.001));
  }
  poseFrom(run, ch, u, t, ground) {
    const L = (a) => run.lerp(a, u);
    const x = L(ch.x), y = L(ch.y);
    this.pose(x, y, ground(x, y), L(ch.h), L(ch.phase), L(ch.arm), L(ch.grab), L(ch.phone), L(ch.wave),
      run.avg(ch.v, u, 5), run.at(ch.vis, u), t);
  }
}

// ── auto-rickshaw ───────────────────────────────────────────────────────────────────────────────────────────────
export class AutoRig {
  constructor(root) {
    this.root = root;
    this.wheels = root.children.filter((o) => o.name.startsWith('AutoRickshaw_wheel'));
    const hl = root.getObjectByName('AutoRickshaw_headlight');
    if (hl) ledify(hl).set([1.0, 0.95, 0.8], 0.15);
    shadows(root);
  }
  pose(run, u, ground) {
    const A = run.auto;
    this.root.visible = run.at(A.active, u) > 0;
    if (!this.root.visible) return;
    const x = run.lerp(A.x, u), y = run.lerp(A.y, u);
    this.root.position.set(x, ground(x, y), -y);
    this.root.rotation.set(0, run.lerp(A.h, u), 0);
    const s = run.lerp(A.spin, u);
    for (const w of this.wheels) w.rotation.z = -s;
  }
}

// ── animals: the CC0 Quaternius rigs, their clips picked and timed as build_scene.animate_glb_dog does ─────────
class AnimalRig {
  constructor(gltf, scale) {
    this.root = new THREE.Group();
    const model = cloneSkinned(gltf.scene);
    model.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.frustumCulled = false;
      const ms = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of ms) { m.metalness = 0; m.roughness = 0.8; }
    });
    const holder = new THREE.Group();
    holder.rotation.y = Math.PI / 2;               // the models face +z; the simulation's heading 0 is +x
    holder.scale.setScalar(scale);
    holder.add(model);
    model.updateMatrixWorld(true);
    holder.position.y = -new THREE.Box3().setFromObject(model).min.y * scale;
    this.root.add(holder);
    this.root.userData.animal = true;
    this.mixer = new THREE.AnimationMixer(model);
    this.actions = {};
    for (const clip of gltf.animations) {
      const a = this.mixer.clipAction(clip);
      a.setLoop(THREE.LoopRepeat, Infinity);
      a.play();
      a.setEffectiveWeight(0);
      this.actions[clip.name] = a;
    }
  }
  mix(parts) {                                     // parts: [[clip, weight, time]]
    for (const a of Object.values(this.actions)) a.setEffectiveWeight(0);
    for (const [name, w, time] of parts) {
      const a = this.actions[name];
      if (!a || w <= 0) continue;
      a.setEffectiveWeight(w);
      a.time = ((time % a.getClip().duration) + a.getClip().duration) % a.getClip().duration;
    }
    this.mixer.update(0);
  }
}

// characters.GLB_DOGS: (model, scale, walk m/s at that scale, gallop m/s at that scale, resting clip)
const DOGS = [['shiba', 0.181, 0.42, 1.40, 'Eating'], ['husky', 0.185, 0.43, 1.50, 'Idle_2_HeadLow'], ['shiba', 0.168, 0.39, 1.30, 'Idle_2']];

export class DogRig extends AnimalRig {
  constructor(gltf, i) {
    const [, scale, walkV, runV, rest] = DOGS[i];
    super(gltf, scale);
    Object.assign(this, { i, walkV, runV, rest });
    this.root.traverse((o) => { o.userData.dog = i; });
  }
  // the clip on every frame of a run, short flickers absorbed (min 10 frames), as runs of [clip, first, last+1]
  prepare(run) {
    const D = run.dogs[this.i], n = run.n;
    const segs = [];
    for (let k = 0; k < n; k++) {
      let barking = false;
      for (let j = Math.max(0, k - 7); j <= Math.min(n - 1, k + 7); j++) if (D.bark[j] > 0.2) { barking = true; break; }
      const vs = run.avg(D.v, k, 9);
      const c = D.state[k] === 'REST' ? this.rest : vs >= 0.9 ? 'Gallop' : vs >= 0.15 ? 'Walk' : barking ? 'Attack' : 'Idle';
      if (segs.length && segs[segs.length - 1][0] === c) segs[segs.length - 1][2] = k + 1;
      else segs.push([c, k, k + 1]);
    }
    const merged = [];
    for (const s of segs) {
      if (merged.length && (s[2] - s[1] < 10 || merged[merged.length - 1][0] === s[0])) merged[merged.length - 1][2] = s[2];
      else merged.push([...s]);
    }
    if (merged.length > 1 && merged[0][2] - merged[0][1] < 10) { merged[1][1] = 0; merged.shift(); }
    this.segs = merged;
  }
  clipTime(name, run, u, t) {
    if (name === 'Walk' || name === 'Gallop') {     // locked to the distance walked: no foot sliding, scrubs exactly
      const dist = run.lerp(run.dogs[this.i].phase, u) / TAU * 0.62;
      return dist / (name === 'Walk' ? this.walkV : this.runV);
    }
    return t + this.i * 1.7;
  }
  pose(run, u, t, ground) {
    const D = run.dogs[this.i];
    const x = run.lerp(D.x, u), y = run.lerp(D.y, u);
    this.root.position.set(x, ground(x, y), -y);
    this.root.rotation.set(0, run.lerp(D.h, u), 0);
    const k = run.idx(u);
    let s = this.segs.findIndex((g) => k >= g[1] && k < g[2]);
    if (s < 0) s = this.segs.length - 1;
    const cur = this.segs[s];
    const w = s > 0 ? clamp((u - cur[1]) / 6, 0, 1) : 1;
    const parts = [[cur[0], w, this.clipTime(cur[0], run, u, t)]];
    if (w < 1) parts.push([this.segs[s - 1][0], 1 - w, this.clipTime(this.segs[s - 1][0], run, u, t)]);
    this.mix(parts);
    return run.lerp(D.bark, u);
  }
}

export class CowRig extends AnimalRig {
  constructor(gltf) { super(gltf, 0.294); }
  place(x, y, h, ground) { this.root.position.set(x, ground(x, y), -y); this.root.rotation.set(0, h, 0); }
  pose(t) { this.mix([['Eating', 1, t]]); }
}

// build_scene.walker_rows, walking the way they face (the film's passer-by on the far pavement walks backwards)
export function walker(t, y, speed, xMin, xMax, phase0) {
  const span = xMax - xMin;
  const d = (((Math.abs(speed) * t + phase0) % span) + span) % span;
  return { x: speed > 0 ? xMin + d : xMax - d, y, h: speed > 0 ? 0 : Math.PI, ph: Math.abs(speed) * t / 1.25 * TAU, v: Math.abs(speed) };
}
