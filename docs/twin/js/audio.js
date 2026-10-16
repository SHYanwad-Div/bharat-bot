// Bharat-Bot twin: sound. Effects and the film's tanpura drone (sim/export_twin_audio.py, all synthesised) are placed
// in 3D with Web Audio and driven by the same simulation frames as the picture: motors by wheel speed, the siren by
// the alarm, barks on the frames the dogs bark, a blip for each control-room decision. The voice reads the captions
// with the visitor's own text-to-speech (Web Speech API), preferring an Indian English voice, so no voice files ship.
import * as THREE from 'three';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const LOOPS = ['music', 'ambience', 'motor', 'rumble', 'servo', 'engine', 'siren'];
const SHOTS = ['bark0', 'bark1', 'bark2', 'bark3', 'moo', 'shutter', 'otp', 'sense', 'ai', 'safety', 'act', 'ok', 'alarm', 'fail', 'whoosh'];
const RANK = { ALARM: 6, OK: 5, ACT: 4, SAFETY: 3, AI: 2, SENSE: 1, INFO: 0 };
// mix (0..1): the voice is the star; effects sit under it, the music well under that
const BLIP = { ALARM: ['alarm', 0.3], OK: ['ok', 0.22], ACT: ['act', 0.22], SAFETY: ['safety', 0.13], AI: ['ai', 0.12], SENSE: ['sense', 0.1], INFO: ['sense', 0.07] };
const MIX = { music: 0.1, musicUnderVoice: 0.4, street: 0.24, streetPaused: 0.14, motor: { bharat: 0.28, baseline: 0.34 },
  rumble: { bharat: 0.3, baseline: 0.42 }, servo: 0.35, siren: 0.5, engine: 0.7, bark: 1.0, moo: 0.65, mooEvery: 21,
  shutter: 0.9, otp: 0.8, fail: 0.38, delivered: 0.4 };

export class Sound {
  constructor(camera) {
    this.listener = new THREE.AudioListener();
    camera.add(this.listener);
    this.ctx = this.listener.context;
    this.on = { master: true, fx: true, music: true };
    this.buffers = {};
    this.meta = {};
    this.ready = false;
    this.started = false;
    this.duck = 1;
    const bus = () => { const g = this.ctx.createGain(); g.connect(this.listener.getInput()); return g; };
    this.musicBus = bus();
    this.fxBus = bus();
    this.uiBus = bus();
    this.lastBark = [0, 0, 0];
  }

