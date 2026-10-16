// Bharat-Bot twin: one simulation run (data/<run>.json, written by sim/export_twin.py), decoded into per-frame arrays.
// Number channels arrive as {k, d, v}: value = v / k, running sums when d = 1. Text and on/off channels arrive as runs
// [[first frame, value], ...] and are expanded to one value per frame.

function decodeNum(c, n) {
  const out = new Float64Array(n);
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc = c.d ? acc + c.v[i] : c.v[i];
    out[i] = acc / c.k;
  }
  return out;
}
function expandRuns(runs, n) {
  const out = new Array(n);
  for (let r = 0; r < runs.length; r++) {
    const end = r + 1 < runs.length ? runs[r + 1][0] : n;
    for (let i = runs[r][0]; i < end; i++) out[i] = runs[r][1];
  }
  return out;
}
function decodeGroup(g, n) {
  const o = {};
  for (const [k, c] of Object.entries(g)) o[k] = Array.isArray(c) ? expandRuns(c, n) : decodeNum(c, n);
  return o;
}

export class Run {
  constructor(j) {
    this.j = j;
    this.name = j.run;
    this.scenario = j.scenario;
    this.robot = j.robot;
    this.label = j.label;
    this.fps = j.fps;
    this.n = j.n;
    this.cfg = j.cfg;
    this.events = j.events;
    this.map = j.map;
    this.windows = j.windows || null;
    this.routeLength = j.routeLength;
    this.battery = j.battery;
    this.R = decodeGroup(j.robotPose, this.n);
    this.dogs = j.dogs.map((d) => decodeGroup(d, this.n));
    this.thief = decodeGroup(j.thief, this.n);
    this.cust = decodeGroup(j.cust, this.n);
    this.auto = decodeGroup(j.auto, this.n);
    this.bag = j.bag ? decodeGroup(j.bag, this.n) : null;
    this.barks = j.barks;
  }
  idx(u) { return Math.min(this.n - 1, Math.max(0, Math.floor(u))); }
  // linear interpolation between frames (u is a fractional frame number)
  lerp(a, u) {
    const i = this.idx(u), j = Math.min(this.n - 1, i + 1), f = Math.min(1, Math.max(0, u - i));
    return a[i] + (a[j] - a[i]) * f;
  }
  at(a, u) { return a[this.idx(u)]; }
  // centred moving average over w frames (the film smooths speeds like this before picking gaits)
  avg(a, u, w) {
    const i = this.idx(u), h = (w - 1) >> 1;
    let s = 0, c = 0;
    for (let k = Math.max(0, i - h); k <= Math.min(this.n - 1, i + h); k++) { s += a[k]; c++; }
    return s / c;
  }
}

const cache = new Map();
export async function loadRun(name) {
  if (!cache.has(name)) {
    cache.set(name, fetch(`data/${name}.json`).then((r) => {
      if (!r.ok) throw new Error(`data/${name}.json: HTTP ${r.status}`);
      return r.json();
    }).then((j) => new Run(j)));
  }
  try {
    return await cache.get(name);
  } catch (e) {
    cache.delete(name);
    throw e;
  }
}
