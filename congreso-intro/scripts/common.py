"""Utilidades compartidas por los scripts de audio e imagen."""

import json
import os
import re

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config", "intro.config.json")
MODELS = os.path.join(ROOT, ".cache", "models")
SAMPLES = os.path.join(ROOT, ".cache", "samples", "vsco")
PUBLIC = os.path.join(ROOT, "public")
SR = 48000


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def seseo(text: str) -> str:
    """Reescribe c(e/i) y z como 's' para forzar pronunciación latinoamericana en el TTS."""

    def keep_case(src: str, rep: str) -> str:
        return rep.upper() if src.isupper() else rep

    text = re.sub(r"[zZ]", lambda m: keep_case(m.group(0), "s"), text)
    text = re.sub(r"([cC])([eéiíEÉIÍ])", lambda m: keep_case(m.group(1), "s") + m.group(2), text)
    return text


def tts_text(line: dict, seseo_enabled: bool) -> str:
    text = line.get("textoTTS") or line["texto"]
    text = text.replace("…", "...")
    if seseo_enabled:
        text = seseo(text)
    return text


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def undb(d):
    return 10 ** (d / 20)
