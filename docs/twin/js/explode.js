// Bharat-Bot twin: click a robot and it comes apart into labelled parts, GH-01 style. Offsets are in the robot's own
// frame (three.js: +x forward, +y up, +z to its right). Parts the simulation moves every frame (wheels, rocker-bogie
// bars) get their offset added after posing; the rest sit at their resting place plus the offset.
import * as THREE from 'three';

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const easeOutBack = (t) => { const c1 = 1.4, c3 = c1 + 1; return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2; };
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

function bharatParts(rig) {
  const W = rig.wheels, A = rig.arms;
  return [
    { name: 'LiDAR', items: [['BharatBot_part_lidar', [0.1, 0.8, 0]], ['BharatBot_lidar', [0.1, 0.8, 0]]],
      text: 'Spins round and measures distances with laser light, all the way round the robot. That gives it a 3D map to steer by.' },
    { name: 'Stereo depth camera', items: [['BharatBot_part_depthcam', [0.6, 0.12, 0]], ['BharatBot_eyes', [0.6, 0.12, 0]]],
      text: 'Two cameras side by side, like a pair of eyes. Together they measure how deep a pothole is and how far away dogs, people and cows are. The face lights dim when dogs are near.' },
    { name: 'Side and rear cameras', items: [['BharatBot_part_camL', [0, 0.12, -0.42]], ['BharatBot_part_camR', [0, 0.12, 0.42]], ['BharatBot_part_camB', [-0.55, 0.12, 0]]],
      text: 'Cameras on both sides and at the back. Before the robot moves out into the lane, the rear one checks for traffic coming up behind.' },
    { name: 'OTP-locked lid', items: [['BharatBot_lidhinge', [0, 0.52, 0]]],
      text: 'Opens only when the customer types the one-time password (OTP) from their phone. A force sensor notices if a stranger pulls at it.' },
    { name: 'Food compartment', items: [['BharatBot_part_cargo', [0, 0.3, 0]]],
      text: 'Holds the order upright, sealed against rain and dust.' },
    { name: 'Siren + red strobe', items: [['BharatBot_part_siren', [-0.62, 0.12, 0]]],
      text: 'A 110 dB siren and a red strobe. If someone lifts or tilts the robot, its motion sensor (IMU) sets them off, and a photo and the live location go to the control room.' },
    { name: 'Sealed body', items: [['BharatBot_part_shell', [0, 0.12, 0]], ['BharatBot_status', [0, 0.12, 0]], ['BharatBot_headlight', [0, 0.12, 0]], ['BharatBot_taillight', [0, 0.12, 0]]],
      text: 'Sealed shell with waterproof (IP67) motors, so it can wade through water up to 8 cm deep. It refuses deeper water. The light strip shows what the robot is doing.' },
    { name: 'Bumper band', items: [['BharatBot_part_bumper', [0, -0.03, 0]]],
      text: 'A bumper all the way round, in India\'s colours. Its switches cut the drive if it touches anything.' },
    { name: 'Visibility flag', items: [['BharatBot_part_flag', [-0.32, 0.3, -0.12]], ['BharatBot_flag', [-0.32, 0.3, -0.12]]],
      text: 'An orange flag on a pole, so auto-rickshaw and scooter drivers notice a robot this low.' },
    { name: 'Rocker-bogie suspension', items: [['BharatBot_part_rockerL', [0, 0, -0.26]], ['BharatBot_part_rockerR', [0, 0, 0.26]],
      ...A.map(([side, , ob]) => [ob, [0, 0, side > 0 ? -0.26 : 0.26], true])],
      text: 'Linked arms, like on the Mars rovers. Each wheel can rise and fall on its own, so all six stay on the ground over potholes and speed breakers.' },
    { name: 'Six 32 cm wheels', items: W.map((w, i) => [w, [0, -0.04, i < 3 ? -0.48 : 0.48], true]),
      text: 'Big wheels that climb about 18 cm. A standard sidewalk robot\'s 18 cm wheels climb only 6 cm.' },
  ];
}

function stdParts(rig) {
  return [
    { name: 'Locked lid', items: [['StdBot_lidhinge', [0, 0.46, 0]]],
      text: 'Locked, but with no force sensor and no alarm. A thief who cannot open it just carries the whole robot away.' },
    { name: 'Body + 2 front cameras', items: [['StdBot_body', [0, 0.12, 0]], ['StdBot_flag', [0, 0.12, 0]], ['StdBot_headlight', [0, 0.12, 0]], ['StdBot_taillight', [0, 0.12, 0]]],
      text: 'The cameras see obstacles, but cannot tell how deep a hole is or whether muddy water hides one.' },
    { name: 'Six 18 cm wheels, rigid chassis', items: rig.wheels.map((w, i) => [w, [0, -0.04, i < 3 ? -0.42 : 0.42], true]),
      text: 'They climb about 6 cm. An 11 cm pothole traps the front wheels, and a 12 cm speed breaker stops it too.' },
  ];
}

