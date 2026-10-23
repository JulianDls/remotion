"""Comprueba la inteligibilidad de la narración en la mezcla final.

Transcribe con Whisper cada frase tomada de public/audio/mix.wav (con música y efectos)
y calcula el WER contra el guion. Uso: .venv/bin/python scripts/check_intelligibility.py
"""

import json
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PUBLIC, ROOT, load_config  # noqa: E402
from generate_voice import make_whisper, transcribe, wer  # noqa: E402


def main(path=None):
    cfg = load_config()
    path = path or os.path.join(PUBLIC, "audio", "mix.wav")
    mix, sr = sf.read(path, dtype="float32")
    mono = mix.mean(axis=1) if mix.ndim == 2 else mix
    manifest = {m["id"]: m for m in json.load(open(os.path.join(PUBLIC, "audio", "voice", "manifest.json"), encoding="utf-8"))["lines"]}
    rec = make_whisper()
    results = []
    for line in cfg["narracion"]:
        d = manifest[line["id"]]["duracion"]
        a = max(0, int((line["inicio"] - 0.15) * sr))
        b = min(len(mono), int((line["inicio"] + d + 0.1) * sr))
        seg = mono[a:b] / (np.max(np.abs(mono[a:b])) + 1e-9) * 0.9
        hyp = transcribe(rec, seg, sr).text.strip()
        e = wer(line["texto"], hyp)
        results.append({"id": line["id"], "texto": line["texto"], "asr": hyp, "wer": round(e, 3)})
        print(f"{line['id']} WER={e:.2f} | {hyp}")
    mean = float(np.mean([r["wer"] for r in results]))
    print(f"WER medio en la mezcla: {mean:.3f}")
    os.makedirs(os.path.join(ROOT, ".cache", "qa"), exist_ok=True)
    json.dump({"archivo": os.path.relpath(path, ROOT), "werMedio": mean, "frases": results}, open(os.path.join(ROOT, ".cache", "qa", "inteligibilidad.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
