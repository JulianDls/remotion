"""Hoja de contactos de fotogramas QA. Uso: contact_sheet.py <dir> <salida_prefijo> [cols] [por_hoja]"""
import glob, os, re, sys
import cv2
import numpy as np

d, prefix = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
per = int(sys.argv[4]) if len(sys.argv) > 4 else 12
files = sorted(glob.glob(os.path.join(d, "f_*.jpg")), key=lambda p: float(re.sub(r"[^0-9_]", "", os.path.basename(p)).strip("_").replace("_", ".")))
tw, th = 480, 270
for k in range(0, len(files), per):
    chunk = files[k : k + per]
    rows = (len(chunk) + cols - 1) // cols
    sheet = np.zeros((rows * (th + 4), cols * (tw + 4), 3), np.uint8)
    for i, f in enumerate(chunk):
        im = cv2.resize(cv2.imread(f), (tw, th), interpolation=cv2.INTER_AREA)
        lab = os.path.basename(f)[2:-4].replace("_", ".") + "s"
        cv2.putText(im, lab, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(im, lab, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        r, c = divmod(i, cols)
        sheet[r * (th + 4) : r * (th + 4) + th, c * (tw + 4) : c * (tw + 4) + tw] = im
    out = f"{prefix}_{k // per + 1}.jpg"
    cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 86])
    print(out)
