"""Instrumentos para la banda sonora: sampler (VSCO-2-CE, CC0) y sintetizadores propios."""

import functools
import glob
import os
import re

import numpy as np
import soundfile as sf
from numba import njit

import dsp
from common import SAMPLES

SR = dsp.SR
NOTE_PC = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def vsco_midi(note, octave):
    """VSCO usa la convención Do central = C3."""
    return (int(octave) + 2) * 12 + NOTE_PC[note]


@functools.lru_cache(maxsize=None)
def load_sample(path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    return dsp.resample(x.astype(np.float64), sr, SR)


@functools.lru_cache(maxsize=4096)
def pitched(path, semis):
    return dsp.pitch_shift_resample(load_sample(path), semis)


def loop_extend(x, needed, xfade=0.5, start=1.0, seed=0):
    """Alarga un sustain encadenando fragmentos internos con fundidos de potencia constante."""
    if len(x) >= needed:
        return x
    rng = np.random.default_rng(seed)
    xf = int(xfade * SR)
    a = int(start * SR)
    b = max(a + 3 * xf, len(x) - int(1.2 * SR))
    out = x[: b].copy()
    fade_in = np.sin(np.linspace(0, np.pi / 2, xf)) ** 1
    fade_out = np.cos(np.linspace(0, np.pi / 2, xf)) ** 1
    while len(out) < needed:
        s = rng.integers(a, max(a + 1, b - 3 * xf))
        seg = x[s:b]
        out[-xf:] = out[-xf:] * fade_out + seg[:xf] * fade_in
        out = np.concatenate([out, seg[xf:]])
    return out


class Sampler:
    def __init__(self, folder, regex, gain=1.0, name=""):
        self.name = name or folder
        self.gain = gain
        self.zones = []
        for f in glob.glob(os.path.join(SAMPLES, folder, "*.wav")):
            m = re.search(regex, os.path.basename(f))
            if not m:
                continue
            gd = m.groupdict()
            midi = vsco_midi(gd["note"], gd["oct"])
            vel = int(gd["vel"]) if gd.get("vel") else 1
            rr = int(gd["rr"]) if gd.get("rr") else 1
            self.zones.append((midi, vel, rr, f))
        if not self.zones:
            raise RuntimeError(f"Sin samples en {folder}")
        self.vels = sorted(set(z[1] for z in self.zones))
        self.rng = np.random.default_rng(abs(hash(folder)) % 2**32)

    def pick(self, midi, velocity):
        vi = self.vels[min(len(self.vels) - 1, int(np.clip(velocity, 0, 0.999) * len(self.vels)))]
        cands = [z for z in self.zones if z[1] == vi]
        best = min(abs(z[0] - midi) for z in cands)
        cands = [z for z in cands if abs(z[0] - midi) == best]
        return cands[self.rng.integers(len(cands))]

    def note(self, midi, dur=None, velocity=0.7, attack=0.0, release=0.4, gain=1.0, offset=0.0):
        """dur=None: suena el sample completo (staccato/one-shot)."""
        zmidi, _, _, path = self.pick(midi, velocity)
        x = pitched(path, int(midi - zmidi))
        if offset > 0:
            x = x[int(offset * SR) :]
        if dur is not None:
            need = int((dur + release) * SR)
            x = loop_extend(x, need, seed=int(midi * 7 + dur * 13))
            x = x[:need].copy()
            env = np.ones(len(x))
            r0 = int(dur * SR)
            rl = len(x) - r0
            if rl > 0:
                env[r0:] = np.cos(np.linspace(0, np.pi / 2, rl)) ** 2
            if attack > 0:
                k = min(len(x), int(attack * SR))
                env[:k] *= np.sin(np.linspace(0, np.pi / 2, k)) ** 2
            x = x * env
        else:
            x = x.copy()
            if attack > 0:
                k = min(len(x), int(attack * SR))
                x[:k] *= np.sin(np.linspace(0, np.pi / 2, k)) ** 2
        vel_gain = 0.35 + 0.65 * velocity
        return x * gain * self.gain * vel_gain


# ------------------------------------------------------------------ osciladores
@njit(cache=True)
def _polyblep(t, dt):
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    elif t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


@njit(cache=True)
def saw(freq, phase0):
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase0
    for i in range(n):
        dt = freq[i] / 48000.0
        out[i] = 2.0 * ph - 1.0 - _polyblep(ph, dt)
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
    return out


@njit(cache=True)
def svf(x, cutoff, q, mode):
    """Filtro de estado variable con frecuencia de corte por muestra. mode: 0=LP 1=BP 2=HP."""
    n = x.shape[0]
    out = np.empty(n)
    ic1 = 0.0
    ic2 = 0.0
    for i in range(n):
        g = np.tan(np.pi * min(cutoff[i], 20000.0) / 48000.0)
        k = 1.0 / q[i]
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            out[i] = v2
        elif mode == 1:
            out[i] = v1
        else:
            out[i] = x[i] - k * v1 - v2
    return out


def pink(n, rng):
    w = rng.standard_normal(n)
    f = np.fft.rfft(w)
    k = np.arange(len(f))
    k[0] = 1
    f /= np.sqrt(k)
    p = np.fft.irfft(f, n)
    return p / (np.std(p) + 1e-9)


def env_adsr(n, a, d, s, r_start, r, sr=SR):
    e = np.zeros(n)
    t = np.arange(n) / sr
    e = np.where(t < a, (t / max(a, 1e-4)), 1.0)
    dec = np.clip((t - a) / max(d, 1e-4), 0, 1)
    e = np.where(t >= a, 1 - (1 - s) * dec, e)
    rel = np.clip((t - r_start) / max(r, 1e-4), 0, 1)
    return e * (1 - rel)


# ------------------------------------------------------------------ coro sintético
FORMANTS = {
    # (frecuencia, ancho de banda, ganancia dB)
    "a_m": [(730, 90, 0), (1090, 110, -5), (2440, 150, -16), (3400, 200, -24), (4100, 250, -30)],
    "a_f": [(850, 90, 0), (1220, 110, -6), (2810, 160, -18), (3300, 200, -26), (4500, 250, -32)],
    "o_m": [(500, 80, 0), (850, 90, -8), (2450, 140, -24), (3300, 180, -30)],
    "u_m": [(330, 70, 0), (870, 90, -14), (2250, 140, -28)],
}


def choir_note(midi, dur, velocity=0.6, vowel="a", voices=7, attack=1.2, release=2.2, seed=0, breath=0.05):
    rng = np.random.default_rng(seed + int(midi * 31))
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    f0 = mtof(midi)
    key = vowel + ("_f" if midi >= 64 and vowel == "a" else "_m")
    if key not in FORMANTS:
        key = vowel + "_m"
    out = np.zeros((n, 2))
    for v in range(voices):
        cents = rng.normal(0, 9)
        rate = rng.uniform(4.6, 5.8)
        depth = rng.uniform(0.003, 0.006)
        drift = np.interp(t, np.linspace(0, t[-1] + 1e-6, 8), rng.normal(0, 0.0025, 8))
        vib_on = np.clip(t / 0.8, 0, 1)
        freq = f0 * 2 ** (cents / 1200) * (1 + vib_on * depth * np.sin(2 * np.pi * rate * t + rng.uniform(0, 6.28)) + drift)
        osc = saw(freq, rng.uniform(0, 1))
        # pulso ligeramente más "vocal": mezcla con versión desfasada (onda menos brillante)
        osc = 0.7 * osc + 0.3 * np.roll(osc, int(SR / f0 / 3))
        p = rng.uniform(-0.8, 0.8)
        out += dsp.pan(osc, p)
    noise = rng.standard_normal((n, 2)) * breath * voices
    src = out + noise
    y = np.zeros_like(src)
    for fq, bw, g in FORMANTS[key]:
        q = fq / bw
        b = dsp._biquad(*_bandpass_coefs(fq, q))
        y += dsp.eq(src, b) * 10 ** (g / 20)
    y = dsp.lp(y, 6000, order=2)
    e = np.ones(n)
    ka = int(attack * SR)
    e[:ka] = np.sin(np.linspace(0, np.pi / 2, ka)) ** 2
    kr = int(release * SR)
    e[-kr:] = np.cos(np.linspace(0, np.pi / 2, kr)) ** 2
    amp = velocity * 0.6 / np.sqrt(voices)
    return y * e[:, None] * amp


def _bandpass_coefs(f0, q):
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    return (alpha, 0.0, -alpha, 1 + alpha, -2 * np.cos(w0), 1 - alpha)


def choir_chord(notes, dur, velocity=0.6, vowel="a", attack=1.5, release=2.5, seed=0, voices=7):
    parts = [choir_note(m, dur, velocity, vowel, voices, attack, release, seed + i * 17) for i, m in enumerate(notes)]
    n = max(len(p) for p in parts)
    out = np.zeros((n, 2))
    for p in parts:
        out[: len(p)] += p
    return out


# ------------------------------------------------------------------ pads sintéticos
def saw_pad(notes, dur, velocity=0.5, cutoff=1200, attack=1.0, release=2.0, detune=12, voices=4, seed=0):
    rng = np.random.default_rng(seed)
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for m in notes:
        for v in range(voices):
            c = (v - (voices - 1) / 2) * detune / max(1, voices - 1) * 2
            freq = np.full(n, mtof(m) * 2 ** (c / 1200))
            osc = saw(freq, rng.uniform(0, 1))
            out += dsp.pan(osc, (v / max(1, voices - 1)) * 1.6 - 0.8)
    cut = np.full(n, float(cutoff))
    q = np.full(n, 0.8)
    for ch in range(2):
        out[:, ch] = svf(out[:, ch], cut, q, 0)
    e = np.ones(n)
    ka = int(attack * SR)
    e[:ka] = np.sin(np.linspace(0, np.pi / 2, ka)) ** 2
    kr = int(release * SR)
    e[-kr:] = np.cos(np.linspace(0, np.pi / 2, kr)) ** 2
    return out * e[:, None] * velocity * 0.15 / np.sqrt(len(notes) * voices)


def sub_bass(midi, dur, velocity=0.6, attack=0.05, release=0.6):
    n = int((dur + release) * SR)
    t = np.arange(n) / SR
    f = mtof(midi)
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    x = dsp.saturate(x * 0.8, 0.6)
    e = env_adsr(n, attack, 0.2, 0.85, dur, release)
    return x * e * velocity * 0.5


def braam(midi, dur, velocity=0.9, seed=0):
    """'Braam' de tráiler: metal grave sintético con filtro que se abre y saturación."""
    rng = np.random.default_rng(seed)
    n = int((dur + 1.5) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in (midi, midi + 12, midi + 19):
        for v in range(5):
            freq = np.full(n, mtof(m) * 2 ** (rng.normal(0, 8) / 1200))
            out += saw(freq, rng.uniform(0, 1)) * (1.0 if m == midi else 0.6)
    cutoff = 150 + 1800 * np.clip(t / 0.35, 0, 1) ** 1.5 * np.exp(-np.clip(t - 0.35, 0, None) / max(dur, 0.5) * 1.2)
    y = svf(out, cutoff, np.full(n, 1.4), 0)
    y = dsp.saturate(y * 0.25, 2.5)
    e = env_adsr(n, 0.04, 0.4, 0.75, dur, 1.4)
    y = y * e * velocity * 0.35
    return dsp.pan(y, 0)


# ------------------------------------------------------------------ percusión y efectos sintéticos
def boom(velocity=1.0, f_start=62, f_end=28, decay=2.6, click=0.6, seed=0):
    rng = np.random.default_rng(seed)
    n = int((decay * 1.6 + 0.2) * SR)
    t = np.arange(n) / SR
    f = f_end + (f_start - f_end) * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / (decay * 0.45))
    body = dsp.saturate(body * 1.6, 2.6) * 0.8
    clk = rng.standard_normal(n) * np.exp(-t / 0.012) * click
    clk = dsp.bp(clk, 500, 4000)
    y = body + clk
    return dsp.pan(y * velocity * 0.9, 0)


def taiko(velocity=1.0, pitch=72, decay=0.7, seed=0):
    rng = np.random.default_rng(seed)
    n = int((decay * 2.5) * SR)
    t = np.arange(n) / SR
    modes = [(1.0, 1.0), (1.59, 0.45), (2.14, 0.3), (2.30, 0.22), (2.65, 0.15), (2.92, 0.1)]
    y = np.zeros(n)
    bend = 1 + 0.35 * np.exp(-t / 0.05)
    for ratio, amp in modes:
        ph = 2 * np.pi * np.cumsum(pitch * ratio * bend) / SR
        y += amp * np.sin(ph + rng.uniform(0, 6.28)) * np.exp(-t / (decay / ratio**0.7))
    stick = dsp.bp(rng.standard_normal(n), 300, 3000) * np.exp(-t / 0.02) * 0.5
    y = dsp.saturate((y + stick) * 0.9, 0.8)
    return dsp.pan(y * velocity * 0.8, rng.uniform(-0.15, 0.15))


def noise_sweep(dur, f0, f1, f2=None, q=2.0, curve=2.0, seed=0, peak_at=0.7, pan_from=0.0, pan_to=0.0):
    """Ruido filtrado con frecuencia que barre (base de whooshes y risers)."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    if f2 is None:
        cutoff = f0 * (f1 / f0) ** (t**curve)
    else:
        up = t < peak_at
        cutoff = np.where(up, f0 * (f1 / f0) ** ((t / peak_at) ** curve), f1 * (f2 / f1) ** ((np.clip(t - peak_at, 0, None) / (1 - peak_at)) ** 0.8))
    src = pink(n, rng) * 0.5 + rng.standard_normal(n) * 0.5
    y = svf(src, cutoff, np.full(n, q), 1)
    p = pan_from + (pan_to - pan_from) * t
    a = (p + 1) * np.pi / 4
    return np.stack([y * np.cos(a), y * np.sin(a)], axis=1)


def whoosh(dur=0.9, velocity=0.7, seed=0, direction=1, bright=1.0):
    peak = 0.62
    y = noise_sweep(dur, 220 * bright, 3800 * bright, 700, q=1.6, curve=1.6, seed=seed, peak_at=peak, pan_from=-0.7 * direction, pan_to=0.7 * direction)
    t = np.linspace(0, 1, y.shape[0])
    env = np.where(t < peak, (t / peak) ** 2.2, np.exp(-(t - peak) / (1 - peak) * 4))
    return y * env[:, None] * velocity * 0.9


def riser(dur=4.0, velocity=0.8, seed=0, shepard=True, noise=True):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    out = np.zeros((n, 2))
    if noise:
        y = noise_sweep(dur, 250, 9000, q=1.2, curve=1.8, seed=seed)
        out += y * (t**2.4)[:, None] * 0.8
    if shepard:
        tt = np.arange(n) / SR
        base = 55.0
        layers = 7
        semis = 12 * t**1.3  # sube una octava en total
        for k in range(layers):
            lf = np.log2(base) + k + semis / 12
            f = 2**lf
            centre = np.log2(base) + layers / 2
            amp = np.exp(-((lf - centre) ** 2) / 2.2)
            ph = 2 * np.pi * np.cumsum(f) / SR
            s = np.sin(ph) * amp * 0.18
            out += np.stack([s, np.roll(s, 37)], axis=1)
        out[:, :] *= (0.15 + 0.85 * t**1.6)[:, None]
    return out * velocity


def reverse_tail(x, land_len=None):
    """Invierte un sonido (p. ej. un plato) para que 'aterrice' al final."""
    y = x[::-1].copy()
    return y


def thunder(dur=4.0, velocity=0.7, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    src = pink(n, rng)
    # crujidos iniciales + retumbe largo
    crack = dsp.bp(rng.standard_normal(n), 800, 5000) * np.exp(-t / 0.08) * (rng.random(n) < 0.02)
    rumble = dsp.lp(src, 180, order=4) * (np.exp(-t / (dur * 0.35)))
    am = 0.6 + 0.4 * np.interp(t, np.linspace(0, dur, 30), rng.random(30))
    y = rumble * am * 2.5 + crack * 3
    y = dsp.saturate(y * 0.7, 0.5)
    return np.stack([y, np.roll(y, 211)], axis=1) * velocity


def wind(dur, velocity=0.4, seed=0, base=420, spread=280):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for ch in range(2):
        src = pink(n, rng)
        lfo = np.interp(t, np.linspace(0, dur, max(4, int(dur / 1.5))), rng.random(max(4, int(dur / 1.5))))
        cutoff = base + spread * lfo
        y = svf(src, cutoff, np.full(n, 1.3), 1)
        gust = 0.55 + 0.45 * np.interp(t, np.linspace(0, dur, max(4, int(dur / 2.5))), rng.random(max(4, int(dur / 2.5))))
        out[:, ch] = y * gust
    return out * velocity * 0.6


def footstep(velocity=0.5, seed=0, wet=0.6):
    rng = np.random.default_rng(seed)
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    heel = dsp.bp(rng.standard_normal(n), 300, 2500) * np.exp(-t / 0.018)
    thud = np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.04) * 0.8
    splash = dsp.bp(rng.standard_normal(n), 3000, 9000) * np.exp(-((t - 0.03) ** 2) / 0.0008) * wet * 0.5
    y = heel * 0.7 + thud + splash
    return dsp.pan(y * velocity * 0.5, rng.uniform(-0.1, 0.1))


def light_thunk(velocity=0.8, seed=0):
    """Encendido de focos de estadio: golpe grave, chasquido mecánico y zumbido eléctrico."""
    rng = np.random.default_rng(seed)
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (70 + 40 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.09)
    click = dsp.bp(rng.standard_normal(n), 1500, 6000) * np.exp(-t / 0.006) * 0.8
    hum = sum(np.sin(2 * np.pi * 60 * k * t) / k for k in (1, 2, 3, 5)) * 0.06 * np.clip(t / 0.05, 0, 1) * np.exp(-t / 0.8)
    y = dsp.saturate((thump + click + hum) * 0.9, 0.6)
    return dsp.pan(y * velocity, rng.uniform(-0.3, 0.3))


def stone_rumble(dur=3.0, velocity=0.6, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    low = dsp.lp(pink(n, rng), 120, order=4) * 2.2
    grind = dsp.bp(rng.standard_normal(n), 180, 900) * (0.5 + 0.5 * np.interp(t, np.linspace(0, dur, 60), rng.random(60)))
    env = np.clip(t / 0.4, 0, 1) * np.clip((dur - t) / 0.8, 0, 1)
    y = (low + grind * 0.5) * env
    return np.stack([y, np.roll(y, 131)], axis=1) * velocity


def heartbeat(velocity=0.6):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    def thump(t0, amp):
        tt = np.clip(t - t0, 0, None)
        f = 48 + 20 * np.exp(-tt / 0.03)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.07) * amp * (t >= t0)
    y = thump(0, 1.0) + thump(0.21, 0.65)
    return dsp.pan(dsp.saturate(y, 0.5) * velocity, 0)
