"""Procesamiento de audio: filtros, dinámica, reverb y utilidades de muestreo."""

from fractions import Fraction

import numpy as np
from numba import njit
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt, sosfiltfilt

SR = 48000


# ---------------------------------------------------------------- filtros
def _biquad(b0, b1, b2, a0, a1, a2):
    return np.array([[b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]])


def peaking(f0, gain_db, q, sr=SR):
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / sr
    alpha = np.sin(w0) / (2 * q)
    return _biquad(1 + alpha * a, -2 * np.cos(w0), 1 - alpha * a, 1 + alpha / a, -2 * np.cos(w0), 1 - alpha / a)


def lowshelf(f0, gain_db, s=1.0, sr=SR):
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / sr
    alpha = np.sin(w0) / 2 * np.sqrt((a + 1 / a) * (1 / s - 1) + 2)
    c = np.cos(w0)
    return _biquad(
        a * ((a + 1) - (a - 1) * c + 2 * np.sqrt(a) * alpha),
        2 * a * ((a - 1) - (a + 1) * c),
        a * ((a + 1) - (a - 1) * c - 2 * np.sqrt(a) * alpha),
        (a + 1) + (a - 1) * c + 2 * np.sqrt(a) * alpha,
        -2 * ((a - 1) + (a + 1) * c),
        (a + 1) + (a - 1) * c - 2 * np.sqrt(a) * alpha,
    )


def highshelf(f0, gain_db, s=1.0, sr=SR):
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / sr
    alpha = np.sin(w0) / 2 * np.sqrt((a + 1 / a) * (1 / s - 1) + 2)
    c = np.cos(w0)
    return _biquad(
        a * ((a + 1) + (a - 1) * c + 2 * np.sqrt(a) * alpha),
        -2 * a * ((a - 1) + (a + 1) * c),
        a * ((a + 1) + (a - 1) * c - 2 * np.sqrt(a) * alpha),
        (a + 1) - (a - 1) * c + 2 * np.sqrt(a) * alpha,
        2 * ((a - 1) - (a + 1) * c),
        (a + 1) - (a - 1) * c - 2 * np.sqrt(a) * alpha,
    )


def hp(x, f, order=2, sr=SR):
    return sosfilt(butter(order, f, "highpass", fs=sr, output="sos"), x, axis=0)


def lp(x, f, order=2, sr=SR):
    return sosfilt(butter(order, f, "lowpass", fs=sr, output="sos"), x, axis=0)


def bp(x, lo, hi, order=2, sr=SR):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=sr, output="sos"), x, axis=0)


def hp0(x, f, order=2, sr=SR):
    """Paso alto sin desfase (para pistas ya alineadas)."""
    return sosfiltfilt(butter(order, f, "highpass", fs=sr, output="sos"), x, axis=0)


def eq(x, *sections):
    sos = np.vstack(sections)
    return sosfilt(sos, x, axis=0)


# ---------------------------------------------------------------- dinámica
@njit(cache=True)
def _env_follow(x, att, rel):
    y = np.empty_like(x)
    e = 0.0
    for i in range(x.shape[0]):
        v = x[i]
        if v > e:
            e = att * e + (1 - att) * v
        else:
            e = rel * e + (1 - rel) * v
        y[i] = e
    return y


def envelope(x, attack_ms, release_ms, sr=SR):
    att = np.exp(-1 / (sr * attack_ms / 1000))
    rel = np.exp(-1 / (sr * release_ms / 1000))
    return _env_follow(np.ascontiguousarray(x, dtype=np.float64), att, rel)


def compressor(x, threshold_db=-20, ratio=3.0, attack_ms=10, release_ms=120, knee_db=6, makeup_db=0.0, sidechain=None, sr=SR):
    """Compresor feed-forward con detector RMS. x: (n,) o (n, ch)."""
    sc = x if sidechain is None else sidechain
    mono = sc if sc.ndim == 1 else np.sqrt(np.mean(sc**2, axis=1))
    env = np.sqrt(envelope(mono**2, attack_ms, release_ms, sr)) + 1e-12
    lvl = 20 * np.log10(env)
    over = lvl - threshold_db
    gr = np.where(
        over <= -knee_db / 2,
        0.0,
        np.where(over >= knee_db / 2, over * (1 - 1 / ratio), (1 - 1 / ratio) * (over + knee_db / 2) ** 2 / (2 * knee_db)),
    )
    g = 10 ** ((makeup_db - gr) / 20)
    return x * (g if x.ndim == 1 else g[:, None]), gr


def expander(x, threshold_db=-50, ratio=2.0, range_db=18, attack_ms=2, release_ms=80, sr=SR):
    mono = x if x.ndim == 1 else np.sqrt(np.mean(x**2, axis=1))
    env = np.sqrt(envelope(mono**2, attack_ms, release_ms, sr)) + 1e-12
    lvl = 20 * np.log10(env)
    under = np.minimum(lvl - threshold_db, 0)
    att = np.maximum(under * (ratio - 1), -range_db)
    g = 10 ** (att / 20)
    return x * (g if x.ndim == 1 else g[:, None])


@njit(cache=True)
def _limiter_gain(peak, ceiling, rel):
    n = peak.shape[0]
    g = np.ones(n)
    cur = 1.0
    for i in range(n):
        target = 1.0 if peak[i] <= ceiling else ceiling / peak[i]
        if target < cur:
            cur = target
        else:
            cur = rel * cur + (1 - rel) * target
        g[i] = cur
    return g


