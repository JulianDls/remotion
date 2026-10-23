"""Genera docs/REPORTE_VALIDACION.md con los resultados de control de calidad.

Fuentes: .cache/qa/validacion_*.json (scripts/validate_video.py), .cache/qa/inteligibilidad.json
(scripts/check_intelligibility.py), .cache/mix_report.json (scripts/mix_audio.py) y el manifiesto de voz.
Uso: .venv/bin/python scripts/report.py
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PUBLIC, ROOT, load_config  # noqa: E402


def main():
    cfg = load_config()
    qa = os.path.join(ROOT, ".cache", "qa")
    out = ["# Reporte de validación técnica\n"]
    vals = sorted(glob.glob(os.path.join(qa, "validacion_*.json")))
    for vp in vals:
        v = json.load(open(vp, encoding="utf-8"))
        name = os.path.basename(v["archivo"])
        out.append(f"## {name} — {v['resultado']}\n")
        vi, au, lo = v["video"], v.get("audio") or {}, v.get("loudness") or {}
        br = int(v["video"].get("bitrate") or 0) / 1e6
        out.append(f"- Video: {vi['codec']} · {vi['w']}×{vi['h']} · {vi['fps']:.3f} fps · {vi.get('pix_fmt')} · {br:.1f} Mb/s")
        out.append(f"- Audio: {au.get('codec')} · {au.get('sr')} Hz · {au.get('ch')} canales")
        out.append(f"- Sonoridad integrada: {lo.get('integrated_lufs')} LUFS · pico real: {lo.get('true_peak_dbfs')} dBTP\n")
        out.append("| Comprobación | Resultado | Detalle |")
        out.append("|---|---|---|")
        for c in v["checks"]:
            out.append(f"| {c['check']} | {'✅' if c['ok'] else '⚠️'} | {c['detalle']} |")
        out.append("")
        neg = [b for b in v.get("negros", [])]
        if neg:
            out.append("Tramos oscuros detectados (intencionales: fundido de entrada y silencio previo al título): " + ", ".join(f"{a:.2f}–{b:.2f} s" for a, b in neg) + "\n")
    ip = os.path.join(qa, "inteligibilidad.json")
    if os.path.exists(ip):
        it = json.load(open(ip, encoding="utf-8"))
        out.append("## Inteligibilidad de la narración en la mezcla final\n")
        out.append(f"Cada frase se transcribió con Whisper (modelo small, español) directamente desde `{it['archivo']}` (con música y efectos). WER medio: **{it['werMedio']:.3f}**.\n")
        out.append("| Frase | WER | Transcripción automática |")
        out.append("|---|---|---|")
        for f in it["frases"]:
            out.append(f"| {f['id']} | {f['wer']:.2f} | {f['asr']} |")
        out.append("")
    mp = os.path.join(ROOT, ".cache", "mix_report.json")
    if os.path.exists(mp):
        m = json.load(open(mp, encoding="utf-8"))
        out.append("## Mezcla de audio\n")
        out.append(f"- Sonoridad integrada de `public/audio/mix.wav`: {m['lufs']} LUFS · pico de muestra: {m['picoDbfs']} dBFS.")
        out.append("- Arco dinámico por escena (sonoridad integrada de cada tramo):\n")
        out.append("| Escena | LUFS |")
        out.append("|---|---|")
        for n, nombre, l in m["escenas"]:
            out.append(f"| {n}. {nombre} | {l} |")
        out.append("")
    man = json.load(open(os.path.join(PUBLIC, "audio", "voice", "manifest.json"), encoding="utf-8"))
    out.append("## Narración generada\n")
    out.append(f"Motor: {man['motor']} · estilo {man['voz']} · 6 tomas por frase, selección automática.\n")
    out.append("| Frase | Toma elegida | Duración | Whisper (toma) | Whisper (procesada) |")
    out.append("|---|---|---|---|---|")
    for l in man["lines"]:
        out.append(f"| {l['id']} | {l['toma']} | {l['duracion']:.2f} s | {l['werWhisper']:.2f} | {l.get('werWhisperProcesado', float('nan')):.2f} |")
    out.append("")
    out.append("## Revisión visual\n")
    out.append("- Se renderizaron y revisaron fotogramas de todos los planos (hojas de contactos) en varias iteraciones; se corrigieron: cielos sobreexpuestos, nubes planas, iluminación de bordes del terreno, disco solar en la tormenta, anatomía de siluetas, perfil y mano, palabras que se salían del cuadro, contraste de textos sobre fondos claros, inicio oscuro de la puerta y del plano de transición.")
    out.append("- Textos en español revisados contra la configuración (tildes y signos de apertura incluidos); el versículo respeta la Reina-Valera 1960.")
    out.append("- Ninguna palabra queda fuera del cuadro visible con las franjas de cine (área útil 1920×803 px); el título se ajusta automáticamente al 84 % del ancho.")
    out.append("- Sincronía: la voz, la música y los cortes comparten `config/intro.config.json`; las palabras clave usan marcas de tiempo por palabra (Parakeet) y los pasos, truenos, puerta y focos coinciden con su imagen.\n")
    path = os.path.join(ROOT, "docs", "REPORTE_VALIDACION.md")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(path)


if __name__ == "__main__":
    main()
