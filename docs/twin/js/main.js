// Bharat-Bot digital twin — main: loading, the 3D street, playback of the simulation runs, cameras, clicking the robot,
// and the controls. Every pose comes from the Python simulation (sim/export_twin.py); nothing here simulates.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Street, terrainMaterial, wallMaterial, waterMaterial } from './terrain.js';
import { loadRun } from './run.js';
import { RobotRig, PersonRig, AutoRig, DogRig, CowRig, walker } from './actors.js';
import { FX } from './fx.js';
import { HUD } from './hud.js';
import { Explode } from './explode.js';
import { Sound, Narrator } from './audio.js';

const $ = (s) => document.querySelector(s);
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const params = new URLSearchParams(location.search);
const MOBILE = matchMedia('(max-width: 820px)').matches;
const T0 = performance.now();
const stats = { fps: 0, frameMs: 0, loadMs: 0, pixelRatio: 1, terrainCheck: null, gpu: '' };

// which run (and which stretch of it) each button plays: Bharat-Bot's handling of a single test is cut from its full run
const TESTS = {
  full: { bharat: ['bharat_full', null], baseline: ['baseline_full', null] },
  pothole: { bharat: ['bharat_full', 'pothole'], baseline: ['baseline_pothole', null] },
  dogs: { bharat: ['bharat_full', 'dogs'], baseline: ['baseline_dogs', null] },
  theft: { bharat: ['bharat_full', 'theft'], baseline: ['baseline_theft', null] },
};
const ORDER = ['full', 'pothole', 'dogs', 'theft'];

// ── renderer, scene, camera ───────────────────────────────────────────────────────────────────────────────────
const canvas = $('#c');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
} catch (e) {
  $('#ld-step').textContent = 'This browser cannot show 3D (WebGL is off or unsupported). The project page has the film and results.';
  throw e;
}
{
  const gl = renderer.getContext();
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  stats.gpu = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : '';
}
renderer.toneMapping = THREE.NeutralToneMapping;   // keeps the film's saturated signage and saffron
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.autoUpdate = false;          // redrawn every other frame (see frame())
const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xc7d3df, 55, 190);
const camera = new THREE.PerspectiveCamera(MOBILE ? 58 : 48, innerWidth / innerHeight, 0.05, 420);
camera.position.set(-6, 3, 6);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.09;
controls.maxPolarAngle = Math.PI * 0.495;
controls.minDistance = 0.5;
controls.maxDistance = 80;
controls.target.set(0, 0.4, -5);
const sound = new Sound(camera);
const narrator = new Narrator((speaking) => sound.ducking(speaking));
// sound settings: the master switch, and effects / music / voice one by one (remembered on this device)
let soundOn = true;
const aud = { fx: true, music: true, voice: true, voiceName: '' };
try {
  soundOn = localStorage.getItem('bb-sound') !== '0';
  Object.assign(aud, JSON.parse(localStorage.getItem('bb-audio') || '{}'));
} catch (e) { /* storage blocked */ }
function applyAudio() {
  sound.set('master', soundOn);
  sound.set('fx', aud.fx);
  sound.set('music', aud.music);
  narrator.on = soundOn && aud.voice;
  if (!narrator.on) narrator.stop();
  narrator.setVoice(aud.voiceName);
  for (const id of ['#sndbtn', '#msnd']) {
    const b = $(id);
    if (b) { b.setAttribute('aria-pressed', soundOn); b.textContent = id === '#msnd' ? (soundOn ? '🔊' : '🔇') : (soundOn ? '🔊 Sound' : '🔇 Muted'); }
  }
  for (const b of document.querySelectorAll('[data-snd]')) {
    b.setAttribute('aria-pressed', aud[b.dataset.snd]);
    b.hidden = b.dataset.snd === 'voice' && !narrator.ok;
  }
  try {
    localStorage.setItem('bb-sound', soundOn ? '1' : '0');
    localStorage.setItem('bb-audio', JSON.stringify(aud));
  } catch (e) { /* storage blocked */ }
}
function setSound(on) { soundOn = on; applyAudio(); }
// the voice picker in Help: the device's English voices, Indian English first
function fillVoices() {
  const sel = $('#voicepick');
  if (!narrator.ok) { sel.closest('label').hidden = true; return; }
  const vs = narrator.english().sort((a, b) => (/en[-_]IN/i.test(b.lang) - /en[-_]IN/i.test(a.lang)) || a.name.localeCompare(b.name));
  sel.innerHTML = vs.map((v) => `<option value="${v.name.replace(/"/g, '&quot;')}">${v.name.replace(/</g, '&lt;')}</option>`).join('');
  if (narrator.voice) sel.value = narrator.voice.name;
}
applyAudio();

