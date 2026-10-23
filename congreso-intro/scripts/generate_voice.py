"""Genera la narración en español por bloques.

- Motor: Supertonic 3 (local, sherpa-onnx). Estilo M2 = voz masculina grave y serena.
- Varias tomas por frase (la síntesis es estocástica); se elige automáticamente la toma
  correcta (Whisper la transcribe sin errores) y más "típica" (la menos atípica en tono y energía).
- Procesado: paso alto, expansor, EQ (calidez, claridad), de-esser, compresión, normalización de sonoridad.
- Marcas de tiempo por palabra con Parakeet (para sincronizar palabras clave en pantalla).

Uso:  .venv/bin/python scripts/generate_voice.py [--takes 6] [--only vo03,vo04]
"""

import argparse
import json
import os
import re
import sys

import numpy as np
import pyloudnorm as pyln
import sherpa_onnx
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp  # noqa: E402
from common import MODELS, PUBLIC, ROOT, load_config, tts_text  # noqa: E402

SUPERTONIC_DIR = os.path.join(MODELS, "sherpa-onnx-supertonic-3-tts-int8-2026-05-11")
WHISPER_DIR = os.path.join(MODELS, "sherpa-onnx-whisper-small")
PARAKEET_DIR = os.path.join(MODELS, "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8")
RAW_DIR = os.path.join(ROOT, ".cache", "voice_raw")
OUT_DIR = os.path.join(PUBLIC, "audio", "voice")

# Orden de estilos dentro de voice.bin (F1..F5, M1..M5)
STYLE_IDS = {f"F{i}": i - 1 for i in range(1, 6)} | {f"M{i}": i + 4 for i in range(1, 6)}

# Ajustes por registro interpretativo
REGISTERS = {
    "intimo": {"speed": 0.86, "lufs": -22.5, "presence": 1.5, "drive": 0.0},
    "firme": {"speed": 0.90, "lufs": -20.0, "presence": 2.5, "drive": 0.15},
    "climax": {"speed": 0.88, "lufs": -18.0, "presence": 3.0, "drive": 0.3},
}


def make_tts():
    d = SUPERTONIC_DIR
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            supertonic=sherpa_onnx.OfflineTtsSupertonicModelConfig(
                duration_predictor=f"{d}/duration_predictor.int8.onnx",
                text_encoder=f"{d}/text_encoder.int8.onnx",
                vector_estimator=f"{d}/vector_estimator.int8.onnx",
                vocoder=f"{d}/vocoder.int8.onnx",
                tts_json=f"{d}/tts.json",
                unicode_indexer=f"{d}/unicode_indexer.bin",
                voice_style=f"{d}/voice.bin",
            ),
            num_threads=4,
        )
    )
    return sherpa_onnx.OfflineTts(cfg)


def make_whisper():
    d = WHISPER_DIR
    return sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{d}/small-encoder.int8.onnx",
        decoder=f"{d}/small-decoder.int8.onnx",
        tokens=f"{d}/small-tokens.txt",
        language="es",
        task="transcribe",
        num_threads=4,
    )


def make_parakeet():
    d = PARAKEET_DIR
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{d}/encoder.int8.onnx",
        decoder=f"{d}/decoder.int8.onnx",
        joiner=f"{d}/joiner.int8.onnx",
        tokens=f"{d}/tokens.txt",
        num_threads=4,
        model_type="nemo_transducer",
    )


def norm_words(t):
    t = t.lower().replace("…", " ")
    t = re.sub(r"[^\wáéíóúñü ]", " ", t)
    return t.split()


def wer(ref, hyp):
    r, h = norm_words(ref), norm_words(hyp)
    d = np.zeros((len(r) + 1, len(h) + 1), int)
    d[:, 0] = range(len(r) + 1)
    d[0, :] = range(len(h) + 1)
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (r[i - 1] != h[j - 1]))
    return d[-1, -1] / max(1, len(r))


def transcribe(rec, x, sr):
    x16 = resample_poly(x, 160, int(sr / 100)).astype(np.float32) if sr != 16000 else x.astype(np.float32)
    s = rec.create_stream()
    s.accept_waveform(16000, x16)
    rec.decode_stream(s)
    return s.result


def trim(x, sr, thresh_db=-42, pre=0.05, post=0.22):
    env = dsp.envelope(np.abs(x), 1, 30, sr)
    lvl = 20 * np.log10(env + 1e-9)
    on = np.where(lvl > lvl.max() + thresh_db)[0]
    if len(on) == 0:
        return x
    a = max(0, on[0] - int(pre * sr))
    b = min(len(x), on[-1] + int(post * sr))
    return x[a:b]


