// Bharat-Bot twin: the film's HUD-style effects in 3D. Bharat-Bot's LiDAR sweep and range ring, its planned path,
// pothole and water markers, detection boxes round what it sees, the calm-mode pulse, the siren rings and strobe,
// the evidence-photo flash and the dogs' bark rings (sim/build_scene.py and characters.py).
import * as THREE from 'three';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

function glow(color, opacity = 0, additive = true) {
  return new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending, toneMapped: false });
}
const fxMesh = (g, m) => { const o = new THREE.Mesh(g, m); o.userData.fx = true; o.raycast = () => {}; return o; };
function flatRing(r0, r1, seg = 64) {
  const g = new THREE.RingGeometry(r0, r1, seg);
  g.rotateX(-Math.PI / 2);
  return g;
}

// HTML labels pinned to points in the scene
class Tags {
  constructor(el) { this.el = el; this.list = []; }
  add(text, color) {
    const d = document.createElement('div');
    d.className = 'tag';
    d.textContent = text;
    d.style.background = color;
    d.hidden = true;
    this.el.appendChild(d);
    const t = { d, pos: new THREE.Vector3(), alpha: 0 };
    this.list.push(t);
    return t;
  }
  clear() { for (const t of this.list) t.d.remove(); this.list = []; }
  update(camera, w, h) {
    const v = new THREE.Vector3();
    for (const t of this.list) {
      v.copy(t.pos).project(camera);
      const show = t.alpha > 0.03 && v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1;
      t.d.hidden = !show;
      if (!show) continue;
      t.d.style.opacity = t.alpha.toFixed(2);
      t.d.style.transform = `translate(${((v.x * 0.5 + 0.5) * w).toFixed(1)}px, ${((-v.y * 0.5 + 0.5) * h).toFixed(1)}px) translate(-50%, -100%)`;
    }
  }
}

export class FX {
  constructor(scene, street, tagsEl) {
    this.scene = scene;
    this.street = street;
    this.tags = new Tags(tagsEl);
    this.group = new THREE.Group();
    scene.add(this.group);
    // always in the scene (intensity 0 when off), so switching them never recompiles shaders
    this.alarmLight = new THREE.PointLight(0xff2010, 0, 7, 1.6);
    this.flash = new THREE.PointLight(0xffffff, 0, 9, 1.4);
    scene.add(this.alarmLight, this.flash);
    this.boxes = [];
    this.runFX = new THREE.Group();
    this.group.add(this.runFX);
  }

  // rings and the sensor sweep ride on each robot
  attachRobot(rig) {
    const root = rig.root, r = rig.r;
    rig.fx = {};
    if (rig.kind === 'bharat') {
      const wedge = new THREE.CircleGeometry(6.4, 12, -14 * Math.PI / 180, 28 * Math.PI / 180);
      wedge.rotateX(-Math.PI / 2);
      const sweep = fxMesh(wedge, glow(0x19e6ff, 0.09));
      sweep.position.y = -0.43;
      sweep.renderOrder = 3;
      rig.lidar.add(sweep);
      const range = fxMesh(flatRing(6.42, 6.5, 128), glow(0x19e6ff, 0.16));
      range.position.y = -r + 0.03;
      root.add(range);
      rig.fx.sensors = [sweep, range];
    }
    rig.fx.calm = [0, 1, 2, 3].map(() => {
      const m = fxMesh(flatRing(0.93, 1.0), glow(0xff9e1f, 0));
      m.position.y = -r + 0.05;
      root.add(m);
      return m;
    });
    rig.fx.siren = [0, 1, 2, 3].map(() => {
      const m = fxMesh(flatRing(0.9, 1.0), glow(0xff1408, 0));
      m.position.y = rig.top + 0.15;
      root.add(m);
      return m;
    });
  }

  attachDog(dog) {
    const ring = fxMesh(new THREE.RingGeometry(0.85, 1.0, 32), glow(0xfff2cc, 0));
    ring.position.set(0.42, 0.42, 0);
    ring.rotation.y = Math.PI / 2;
    dog.root.add(ring);
    dog.barkRing = ring;
  }