const SUN_DIR = new THREE.Vector3(0.426, 0.669, 0.609).normalize();   // build_scene.lighting's sun, in three.js axes
const sun = new THREE.DirectionalLight(0xfff1df, 2.7);
sun.castShadow = true;
sun.shadow.camera.left = sun.shadow.camera.bottom = -17;
sun.shadow.camera.right = sun.shadow.camera.top = 17;
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 90;
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.025;
scene.add(sun, sun.target);
scene.add(new THREE.HemisphereLight(0xd6e6ff, 0x75604c, 0.55));

let HQ = false;
try { HQ = localStorage.getItem('bb-hq') === '1'; } catch (e) { /* storage blocked */ }
let PR = 1;
function applyQuality() {
  PR = HQ ? Math.min(devicePixelRatio, 2) : Math.min(devicePixelRatio, MOBILE ? 1.5 : 1);
  renderer.setPixelRatio(PR);
  renderer.setSize(innerWidth, innerHeight, false);
  const ms = HQ ? 4096 : MOBILE ? 1024 : 2048;
  sun.shadow.mapSize.set(ms, ms);
  if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; }
  const type = HQ ? THREE.PCFSoftShadowMap : THREE.PCFShadowMap;
  if (renderer.shadowMap.type !== type) {
    renderer.shadowMap.type = type;
    scene.traverse((o) => { if (o.material) for (const m of [].concat(o.material)) m.needsUpdate = true; });
  }
  renderer.shadowMap.needsUpdate = true;
  $('#hqbtn').setAttribute('aria-pressed', HQ);
  stats.pixelRatio = PR;
}
applyQuality();
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight, false);
  if (P.run) hud.buildRoute();
});

