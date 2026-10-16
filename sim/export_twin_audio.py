"""Sounds for the browser twin (docs/twin/audio), synthesised with numpy like the film's soundtrack: no samples, no
licences. The film's own synths (video/scripts/make_audio.py) give the tanpura drone, the siren and the chimes; the
street, the robot's motors, the auto-rickshaw, the dogs and the cow are new here.

  python sim/export_twin_audio.py        -> docs/twin/audio/*.mp3 + audio.json

Loops carry 0.1 s of extra sound at both ends, so the browser can loop the middle exactly (audio.json gives each
loop's start and end) whatever padding the MP3 encoder adds. The voice is not here: the twin reads its captions with
the visitor's own text-to-speech (Web Speech API).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "docs", "twin", "audio")
FILM_AUDIO = os.path.join(ROOT, "video", "public", "audio")
_spec = importlib.util.spec_from_file_location("make_audio", os.path.join(ROOT, "video", "scripts", "make_audio.py"))
MA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MA)
SR = MA.SR
MARGIN = 0.1
rng = np.random.default_rng(2026)
manifest = {}


# ----------------------------------------------------------------------------------------------- helpers
def t_axis(d):
    return np.arange(int(round(d * SR))) / SR


def lowpass(x, fc):
    """One-pole low-pass (a soft 6 dB/octave slope, enough for distance and rumble)."""
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def bandpass(x, f0, q):
    """RBJ biquad band-pass (constant peak gain)."""
    w = 2 * np.pi * f0 / SR
    alpha = np.sin(w) / (2 * q)
    b0, b2, a0, a1, a2 = alpha, -alpha, 1 + alpha, -2 * np.cos(w), 1 - alpha
    b0, b2, a1, a2 = b0 / a0, b2 / a0, a1 / a0, a2 / a0
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        o = b0 * v + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, o
        y[i] = o
    return y


def env(n, attack, release):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / release)


def seamless(x, loop_len, fade=0.25):
    """The first loop_len seconds of x, its start cross-faded with what follows, so it repeats without a seam."""
    L, C = int(round(loop_len * SR)), int(round(fade * SR))
    y = x[:L].copy()
    k = np.linspace(0, 1, C)[:, None] if x.ndim == 2 else np.linspace(0, 1, C)
    y[:C] = x[:C] * np.sin(k * np.pi / 2) + x[L:L + C] * np.cos(k * np.pi / 2)
    return y


def write(name, x, loop=False, kbps=64, stereo=False, gain_db=-1.0):
    """Normalise, add loop margins, encode to MP3 with ffmpeg and note the loop points."""
    x = np.asarray(x, np.float64)
    if stereo and x.ndim == 1:
        x = np.stack([x, x], 1)
    if not stereo and x.ndim == 2:
        x = x.mean(1)
    x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (gain_db / 20)
    entry = {"duration": round(len(x) / SR, 4)}
    if loop:
        m = int(MARGIN * SR)
        x = np.concatenate([x[-m:], x, x[:m]])
        entry.update(loopStart=MARGIN, loopEnd=round(MARGIN + entry["duration"], 4))
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    ch = 2 if stereo else 1
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(ch)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        dst = os.path.join(OUT, f"{name}.mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-codec:a", "libmp3lame", "-b:a", f"{kbps}k",
                        "-ac", str(ch), dst], check=True)
    entry["kb"] = round(os.path.getsize(dst) / 1024)
    manifest[name] = entry
    print(f"{name}.mp3: {entry['duration']:.2f} s{' loop' if loop else ''}, {entry['kb']} KB", flush=True)


def read_wav(path):
    with wave.open(path, "rb") as w:
        n, ch = w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float64) / 32767
    return x.reshape(-1, ch)


# ----------------------------------------------------------------------------------------------- music + street
def music_loop():
    """65 s of the film's tanpura drone: 25 cycles of the strings and 91 beats of the pulse, so it loops in time."""
    path = os.path.join(FILM_AUDIO, "music.wav")
    x = read_wav(path) if os.path.exists(path) else MA.music(95.0)
    s = int(20.0 * SR)
    return seamless(x[s:], 65.0, fade=1.5)