export class Explode {
  constructor(api) {
    this.api = api;           // { camera, controls, fly, pause, resume, setFocus }
    this.rig = null;
    this.e = 0;
    this.target = 0;
    this.labels = [];
    this.hover = -1;
    this.$ = (s) => document.querySelector(s);
    this.$('#p-close').addEventListener('click', () => this.close());
  }
  get open() { return !!this.rig; }

  show(rig) {
    if (this.rig === rig) return;
    if (this.rig) this.close(true);
    this.rig = rig;
    const parts = (rig.kind === 'bharat' ? bharatParts(rig) : stdParts(rig)).map((p, k) => ({
      ...p, k, items: p.items.map(([n, off, posed]) => {
        const obj = typeof n === 'string' ? rig.root.getObjectByName(n) : n;
        return obj ? { obj, off: new THREE.Vector3(...off), posed: !!posed, base: obj.position.clone() } : null;
      }).filter(Boolean),
    }));
    this.parts = parts;
    for (const p of parts) for (const it of p.items) it.obj.traverse((m) => { if (m.isMesh) m.userData.part = p.k; });
    this.target = 1;
    this.t0 = performance.now();
    this.api.pause();
    this.api.setFocus(true);
    // camera: a three-quarter view from the front left, far enough to fit the exploded robot beside the panel
    const bharat = rig.kind === 'bharat', mobile = innerWidth <= 820;
    const c = new THREE.Vector3(0, bharat ? (mobile ? 0.6 : 0.5) : 0.35, 0).applyMatrix4(rig.root.matrixWorld);
    const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, rig.root.rotation.y, 0));
    const dir = new THREE.Vector3(0.75, 0.5, -0.85).applyQuaternion(q).normalize();
    this.saved = { pos: this.api.camera.position.clone(), target: this.api.controls.target.clone() };
    this.api.fly(c.clone().addScaledVector(dir, this.api.fitDistance(bharat ? (mobile ? 1.45 : 1.3) : 0.95)), c, 1.1);
    // labels + parts list
    const box = this.$('#labels');
    box.innerHTML = '';
    this.labels = parts.map((p, i) => {
      const el = document.createElement('div');
      el.className = 'plab';
      el.innerHTML = `<i>${i + 1}</i><span>${esc(p.name)}</span>`;
      el.addEventListener('mouseenter', () => this.highlight(i));
      el.addEventListener('mouseleave', () => this.highlight(-1));
      el.addEventListener('click', (e) => { e.stopPropagation(); this.highlight(i, true); });
      box.appendChild(el);
      setTimeout(() => el.classList.add('show'), 500 + i * 45);
      return { el, p };
    });
    this.$('#p-title').textContent = bharat ? 'Bharat-Bot, taken apart' : 'The standard robot, taken apart';
    this.$('#p-sum').textContent = bharat
      ? 'The India-adapted design. Hover or tap a part to find it on the robot.'
      : 'A typical US-style sidewalk robot, built for smooth pavements.';
    this.$('#parts').innerHTML = parts.map((p, i) => `<li data-i="${i}"><i>${i + 1}</i><div><b>${esc(p.name)}</b><small>${esc(p.text)}</small></div></li>`).join('')
      + (bharat ? '' : '<li class="vs"><div><b>Missing, compared with Bharat-Bot</b><small>Depth camera and LiDAR, rocker-bogie suspension, '
        + 'big wheels, a tamper alarm and a protocol for street dogs.</small></div></li>');
    for (const li of this.$('#parts').querySelectorAll('li[data-i]')) {
      li.addEventListener('mouseenter', () => this.highlight(+li.dataset.i));
      li.addEventListener('mouseleave', () => this.highlight(-1));
      li.addEventListener('click', () => this.highlight(+li.dataset.i, true));
    }
    this.$('#panel').hidden = false;
  }

  close(immediate = false) {
    if (!this.rig) return;
    this.highlight(-1);
    this.target = 0;
    this.closing = this.rig;
    if (immediate) { this.e = 0; this.apply(); this.closing = null; }
    this.rig = null;
    this.$('#labels').innerHTML = '';
    this.$('#leaders').innerHTML = '';
    this.$('#panel').hidden = true;
    this.api.setFocus(false);
    if (!immediate && this.saved) this.api.fly(this.saved.pos, this.saved.target, 0.9);
    this.saved = null;
    this.api.resume();
  }

  highlight(i, sticky = false) {
    if (sticky) this.sticky = i;
    if (i < 0 && this.sticky >= 0 && !sticky) i = this.sticky;
    if (this.hover === i) return;
    this.hover = i;
    const parts = this.parts || [];
    parts.forEach((p, k) => {
      for (const it of p.items) it.obj.traverse((m) => {
        if (!m.isMesh || !m.material.emissive) return;
        if (m.userData.baseEm === undefined) m.userData.baseEm = [m.material.emissive.clone(), m.material.emissiveIntensity];
        if (k === i && !m.userData.led) { m.material.emissive.set(0xff9933); m.material.emissiveIntensity = 0.45; }
        else if (!m.userData.led) { m.material.emissive.copy(m.userData.baseEm[0]); m.material.emissiveIntensity = m.userData.baseEm[1]; }
      });
    });
    this.labels.forEach((l, k) => l.el.classList.toggle('hl', k === i));
    for (const li of document.querySelectorAll('#parts li[data-i]')) li.classList.toggle('hl', +li.dataset.i === i);
    if (sticky) document.querySelector(`#parts li[data-i="${i}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  // which part a mesh belongs to (for hover and click while open)
  partOf(mesh) { return mesh?.userData.part ?? -1; }

  // called every frame after the robot has been posed
  update(dt) {
    const rig = this.rig || this.closing;
    if (!rig) return;
    const speed = this.target ? 1 / 1.1 : 1 / 0.6;
    this.e = this.target ? Math.min(1, this.e + dt * speed) : Math.max(0, this.e - dt * speed);
    this.apply();
    if (!this.target && this.e <= 0) {
      for (const p of this.parts) for (const it of p.items) if (!it.posed) it.obj.position.copy(it.base);
      this.closing = null;
      this.parts = null;
    }
    if (this.rig) this.updateLabels();
  }

  apply() {
    if (!this.parts) return;
    for (const p of this.parts) {
      const u = Math.min(1, Math.max(0, (this.e * 1.3 - p.k * 0.03) / 0.9));
      const f = this.target ? easeOutBack(u) : easeInOut(u);
      for (const it of p.items) {
        if (it.posed) it.obj.position.addScaledVector(it.off, f);
        else it.obj.position.copy(it.base).addScaledVector(it.off, f);
      }
    }
  }

  updateLabels() {
    const cam = this.api.camera, W = innerWidth, H = innerHeight;
    const centre = new THREE.Vector3(0, 0.3, 0).applyMatrix4(this.rig.root.matrixWorld).project(cam);
    const cx = (centre.x * 0.5 + 0.5) * W, cy = (-centre.y * 0.5 + 0.5) * H;
    let lines = '';
    const box = new THREE.Box3(), tmp = new THREE.Box3(), v = new THREE.Vector3();
    for (const l of this.labels) {
      const it = l.p.items[0];
      if (!it) continue;
      box.makeEmpty();
      it.obj.traverse((m) => {            // the part's own meshes, not effects hung on it (the LiDAR's sweep)
        if (!m.isMesh || m.userData.fx) return;
        if (!m.geometry.boundingBox) m.geometry.computeBoundingBox();
        box.union(tmp.copy(m.geometry.boundingBox).applyMatrix4(m.matrixWorld));
      });
      if (box.isEmpty()) continue;
      box.getCenter(v).project(cam);
      if (v.z > 1) { l.el.style.display = 'none'; continue; }
      l.el.style.display = '';
      const x = (v.x * 0.5 + 0.5) * W, y = (-v.y * 0.5 + 0.5) * H;
      let dx = x - cx, dy = y - cy;
      const d = Math.hypot(dx, dy) || 1;
      dx /= d; dy /= d;
      const half = (l.el.offsetWidth || 120) / 2 + 6;
      const lx = Math.min(W - half, Math.max(half, x + dx * 46)), ly = Math.min(H - 16, Math.max(70, y + dy * 30));
      l.el.style.left = `${lx}px`;
      l.el.style.top = `${ly}px`;
      if (this.e > 0.6) lines += `<line x1="${x.toFixed(1)}" y1="${y.toFixed(1)}" x2="${lx.toFixed(1)}" y2="${ly.toFixed(1)}"/><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.6"/>`;
    }
    this.$('#leaders').innerHTML = lines;
  }
}
