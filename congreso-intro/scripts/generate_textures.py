"""Texturas auxiliares: niebla en mosaico (sin costuras) y grano de película animado."""
import os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PUBLIC
from plates_lib import fbm, smoothstep

OUT = os.path.join(PUBLIC, "images", "textures")
os.makedirs(OUT, exist_ok=True)

# niebla: dos texturas en mosaico 2048x1024 (alfa = densidad)
for k, (cells, stretch, lo, hi) in enumerate([(3, 2.2, 0.32, 0.85), (6, 1.6, 0.4, 0.9)]):
    w, h = 2048, 1024
    n = fbm(w, h, cells, 7, 0.55, seed=200 + k, tile=True)
    n = (n - n.min()) / (n.max() - n.min())
    a = smoothstep(lo, hi, n)
    a = (a * 255).astype(np.uint8)
    rgba = np.dstack([np.full((h, w), 255, np.uint8)] * 3 + [a])
    cv2.imwrite(os.path.join(OUT, f"niebla{k}.webp"), rgba, [cv2.IMWRITE_WEBP_QUALITY, 85])

# grano: 8 cuadros de 512x512 (gris medio + ruido), para mezclar en 'overlay'
rng = np.random.default_rng(3)
for k in range(8):
    g = rng.standard_normal((512, 512)).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 0.65)
    g = np.clip(128 + g * 38, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(OUT, f"grano{k}.png"), g)
print("texturas:", sorted(os.listdir(OUT)))
