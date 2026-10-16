"""Synthesise the soundtrack and sound effects for the Bharat-Bot film (numpy only, no samples, no licences).

  python video/scripts/make_audio.py      -> video/public/audio/*.wav

music.wav : ~3 min tanpura-style drone (Karplus-Strong plucked strings on Pa-Sa'-Sa'-Sa) over a soft sub pad
            and a gentle electronic pulse.
sfx       : whoosh, ping, alert, siren, fail (low buzzer), success (rising chime).
"""
import os
import wave

import numpy as np

SR = 48000
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "audio")
rng = np.random.default_rng(7)


def save(name, x):
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    peak = np.max(np.abs(x)) + 1e-9
    x = x / peak * 0.89
    pcm = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{name}: {len(x) / SR:.1f} s")


def karplus(freq, dur, decay=0.996, bright=0.5):
    n = int(dur * SR)
    period = int(SR / freq)
    buf = rng.uniform(-1, 1, period) * (1 - bright) + np.sign(rng.uniform(-1, 1, period)) * bright
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = decay * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return out


def jawari(x):
    """The tanpura's buzzing bridge: a little soft clipping adds the shimmering overtones."""
    return np.tanh(2.2 * x) * 0.7 + x * 0.3


def reverb(x, seconds=2.2, mix=0.32):
    n = int(seconds * SR)
    ir = rng.normal(0, 1, n) * np.exp(-np.linspace(0, 7, n))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    wet /= np.max(np.abs(wet)) + 1e-9
    return x * (1 - mix) + wet * mix * np.max(np.abs(x))


def music(total=190.0):
    n = int(total * SR)
    mix = np.zeros(n)
    sa = 138.59                                   # C#3: a common male tanpura pitch
    notes = [sa * 1.5, sa * 2, sa * 2, sa]        # Pa, Sa', Sa', Sa
    cycle, t = 2.6, 0.0
    strings = {f: jawari(karplus(f, 3.2, 0.9985, 0.35)) for f in set(notes)}
    while t < total - 3.3:
        for k, f in enumerate(notes):
            s = int((t + k * cycle / 4) * SR)
            pluck = strings[f] * (0.8 + 0.2 * rng.random())
            e = min(n, s + len(pluck))
            mix[s:e] += pluck[: e - s]
        t += cycle
    tt = np.arange(n) / SR
    pad = 0.18 * np.sin(2 * np.pi * sa / 2 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 9.0))
    pad += 0.08 * np.sin(2 * np.pi * sa * 0.75 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * tt / 13.0 + 1.0))
    beat = 60 / 84                                # soft pulse at 84 bpm
    pulse = np.zeros(n)
    kick = np.sin(2 * np.pi * 55 * np.arange(int(0.25 * SR)) / SR) * np.exp(-np.linspace(0, 9, int(0.25 * SR)))
    for b in np.arange(8 * beat, total - 6, beat):
        s = int(b * SR)
        pulse[s:s + len(kick)] += kick * (0.55 if int(round(b / beat)) % 4 == 0 else 0.3)
    left = reverb(mix * 0.55 + pad) + pulse
    right = reverb(np.roll(mix, int(0.012 * SR)) * 0.55 + pad) + pulse
    fade = np.minimum(1, np.minimum(tt / 3.0, (total - tt) / 4.0))
    return np.stack([left * fade, right * fade], 1)


def whoosh(d=0.9):
    n = int(d * SR)
    noise = rng.normal(0, 1, n)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    cut = np.linspace(0.02, 0.35, n)
    y, acc = np.zeros(n), 0.0
    for i in range(n):                            # sweeping one-pole low-pass
        acc += cut[i] * (noise[i] - acc)
        y[i] = acc
    return y * env


def tone(freqs, d, decay=6.0):
    t = np.arange(int(d * SR)) / SR
    return sum(np.sin(2 * np.pi * f * t) for f in freqs) * np.exp(-decay * t)


def siren(d=3.0):
    t = np.arange(int(d * SR)) / SR
    f = 700 + 500 * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 2.0 * t)))
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sign(np.sin(phase)) * 0.35 + np.sin(phase) * 0.65


def fail(d=0.7):
    t = np.arange(int(d * SR)) / SR
    return (np.sign(np.sin(2 * np.pi * 110 * t)) * 0.5 + np.sin(2 * np.pi * 82 * t)) * np.exp(-2.5 * t)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    save("music.wav", music())
    save("whoosh.wav", whoosh())
    save("ping.wav", tone([1318.5, 1975.5], 0.6, 7))
    save("alert.wav", np.concatenate([tone([880], 0.14, 10), tone([1175], 0.3, 8)]))
    save("siren.wav", siren())
    save("fail.wav", fail())
    save("success.wav", np.concatenate([tone([1046.5], 0.12, 9), tone([1318.5], 0.12, 9), tone([1568, 2093], 0.6, 4)]))