def limiter(x, ceiling_db=-1.0, lookahead_ms=5, release_ms=80, sr=SR):
    """Limitador brickwall con lookahead. x: (n, ch)."""
    x2 = x if x.ndim == 2 else x[:, None]
    la = int(sr * lookahead_ms / 1000)
    peak = np.max(np.abs(x2), axis=1)
    # máximo en ventana de lookahead (hacia adelante)
    from scipy.ndimage import maximum_filter1d

    pk = maximum_filter1d(peak, size=2 * la + 1, origin=0)
    ceiling = 10 ** (ceiling_db / 20)
    rel = np.exp(-1 / (sr * release_ms / 1000))
    g = _limiter_gain(pk, ceiling, rel)
    # suavizado para evitar distorsión
    from scipy.ndimage import uniform_filter1d

    g = np.minimum(g, uniform_filter1d(g, size=la + 1))
    y = x2 * g[:, None]
    y = np.clip(y, -ceiling, ceiling)
    return y if x.ndim == 2 else y[:, 0]


def deesser(x, lo=5200, hi=10000, threshold_db=-30, ratio=4, sr=SR):
    band = bp(x, lo, hi, order=2, sr=sr)
    _, gr = compressor(band, threshold_db, ratio, attack_ms=1.5, release_ms=60, knee_db=4, sr=sr)
    g = 10 ** (-gr / 20)
    reduce = band * ((g - 1) if band.ndim == 1 else (g - 1)[:, None])
    return x + reduce


def saturate(x, drive=1.0):
    if drive <= 0:
        return x
    return np.tanh(x * (1 + drive)) / np.tanh(1 + drive)


# ---------------------------------------------------------------- reverb
def make_ir(seconds=3.0, sr=SR, predelay_ms=20, damping_hz=6000, low_cut=180, width=1.0, seed=7, early=True):
    """IR estéreo sintética: ruido con decaimiento exponencial y amortiguación de agudos progresiva."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n) / sr
    rt60 = seconds
    decay = np.exp(-6.91 * t / rt60)
    ir = rng.standard_normal((n, 2)) * decay[:, None]
    # amortiguación: mezcla de versión filtrada que gana peso con el tiempo
    dark = lp(ir, damping_hz * 0.35, order=2, sr=sr)
    w = np.clip(t / (rt60 * 0.6), 0, 1)[:, None]
    ir = ir * (1 - w) + dark * w * 1.4
    ir = lp(ir, damping_hz, order=2, sr=sr)
    ir = hp(ir, low_cut, order=2, sr=sr)
    # fade-in suave para difusión
    fade = np.clip(t / 0.03, 0, 1) ** 2
    ir *= fade[:, None]
    if early:
        for k in range(12):
            dt = rng.uniform(0.004, 0.06)
            amp = rng.uniform(0.15, 0.5) * (1 - k / 14)
            idx = int(dt * sr)
            ch = k % 2
            if idx < n:
                ir[idx, ch] += amp
    pd = np.zeros((int(sr * predelay_ms / 1000), 2))
    ir = np.vstack([pd, ir])
    mid = ir.mean(axis=1, keepdims=True)
    ir = mid + (ir - mid) * width
    ir /= np.sqrt(np.sum(ir**2) / 2)
    return ir


def convolve_stereo(x, ir):
    """x: (n,) o (n,2); ir: (m,2) -> (n+m-1, 2)."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    out = np.zeros((x.shape[0] + ir.shape[0] - 1, 2))
    for c in range(2):
        out[:, c] = fftconvolve(x[:, c], ir[:, c])
    return out


# ---------------------------------------------------------------- utilidades
def resample(x, sr_in, sr_out):
    if sr_in == sr_out:
        return x
    fr = Fraction(sr_out, sr_in).limit_denominator(2000)
    return resample_poly(x, fr.numerator, fr.denominator, axis=0)


def pitch_shift_resample(x, semitones):
    """Cambia la altura re-muestreando (como un sampler clásico: también cambia la duración)."""
    if abs(semitones) < 1e-6:
        return x
    ratio = 2 ** (semitones / 12)
    fr = Fraction(1 / ratio).limit_denominator(400)
    return resample_poly(x, fr.numerator, fr.denominator, axis=0)


def fade(x, fade_in=0.0, fade_out=0.0, sr=SR):
    y = x.copy()
    n = y.shape[0]
    if fade_in > 0:
        k = min(n, int(fade_in * sr))
        ramp = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
        y[:k] *= ramp if y.ndim == 1 else ramp[:, None]
    if fade_out > 0:
        k = min(n, int(fade_out * sr))
        ramp = np.cos(np.linspace(0, np.pi / 2, k)) ** 2
        y[n - k :] *= ramp if y.ndim == 1 else ramp[:, None]
    return y


def pan(x, p):
    """Panorama de potencia constante. p en [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def add_at(buf, x, t, sr=SR, gain=1.0):
    """Suma x (n,2) en buf (N,2) a partir del segundo t."""
    i = int(round(t * sr))
    if i >= buf.shape[0]:
        return
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(x.shape[0], buf.shape[0] - i)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    buf[i : i + n] += x[:n] * gain