def f0_contour(x, sr, n_points=40):
    """F0 por autocorrelación (YIN simplificado) muestreado en n_points; NaN en tramos sordos."""
    x = resample_poly(x, 160, int(sr / 100)) if sr != 16000 else x
    sr = 16000
    frame, hop = 640, 160
    tmin, tmax = int(sr / 300), int(sr / 60)
    vals = []
    for st in range(0, len(x) - frame - tmax, hop):
        seg = x[st : st + frame + tmax]
        if np.sqrt(np.mean(seg[:frame] ** 2)) < 0.01:
            vals.append(np.nan)
            continue
        d = np.array([np.sum((seg[:frame] - seg[t : t + frame]) ** 2) for t in range(tmax + 1)])
        cm = np.ones_like(d)
        cm[1:] = d[1:] * np.arange(1, len(d)) / np.maximum(np.cumsum(d[1:]), 1e-9)
        idx = np.where(cm[tmin:] < 0.15)[0]
        vals.append(sr / (idx[0] + tmin) if len(idx) else np.nan)
    v = np.array(vals)
    if len(v) < 2:
        return np.full(n_points, np.nan)
    xi = np.linspace(0, len(v) - 1, n_points)
    out = np.full(n_points, np.nan)
    for k, p in enumerate(xi):
        w = v[max(0, int(p) - 2) : int(p) + 3]
        w = w[~np.isnan(w)]
        if len(w):
            out[k] = np.median(w)
    return out


def energy_contour(x, n_points=40):
    chunks = np.array_split(x, n_points)
    return np.array([20 * np.log10(np.sqrt(np.mean(c**2)) + 1e-9) for c in chunks])


def process(x, sr, reg):
    """Cadena de voz: 44.1k -> 48k, limpieza, EQ, de-esser, compresión, sonoridad."""
    x = dsp.resample(x.astype(np.float64), sr, dsp.SR)
    sr = dsp.SR
    x = dsp.hp(x, 75, order=4)
    x = dsp.expander(x, threshold_db=-48, ratio=2.5, range_db=20, attack_ms=3, release_ms=90)
    x = dsp.eq(
        x,
        dsp.lowshelf(140, 1.5),
        dsp.peaking(330, -2.5, 1.0),
        dsp.peaking(3200, reg["presence"], 0.9),
        dsp.highshelf(9500, 2.0),
    )
    x = dsp.deesser(x, 5500, 10000, threshold_db=-34, ratio=4)
    x, _ = dsp.compressor(x, threshold_db=-24, ratio=3.0, attack_ms=8, release_ms=140, knee_db=6)
    x = dsp.saturate(x * 0.9, reg["drive"]) / 0.9 if reg["drive"] > 0 else x
    meter = pyln.Meter(sr)
    loud = meter.integrated_loudness(x)
    x = x * 10 ** ((reg["lufs"] - loud) / 20)
    peak = np.max(np.abs(x))
    if peak > 0.89:
        x = dsp.limiter(x[:, None], ceiling_db=-1.0)[:, 0]
    x = dsp.fade(x, 0.01, 0.12, sr)
    return x.astype(np.float32)