  // per-run effects: Bharat-Bot's planned path, pothole markers and detection boxes (only the robot that senses)
  setRun(run, rigs) {
    this.runFX.clear();
    this.tags.clear();
    this.boxes = [];
    this.ribbon = null;
    this.marks = [];
    this.run = run;
    this.sees = !!run.cfg.sees_potholes;
    if (!this.sees) return;
    this.buildRibbon(run);
    this.buildMarks(run);
    const S = this.street.d;
    const add = (key, size, color, label, track) => {
      const g = new THREE.BoxGeometry(1, 1, 1);
      const lines = new THREE.LineSegments(new THREE.EdgesGeometry(g), new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0, toneMapped: false, depthWrite: false }));
      const fill = fxMesh(g, glow(color, 0, false));
      const box = new THREE.Group();
      box.add(lines, fill);
      box.scale.set(size[0], size[2], size[1]);
      this.runFX.add(box);
      const tag = this.tags.add(label, `#${new THREE.Color(color).getHexString()}`);
      this.boxes.push({ key, box, lines, fill, size, tag, track, vis: this.visTrack(run, key) });
    };
    run.dogs.forEach((D, i) => add(`dog${i}`, [0.9, 0.42, 0.78], 0xff9a0d, `DOG 0.9${4 + i}`, (u) => [run.lerp(D.x, u), run.lerp(D.y, u), run.lerp(D.h, u)]));
    add('thief', [0.6, 0.6, 1.9], 0xff2799, 'PERSON 0.97', (u) => [run.lerp(run.thief.x, u), run.lerp(run.thief.y, u), run.lerp(run.thief.h, u)]);
    add('cow', [2.6, 0.95, 1.55], 0xffd91a, 'COW 0.99', () => [S.places.cow[0], S.places.cow[1], S.places.cow[2]]);
    add('auto', [2.9, 1.5, 1.95], 0x4d99ff, 'AUTO-RICKSHAW 0.96', (u) => [run.lerp(run.auto.x, u), run.lerp(run.auto.y, u), run.lerp(run.auto.h, u)]);
  }

  // build_sim_shot's detection rules, one 0/1 per frame
  visTrack(run, key) {
    const n = run.n, out = new Float32Array(n), R = run.R, S = this.street.d;
    for (let k = 0; k < n; k++) {
      const rx = R.x[k], ry = R.y[k];
      let on = false;
      if (key.startsWith('dog')) {
        const D = run.dogs[+key[3]];
        on = ['ALERT', 'CHASE', 'RETREAT'].includes(D.state[k]) && Math.hypot(D.x[k] - rx, D.y[k] - ry) < 8.5;
      } else if (key === 'thief') {
        const T = run.thief;
        on = !['WAIT', 'GONE'].includes(T.state[k]) && Math.hypot(T.x[k] - rx, T.y[k] - ry) < 9;
      } else if (key === 'cow') {
        on = rx > S.places.cow[0] - 13 && rx < S.places.cow[0] + 1.5;
      } else if (key === 'auto') {
        const A = run.auto;
        on = A.active[k] > 0 && Math.hypot(A.x[k] - rx, A.y[k] - ry) < 30 && A.x[k] < rx + 6;
      }
      out[k] = on ? 1 : 0;
    }
    return out;
  }

  buildRibbon(run) {
    const { x, y } = run.map.route;
    const n = x.length, pos = [], sAttr = [], idx = [];
    let s = 0;
    for (let i = 0; i < n; i++) {
      if (i) s += Math.hypot(x[i] - x[i - 1], y[i] - y[i - 1]);
      const a = Math.max(0, i - 1), b = Math.min(n - 1, i + 1);
      let dx = x[b] - x[a], dy = y[b] - y[a];
      const L = Math.hypot(dx, dy) || 1;
      dx /= L; dy /= L;
      const z = this.street.height(x[i], y[i]) + this.street.waterDepth(x[i], y[i]) + 0.025;
      for (const side of [1, -1]) {
        const px = x[i] - dy * 0.08 * side, py = y[i] + dx * 0.08 * side;
        pos.push(px, z, -py);
        sAttr.push(s);
      }
      if (i < n - 1) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('s', new THREE.Float32BufferAttribute(sAttr, 1));
    g.setIndex(idx);
    const mat = new THREE.ShaderMaterial({
      uniforms: { uS0: { value: 0 }, uS1: { value: 8 }, uFlow: { value: 0 } },
      vertexShader: 'attribute float s; varying float vS; void main() { vS = s; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform float uS0, uS1, uFlow; varying float vS;
        void main() {
          float win = clamp((vS - uS0) / 0.5, 0.0, 1.0) * clamp((uS1 - vS) / 2.5, 0.0, 1.0);
          float chev = fract((vS - uFlow) * 2.2) < 0.45 ? 1.0 : 0.5;
          gl_FragColor = vec4(vec3(0.05, 0.85, 1.0) * 1.3, win * chev * 0.85);
        }`,
      transparent: true, depthWrite: false, side: THREE.DoubleSide,
    });
    this.ribbon = fxMesh(g, mat);
    this.ribbon.renderOrder = 2;
    this.runFX.add(this.ribbon);
  }

  buildMarks(run) {
    run.map.potholes.forEach((p, i) => {
      if (p.detect === null || p.detect === undefined) return;
      const ph = this.street.potholes[i];
      const wade = p.water > 0 && p.depth <= 0.06;
      const color = wade ? 0x26ff59 : 0xff1f0d;
      const pts = [];
      for (let k = 0; k < 72; k++) {
        const th = (2 * Math.PI * k) / 72, rr = ph.rimRadius(th) + 0.06;
        const x = p.cx + rr * Math.cos(th), y = p.cy + rr * Math.sin(th);
        pts.push(new THREE.Vector3(x, this.street.height(x, y) + 0.03, -y));
      }
      const tube = fxMesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true), 144, 0.022, 4, true), glow(color, 0, false));
      tube.renderOrder = 2;
      this.runFX.add(tube);
      const label = wade ? `WATER ${(p.water * 100).toFixed(1)} cm · OK` : `−${Math.round(p.depth * 100)} cm${p.water > 0 ? ' + WATER' : ''}`;
      const tag = this.tags.add(label, wade ? '#26ff59' : '#ff5a47');
      tag.pos.set(p.cx, 0.55, -p.cy);
      this.marks.push({ tube, tag, f0: p.detect, f1: p.passed ?? run.n });
    });
  }

  update(run, u, t, rig, dogs, alarmInfo, camera, w, h) {
    const k = run.idx(u);
    // robot rings: calm-mode pulse while it holds still for the dogs, siren rings in an alarm
    const R = run.R;
    let deter = 0;
    for (let j = Math.max(0, k - 4); j <= Math.min(run.n - 1, k + 4); j++) deter += run.at(R.deter, j) ? 1 : 0;
    deter /= 9;
    const alarm = alarmInfo.alarm ? 1 : 0;
    rig.fx.calm.forEach((m, i) => {
      const ph = (((t / 1.7) - i / 4) % 1 + 1) % 1, r = 0.55 + 1.75 * ph;
      m.scale.setScalar(r);
      m.material.opacity = 0.42 * (1 - ph) ** 1.5 * deter;
      m.visible = m.material.opacity > 0.003;
    });
    rig.fx.siren.forEach((m, i) => {
      const ph = (((t / 0.8) - i / 4) % 1 + 1) % 1, r = 0.35 + 2.05 * ph;
      m.scale.setScalar(r);
      m.material.opacity = 0.9 * (1 - ph) ** 1.5 * alarm;
      m.visible = m.material.opacity > 0.003;
    });
    const top = new THREE.Vector3(0, rig.top + 0.35, 0).applyMatrix4(rig.root.matrixWorld);
    this.alarmLight.position.copy(top);
    this.alarmLight.intensity = alarm && alarmInfo.strobe ? 9 : 0;
    // the evidence photo: one bright flash in front of the robot when the alarm starts
    let on = -1;
    for (let j = Math.max(0, k - 4); j <= k; j++) if (run.at(R.alarm, j) && (j === 0 || !run.at(R.alarm, j - 1))) on = j;
    this.flash.intensity = on >= 0 && k - on < 3 ? 60 : 0;
    this.flash.position.copy(new THREE.Vector3(0.7, 0.4, 0).applyMatrix4(rig.root.matrixWorld));
    // dog bark rings
    dogs.forEach((d, i) => {
      const b = run.lerp(run.dogs[i].bark, u);
      d.barkRing.visible = b > 0.02;
      d.barkRing.scale.setScalar(b > 0.02 ? 0.25 + 0.9 * (1 - b) : 0.001);
      d.barkRing.material.opacity = b * 0.9;
    });
    // what Bharat-Bot senses
    if (this.sees) {
      const s = run.lerp(R.s, u);
      const m = this.ribbon.material.uniforms;
      m.uS0.value = s + 0.45; m.uS1.value = s + 8.0; m.uFlow.value = t * 1.6;
      for (const mk of this.marks) {
        const a = clamp((u - mk.f0) / 8, 0, 1) * clamp(1 - (u - mk.f1) / 15, 0, 1) * 0.95;
        mk.tube.material.opacity = a;
        mk.tube.visible = a > 0.003;
        mk.tag.alpha = a;
      }
      for (const b of this.boxes) {
        let vis = 0;
        for (let j = Math.max(0, k - 2); j <= Math.min(run.n - 1, k + 2); j++) vis += b.vis[j];
        vis /= 5;
        b.box.visible = vis > 0.01;
        if (!b.box.visible) { b.tag.alpha = 0; continue; }
        const [x, y, hd] = b.track(u);
        const gz = this.street.height(x, y);
        b.box.position.set(x, gz + b.size[2] / 2, -y);
        b.box.rotation.set(0, hd, 0);
        b.lines.material.opacity = 0.9 * vis;
        b.fill.material.opacity = 0.07 * vis;
        b.tag.pos.set(x, gz + b.size[2] + 0.18, -y);
        b.tag.alpha = 0.95 * vis;
      }
    }
    this.tags.update(camera, w, h);
  }
}
