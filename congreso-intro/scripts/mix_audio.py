"""Mezcla final: voz + música + efectos -> public/audio/mix.wav (48 kHz, estéreo, 24 bit).

- Coloca cada bloque de voz en su instante de config/intro.config.json.
- La música y los efectos bajan automáticamente bajo la voz (sidechain), con más reducción
  en la banda de inteligibilidad (1-4 kHz) para que la voz siempre se entienda.
- Aplica los volúmenes de la config (audio.volumenVoz / volumenMusica / volumenEfectos).
- Masterización: compresión suave, limitador (techo -1 dBFS) y normalización a -14 LUFS.

Uso: .venv/bin/python scripts/mix_audio.py
"""

import json
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp  # noqa: E402
from common import PUBLIC, ROOT, load_config  # noqa: E402

SR = dsp.SR
TARGET_LUFS = -14.0
MARGIN_DB = 4.0  # la música queda al menos 7 dB por debajo de la voz mientras habla
# nivel objetivo del fondo (música+efectos, sin voz) relativo a la sonoridad de la voz, por escena
BED_REL_DB = {1: -14.0, 2: -10.0, 3: -6.0, 4: 1.0, 5: 5.0, 6: 6.0, 7: 5.0}


def main():
    cfg = load_config()
    dur = cfg["video"]["duracionSegundos"]
    n = int(dur * SR)
    vol = cfg["audio"]
    manifest = json.load(open(os.path.join(PUBLIC, "audio", "voice", "manifest.json"), encoding="utf-8"))
    clips = {m["id"]: m for m in manifest["lines"]}

    # ------------------------------------------------ voz
    voice = np.zeros(n + 6 * SR)
    for line in cfg["narracion"]:
        m = clips.get(line["id"])
        if m is None:
            raise SystemExit(f"Falta la voz {line['id']}: ejecuta scripts/generate_voice.py")
        x, sr = sf.read(os.path.join(PUBLIC, m["file"]), dtype="float64")
        assert sr == SR
        i = int(round(line["inicio"] * SR))
        voice[i : i + len(x)] += x
    voice_st = np.stack([voice, voice], axis=1)
    plate = dsp.make_ir(1.7, predelay_ms=30, damping_hz=6500, low_cut=300, seed=21, width=1.1)
    wet = dsp.convolve_stereo(dsp.hp(voice, 250), plate)[: len(voice)]
    voice_st = voice_st + wet * 0.07
    voice_st = voice_st[:n]

    music, _ = sf.read(os.path.join(ROOT, ".cache", "stems", "music.wav"), dtype="float64")
    sfx, _ = sf.read(os.path.join(ROOT, ".cache", "stems", "sfx.wav"), dtype="float64")
    music, sfx = music[:n], sfx[:n]

    # ------------------------------------------------ arco dinámico: nivel del fondo (música+efectos) por escena
    # Se mide el fondo fuera de los momentos con voz y se lleva a un objetivo relativo a la voz.
    meter = pyln.Meter(SR)
    v_int = meter.integrated_loudness(voice_st)
    t = np.arange(n) / SR
    v_env = 10 * np.log10(dsp.envelope(voice[:n] ** 2, 10, 400) + 1e-12)
    no_voice = v_env < -50
    bed = music * 0.9 + sfx * 0.7
    pts_t, pts_g = [], []
    for esc in cfg["escenas"]:
        a_, b_ = int(esc["inicio"] * SR), int(esc["fin"] * SR)
        mask = no_voice[a_:b_]
        seg = bed[a_:b_][mask] if mask.sum() > SR else bed[a_:b_]
        try:
            l_bed = meter.integrated_loudness(seg)
        except Exception:
            l_bed = -70.0
        target = v_int + BED_REL_DB[esc["n"]]
        g = float(np.clip(target - l_bed, -12, 18)) if np.isfinite(l_bed) else 0.0
        pts_t += [esc["inicio"] + 0.25, esc["fin"] - 0.25]
        pts_g += [g, g]
        print(f"  fondo escena {esc['n']}: {l_bed:6.1f} LUFS -> objetivo {target:6.1f} (ganancia {g:+.1f} dB)")
    arc = 10 ** (np.interp(t, pts_t, pts_g) / 20)
    music = music * arc[:, None]
    sfx = sfx * arc[:, None]

    # ------------------------------------------------ sidechain adaptativo (la voz manda)
    def level_db(x, att=30, rel=300):
        mono = x if x.ndim == 1 else x.mean(axis=1)
        mono = dsp.hp(mono, 150, order=2)
        return 10 * np.log10(dsp.envelope(mono**2, att, rel) + 1e-12)

    v_db = level_db(voice[:n], 10, 250)
    active = dsp.envelope((v_db > -45).astype(float), 20, 450)
    bed_db = level_db(music * 0.9 + sfx * 0.7, 30, 300)
    want = np.minimum(0.0, (v_db - MARGIN_DB) - bed_db)
    want = np.maximum(want, -9.0)
    gain_db = np.where(active > 0.05, want * np.clip(active, 0, 1), 0.0) - 2.5 * active
    gain_db = -dsp.envelope(-gain_db, 40, 450)
    g = 10 ** (gain_db / 20)
    lowp = dsp.lp(music, 900, order=2)
    highp = dsp.hp(music, 4500, order=2)
    midp = music - lowp - highp
    carve = 10 ** (-5.5 * np.clip(active, 0, 1) / 20)
    music = (lowp + highp + midp * carve[:, None]) * g[:, None]
    sfx = sfx * (10 ** (gain_db * 0.5 / 20))[:, None]  # la percusión baja menos: mantiene la energía

    def soft_clip(x, t=0.55):
        a = np.abs(x)
        y = np.where(a < t, a, t + (1 - t) * np.tanh((a - t) / (1 - t)))
        return np.sign(x) * y

    sfx = soft_clip(sfx * 0.7) / 0.7
    stems = {
        "voz": voice_st * vol["volumenVoz"],
        "musica": music * 0.9 * vol["volumenMusica"],
        "efectos": sfx * 0.7 * vol["volumenEfectos"],
    }
    mix = sum(stems.values())

    # ------------------------------------------------ master
    mix, _ = dsp.compressor(mix, threshold_db=-14, ratio=1.8, attack_ms=20, release_ms=200, knee_db=8)
    pre_peak = np.max(np.abs(mix))
    for _ in range(3):
        loud = meter.integrated_loudness(mix)
        mix = mix * 10 ** ((TARGET_LUFS - loud) / 20)
        mix = dsp.limiter(mix, ceiling_db=-1.0, lookahead_ms=5, release_ms=120)
    loud = meter.integrated_loudness(mix)
    peak = 20 * np.log10(np.max(np.abs(mix)))
    print(f"ganancia de master aplicada ~ {20*np.log10(np.max(np.abs(mix))/pre_peak):+.1f} dB sobre el pico previo")

    out_dir = os.path.join(PUBLIC, "audio")
    os.makedirs(os.path.join(out_dir, "stems"), exist_ok=True)
    sf.write(os.path.join(out_dir, "mix.wav"), mix.astype(np.float32), SR, subtype="PCM_24")
    for name, x in stems.items():
        sf.write(os.path.join(out_dir, "stems", f"{name}.flac"), np.clip(x, -1, 1).astype(np.float32), SR, subtype="PCM_24")
    print(f"mix.wav: {loud:.1f} LUFS integrado, pico {peak:.2f} dBFS")

    # informe por escena
    report = []
    for esc in cfg["escenas"]:
        a, b = int(esc["inicio"] * SR), int(esc["fin"] * SR)
        seg = mix[a:b]
        l = meter.integrated_loudness(seg) if b - a > SR * 0.5 else float("nan")
        report.append((esc["n"], esc["nombre"], round(l, 1)))
        print(f"  escena {esc['n']} {esc['nombre']:<26s} {l:6.1f} LUFS")
    json.dump({"lufs": round(loud, 2), "picoDbfs": round(peak, 2), "escenas": report}, open(os.path.join(ROOT, ".cache", "mix_report.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
