"""Validación técnica de un MP4 renderizado.

Comprueba: contenedor y códecs, resolución, fps, duración, audio (48 kHz estéreo), sonoridad
integrada y pico real (EBU R128), silencios inesperados, fotogramas negros inesperados y
extrae un fotograma representativo de cada plano para inspección.

Uso: .venv/bin/python scripts/validate_video.py output/intro_congreso.mp4 [--frames]
Escribe el resultado en .cache/qa/validacion_<nombre>.json
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, load_config  # noqa: E402


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    path = sys.argv[1]
    want_frames = "--frames" in sys.argv
    cfg = load_config()
    res = {"archivo": path, "checks": []}

    def check(name, ok, detail):
        res["checks"].append({"check": name, "ok": bool(ok), "detalle": detail})
        print(f"[{'OK' if ok else 'FALLO'}] {name}: {detail}")

    pr = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    fmt = pr["format"]
    dur = float(fmt["duration"])
    num, den = map(int, v["r_frame_rate"].split("/"))
    fps = num / den
    res["video"] = {"codec": v["codec_name"], "w": v["width"], "h": v["height"], "fps": fps, "pix_fmt": v.get("pix_fmt"), "bitrate": fmt.get("bit_rate")}
    res["audio"] = {"codec": a["codec_name"], "sr": int(a["sample_rate"]), "ch": a["channels"]} if a else None
    check("Contenedor MP4", "mp4" in fmt["format_name"], fmt["format_name"])
    check("Códec de video H.264", v["codec_name"] == "h264", f"{v['codec_name']} {v.get('profile', '')} {v.get('pix_fmt')}")
    check("Frecuencia 30 fps", abs(fps - cfg["video"]["fps"]) < 0.01, f"{fps:.3f} fps")
    check("Duración ≈ 90 s", abs(dur - cfg["video"]["duracionSegundos"]) < 0.2, f"{dur:.3f} s")
    check("Resolución 16:9", abs(v["width"] / v["height"] - 16 / 9) < 0.01, f"{v['width']}×{v['height']}")
    if a:
        check("Audio AAC estéreo 48 kHz", a["codec_name"] == "aac" and int(a["sample_rate"]) == 48000 and a["channels"] == 2, f"{a['codec_name']} {a['sample_rate']} Hz {a['channels']} canales")
        adur = float(a.get("duration", dur))
        check("Audio cubre todo el video", abs(adur - dur) < 0.15, f"audio {adur:.3f} s / video {dur:.3f} s")
    # sonoridad EBU R128
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-filter_complex", "ebur128=peak=true", "-f", "null", "-"]).stderr
    m_i = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    m_tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)
    lufs = float(m_i[-1]) if m_i else None
    tp = float(m_tp[-1]) if m_tp else None
    res["loudness"] = {"integrated_lufs": lufs, "true_peak_dbfs": tp}
    check("Sonoridad integrada (−16…−12 LUFS)", lufs is not None and -16.5 <= lufs <= -11.5, f"{lufs} LUFS")
    check("Sin saturación (pico real ≤ −0,5 dBTP)", tp is not None and tp <= -0.5, f"{tp} dBTP")
    # silencios (se espera uno: el silencio controlado antes del título)
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "silencedetect=noise=-60dB:d=0.4", "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", out)]
    sil = list(zip(starts, ends + [dur] * (len(starts) - len(ends))))
    t_cut, t_rev = cfg["sincronia"]["corteSilencio"], cfg["sincronia"]["revelacionTitulo"]
    unexpected = [s for s in sil if not (s[0] >= t_cut - 0.2 and s[1] <= t_rev + 0.2) and not (s[0] < 0.6 and s[1] < 1.5)]
    res["silencios"] = sil
    check("Sin silencios accidentales", len(unexpected) == 0, f"silencios: {[(round(x, 2), round(y, 2)) for x, y in sil]}")
    # negros (se esperan: inicio y el instante antes del título)
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vf", "blackdetect=d=0.5:pic_th=0.985:pix_th=0.06", "-an", "-f", "null", "-"]).stderr
    blacks = [(float(x), float(y)) for x, y in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", out)]
    unexpected_b = [b for b in blacks if not (b[0] < 1.0) and not (b[0] >= t_cut - 0.3 and b[1] <= t_rev + 0.3)]
    res["negros"] = blacks
    check("Sin pantallas negras accidentales", len(unexpected_b) == 0, f"tramos negros: {[(round(x, 2), round(y, 2)) for x, y in blacks]}")
    # fotogramas representativos de cada plano
    if want_frames:
        name = os.path.splitext(os.path.basename(path))[0]
        fdir = os.path.join(ROOT, ".cache", "qa", f"frames_{name}")
        os.makedirs(fdir, exist_ok=True)
        for p in cfg["planos"]:
            t = (p["inicio"] + p["fin"]) / 2
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-q:v", "3", os.path.join(fdir, f"f_{t:.2f}".replace(".", "_") + ".jpg")])
        res["fotogramas"] = fdir
        print("fotogramas:", fdir)
    ok = all(c["ok"] for c in res["checks"])
    res["resultado"] = "APROBADO" if ok else "CON OBSERVACIONES"
    os.makedirs(os.path.join(ROOT, ".cache", "qa"), exist_ok=True)
    outp = os.path.join(ROOT, ".cache", "qa", f"validacion_{os.path.splitext(os.path.basename(path))[0]}.json")
    json.dump(res, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(res["resultado"], "->", outp)


if __name__ == "__main__":
    main()
