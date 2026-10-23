"""Vista previa rápida de un entorno: compone sus capas en orden y guarda un JPG reducido.

Uso: .venv/bin/python scripts/preview_plate.py <entorno> <salida.jpg> capa1 capa2 ...
Prefijo '+' en una capa = mezcla aditiva (screen).
"""
import os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PUBLIC

env, outp, layers = sys.argv[1], sys.argv[2], sys.argv[3:]
base = None
for name in layers:
    add = name.startswith("+")
    name = name.lstrip("+")
    p = os.path.join(PUBLIC, "images", "plates", env, name)
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
    if im.shape[2] == 3:
        im = np.dstack([im, np.ones(im.shape[:2], np.float32)])
    rgb, a = im[..., :3], im[..., 3:4]
    if base is None:
        base = rgb * a
        continue
    if add:
        base = 1 - (1 - base) * (1 - rgb * a)
    else:
        base = base * (1 - a) + rgb * a
out = cv2.resize((np.clip(base, 0, 1) * 255).astype(np.uint8), (1600, 900), interpolation=cv2.INTER_AREA)
cv2.imwrite(outp, out, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(outp)
