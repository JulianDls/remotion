"""Genera docs/GUION.md a partir de config/intro.config.json y del manifiesto de voz.

Uso: .venv/bin/python scripts/export_docs.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PUBLIC, ROOT, load_config  # noqa: E402


def ts(s):
    m = int(s // 60)
    return f"{m:02d}:{s - m * 60:05.2f}"


def main():
    cfg = load_config()
    man = {m["id"]: m for m in json.load(open(os.path.join(PUBLIC, "audio", "voice", "manifest.json"), encoding="utf-8"))["lines"]}
    ev = cfg["evento"]
    out = []
    out.append("# Guion definitivo — Intro del congreso juvenil\n")
    out.append(f"Duración: {cfg['video']['duracionSegundos']} s · {cfg['video']['ancho']}×{cfg['video']['alto']} · {cfg['video']['fps']} fps · Narración en español latinoamericano neutro (voz sintética Supertonic 3, estilo {cfg['voz']['estilo']}).\n")
    out.append("> Este documento se genera con `scripts/export_docs.py` a partir de `config/intro.config.json`; si cambias la configuración, vuelve a generarlo.\n")
    out.append("## Narración\n")
    out.append("| # | Escena | Entra | Sale | Registro | Texto |")
    out.append("|---|---|---|---|---|---|")
    for i, l in enumerate(cfg["narracion"], 1):
        d = man.get(l["id"], {}).get("duracion", 0)
        out.append(f"| {i} | {l['escena']} | {ts(l['inicio'])} | {ts(l['inicio'] + d)} | {l['registro']} | {l['texto']} |")
    out.append("")
    out.append("## Textos en pantalla\n")
    v = ev["versiculo"]
    out.append(f"- **Versículo** ({ts(cfg['sincronia']['versiculoLineas'][0])}–{ts(cfg['sincronia']['versiculoSalida'])}): «{' '.join(v['lineas'])}» — {v['referencia']} ({v['traduccion']}).")
    for k in cfg["palabrasClave"]:
        when = f"al pronunciar «{k['enPalabra']}» ({k['vozId']})" if k.get("vozId") else ts(k["inicio"])
        out.append(f"- **{k['palabra']}** — {when}.")
    out.append(f"- **Título** ({ts(cfg['sincronia']['revelacionTitulo'])}): {ev['nombre']}")
    out.append(f"- **Subtítulo** ({ts(cfg['sincronia']['subtitulo'])}): {ev['subtitulo']}")
    out.append(f"- **Lema** ({ts(cfg['sincronia']['impactoFinal'])}): {ev['lema']}")
    out.append("")
    out.append("## Escenas y planos\n")
    for esc in cfg["escenas"]:
        out.append(f"### Escena {esc['n']} — {esc['nombre']} ({ts(esc['inicio'])}–{ts(esc['fin'])})\n")
        out.append("| Plano | Entra | Sale | Tipo | Descripción |")
        out.append("|---|---|---|---|---|")
        for p in cfg["planos"]:
            if esc["inicio"] - 1e-6 <= p["inicio"] < esc["fin"] - 1e-6:
                out.append(f"| {p['id']} | {ts(p['inicio'])} | {ts(p['fin'])} | {p['tipo']} | {p['descripcion']} |")
        out.append("")
    out.append("## Puntos de sincronización (imagen + audio)\n")
    for k, val in cfg["sincronia"].items():
        if k.startswith("_"):
            continue
        out.append(f"- `{k}`: {val}")
    out.append("")
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    path = os.path.join(ROOT, "docs", "GUION.md")
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(path)


if __name__ == "__main__":
    main()
