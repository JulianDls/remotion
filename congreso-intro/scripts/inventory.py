"""Genera docs/INVENTARIO_RECURSOS.md: cada archivo de public/ con escena, origen, licencia y resolución/duración.

Uso: .venv/bin/python scripts/inventory.py
"""

import json
import os
import sys

import cv2
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PUBLIC, ROOT, load_config  # noqa: E402

GEN_IMG = "Generado por código para este proyecto (scripts/generate_plates.py)"
LIC_OWN = "Obra original del proyecto (libre uso para el evento)"

ENV_SCENES = {
    "horizonte": "1B",
    "ciudad_aerea": "2A",
    "calle": "2B",
    "skyline": "2C",
    "acantilado": "2D, 3F",
    "acantilado_luz": "5I",
    "tormenta": "3A",
    "cumbre": "3C, 3H",
    "cresta": "3D",
    "rayos": "3E, 5L",
    "cielo": "3G, 4A",
    "puerta": "4B",
    "campo": "5E",
    "amanecer": "4C, 5F, 5K, 5L",
}


def img_info(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is None:
        return "?"
    h, w = im.shape[:2]
    ch = 1 if im.ndim == 2 else im.shape[2]
    return f"{w}×{h}" + (" con alfa" if ch == 4 else "")


def main():
    cfg = load_config()
    rows = []
    pdir = os.path.join(PUBLIC, "images", "plates")
    for env in sorted(os.listdir(pdir)):
        d = os.path.join(pdir, env)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            rows.append((f"images/plates/{env}/{f}", ENV_SCENES.get(env, "—"), GEN_IMG + (" — render 3D por raymarching" if env not in ("calle", "puerta", "ciudad_aerea", "skyline") else ""), LIC_OWN, img_info(os.path.join(d, f)), "—"))
    tdir = os.path.join(PUBLIC, "images", "textures")
    for f in sorted(os.listdir(tdir)):
        rows.append((f"images/textures/{f}", "varias (niebla / grano)", "Generado por código (scripts/generate_textures.py)", LIC_OWN, img_info(os.path.join(tdir, f)), "—"))
    man = {m["id"]: m for m in json.load(open(os.path.join(PUBLIC, "audio", "voice", "manifest.json"), encoding="utf-8"))["lines"]}
    for l in cfg["narracion"]:
        p = os.path.join(PUBLIC, "audio", "voice", f"{l['id']}.wav")
        info = sf.info(p)
        rows.append(
            (
                f"audio/voice/{l['id']}.wav",
                str(l["escena"]),
                "Voz sintética Supertonic 3 (Supertone Inc.) generada localmente con sherpa-onnx; procesada por scripts/generate_voice.py",
                "Modelo: OpenRAIL-M · Código: MIT (uso comercial permitido; ver restricciones de uso de la licencia)",
                f"{info.samplerate} Hz, {info.channels} canal",
                f"{info.duration:.2f} s",
            )
        )
    for f, desc in [("mix.wav", "Mezcla final masterizada (voz + música + efectos)"), ("stems/voz.flac", "Pista de voz"), ("stems/musica.flac", "Pista de música"), ("stems/efectos.flac", "Pista de efectos")]:
        p = os.path.join(PUBLIC, "audio", f)
        if os.path.exists(p):
            info = sf.info(p)
            rows.append(
                (
                    f"audio/{f}",
                    "1–7",
                    desc + ". Música compuesta por código (scripts/compose_score.py) con samples de VS Chamber Orchestra 2 CE y síntesis propia",
                    "Composición original del proyecto; samples VSCO-2-CE en CC0 1.0",
                    f"{info.samplerate} Hz, {info.channels} canales",
                    f"{info.duration:.2f} s",
                )
            )
    fdir = os.path.join(PUBLIC, "fonts")
    for f in sorted(os.listdir(fdir)):
        if f.endswith(".ttf"):
            rows.append((f"fonts/{f}", "textos", "Google Fonts (repositorio google/fonts)", "SIL Open Font License 1.1 (archivo OFL incluido)", "—", "—"))
    out = ["# Inventario de recursos audiovisuales\n"]
    out.append("Todos los recursos visuales y sonoros de la intro se generaron por código para este proyecto o provienen de fuentes con licencia libre verificada. No se usa material del video de referencia, ni música comercial, ni bancos de imágenes.\n")
    out.append("| Archivo (en `public/`) | Escena / plano | Fuente | Licencia / permiso | Resolución / formato | Duración |")
    out.append("|---|---|---|---|---|---|")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    out.append("")
    out.append("## Recursos externos usados durante la producción (no incluidos en `public/`)\n")
    out.append("| Recurso | Uso | Licencia |")
    out.append("|---|---|---|")
    out.append("| VS Chamber Orchestra 2 Community Edition (github.com/sgossner/VSCO-2-CE) | Samples de cuerdas, metales, timbales, platos, gong, arpa, glockenspiel y piano usados por el sampler de `compose_score.py` | CC0 1.0 (dominio público) |")
    out.append("| Supertonic 3 int8 (sherpa-onnx, Supertone Inc.) | Síntesis de la narración | Modelo OpenRAIL-M, código MIT |")
    out.append("| Whisper small (OpenAI) vía sherpa-onnx | Verificación automática de la dicción (no aparece en el video) | MIT |")
    out.append("| Parakeet TDT 0.6B v3 (NVIDIA) vía sherpa-onnx | Marcas de tiempo por palabra para sincronizar textos (no aparece en el video) | CC-BY-4.0 |")
    out.append("| Remotion 4.0.538 | Composición y render del video | Remotion License: gratuita para personas, organizaciones sin fines de lucro y empresas de hasta 3 empleados; las demás necesitan licencia de empresa (remotion.pro) |")
    out.append("| Bebas Neue, Montserrat, Oswald | Tipografías | SIL OFL 1.1 |")
    out.append("")
    path = os.path.join(ROOT, "docs", "INVENTARIO_RECURSOS.md")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(path, len(rows), "recursos")


if __name__ == "__main__":
    main()
