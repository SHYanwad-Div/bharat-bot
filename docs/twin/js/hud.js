// Bharat-Bot twin: the control-room HUD, as in the film (video/src/bharat/ControlRoomHud.tsx). The SENSE -> AI ->
// SAFETY -> ACT chain, the log, speed and state, the route strip and the playback bar, plus a plain-English caption
// for each moment and a result card at the end of a run.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export const C = { saffron: '#ff9933', green: '#2ecc71', amber: '#f5b301', red: '#ef4444', blue: '#38bdf8', violet: '#a78bfa',
  muted: '#93a1b8', act: '#e2e8f0', text: '#f5f7fa', std: '#3987e5' };
const LEVEL = { SENSE: C.blue, AI: C.violet, SAFETY: C.amber, ACT: C.act, OK: C.green, ALARM: C.red, INFO: C.muted };
const MODE = { CRUISE: C.green, ARRIVING: C.green, DELIVERED: C.green, 'POTHOLE AVOID': C.saffron, 'SPEED BREAKER': C.amber,
  WADING: C.blue, 'DOG HOTSPOT': C.amber, 'DOG FREEZE': C.amber, CREEP: C.amber, YIELD: C.blue, 'PERSON IN PATH': C.amber,
  DELIVERING: C.blue, TAMPER: C.red, ALARM: C.red, BLOCKED: C.red, STUCK: C.red, STOLEN: C.red };
const modeName = (m) => (m === 'TURN' ? 'CRUISE' : m);

// what each logged decision means, in plain words (shown under the decision chain)
// (the first event of a moment that has a caption is shown, so each caption tells the whole moment)
const CAPTIONS = [
  [/^Pothole \d+ cm deep/, 'Its depth camera sees a pothole 7 m ahead, so it plans a path round it.'],
  [/^Water-filled pothole/, 'Muddy water hides how deep this hole is, so it won\'t drive in. It goes round on solid road.'],
  [/^Speed breaker/, 'A 12 cm speed breaker with no paint on it. It slows down and climbs over on its big wheels.'],
  [/^Waterlogged patch/, 'Shallow water, 3.5 cm deep. That is under its 8 cm limit, so it wades through slowly.'],
  [/^Fleet map: dog hotspot/, 'Other robots reported dogs near this garbage heap, so it slows down early.'],
  [/^3 street dogs running/, 'Three street dogs run at it. Dogs chase things that move, so it stops and keeps still.'],
  [/^Calm mode/, 'Motors silent, face lights dimmed. Nothing moving means nothing to chase.'],
  [/^Dogs lost interest/, 'With nothing to chase, the dogs lose interest and walk back.'],
  [/^Pass slowly and calmly/, 'It creeps past the resting dogs at walking pace.'],
  [/^Back to cruise/, 'Past the dogs: no bites, no chase. Back to normal speed.'],
  [/^Cow standing in the lane/, 'A cow blocks its lane and an auto-rickshaw is coming up behind, so it waits at the edge.'],
  [/^Gap clear/, 'The auto has passed. It goes round the cow, then back to the left edge.'],
  [/^Person stepping into the path/, 'A man steps into the robot\'s path.'],
  [/^Stop: person in the path/, 'It stops. It never pushes through people.'],
  [/^Lid pulled by a stranger/, 'He pulls at the lid. It stays locked: only the customer\'s OTP opens it.'],
  [/^IMU: robot lifted/, 'He lifts the robot. It feels itself leave the ground and sounds a 110 dB siren with a red strobe.'],
  [/^Thief fled/, 'The thief drops it and runs. A photo and the location went to the control room. The delivery carries on.'],
  [/^Customer notified/, 'The customer gets a message: the robot is 20 seconds away.'],
  [/^Arrived at the gate/, 'At the gate. It waits for the customer.'],
  [/^OTP .* verified/, 'The customer types the OTP. The lid opens for them only.'],
  [/^DELIVERED/, 'Delivered: 69 m in 87 s, with every hazard on the way handled.'],
  [/^STUCK in a pothole/, 'Its small wheels drop into the hole and cannot climb out. Someone has to come and lift it out.'],
  [/^Dogs chasing/, 'It keeps driving, and dogs chase things that move. Now they are chasing it.'],
  [/^BLOCKED by 3 dogs/, 'The dogs block its path. Every time it lurches forward they get excited again.'],
  [/^Lid pulled$/, 'The lid is locked, so he simply picks up the whole robot.'],
  [/^Robot lifted and carried away/, 'No alarm and no motion sensor: nobody notices it being carried off.'],
  [/^STOLEN/, 'Gone, with the food inside.'],
];
const INTRO = {
  'full:bharat': 'Bharat-Bot leaves Biryani House with an order. 69 m to the customer\'s gate.',
  'full:baseline': 'A standard US-style sidewalk robot tries the same delivery.',
  'pothole:bharat': 'Bharat-Bot on the broken stretch: potholes, some full of muddy water.',
  'pothole:baseline': 'The standard robot drives straight down the lane. There is a pothole 6 m ahead.',
  'dogs:bharat': 'Bharat-Bot reaches the garbage heap where three street dogs rest.',
  'dogs:baseline': 'The standard robot drives past three street dogs resting by the garbage heap.',
  'theft:bharat': 'Bharat-Bot passes the man waiting on the pavement.',
  'theft:baseline': 'A man is waiting on the pavement, looking at his phone.',
};
const RESULT = {
  'full:bharat': ['DELIVERED', C.green, '69 m in 87 s: six road hazards, three dogs, a cow, an auto-rickshaw and a thief, all handled.'],
  'full:baseline': ['STUCK', C.red, 'The standard robot got 8 m. Its small wheels cannot climb out of an 11 cm pothole, so it waits for a human rescue.'],
  'pothole:bharat': ['PASSED', C.green, 'It saw each hole 7 m ahead and steered round it. Its wheels never dropped in.'],
  'pothole:baseline': ['STUCK', C.red, 'Front wheels in an 11 cm hole. This robot climbs only 6 cm, so it needs a human to rescue it.'],
  'dogs:bharat': ['PASSED', C.green, 'It froze, the dogs lost interest and walked away, and it crept past. No bites, no chase.'],
  'dogs:baseline': ['BLOCKED', C.red, 'It kept moving, so the dogs kept chasing. They block it and the delivery stalls.'],
  'theft:bharat': ['PASSED', C.green, 'The lid stayed locked, the siren went off when he lifted it, and he ran.'],
  'theft:baseline': ['STOLEN', C.red, 'No alarm and no tamper sensor. He carries it off and nobody notices.'],
};