def horn(f1, f2, d):
    t = t_axis(d)
    x = np.sign(np.sin(2 * np.pi * f1 * t)) + 0.8 * np.sign(np.sin(2 * np.pi * f2 * t))
    return lowpass(x, 1400) * np.minimum(1, t / 0.01) * np.minimum(1, (d - t) / 0.03)


def crow(d=0.32):
    t = t_axis(d)
    f = 620 * (1 - 0.25 * t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.tanh(3 * np.sin(ph)) + 0.4 * rng.normal(0, 1, len(t))
    return bandpass(x, 1300, 2.5) * env(len(t), 0.02, 0.12)


def ambience(d=32.0):
    """A street a few houses away: traffic rumble, horns (the double beep), a scooter going by, crows."""
    n = int((d + 0.5) * SR)
    t = np.arange(n) / SR
    brown = np.cumsum(rng.normal(0, 1, n))
    brown -= lowpass(brown, 0.5)                                   # keep it from drifting
    rumble = lowpass(brown, 180) * (0.65 + 0.35 * np.sin(2 * np.pi * t / 11.0))
    rumble /= np.max(np.abs(rumble))
    mix = 0.55 * rumble
    for at, (f1, f2) in zip((2.3, 9.8, 17.1, 24.6, 28.9), ((410, 515), (380, 470), (440, 560), (395, 500), (420, 530))):
        h = np.concatenate([horn(f1, f2, 0.17), np.zeros(int(0.07 * SR)), horn(f1, f2, 0.22)])
        s = int(at * SR)
        mix[s:s + len(h)] += 0.11 * h
    sc = t_axis(4.5)                                               # a scooter passing in the distance
    f = 118 * (1.04 - 0.08 * sc / 4.5)
    whine = lowpass(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)), 900) * np.sin(np.pi * sc / 4.5) ** 2
    s = int(13.0 * SR)
    mix[s:s + len(whine)] += 0.16 * whine
    for at in (5.5, 5.9, 21.0, 21.5, 21.9):
        c = crow()
        s = int(at * SR)
        mix[s:s + len(c)] += 0.06 * c
    mix = MA.reverb(mix, 1.6, 0.25)
    return seamless(mix, d, fade=0.5)


# ----------------------------------------------------------------------------------------------- the robot
def motor(d=1.0):
    """Hub motors under load: a soft electric whir (narrow-band noise round a gear whine that wavers), a low hum and
    bearing hiss. Mostly noise, so it reads as machinery rather than a tone."""
    t = t_axis(d + 0.3)
    n = len(t)
    whir = bandpass(rng.normal(0, 1, n), 1350, 9.0) + 0.35 * bandpass(rng.normal(0, 1, n), 2700, 12.0)
    whir /= np.max(np.abs(whir))
    whine = 0.18 * np.sin(2 * np.pi * 1350 * t + 0.6 * np.sin(2 * np.pi * 3 * t))
    hum = 0.3 * np.sin(2 * np.pi * 95 * t) + 0.12 * np.sin(2 * np.pi * 190 * t)
    hiss = highpass(lowpass(rng.normal(0, 1, n), 2500), 800)
    hiss *= 0.1 / np.max(np.abs(hiss))
    return seamless(whir * 0.8 + whine + hum + hiss, d, 0.25)


def rumble(d=1.5):
    """Tyres on broken asphalt: low road noise with the odd crunch of gravel."""
    t = t_axis(d + 0.3)
    x = lowpass(rng.normal(0, 1, len(t)), 260)
    x /= np.max(np.abs(x))
    for at in rng.uniform(0, d + 0.3, 18):
        s = int(at * SR)
        g = bandpass(rng.normal(0, 1, int(0.012 * SR)), rng.uniform(1500, 3500), 3) * np.exp(-np.linspace(0, 6, int(0.012 * SR)))
        x[s:s + len(g)] += 0.6 * g[: len(x) - s]
    return seamless(x, d, 0.2)


