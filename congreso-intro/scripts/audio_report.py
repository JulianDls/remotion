"""Informe visual del audio: sonoridad a corto plazo (mezcla y pistas) y espectrograma.

Genera .cache/qa/audio_report.png. Uso: .venv/bin/python scripts/audio_report.py
"""

import json
import os
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw
from scipy.signal import stft

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp  # noqa: E402
from common import PUBLIC, ROOT, load_config  # noqa: E402

SR = dsp.SR
W, H = 1800, 900


def kweight(x):
    # aproximación de la ponderación K (BS.1770): shelving agudo + paso alto
    x = dsp.eq(x, dsp.highshelf(1680, 4.0, 0.7), dsp.peaking(38, 0, 0.5))
    return dsp.hp(x, 38, order=2)


def short_term(x, win=0.4, hop=0.1):
    mono = x if x.ndim == 1 else x
    k = kweight(mono)
    p = (k**2).mean(axis=1) * 2 if k.ndim == 2 else k**2
    w, h = int(win * SR), int(hop * SR)
    out = []
    for i in range(0, len(p) - w, h):
        out.append(-0.691 + 10 * np.log10(p[i : i + w].mean() + 1e-12))
    return np.array(out)


def main():
    cfg = load_config()
    dur = cfg["video"]["duracionSegundos"]
    tracks = {
        "mezcla": sf.read(os.path.join(PUBLIC, "audio", "mix.wav"))[0],
        "voz": sf.read(os.path.join(PUBLIC, "audio", "stems", "voz.flac"))[0],
        "musica": sf.read(os.path.join(PUBLIC, "audio", "stems", "musica.flac"))[0],
        "efectos": sf.read(os.path.join(PUBLIC, "audio", "stems", "efectos.flac"))[0],
    }
    colors = {"mezcla": (255, 255, 255), "voz": (255, 200, 90), "musica": (90, 150, 255), "efectos": (255, 90, 90)}
    img = Image.new("RGB", (W, H), (10, 12, 18))
    d = ImageDraw.Draw(img)
    top, bot = 40, 520
    lo, hi = -50, -5

    def y_of(db):
        return bot - (np.clip(db, lo, hi) - lo) / (hi - lo) * (bot - top)

    for db in range(lo, hi + 1, 5):
        y = y_of(db)
        d.line([(60, y), (W - 10, y)], fill=(40, 44, 55))
        d.text((10, y - 6), f"{db}", fill=(140, 140, 150))
    for esc in cfg["escenas"]:
        x = 60 + esc["inicio"] / dur * (W - 70)
        d.line([(x, top), (x, H - 10)], fill=(80, 80, 100))
        d.text((x + 3, top - 30), f"E{esc['n']}", fill=(200, 200, 220))
    for line in cfg["narracion"]:
        x = 60 + line["inicio"] / dur * (W - 70)
        d.rectangle([x, bot + 6, x + 6, bot + 14], fill=(255, 200, 90))
    for name, x in tracks.items():
        st = short_term(x)
        pts = [(60 + (i * 0.1) / dur * (W - 70), y_of(v)) for i, v in enumerate(st)]
        d.line(pts, fill=colors[name], width=2 if name == "mezcla" else 1)
    yy = top
    for name, c in colors.items():
        d.text((W - 160, yy), name, fill=c)
        yy += 14
    # espectrograma de la mezcla
    mono = tracks["mezcla"].mean(axis=1)
    f, t, Z = stft(mono, SR, nperseg=4096, noverlap=3072)
    S = 20 * np.log10(np.abs(Z) + 1e-7)
    S = np.clip((S - (S.max() - 90)) / 90, 0, 1)
    ys = np.geomspace(30, 20000, 330)
    idx = np.searchsorted(f, ys).clip(0, len(f) - 1)
    spec = (S[idx][::-1] * 255).astype(np.uint8)
    sp = Image.fromarray(spec).resize((W - 70, 330)).convert("RGB")
    img.paste(sp, (60, 560))
    d.text((10, 560), "20k", fill=(200, 200, 200))
    d.text((10, 880), "30Hz", fill=(200, 200, 200))
    os.makedirs(os.path.join(ROOT, ".cache", "qa"), exist_ok=True)
    out = os.path.join(ROOT, ".cache", "qa", "audio_report.png")
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