// ── loading ──────────────────────────────────────────────────────────────────────────────────────────────────
const draco = new DRACOLoader().setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/');
const gltfLoader = new GLTFLoader().setDRACOLoader(draco);
const texLoader = new THREE.TextureLoader();
const KB = { street: 810, robots: 75, people: 94, auto: 43, dog_shiba: 407, dog_husky: 432, cow: 403, tex: 1370, sky: 380, data: 460 };
const got = {};
const total = Object.values(KB).reduce((a, b) => a + b, 0);
let failed = false;
function progress(key, frac, msg) {
  if (failed) return;
  got[key] = Math.max(got[key] || 0, clamp(frac, 0, 1) * KB[key]);
  const sum = Object.values(got).reduce((a, b) => a + b, 0);
  $('#ld-bar').style.width = `${Math.round((sum / total) * 100)}%`;
  if (msg) $('#ld-step').textContent = msg;
}
// a busy phone or a flaky connection can drop a download: try each file three times before giving up
async function retry(fn, tries = 3) {
  for (let i = 0; ; i++) {
    try { return await fn(); } catch (e) {
      if (i + 1 >= tries || failed) throw e;
      await new Promise((r) => setTimeout(r, 700 * (i + 1)));
    }
  }
}
function glb(name, label) {
  return retry(() => gltfLoader.loadAsync(`models/${name}.glb`, (e) => progress(name, e.total ? e.loaded / e.total : 0.5, `Loading ${label}…`)))
    .then((g) => { progress(name, 1); return g; });
}
function texture(file, srgb = true) {
  return retry(() => new Promise((res, rej) => texLoader.load(`models/tex/${file}`, (t) => {
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    res(t);
  }, undefined, rej)));
}
async function loadTextures() {
  const files = [['asphalt', 'asphalt_02_diff.jpg'], ['asphaltN', 'asphalt_02_nor_gl.jpg', false], ['damaged', 'road_damaged_2_diff.jpg'],
    ['dirt', 'red_laterite_soil_stones_diff.jpg'], ['dirtN', 'red_laterite_soil_stones_nor_gl.jpg', false], ['mud', 'red_dirt_mud_01_diff.jpg'],
    ['plaster', 'painted_plaster_wall_diff.jpg']];
  const out = {};
  let n = 0;
  await Promise.all(files.map(([k, f, srgb]) => texture(f, srgb !== false).then((t) => { out[k] = t; progress('tex', ++n / files.length); })));
  return out;
}
async function loadSky() {
  const [bg, hdr] = await Promise.all([
    retry(() => new Promise((res, rej) => texLoader.load('models/sky.jpg', res, undefined, rej))),
    retry(() => new RGBELoader().loadAsync('models/sky.hdr')),
  ]);
  progress('sky', 1);
  bg.mapping = THREE.EquirectangularReflectionMapping;
  bg.colorSpace = THREE.SRGBColorSpace;
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  const pm = new THREE.PMREMGenerator(renderer);
  const env = pm.fromEquirectangular(hdr).texture;
  hdr.dispose();
  pm.dispose();
  return { bg, env };
}
const fetchJSON = (url) => retry(() => fetch(url).then((r) => { if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`); return r.json(); }));

// ── the world ────────────────────────────────────────────────────────────────────────────────────────────────
let street, rigs, parcel, dogs, cow, thief, customer, walkers, autoRig, fx;
const hud = new HUD();

function buildStreet(sd, tex, gStreet) {
  street = new Street(sd);
  stats.terrainCheck = street.selfCheck();
  if (stats.terrainCheck > 1e-6) console.warn('terrain differs from the simulation by', stats.terrainCheck, 'm');
  const terrain = new THREE.Mesh(street.buildMesh(MOBILE ? 0.1 : 0.075), terrainMaterial(tex, sd.speedBreaker.x0));
  terrain.receiveShadow = true;
  terrain.name = 'terrain';
  scene.add(terrain);
  const under = new THREE.Mesh(new THREE.PlaneGeometry(500, 500), new THREE.MeshStandardMaterial({ color: 0x7d6656, roughness: 1 }));
  under.rotation.x = -Math.PI / 2;
  under.position.y = -0.04;
  under.receiveShadow = true;
  scene.add(under);
  const wall = wallMaterial(tex.plaster);
  const water = waterMaterial();
  gStreet.scene.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = o.receiveShadow = true;
    const n = o.material.name;
    if (n === 'vc_Wall') o.material = wall;
    else if (n === 'Water') { o.material = water; o.castShadow = false; }
    else if (n === 'RoadPaint') Object.assign(o.material, { polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
    else if (n === 'D_glass' || n === 'Glass') o.material.envMapIntensity = 1.6;
  });
  const back = gStreet.scene.getObjectByName('Backdrop');
  back?.traverse((o) => { if (o.isMesh) o.castShadow = false; });
  scene.add(gStreet.scene);
  return water;
}

function buildActors(g) {
  const take = (gl, name) => { const o = gl.scene.getObjectByName(name); scene.add(o); return o; };
  rigs = { bharat: new RobotRig(take(g.robots, 'BharatBot'), 'bharat'), baseline: new RobotRig(take(g.robots, 'StdBot'), 'baseline') };
  parcel = take(g.robots, 'Parcel');
  parcel.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  thief = new PersonRig(take(g.people, 'Thief'));
  customer = new PersonRig(take(g.people, 'Customer'));
  walkers = [new PersonRig(take(g.people, 'Walker0')), new PersonRig(take(g.people, 'Walker1'))];
  autoRig = new AutoRig(take(g.auto, 'AutoRickshaw'));
  dogs = [new DogRig(g.shiba, 0), new DogRig(g.husky, 1), new DogRig(g.shiba, 2)];
  for (const d of dogs) scene.add(d.root);
  cow = new CowRig(g.cow);
  scene.add(cow.root);
  const [cx, cy, ch] = street.d.places.cow;
  cow.place(cx, cy, ch, ground);
  fx = new FX(scene, street, $('#tags'));
  fx.attachRobot(rigs.bharat);
  fx.attachRobot(rigs.baseline);
  for (const d of dogs) fx.attachDog(d);
}
const ground = (x, y) => street.height(x, y);

// ── playback ─────────────────────────────────────────────────────────────────────────────────────────────────
const P = { test: 'full', robot: 'bharat', run: null, clip: [0, 0], t: 0, playing: false, speed: 1, ended: false, started: false };
let selectSeq = 0;
async function select(test, robot, { keepCamera = false } = {}) {
  const seq = ++selectSeq;
  const [name, win] = TESTS[test][robot];
  let run;
  try {
    run = await loadRun(name);
  } catch (e) {
    $('#caption').textContent = `Could not load ${name}: ${e.message}`;
    $('#caption').classList.remove('fade');
    return;
  }
  if (seq !== selectSeq) return;
  explode.close(true);
  narrator.stop();
  Object.assign(P, { test, robot, run, clip: win ? run.windows[win] : [0, run.n - 1], t: 0, ended: false });
  lastU = P.clip[0];
  spokenKey = null;
  spokenText = '';
  for (const d of dogs) d.prepare(run);
  rigs.bharat.root.visible = robot === 'bharat';
  rigs.baseline.root.visible = robot === 'baseline';
  fx.setRun(run);
  hud.setRun(run, P.clip, test, robot);
  for (const b of document.querySelectorAll('#tests [data-test]')) b.setAttribute('aria-pressed', b.dataset.test === test);
  for (const b of document.querySelectorAll('#robots [data-robot]')) b.setAttribute('aria-pressed', b.dataset.robot === robot);
  $('#robotnote').textContent = robot === 'bharat'
    ? 'Bharat-Bot, the India-adapted design. Switch to see a standard robot on the same street.'
    : 'A standard US-style sidewalk robot: small wheels, no pothole sensing, no dog or theft protocol.';
  try {
    const q = new URLSearchParams(location.search);
    q.set('test', test);
    q.set('robot', robot);
    history.replaceState(null, '', `?${q}`);
  } catch (e) { /* file:// */ }
  poseAll(P.clip[0]);
  if (!keepCamera) setCam(cam.mode === 'orbit' ? 'follow' : cam.mode, true);
  setPlaying(P.started);
}
function setPlaying(on) {
  P.playing = on;
  if (!on) narrator.stop();
  $('#playbtn').innerHTML = on ? '&#10074;&#10074;' : '&#9654;';
  $('#playbtn').setAttribute('aria-label', on ? 'Pause' : 'Play');
  if (on) hud.hideResult();
}
function togglePlay() {
  if (!P.run) return;
  if (explode.open) explode.close();
  if (P.ended) { P.t = 0; P.ended = false; lastU = P.clip[0]; }
  setPlaying(!P.playing);
}
function seek(t) {
  if (!P.run) return;
  const dur = (P.clip[1] - P.clip[0]) / P.run.fps;
  P.t = clamp(t, 0, dur);
  lastU = P.clip[0] + P.t * P.run.fps;            // a jump: no sounds for the frames skipped
  if (P.t < dur) { P.ended = false; hud.hideResult(); }
}
function setSpeed(s) {
  P.speed = s;
  for (const b of document.querySelectorAll('[data-speed]')) b.setAttribute('aria-pressed', +b.dataset.speed === s);
  $('#mspeed').textContent = `${s}×`;
}
const activeRig = () => rigs[P.robot];

function poseAll(u) {
  const run = P.run, t = u / run.fps;
  const rig = activeRig();
  const info = rig.pose(run, u, t);
  if (run.bag) {
    parcel.visible = true;
    parcel.position.set(run.lerp(run.bag.x, u), run.lerp(run.bag.z, u), -run.lerp(run.bag.y, u));
    parcel.rotation.set(0, run.lerp(run.R.h, u), 0);
  } else parcel.visible = false;
  for (const d of dogs) d.pose(run, u, t, ground);
  cow.pose(t);
  thief.poseFrom(run, run.thief, u, t, ground);
  customer.poseFrom(run, run.cust, u, t, ground);
  [[-5.0, -1.15, 10.0], [-5.35, 0.95, 30.0]].forEach(([y, sp, ph0], i) => {
    const w = walker(t, y, sp, -10, 78, ph0);
    walkers[i].pose(w.x, w.y, ground(w.x, w.y), w.h, w.ph, 0, 0, 0, 0, w.v, 1, t);
  });
  autoRig.pose(run, u, ground);
  return info;
}

// ── cameras: follow modes ride along with the robot (drag still orbits), static ones stay put ───────────────────
const cam = { mode: 'follow', fly: null, rel: null };
const FOLLOW = ['follow', 'top', 'low'];
const CAMS = ['follow', 'orbit', 'street', 'top', 'low'];
const CAM_NAMES = { follow: 'Follow', orbit: 'Free', street: 'Street', top: 'Top', low: 'Ground' };
function focus() {
  return new THREE.Vector3(0, 0.3, 0).applyMatrix4(activeRig().root.matrixWorld);
}
function fly(pos, target, dur = 1.1) { cam.rel = null; cam.fly = { p0: camera.position.clone(), t0: controls.target.clone(), p1: pos.clone(), t1: target.clone(), k: 0, dur }; }
function setCam(mode, snap = false) {
  cam.mode = mode;
  for (const b of document.querySelectorAll('#cams [data-cam]')) b.setAttribute('aria-pressed', b.dataset.cam === mode);
  $('#mcam').textContent = CAM_NAMES[mode];
  const rig = activeRig();
  rig.root.updateMatrixWorld(true);
  const f = focus();
  const h = rig.root.rotation.y;
  const fwd = new THREE.Vector3(Math.cos(h), 0, -Math.sin(h)), right = new THREE.Vector3(Math.sin(h), 0, Math.cos(h));
  const far = MOBILE ? 1.35 : 1;
  let off = null;
  if (mode === 'follow') off = fwd.clone().multiplyScalar(-3.0 * far).addScaledVector(right, 2.0 * far).add(new THREE.Vector3(0, 1.2 * far, 0));
  if (mode === 'top') off = new THREE.Vector3(0, 15, 0.02);
  if (mode === 'low') off = fwd.clone().multiplyScalar(4.2).addScaledVector(right, 1.0).add(new THREE.Vector3(0, -0.05, 0));
  if (off) {
    cam.fly = null;
    if (snap) { controls.target.copy(f); camera.position.copy(f).add(off); cam.rel = null; } else cam.rel = { o0: camera.position.clone().sub(controls.target), o1: off, k: 0, dur: 1.1 };
    return;
  }
  if (mode === 'street') {
    const R = P.run.R;
    let lo = Infinity, hi = -Infinity;
    for (let i = P.clip[0]; i <= P.clip[1]; i++) { lo = Math.min(lo, R.x[i]); hi = Math.max(hi, R.x[i]); }
    // from high above the centre line at the near end, looking down the street (the shop rows can't block it)
    const mid = (lo + hi) / 2, span = Math.max(12, hi - lo);
    const t = new THREE.Vector3(mid, 0, -1.5);
    fly(t.clone().add(new THREE.Vector3(-span * 0.42 - 3, span * 0.38 + 7, 2.5)), t, snap ? 0.01 : 1.2);
  }
}
function updateCamera(dt) {
  if (cam.fly) {
    const F = cam.fly;
    F.k = Math.min(1, F.k + dt / F.dur);
    const e = ease(F.k);
    camera.position.lerpVectors(F.p0, F.p1, e);
    controls.target.lerpVectors(F.t0, F.t1, e);
    if (F.k >= 1) cam.fly = null;
    return;
  }
  if (explode.open || !FOLLOW.includes(cam.mode)) return;
  const f = focus();
  if (cam.rel) {
    const R = cam.rel;
    R.k = Math.min(1, R.k + dt / R.dur);
    const off = R.o0.clone().lerp(R.o1, ease(R.k));
    controls.target.copy(f);
    camera.position.copy(f).add(off);
    if (R.k >= 1) cam.rel = null;
    return;
  }
  const d = f.clone().sub(controls.target).multiplyScalar(1 - Math.exp(-dt * 9));
  controls.target.add(d);
  camera.position.add(d);
}

// ── explode view, picking ─────────────────────────────────────────────────────────────────────────────────────
let wasPlaying = false;
const explode = new Explode({
  camera, controls, fly, fitDistance: (r) => fitDistance(r),
  pause: () => { wasPlaying = P.playing; setPlaying(false); },
  resume: () => { if (wasPlaying && !P.ended) setPlaying(true); },
  setFocus: (on) => {
    $('#app').classList.toggle('focus', on);
    narrator.stop();
    if (on) sound.ui('whoosh', 0.22);
  },
  onPick: (part) => { narrator.stop(); narrator.say(`${part.name}. ${part.text}`); },   // the voice explains a clicked part
});
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
function pickRobot(x, y) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const rig = activeRig();
  const meshes = [];
  rig.root.traverse((o) => { if (o.isMesh && o.visible) meshes.push(o); });
  return ray.intersectObjects(meshes, false)[0]?.object || null;
}
const pointer = { x: 0, y: 0, down: null, moved: false };
canvas.addEventListener('pointerdown', (e) => { pointer.down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
canvas.addEventListener('pointermove', (e) => { pointer.x = e.clientX; pointer.y = e.clientY; pointer.moved = true; });
canvas.addEventListener('pointerleave', () => { $('#hint').hidden = true; });
canvas.addEventListener('pointerup', (e) => {
  const d = pointer.down;
  pointer.down = null;
  if (!d || Math.hypot(e.clientX - d.x, e.clientY - d.y) > 6 || performance.now() - d.t > 600 || !P.run) return;
  const hit = pickRobot(e.clientX, e.clientY);
  if (explode.open) {
    if (hit) explode.highlight(explode.partOf(hit), true);
    else explode.close();
    return;
  }
  if (hit) explode.show(activeRig());
});
let hoverTick = 0;
function updateHover() {
  if (!pointer.moved || pointer.down || MOBILE || ++hoverTick % 3) return;
  pointer.moved = false;
  const hit = P.run ? pickRobot(pointer.x, pointer.y) : null;
  const hint = $('#hint');
  canvas.style.cursor = hit ? 'pointer' : '';
  if (explode.open) {
    if (hit) explode.highlight(explode.partOf(hit));
    hint.hidden = true;
    return;
  }
  hint.hidden = !hit;
  if (hit) {
    hint.textContent = `${P.robot === 'bharat' ? 'Bharat-Bot' : 'Standard robot'}: click to take it apart`;
    hint.style.left = `${pointer.x}px`;
    hint.style.top = `${pointer.y}px`;
  }
}

// ── controls ─────────────────────────────────────────────────────────────────────────────────────────────────
for (const b of document.querySelectorAll('#tests [data-test]')) {
  b.addEventListener('click', () => {
    if (b.dataset.test === 'replay') { seek(0); setPlaying(true); return; }
    select(b.dataset.test, P.robot);
  });
}
for (const b of document.querySelectorAll('#robots [data-robot]')) b.addEventListener('click', () => select(P.test, b.dataset.robot));
for (const b of document.querySelectorAll('[data-speed]')) b.addEventListener('click', () => setSpeed(+b.dataset.speed));
for (const b of document.querySelectorAll('#cams [data-cam]')) b.addEventListener('click', () => setCam(b.dataset.cam));
$('#playbtn').addEventListener('click', togglePlay);
$('#sndbtn').addEventListener('click', () => { sound.start({ rigs, dogs, cow, auto: autoRig }); setSound(!soundOn); });
$('#msnd').addEventListener('click', () => { sound.start({ rigs, dogs, cow, auto: autoRig }); setSound(!soundOn); });
for (const b of document.querySelectorAll('[data-snd]')) {
  b.addEventListener('click', () => {
    sound.start({ rigs, dogs, cow, auto: autoRig });
    aud[b.dataset.snd] = !aud[b.dataset.snd];
    if (aud[b.dataset.snd] && !soundOn) soundOn = true;      // switching one part on also unmutes
    applyAudio();
  });
}
$('#voicepick').addEventListener('change', (e) => {
  aud.voiceName = e.target.value;
  applyAudio();
  narrator.stop();
  narrator.say('This voice will read the captions.');
});
document.addEventListener('visibilitychange', () => { if (document.hidden) { sound.pause(); narrator.stop(); } else sound.resume(); });
$('#mspeed').addEventListener('click', () => setSpeed({ 1: 2, 2: 4, 4: 1 }[P.speed]));
$('#mcam').addEventListener('click', () => setCam(CAMS[(CAMS.indexOf(cam.mode) + 1) % CAMS.length]));
$('#mlog').addEventListener('click', () => {
  const on = $('#mlog').getAttribute('aria-pressed') !== 'true';
  $('#mlog').setAttribute('aria-pressed', on);
  $('#feed').classList.toggle('mshow', on);
});
const scrub = $('#scrub');
scrub.addEventListener('pointerdown', () => { hud.scrubbing = true; });
scrub.addEventListener('input', () => {
  hud.scrubbing = true;
  seek((scrub.value / 1000) * (P.clip[1] - P.clip[0]) / P.run.fps);
});
scrub.addEventListener('change', () => { hud.scrubbing = false; });
addEventListener('pointerup', () => { hud.scrubbing = false; });
$('#hqbtn').addEventListener('click', () => {
  HQ = !HQ;
  try { localStorage.setItem('bb-hq', HQ ? '1' : '0'); } catch (e) { /* storage blocked */ }
  applyQuality();
});
const help = (on) => { $('#help').hidden = !on; if (on) { fillVoices(); $('#help-ok').focus(); } };
$('#helpbtn').addEventListener('click', () => help(true));
$('#mhelp').addEventListener('click', () => help(true));
$('#help-ok').addEventListener('click', () => help(false));
$('#help').addEventListener('click', (e) => { if (e.target.id === 'help') help(false); });
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' && e.code !== 'Space') return;
  if (!P.started) return;
  if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
  else if (e.code === 'ArrowLeft') seek(P.t - 5);
  else if (e.code === 'ArrowRight') seek(P.t + 5);
  else if (e.code === 'Digit1') setSpeed(1);
  else if (e.code === 'Digit2') setSpeed(2);
  else if (e.code === 'Digit4') setSpeed(4);
  else if (e.code === 'KeyC') setCam(CAMS[(CAMS.indexOf(cam.mode) + 1) % CAMS.length]);
  else if (e.code === 'KeyM') setSound(!soundOn);
  else if (e.code === 'KeyH' || e.key === '?') help($('#help').hidden);
  else if (e.code === 'Escape') { if (!$('#help').hidden) help(false); else explode.close(); }
});

// ── frame loop ───────────────────────────────────────────────────────────────────────────────────────────────
let last = performance.now(), waterMat = null, fpsAcc = 0, fpsN = 0, fpsT = 0, slow = 0, lastU = 0, spokenKey = null, spokenText = '';
function frame(now) {
  requestAnimationFrame(frame);
  tick(now);
}
function tick(now) {
  const dt = Math.max(0, Math.min(0.1, (now - last) / 1000));
  last = now;
  if (!P.run) return;
  const run = P.run, fps = run.fps, dur = (P.clip[1] - P.clip[0]) / fps;
  if (P.playing) {
    P.t += dt * P.speed;
    if (P.t >= dur) {
      P.t = dur;
      setPlaying(false);
      if (!P.ended) {
        P.ended = true;
        const said = hud.showResult(() => { seek(0); setPlaying(true); },
          () => select(P.test, P.robot === 'bharat' ? 'baseline' : 'bharat'),
          () => select(ORDER[(ORDER.indexOf(P.test) % 3) + 1], P.robot));
        narrator.say(said);
      }
    }
  }
  const u = P.clip[0] + P.t * fps;
  const prevU = lastU;
  lastU = u;
  const info = poseAll(u);
  explode.update(dt);
  const rig = activeRig();
  rig.root.updateMatrixWorld(true);
  fx.update(run, u, u / fps, rig, dogs, info, camera, innerWidth, innerHeight);
  updateCamera(dt);
  controls.update();
  fx.runFX.visible = !explode.open;
  for (const s of rig.fx.sensors || []) s.visible = !explode.open;
  applyViewOffset(dt);
  // the sun's shadow box follows the view, snapped to whole shadow-map texels so edges don't shimmer
  const tg = controls.target;
  const texel = (sun.shadow.camera.right - sun.shadow.camera.left) / sun.shadow.mapSize.x;
  const sx = Math.round(tg.dot(LIGHT_X) / texel) * texel, sy = Math.round(tg.dot(LIGHT_Y) / texel) * texel, sz = tg.dot(LIGHT_Z);
  sun.target.position.copy(LIGHT_X).multiplyScalar(sx).addScaledVector(LIGHT_Y, sy).addScaledVector(LIGHT_Z, sz);
  sun.position.copy(sun.target.position).addScaledVector(SUN_DIR, 45);
  if (++shadowTick % 2 === 0 || !P.playing) renderer.shadowMap.needsUpdate = true;
  if (waterMat) waterMat.userData.time.value = now / 1000;
  const caption = hud.update(run, u, u / fps, P.playing);
  // the voice reads each caption once, while it plays normally (not while scrubbing or after a jump, not at 4x); a
  // caption that appeared while paused (the opening line before Start) is read when play begins
  if (caption && caption.key !== spokenKey && P.playing && P.speed < 4 && !hud.scrubbing && Math.abs(u - prevU) < 45) {
    spokenKey = caption.key;
    if (caption.text !== spokenText) narrator.say(caption.text, P.speed > 1 ? 1.35 : 1.02);
    spokenText = caption.text;
  }
  sound.update({ run, u, prevU, playing: P.playing, rig, explode: explode.open });
  updateHover();
  renderer.render(scene, camera);
  // frame rate (shown with ?debug). If frames come slowly but steadily (a busy GPU, not a hidden tab that the browser
  // throttles), drop the resolution a notch, down to 0.8
  fpsAcc += dt; fpsN++;
  if (fpsAcc >= 1) {
    stats.fps = Math.round(fpsN / fpsAcc);
    stats.frameMs = +(1000 * fpsAcc / fpsN).toFixed(1);
    const busy = stats.frameMs > 24 && stats.frameMs < 70;
    if (!HQ && busy && PR > 0.8 && ++fpsT > 3 && !document.hidden) {
      if (++slow >= 3) { PR = Math.max(0.8, +(PR - 0.1).toFixed(2)); renderer.setPixelRatio(PR); stats.pixelRatio = PR; slow = 0; }
    } else slow = 0;
    if (params.has('debug')) { $('#fps').hidden = false; $('#fps').textContent = `${stats.fps} fps · ${stats.frameMs} ms · ${renderer.info.render.calls} draws · ${(renderer.info.render.triangles / 1000).toFixed(0)}k tris · pr ${PR}`; }
    fpsAcc = 0; fpsN = 0;
  }
}
// shadow-camera axes (the light looks along -SUN_DIR)
const LIGHT_Z = SUN_DIR.clone().negate();
const LIGHT_X = new THREE.Vector3().crossVectors(LIGHT_Z, new THREE.Vector3(0, 1, 0)).normalize();
const LIGHT_Y = new THREE.Vector3().crossVectors(LIGHT_X, LIGHT_Z).normalize();
let shadowTick = 0;

// with the parts panel open, shift the picture so the robot sits in the free part of the screen
let offK = 0;
function panelSize() {
  return MOBILE ? { w: 0, h: innerHeight * 0.52 + 12 } : { w: Math.min(400, innerWidth * 0.4) + 20, h: 0 };
}
function applyViewOffset(dt) {
  const want = explode.open ? 1 : 0;
  if (offK === want && !want) return;
  offK = want ? Math.min(1, offK + dt / 0.45) : Math.max(0, offK - dt / 0.45);
  const k = ease(offK), p = panelSize(), W = innerWidth, H = innerHeight;
  if (k <= 0) { camera.clearViewOffset(); return; }
  if (MOBILE) camera.setViewOffset(W, H + p.h * k, 0, p.h * k, W, H);
  else camera.setViewOffset(W + p.w * k, H, p.w * k, 0, W, H);
}
// camera distance that fits a sphere of radius r in the part of the screen the panel leaves free
function fitDistance(r) {
  const p = panelSize(), W = innerWidth, H = innerHeight, tv = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const tanV = MOBILE ? tv * (H - p.h) / (H + p.h) : tv;
  const tanH = MOBILE ? tv * W / (H + p.h) : tv * (W - p.w) / H;
  return (r / Math.sin(Math.atan(Math.min(tanV, tanH)))) * 1.04;
}

// ── boot ─────────────────────────────────────────────────────────────────────────────────────────────────────
(async function boot() {
  try {
    const [sd, tex, sky, gStreet, robots, people, auto, shiba, husky, cowG] = await Promise.all([
      fetchJSON('data/street.json'), loadTextures(), loadSky(),
      glb('street', 'the street'), glb('robots', 'the robots'), glb('people', 'people'), glb('auto', 'the auto-rickshaw'),
      glb('dog_shiba', 'street dogs'), glb('dog_husky', 'street dogs'), glb('cow', 'the cow'),
    ]);
    $('#ld-step').textContent = 'Building the street…';
    scene.background = sky.bg;
    scene.environment = sky.env;
    scene.environmentIntensity = 0.75;
    waterMat = buildStreet(sd, tex, gStreet);
    buildActors({ robots, people, auto, shiba, husky, cow: cowG });
    sound.load().catch((e) => console.warn('sound could not load:', e));   // in the background; the twin works without it
    const test = TESTS[params.get('test')] ? params.get('test') : 'full';
    const robot = ['bharat', 'baseline'].includes(params.get('robot')) ? params.get('robot') : 'bharat';
    await select(test, robot);
    progress('data', 1);
    renderer.compile(scene, camera);
    stats.loadMs = Math.round(performance.now() - T0);
    requestAnimationFrame(frame);
    $('#ld-step').textContent = `Ready in ${(stats.loadMs / 1000).toFixed(1)} s.`;
    const go = $('#ld-start');
    go.hidden = false;
    go.focus();
    const start = () => {
      $('#loading').classList.add('done');
      setTimeout(() => { $('#loading').hidden = true; }, 900);
      P.started = true;
      sound.start({ rigs, dogs, cow, auto: autoRig });   // inside the click, so the browser lets sound play
      narrator.unlock();
      applyAudio();
      setPlaying(true);
      for (const n of ['bharat_full', 'baseline_full', 'baseline_pothole', 'baseline_dogs', 'baseline_theft']) loadRun(n).catch(() => {});
    };
    go.addEventListener('click', start, { once: true });
    if (params.has('autostart')) start();
  } catch (e) {
    console.error(e);
    failed = true;
    $('#ld-step').textContent = `Could not load the twin (${e.message || e}). Check your connection, close other tabs if memory is short, and try again.`;
    const again = $('#ld-start');
    again.textContent = 'Try again';
    again.hidden = false;
    again.addEventListener('click', () => location.reload(), { once: true });
  }
})();

window.twin = { P, stats, select, seek, setCam, setSpeed, togglePlay, renderer, scene, camera, controls, explode: () => explode,
  rigs: () => rigs, sound, narrator, setSound,
  // for testing: run n frames of dt seconds straight away (a hidden browser tab barely draws)
  step: (n, dt = 1 / 30) => { for (let i = 0; i < n; i++) tick(last + dt * 1000); } };