def servo(d=0.8):
    t = t_axis(d + 0.3)
    x = np.sign(np.sin(2 * np.pi * 320 * t)) * 0.4 + np.sin(2 * np.pi * 640 * t) * 0.3
    x = bandpass(x, 900, 1.5) * (0.8 + 0.2 * np.sin(2 * np.pi * 20 * t))
    return seamless(x, d, 0.15)


def shutter():
    """The evidence photo: a camera click-clack."""
    out = np.zeros(int(0.22 * SR))
    for at, f, g in ((0.0, 3200, 1.0), (0.075, 2400, 0.7)):
        n = int(0.03 * SR)
        c = bandpass(rng.normal(0, 1, n), f, 4) * np.exp(-np.linspace(0, 9, n)) * g
        s = int(at * SR)
        out[s:s + n] += c
    return out


def otp():
    """OTP accepted: two beeps, then the lid's lock clacks open."""
    beep = MA.tone([1568], 0.07, 4) * np.minimum(1, t_axis(0.07) / 0.004)
    gap = np.zeros(int(0.06 * SR))
    clack_n = int(0.09 * SR)
    clack = (bandpass(rng.normal(0, 1, clack_n), 900, 2) + 0.6 * np.sin(2 * np.pi * 140 * np.arange(clack_n) / SR)) \
        * np.exp(-np.linspace(0, 8, clack_n))
    return np.concatenate([beep, gap, beep, np.zeros(int(0.16 * SR)), 0.8 * clack])


def blip(f0, f1, d=0.16, decay=14):
    t = t_axis(d)
    f = f0 + (f1 - f0) * np.minimum(1, t / (d * 0.5))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-decay * t) * np.minimum(1, t / 0.004)


def click():
    n = int(0.05 * SR)
    return bandpass(rng.normal(0, 1, n), 2000, 3) * np.exp(-np.linspace(0, 10, n)) + 0.3 * blip(1760, 1760, 0.05, 40)


# ----------------------------------------------------------------------------------------------- street life
def engine(d=2.0):
    """An auto-rickshaw's two-stroke: 42 exhaust pops a second through a short pipe, with rattle (loops every 2 s)."""
    n = int((d + 0.3) * SR)
    x = np.zeros(n)
    pop_n = int(0.022 * SR)
    tt = np.arange(pop_n) / SR
    pop = (np.sin(2 * np.pi * 110 * tt) + 0.5 * np.sin(2 * np.pi * 230 * tt) + 0.35 * rng.normal(0, 1, pop_n)) * np.exp(-tt / 0.006)
    for k in range(int((d + 0.3) * 42)):
        s = int((k / 42 + rng.normal(0, 0.0006)) * SR)
        if 0 <= s < n - pop_n:
            x[s:s + pop_n] += pop * rng.uniform(0.75, 1.0)
    x = lowpass(x, 2200)
    gate = 0.5 + 0.5 * np.sin(2 * np.pi * 42 * np.arange(n) / SR)
    rattle = bandpass(rng.normal(0, 1, n), 1800, 2.5) * gate ** 4              # loose panels shaking with each pop
    tick = bandpass(rng.normal(0, 1, n), 3200, 6.0) * gate ** 12               # the tappets' metallic tick
    norm = lambda v: v / np.max(np.abs(v))
    x = np.tanh(2.0 * (norm(highpass(x, 150)) + 0.8 * norm(rattle) + 0.35 * norm(tick)))   # small speakers can't do the low thud
    return seamless(highpass(x, 90), d, 0.2)