  async load() {
    const meta = await fetch('audio/audio.json').then((r) => r.json());
    this.meta = meta;
    await Promise.all([...LOOPS, ...SHOTS].map(async (name) => {
      const data = await fetch(`audio/${name}.mp3`).then((r) => { if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`); return r.arrayBuffer(); });
      this.buffers[name] = await this.ctx.decodeAudioData(data);
    }));
    this.ready = true;
    if (this.wantStart) this.start(this.wantStart);
  }

  // a looping source: plain (music, street) or placed in the scene (motors, engine, siren)
  loop(name, parent, { ref = 4, vol = 0 } = {}) {
    const a = parent ? new THREE.PositionalAudio(this.listener) : new THREE.Audio(this.listener);
    a.setBuffer(this.buffers[name]);
    a.setLoop(true);
    const m = this.meta[name];
    if (m?.loopStart) { a.setLoopStart(m.loopStart); a.setLoopEnd(m.loopEnd); a.offset = m.loopStart; }
    a.gain.disconnect();                       // route through our bus instead of straight to the listener
    a.gain.connect(name === 'music' ? this.musicBus : this.fxBus);
    if (parent) {
      a.setRefDistance(ref);
      a.setRolloffFactor(1.2);
      parent.add(a);
    }
    a.setVolume(vol);
    a.play();
    return a;
  }

  // one emitter in the scene for short sounds (a bark, the camera click)
  emitter(parent, ref = 5) {
    const a = new THREE.PositionalAudio(this.listener);
    a.setRefDistance(ref);
    a.setRolloffFactor(1.2);
    a.gain.disconnect();
    a.gain.connect(this.fxBus);
    parent.add(a);
    return a;
  }

  fire(a, name, vol = 1, rate = 1) {
    if (!this.buffers[name]) return;
    if (a.isPlaying) a.stop();
    a.setBuffer(this.buffers[name]);
    a.setLoop(false);
    a.setVolume(vol);
    a.setPlaybackRate(rate);
    a.play();
  }

  // control-room blips and chimes: not placed, straight to the speakers
  ui(name, vol) {
    if (!this.buffers[name] || !this.on.master || !this.on.fx) return;
    const s = this.ctx.createBufferSource();
    s.buffer = this.buffers[name];
    const g = this.ctx.createGain();
    g.gain.value = vol;
    s.connect(g).connect(this.uiBus);
    s.start();
  }

  // call from a click or key press (browsers only start sound after the visitor does something)
  start(scene) {
    this.wantStart = scene;
    if (this.ctx.state !== 'running') this.ctx.resume();
    if (!this.ready || this.started) return;
    this.started = true;
    const { rigs, dogs, cow, auto } = scene;
    this.music = this.loop('music');
    this.street = this.loop('ambience');
    this.robot = new THREE.Group();
    this.motor = this.loop('motor', this.robot, { ref: 3.5 });
    this.rumble = this.loop('rumble', this.robot, { ref: 3.5 });
    this.servo = this.loop('servo', this.robot, { ref: 3 });
    this.siren = this.loop('siren', this.robot, { ref: 7 });
    this.robotShot = this.emitter(this.robot, 4);
    this.engine = this.loop('engine', auto.root, { ref: 6 });
    this.dogVoices = dogs.map((d) => this.emitter(d.root, 5));
    this.cowVoice = this.emitter(cow.root, 7);
    this.rigs = rigs;
    this.apply();
  }

  setRig(rig) { if (this.robot && this.robot.parent !== rig.root) rig.root.add(this.robot); }

  set(key, on) { this.on[key] = on; this.apply(); }
  apply() {
    const m = this.on.master;
    const at = this.ctx.currentTime;
    this.musicBus.gain.setTargetAtTime(m && this.on.music ? MIX.music * this.duck : 0, at, 0.25);
    this.fxBus.gain.setTargetAtTime(m && this.on.fx ? 1 : 0, at, 0.05);
    this.uiBus.gain.setTargetAtTime(m && this.on.fx ? 0.8 : 0, at, 0.05);
  }
  ducking(on) { this.duck = on ? MIX.musicUnderVoice : 1; this.apply(); }

  // every frame: s = { run, u, prevU, playing, rig, explode }
  update(s) {
    if (!this.started) return;
    const { run, u, playing, rig } = s;
    this.setRig(rig);
    const live = playing && !s.explode;
    const R = run.R, fps = run.fps, k = run.idx(u), k0 = Math.max(0, k - 1);
    const wheel = Math.abs(R.spinL[k] - R.spinL[k0] + R.spinR[k] - R.spinR[k0]) / 2 * fps * rig.r;   // m/s at the tyres
    const v = Math.max(0, run.lerp(R.v, u));
    const bharat = rig.kind === 'bharat';
    const kind = bharat ? 'bharat' : 'baseline';
    this.motor.setVolume(live ? clamp(wheel / 1.6, 0, 1.3) * MIX.motor[kind] : 0);
    this.motor.setPlaybackRate((bharat ? 0.72 : 1.0) + 0.45 * clamp(wheel / 1.6, 0, 1.4));
    this.rumble.setVolume(live ? clamp(v / 1.6, 0, 1) * MIX.rumble[kind] : 0);
    this.rumble.setPlaybackRate(0.8 + 0.4 * clamp(v / 1.6, 0, 1));
    const lid = Math.abs(R.lid[k] - R.lid[k0]) * fps;
    this.servo.setVolume(live ? clamp(lid / 1.2, 0, 1) * MIX.servo : 0);
    this.siren.setVolume(live && run.at(R.alarm, u) > 0 ? MIX.siren : 0);
    const A = run.auto;
    const autoV = Math.abs(A.spin[k] - A.spin[k0]) * fps * 0.2;
    this.engine.setVolume(live && A.active[k] > 0 ? MIX.engine : 0);
    this.engine.setPlaybackRate(0.8 + autoV / 14);
    this.street.setVolume(this.on.fx ? (playing ? MIX.street : MIX.streetPaused) : 0);
    this.music.setVolume(1);
    // what happened on the frames just played (not on jumps or rewinds)
    const step = u - s.prevU;
    if (!live || step <= 0 || step > 45) return;
    const f0 = Math.floor(s.prevU), f1 = Math.floor(u);
    if (f1 <= f0) return;
    const now = performance.now();
    for (const [f, d] of run.barks) {
      if (f <= f0 || f > f1 || now - this.lastBark[d] < 160) continue;
      this.lastBark[d] = now;
      const shiba = d !== 1;
      const pick = (f * 7 + d * 3) % 2;
      this.fire(this.dogVoices[d], shiba ? `bark${pick}` : `bark${2 + pick}`, MIX.bark, d === 2 ? 1.06 : 1);
    }
    let lead = null;
    for (const e of run.events) {
      if (e.f <= f0 || e.f > f1) continue;
      if (!lead || RANK[e.level] > RANK[lead.level]) lead = e;
      if (/^Photo \+ live GPS/.test(e.title)) this.fire(this.robotShot, 'shutter', MIX.shutter);
      if (/^OTP .* verified/.test(e.title)) this.fire(this.robotShot, 'otp', MIX.otp);
    }
    if (lead) {
      const failed = lead.level === 'ALARM' && run.robot === 'baseline';
      const [name, vol] = failed ? ['fail', MIX.fail] : /^DELIVERED/.test(lead.title) ? ['ok', MIX.delivered] : BLIP[lead.level];
      this.ui(name, vol);
    }
    // the cow in the lane moos now and then
    const per = MIX.mooEvery * fps;
    if (Math.floor((f1 + 6 * fps) / per) > Math.floor((f0 + 6 * fps) / per)) this.fire(this.cowVoice, 'moo', MIX.moo);
  }

  pause() { this.ctx.suspend(); }
  resume() { if (this.started) this.ctx.resume(); }
}

// ── the voice ───────────────────────────────────────────────────────────────────────────────────────────────────
// captions are written for reading; say units and short forms the way a person would
// a size before a noun is singular ('a 12 cm hump' is a 12-centimetre hump); before 'deep', 'ahead'... it is plural
const PLURAL_NEXT = '(?:deep|wide|long|high|tall|ahead|back|away|of|to|and|in|or|on|at|by)\\b';
const SPOKEN = [[new RegExp(`(\\d+(?:\\.\\d+)?)\\s?cm\\b(?=\\s+(?!${PLURAL_NEXT})[a-z])`, 'g'), '$1 centimetre'],
  [/(\d+(?:\.\d+)?)\s?cm\b/g, '$1 centimetres'], [/(\d+(?:\.\d+)?)\s?m\b/g, '$1 metres'], [/\bIP67\b/g, 'I P 67'],
  [/(\d+(?:\.\d+)?)\s?s\b/g, '$1 seconds'], [/(\d+)\s?dB\b/g, '$1 decibel'], [/km\/h/g, 'kilometres an hour'],
  [/\bOTP\b/g, 'O T P'], [/\bIMU\b/g, 'I M U'], [/\bGPS\b/g, 'G P S'], [/\bAI\b/g, 'A I'], [/·/g, ','], [/–/g, ' to ']];
export const speakable = (text) => SPOKEN.reduce((s, [re, to]) => s.replace(re, to), text);

export class Narrator {
  constructor(onSpeaking) {
    this.synth = window.speechSynthesis || null;
    this.ok = !!this.synth && typeof SpeechSynthesisUtterance !== 'undefined';
    this.on = true;
    this.voice = null;
    this.wanted = '';
    this.pending = null;
    this.speaking = false;
    this.onSpeaking = onSpeaking || (() => {});
    if (this.ok) {
      this.pickVoice();
      this.synth.addEventListener?.('voiceschanged', () => this.pickVoice());
    }
  }
  english() { return this.ok ? this.synth.getVoices().filter((v) => /^en([-_]|$)/i.test(v.lang)) : []; }
  // the visitor's choice if set; otherwise natural-sounding Indian English, then any natural English voice
  pickVoice() {
    const vs = this.english();
    if (!vs.length) return;
    const chosen = vs.find((v) => v.name === this.wanted);
    const score = (v) => (/en[-_]IN/i.test(v.lang) ? 3 : /en[-_]GB/i.test(v.lang) ? 1.5 : /en[-_]US/i.test(v.lang) ? 1 : 0.5)
      + (/natural|neural|online|google|premium|enhanced|siri/i.test(v.name) ? 2.5 : 0);
    this.voice = chosen || vs.slice().sort((a, b) => score(b) - score(a))[0];
  }
  setVoice(name) { this.wanted = name; this.pickVoice(); }
  // browsers (iOS above all) allow speech only after a tap: say nothing, inside the tap
  unlock() {
    if (!this.ok) return;
    const u = new SpeechSynthesisUtterance(' ');
    u.volume = 0;
    this.synth.speak(u);
  }
  say(text, rate = 1) {
    if (!this.ok || !this.on || !text) return;
    if (this.speaking) { this.pending = { text, rate, at: performance.now() }; return; }
    this.speak(text, rate);
  }
  speak(text, rate) {
    const u = new SpeechSynthesisUtterance(speakable(text));
    if (this.voice) { u.voice = this.voice; u.lang = this.voice.lang; } else u.lang = 'en-IN';
    u.rate = rate;
    u.pitch = 1;
    u.onstart = () => { this.speaking = true; this.onSpeaking(true); };
    const done = () => {
      if (this.utterance !== u) return;
      this.speaking = false;
      this.onSpeaking(false);
      const p = this.pending;
      this.pending = null;
      if (p && performance.now() - p.at < 6000 && this.on) this.speak(p.text, p.rate);   // a stale line is dropped
    };
    u.onend = done;
    u.onerror = done;
    this.utterance = u;
    this.speaking = true;
    this.synth.speak(u);
  }
  stop() {
    if (!this.ok) return;
    this.pending = null;
    this.utterance = null;
    this.speaking = false;
    this.synth.cancel();
    this.onSpeaking(false);
  }
}
