"""Vista previa de un entorno a partir de meta.json (capa lejana + rayos + capas cercanas)."""
import json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PUBLIC

D = os.path.join(PUBLIC, "images", "plates")
meta = json.load(open(os.path.join(D, "meta.json")))
outdir = sys.argv[1]
for env in sys.argv[2:]:
    m = meta[env]
    capas = m["capas"]
    order = [capas[-1]] + (["+" + m["rayos"]] if m.get("rayos") else []) + capas[:-1][::-1]
    base = None
    for name in order:
        add = name.startswith("+"); name = name.lstrip("+")
        im = cv2.imread(os.path.join(D, env, name), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
        if im.shape[2] == 3:
            im = np.dstack([im, np.ones(im.shape[:2], np.float32)])
        rgb, a = im[..., :3], im[..., 3:4]
        if base is None:
            base = rgb; continue
        base = 1 - (1 - base) * (1 - rgb * a) if add else base * (1 - a) + rgb * a
    img = (np.clip(base, 0, 1) * 255).astype(np.uint8)
    if "luz" in m:
        x, y = int(m["luz"][0] * img.shape[1]), int(m["luz"][1] * img.shape[0])
        cv2.circle(img, (x, y), 6, (0, 0, 255), 1)
    img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_AREA)
    p = os.path.join(outdir, f"{env}.jpg")
    cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(p)