export class HUD {
  constructor() {
    this.log = $('#log');
    this.shown = -1;
    this.capKey = '';
    this.routeTick = 0;
  }

  setRun(run, clip, test, robot) {
    this.run = run; this.clip = clip; this.test = test; this.robot = robot;
    this.key = `${test}:${robot}`;
    this.events = run.events.filter((e) => e.f >= clip[0] && e.f <= clip[1]);
    this.shown = -1;
    this.log.innerHTML = '';
    this.capKey = null;
    const dur = (clip[1] - clip[0]) / run.fps;
    $('#ticks').innerHTML = this.events.filter((e) => e.level !== 'INFO').map((e) => `<i style="left:${(((e.f - clip[0]) / run.fps / dur) * 100).toFixed(2)}%;background:${LEVEL[e.level]}" title="${esc(e.title)}"></i>`).join('');
    this.buildRoute();
    this.hideResult();
  }

  // ── route strip: the whole street from above, the stretch this run covers highlighted ──
  buildRoute() {
    const svg = $('#route');
    const W = Math.max(200, svg.clientWidth || 600), H = svg.clientHeight || 64;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    const run = this.run, x0 = -4, x1 = 68, top = 15, bot = H - 4;
    const sx = (x) => ((x - x0) / (x1 - x0)) * W;
    const sy = (y) => top + (bot - top) / 2 - (y / 6.6) * ((bot - top) / 2);
    this.sx = sx; this.sy = sy;
    const R = run.R, c = this.clip;
    let lo = Infinity, hi = -Infinity;
    for (let i = c[0]; i <= c[1]; i++) { lo = Math.min(lo, R.x[i]); hi = Math.max(hi, R.x[i]); }
    const a = sx(lo - 1), b = sx(hi + 1);
    let s = `<rect x="0" y="${sy(6.6)}" width="${W}" height="${sy(-6.6) - sy(6.6)}" fill="rgba(140,90,60,0.25)" rx="3"/>`;
    s += `<rect x="0" y="${sy(3.5)}" width="${W}" height="${sy(-3.5) - sy(3.5)}" fill="rgba(70,76,88,0.9)"/>`;
    s += `<rect x="${a}" y="${sy(6.6)}" width="${Math.max(2, b - a)}" height="${sy(-6.6) - sy(6.6)}" fill="rgba(255,153,51,0.13)" stroke="rgba(255,153,51,0.5)" rx="3"/>`;
    s += `<line x1="0" x2="${W}" y1="${sy(0)}" y2="${sy(0)}" stroke="rgba(255,255,255,0.35)" stroke-dasharray="7 9"/>`;
    for (const p of run.map.potholes) {
      if (p.cx < x0 || p.cx > x1) continue;
      s += `<ellipse cx="${sx(p.cx)}" cy="${sy(p.cy)}" rx="${Math.max(2, (p.rx / (x1 - x0)) * W)}" ry="${Math.max(2, p.ry * (bot - top) / 13.2)}" fill="${p.water > 0 ? 'rgba(56,189,248,0.9)' : 'rgba(239,68,68,0.9)'}"/>`;
    }
    const names = { start: 'BIRYANI HOUSE', breaker: 'BREAKER', dogs: 'DOGS', cow: 'COW', thief: 'THIEF', gate: 'GATE' };
    for (const pl of run.map.places) {
      const lx = sx(pl.x);
      const anchor = lx < 50 ? 'start' : lx > W - 30 ? 'end' : 'middle';
      const tx = anchor === 'start' ? Math.max(1, lx - 6) : anchor === 'end' ? Math.min(W - 1, lx + 6) : lx;
      s += `<circle cx="${lx}" cy="${sy(pl.y)}" r="3.5" fill="${pl.kind === 'gate' ? C.green : C.amber}"/>`;
      s += `<text x="${tx}" y="10" text-anchor="${anchor}" font-size="10" font-weight="700" fill="${C.muted}" font-family="Rajdhani, sans-serif" letter-spacing="1">${names[pl.kind]}</text>`;
    }
    if (run.robot === 'bharat') {
      const pts = run.map.route.x.map((x, i) => `${sx(x).toFixed(1)},${sy(run.map.route.y[i]).toFixed(1)}`).join(' ');
      s += `<polyline points="${pts}" fill="none" stroke="rgba(255,255,255,0.28)" stroke-width="1.5"/>`;
    }
    s += '<polyline id="r-done" fill="none" stroke="#ff9933" stroke-width="2.5" stroke-linecap="round"/><circle id="r-bot" r="5" fill="#fff" stroke-width="3"/>';
    svg.innerHTML = s;
    this.routeTick = 0;
  }