def glottal(f0, d, jitter=0.06, shimmer=0.22, sub=0.0, open_q=0.6):
    """Voice source made of single glottal pulses (Rosenberg shape, differentiated), each cycle's length and strength
    a little random (jitter, shimmer), optionally every other cycle weaker (a rough, growly voice). f0(t) in Hz."""
    n = int(d * SR)
    x = np.zeros(n + SR // 50)
    t, k = 0.0, 0
    while t < d:
        T = (1.0 / f0(t)) * (1 + jitter * rng.normal())
        T = max(T, 0.35 / f0(t))
        amp = max(0.15, 1 + shimmer * rng.normal()) * ((1 - sub) if k % 2 else 1.0)
        tp, tn = int(open_q * 0.66 * T * SR), int(open_q * 0.34 * T * SR)
        flow = np.concatenate([0.5 - 0.5 * np.cos(np.pi * np.arange(tp) / max(tp, 1)),
                               np.cos(0.5 * np.pi * np.arange(tn) / max(tn, 1))])
        pulse = np.diff(flow, prepend=0.0)
        i = int(t * SR)
        x[i:i + len(pulse)] += amp * pulse
        t += T
        k += 1
    return x[:n]


def formants(x, tracks):
    """Parallel resonators whose centre frequencies glide: tracks = [(f(t), bandwidth Hz, gain), ...]."""
    out = np.zeros_like(x)
    tt = np.arange(len(x)) / SR
    for fc, bw, g in tracks:
        f = fc(tt)
        r = np.exp(-np.pi * bw / SR)
        a1, a2 = 2 * r * np.cos(2 * np.pi * f / SR), -r * r
        y1 = y2 = 0.0
        y = np.empty_like(x)
        for i, v in enumerate(x):
            o = (1 - r) * v + a1[i] * y1 + a2 * y2
            y2, y1 = y1, o
            y[i] = o
        out += g * y
    return out


def highpass(x, fc):
    return x - lowpass(x, fc)


def street_echo(x):
    """Shop fronts a few metres away: three early reflections and a very short tail (outdoors, not a hall)."""
    y = np.concatenate([x, np.zeros(int(0.12 * SR))])
    for ms, g in ((11, 0.22), (23, 0.13), (38, 0.07)):
        s = int(ms / 1000 * SR)
        y[s:s + len(x)] += g * x
    return MA.reverb(y, 0.25, 0.06)


def bark(size, double=False):
    """A street dog's bark. size 'small' (the shiba inus: a sharp 'yap') or 'big' (the husky: a deep 'woof').
    A rough voice that jumps up and falls, breath noise, a burst at the start, and a mouth that opens then closes."""
    big = size == "big"
    d = 0.22 if big else 0.15

    def one(scale=1.0):
        f_peak, f_end = (430, 260) if big else (720, 470)
        f0 = lambda t: (f_end + (f_peak - f_end) * np.exp(-((t - 0.025) / 0.05) ** 2)) * scale * (0.85 + 0.15 * min(1, t / 0.02))
        src = glottal(f0, d, jitter=0.09 if big else 0.07, shimmer=0.3, sub=0.4 if big else 0.15, open_q=0.5)
        breath = rng.normal(0, 1, len(src)) * (0.3 if big else 0.2)
        k = np.linspace(0, 1, len(src))
        open_ = np.exp(-((k - 0.3) / 0.35) ** 2)                         # mouth opens, then closes again
        F = ((700, 1250, 2500) if big else (980, 1850, 3100))
        tracks = [(lambda t, f=F[0]: f * (0.75 + 0.35 * np.interp(t, np.linspace(0, d, len(open_)), open_)), 160, 1.0),
                  (lambda t, f=F[1]: f * (0.85 + 0.2 * np.interp(t, np.linspace(0, d, len(open_)), open_)), 200, 0.8),
                  (lambda t, f=F[2]: np.full_like(t, f), 300, 0.45)]
        voice = formants(src * 10 + breath * 0.12, tracks)
        burst = highpass(rng.normal(0, 1, int(0.008 * SR)), 1200) * np.exp(-np.linspace(0, 5, int(0.008 * SR)))
        voice[:len(burst)] += burst * 0.5 * np.max(np.abs(voice))
        shape = np.minimum(1, k * d / 0.004) * np.exp(-np.maximum(0, k * d - 0.035) / (0.05 if big else 0.035))
        return np.tanh(1.6 * voice / (np.max(np.abs(voice)) + 1e-9)) * shape
    b = one()
    if double:
        b = np.concatenate([b, np.zeros(int((0.11 if big else 0.08) * SR)), 0.8 * one(0.94)])
    return street_echo(highpass(b, 160))


def moo(d=1.9):
    """A cow's moo: a low, slightly rough voice that starts nasal ('mm') and opens into 'ooo', pitch rising then sagging."""
    f0 = lambda t: 100 + 32 * np.sin(np.pi * min(1.0, t / (0.55 * d))) - 20 * (t / d) ** 2
    src = glottal(f0, d, jitter=0.03, shimmer=0.12, sub=0.12, open_q=0.7)
    k = np.linspace(0, 1, len(src))
    open_ = np.clip((k - 0.08) / 0.27, 0, 1) ** 2 * (3 - 2 * np.clip((k - 0.08) / 0.27, 0, 1))
    at = lambda t: np.interp(t, np.linspace(0, d, len(open_)), open_)
    voice = formants(src * 6 + rng.normal(0, 1, len(src)) * 0.02,
                     [(lambda t: 270 + 280 * at(t), 90, 1.0), (lambda t: 880 + 170 * at(t), 130, 0.55),
                      (lambda t: np.full_like(t, 2350.0), 220, 0.12)])
    shape = np.minimum(1, k * d / 0.12) * np.minimum(1, (1 - k) * d / 0.35)
    voice = lowpass(np.tanh(1.2 * voice / np.max(np.abs(voice))) * shape, 2800)
    return street_echo(highpass(voice, 70))


# ----------------------------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    write("music", music_loop(), loop=True, kbps=80, stereo=True, gain_db=-1.0)
    write("ambience", ambience(), loop=True, kbps=48)
    write("motor", motor(), loop=True, kbps=56)
    write("rumble", rumble(), loop=True, kbps=48)
    write("servo", servo(), loop=True, kbps=48)
    write("engine", engine(), loop=True, kbps=56)
    write("siren", seamless(lowpass(MA.siren(3.6), 2600), 3.0, 0.3), loop=True, kbps=56)   # the film's, a little softer
    write("bark0", bark("small"), kbps=64)                         # the two shiba inus: a sharp 'yap'
    write("bark1", bark("small", double=True), kbps=64)
    write("bark2", bark("big"), kbps=64)                           # the husky: a deep 'woof'
    write("bark3", bark("big", double=True), kbps=64)
    write("moo", moo(), kbps=56)
    write("shutter", shutter(), kbps=56)
    write("otp", otp(), kbps=56)
    write("sense", blip(1175, 1320, 0.14), kbps=48)
    write("ai", np.concatenate([blip(880, 880, 0.08, 20), blip(1320, 1320, 0.12, 16)]), kbps=48)
    write("safety", np.concatenate([blip(660, 660, 0.07, 22), blip(990, 990, 0.14, 14)]), kbps=48)
    write("act", click(), kbps=48)
    write("ok", np.concatenate([MA.tone([1046.5], 0.12, 9), MA.tone([1318.5], 0.12, 9), MA.tone([1568, 2093], 0.6, 4)]), kbps=56)
    write("alarm", np.concatenate([MA.tone([880], 0.14, 10), MA.tone([1175], 0.3, 8)]), kbps=56)
    write("fail", MA.fail(), kbps=56)
    write("whoosh", MA.whoosh(), kbps=56)
    with open(os.path.join(OUT, "audio.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(f"total {sum(e['kb'] for e in manifest.values())} KB", flush=True)


if __name__ == "__main__":
    sys.exit(main())