def words_with_times(result, offset=0.0):
    toks, ts = list(result.tokens), list(result.timestamps)
    words = []
    for tok, t in zip(toks, ts):
        if tok.startswith((" ", "▁")) or not words:
            words.append({"w": tok.strip().lstrip("▁"), "start": round(t + offset, 3)})
        else:
            words[-1]["w"] += tok
    clean = []
    for i, w in enumerate(words):
        txt = re.sub(r"[^\wáéíóúñüÁÉÍÓÚÑÜ]", "", w["w"])
        if not txt:
            continue
        end = words[i + 1]["start"] if i + 1 < len(words) else None
        clean.append({"w": txt.lower(), "start": w["start"], "end": end})
    return clean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--takes", type=int, default=6)
    ap.add_argument("--only", type=str, default="")
    ap.add_argument("--reprocess", action="store_true", help="Reutiliza la toma elegida (no vuelve a sintetizar)")
    args = ap.parse_args()

    cfg = load_config()
    vcfg = cfg["voz"]
    sid = STYLE_IDS[vcfg["estilo"]]
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        manifest = {m["id"]: m for m in json.load(open(manifest_path, encoding="utf-8"))["lines"]}

    only = set(filter(None, args.only.split(",")))
    tts = make_tts()
    whisper = make_whisper()
    parakeet = make_parakeet()

    for line in cfg["narracion"]:
        if only and line["id"] not in only:
            continue
        reg = REGISTERS[line.get("registro", "firme")]
        speed = line.get("velocidad", reg["speed"] * vcfg["velocidad"] / 0.88)
        text = tts_text(line, vcfg["seseo"])
        print(f"\n== {line['id']}  «{line['texto']}»\n   TTS: «{text}»  speed={speed:.3f}", flush=True)

        takes = []
        if args.reprocess and line["id"] in manifest:
            k = manifest[line["id"]]["toma"]
            x, sr = sf.read(os.path.join(RAW_DIR, f"{line['id']}_take{k}.wav"), dtype="float32")
            hyp = transcribe(whisper, x, sr).text.strip()
            takes.append({"k": k, "x": x, "sr": sr, "hyp": hyp, "wer": wer(line["texto"], hyp), "f0": f0_contour(x, sr), "en": energy_contour(x)})
        for k in range(0 if takes else args.takes):
            g = sherpa_onnx.GenerationConfig()
            g.sid = sid
            g.speed = speed
            g.num_steps = vcfg["pasos"]
            g.extra = {"lang": "es"}
            a = tts.generate(text, g)
            x = np.array(a.samples, dtype=np.float32)
            sr = a.sample_rate
            x = trim(x, sr)
            sf.write(os.path.join(RAW_DIR, f"{line['id']}_take{k}.wav"), x, sr)
            hyp = transcribe(whisper, x, sr).text.strip()
            e = wer(line["texto"], hyp)
            f0 = f0_contour(x, sr)
            en = energy_contour(x)
            takes.append({"k": k, "x": x, "sr": sr, "hyp": hyp, "wer": e, "f0": f0, "en": en})
            print(f"   take{k}: dur={len(x)/sr:.2f}s WER={e:.2f} F0med={np.nanmedian(f0):.0f}Hz | {hyp}", flush=True)

        best_wer = min(t["wer"] for t in takes)
        cands = [t for t in takes if t["wer"] == best_wer]
        f0m = np.nanmedian(np.array([12 * np.log2(t["f0"]) for t in takes]), axis=0)
        enm = np.median(np.array([t["en"] for t in takes]), axis=0)

        def atypicality(t):
            df = 12 * np.log2(t["f0"]) - f0m
            df = df[~np.isnan(df)]
            return (np.mean(np.abs(df)) if len(df) else 5.0) + 0.15 * np.mean(np.abs(t["en"] - enm))

        best = min(cands, key=atypicality)
        print(f"   -> elegida take{best['k']} (WER {best['wer']:.2f}, atipicidad {atypicality(best):.2f})")

        y = process(best["x"], best["sr"], reg)
        out_file = os.path.join(OUT_DIR, f"{line['id']}.wav")
        sf.write(out_file, y, dsp.SR, subtype="PCM_24")
        post = transcribe(whisper, y, dsp.SR).text.strip()
        post_wer = wer(line["texto"], post)
        print(f"   whisper(procesado): WER={post_wer:.2f} | {post}")
        pk = transcribe(parakeet, y, dsp.SR)
        words = words_with_times(pk)
        dur = len(y) / dsp.SR
        for w in words:
            if w["end"] is None:
                w["end"] = round(dur - 0.15, 3)
        manifest[line["id"]] = {
            "id": line["id"],
            "file": f"audio/voice/{line['id']}.wav",
            "texto": line["texto"],
            "textoTTS": text,
            "duracion": round(dur, 3),
            "toma": best["k"],
            "asrWhisper": best["hyp"],
            "werWhisper": best["wer"],
            "asrWhisperProcesado": post,
            "werWhisperProcesado": post_wer,
            "asrParakeet": pk.text.strip(),
            "palabras": words,
        }
        print(f"   parakeet: {pk.text.strip()}")
        print("   palabras:", " ".join(f"{w['w']}@{w['start']:.2f}" for w in words))

    ordered = [manifest[l["id"]] for l in cfg["narracion"] if l["id"] in manifest]
    json.dump({"voz": vcfg["estilo"], "motor": vcfg["motor"], "lines": ordered}, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nManifest:", manifest_path)


if __name__ == "__main__":
    main()