  update(run, u, t, playing) {
    const c = this.clip, fps = run.fps, k = run.idx(u);
    const rel = (u - c[0]) / fps, dur = (c[1] - c[0]) / fps;
    $('#clock').textContent = `${Math.max(0, rel).toFixed(1).padStart(5, '0')} s`;
    const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
    $('#time').textContent = `${fmt(Math.max(0, rel))} / ${fmt(dur)}`;
    if (!this.scrubbing) $('#scrub').value = Math.round((rel / dur) * 1000);
    // log: everything logged so far in this clip, newest first
    const past = this.events.filter((e) => e.f <= k);
    if (past.length !== this.shown) {
      if (past.length < this.shown || this.shown < 0) this.log.innerHTML = '';
      const from = Math.max(0, this.shown < 0 || past.length < this.shown ? 0 : this.shown);
      for (const e of past.slice(from)) {
        const li = document.createElement('li');
        li.className = e.level;
        li.innerHTML = `<time>${((e.f - c[0]) / fps).toFixed(1)}s</time><b style="color:${LEVEL[e.level]}">${e.level}</b><p>${esc(e.title)}<small>${esc(e.detail)}</small></p>`;
        this.log.prepend(li);
      }
      if (!past.length) this.log.innerHTML = '<li class="empty">Nothing logged yet. Events appear here as the robot senses, decides and acts.</li>';
      this.shown = past.length;
    }
    // decision chain: the newest moment lights its furthest stage for 2.2 s (an alarm lights the last stage red)
    const last = past[past.length - 1];
    const age = last ? (k - last.f) / fps : 99;
    const lead = last ? past.find((e) => e.f === last.f && e.level === 'ALARM') || last : null;
    const active = lead && age < 2.2 ? (lead.level === 'INFO' ? 'SENSE' : lead.level) : null;
    for (const sp of document.querySelectorAll('#chain span')) {
      const l = sp.dataset.l;
      const lit = active === l || (active === 'ALARM' && l === 'OK');
      const col = LEVEL[active === 'ALARM' && l === 'OK' ? 'ALARM' : l];
      sp.classList.toggle('on', lit);
      sp.style.background = lit ? col : '';
      sp.style.boxShadow = lit ? `0 0 18px ${col}` : '';
      sp.textContent = l === 'OK' && active === 'ALARM' ? 'ALARM' : l === 'ACT' ? 'ACTUATORS' : l;
    }
    // caption: the plain-words version of the newest moment that has one (up to 6.5 s old), or the run's opening line
    let cap = '', capKey = '', capCol = C.saffron;
    for (let i = past.length - 1; i >= 0 && !cap && (k - past[i].f) / fps < 6.5;) {
      let j = i;
      while (j > 0 && past[j - 1].f === past[i].f) j--;
      for (let m = j; m <= i && !cap; m++) {
        const hit = CAPTIONS.find(([re]) => re.test(past[m].title));
        if (hit) { cap = hit[1]; capKey = `${past[m].f}:${m}`; capCol = LEVEL[(past.find((e) => e.f === past[m].f && e.level === 'ALARM') || past[m]).level]; }
      }
      i = j - 1;
    }
    if (!cap && rel < 4.5 && !past.length) { cap = INTRO[this.key] || ''; capKey = `intro:${this.key}`; }
    let spoken = null;
    if (capKey !== this.capKey) {
      this.capKey = capKey;
      const el = $('#caption');
      if (cap) {
        el.textContent = cap;
        el.style.borderLeftColor = capCol;
        el.classList.remove('fade');
        spoken = cap;
      } else el.classList.add('fade');
    }
    // speed + state
    const R = run.R;
    const v = Math.max(0, run.lerp(R.v, u));
    const mode = modeName(run.at(R.mode, u));
    const col = MODE[mode] || C.muted;
    const ring = 2 * Math.PI * 62;
    const val = $('#g-val'), trk = $('#g-track');
    trk.setAttribute('stroke-dasharray', `${ring * 0.75} ${ring}`);
    trk.setAttribute('transform', 'rotate(135 80 80)');
    val.setAttribute('stroke-dasharray', `${Math.max(0.5, ring * 0.75 * Math.min(1, v / 2))} ${ring}`);
    val.setAttribute('transform', 'rotate(135 80 80)');
    val.setAttribute('stroke', col);
    $('#g-num').textContent = v.toFixed(1);
    const st = $('#state');
    st.textContent = mode;
    st.style.color = col;
    const ms = $('#mstate');
    ms.textContent = mode;
    ms.title = `${v.toFixed(1)} m/s`;
    ms.style.color = col;
    const s = run.lerp(R.s, u);
    const toGate = run.scenario === 'bharat_full' && run.robot === 'bharat';
    const batt = Math.round((run.battery[0] + run.battery[1] * k) * 100);
    const tilt = Math.max(Math.abs(run.lerp(R.pitch, u)), Math.abs(run.lerp(R.roll, u))) * 180 / Math.PI;
    const lid = run.lerp(R.lid, u) > 0.05 ? 'OPEN' : 'LOCKED';
    $('#facts').innerHTML = `<span>${toGate ? `TO GATE <b>${Math.max(0, run.routeLength - s).toFixed(0)} m</b>` : `DRIVEN <b>${s.toFixed(1)} m</b>`}</span>`
      + `<span>BATT <b>${batt}%</b></span><span>LID <b style="color:${lid === 'OPEN' ? C.green : C.text}">${lid}</b></span><span>TILT <b>${tilt.toFixed(0)}°</b></span>`;
    // route strip: path driven so far and the robot
    if (this.sx && (++this.routeTick % 3 === 0 || !playing)) {
      const pts = [];
      for (let i = c[0]; i <= k; i += 6) pts.push(`${this.sx(R.x[i]).toFixed(1)},${this.sy(R.y[i]).toFixed(1)}`);
      pts.push(`${this.sx(run.lerp(R.x, u)).toFixed(1)},${this.sy(run.lerp(R.y, u)).toFixed(1)}`);
      document.getElementById('r-done')?.setAttribute('points', pts.join(' '));
      const dot = document.getElementById('r-bot');
      if (dot) {
        dot.setAttribute('cx', this.sx(run.lerp(R.x, u)).toFixed(1));
        dot.setAttribute('cy', this.sy(run.lerp(R.y, u)).toFixed(1));
        dot.setAttribute('stroke', col);
      }
    }
    return spoken;          // a caption that just appeared (for the voice), or null
  }

  showResult(onReplay, onOther, onNext) {
    const [word, col, text] = RESULT[this.key];
    const el = $('#result');
    const other = this.robot === 'bharat' ? 'Try the US robot' : 'Now try Bharat-Bot';
    el.innerHTML = `<b style="color:${col}">${word}</b><p>${esc(text)}</p><div class="row">`
      + `<button class="btn" id="r-replay">↺ Replay</button><button class="btn" id="r-other">${other}</button>`
      + `${this.test === 'full' ? '' : '<button class="btn" id="r-next">Next test →</button>'}</div>`;
    el.hidden = false;
    $('#r-replay').onclick = onReplay;
    $('#r-other').onclick = onOther;
    $('#r-next')?.addEventListener('click', onNext);
    return `${word.charAt(0) + word.slice(1).toLowerCase()}. ${text}`;
  }
  hideResult() { $('#result').hidden = true; }
}
