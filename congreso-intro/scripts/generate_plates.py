"""Genera los fondos procedurales por capas en public/images/plates/<entorno>/.

Uso: .venv/bin/python scripts/generate_plates.py [entorno ...]
     PLATE_SCALE=0.5 para vistas previas rápidas.

Entornos de paisaje: render 3D por raymarching (scripts/terrain.py), separados en capas por
distancia para animarlos con parallax. Entornos urbanos/arquitectónicos: composición 2D procedural.
"""

import json
import math
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terrain as T  # noqa: E402
from common import PUBLIC, load_config  # noqa: E402
from plates_lib import (  # noqa: E402
    blur,
    col,
    fbm,
    glow,
    god_rays,
    lin_to_srgb,
    noise1d,
    save_rgb,
    save_rgba,
    smoothstep,
    stars,
    tonemap,
    vgrad,
    warp,
)

SCALE = float(os.environ.get("PLATE_SCALE", "1"))
W, H = int(3200 * SCALE), int(1800 * SCALE)
OUTDIR = os.path.join(PUBLIC, "images", "plates")
PAL = load_config()["paleta"]
C_BLACK = col(PAL["negro"])
C_NIGHT = col(PAL["azulNoche"])
C_BLUE = col(PAL["azulElectrico"])
C_WHITE = col(PAL["blanco"])
C_GOLD = col(PAL["dorado"])


def out(env, name):
    return os.path.join(OUTDIR, env, name)


# ================================================================== terreno 3D
def mkP(scale_xz=3.0, scale_y=1.6, octaves=9, seed=7, erosion=1.0, ridge=0.25, base=0.0, valley=(0, 0, 0), cliff=(0, 0, 0, 0), flat=(0, 0, 0, 0, 0, 0), peak=(0, 0, 0, 0)):
    return np.array([scale_xz, scale_y, octaves, seed, erosion, ridge, base, *valley, *cliff, *flat, *peak], np.float64)


def project(cam, d, w, h):
    f, r, u, tf = cam[3:6], cam[6:9], cam[9:12], cam[12]
    d = np.asarray(d, np.float64)
    z = d @ f
    if z <= 1e-6:
        return None
    x = (d @ r) / z / tf / (w / h)
    y = (d @ u) / z / tf
    return (x + 1) / 2 * w, (1 - y) / 2 * h


def ground_line(alpha, n=240):
    h, w = alpha.shape
    xs = np.linspace(0, w - 1, n).astype(int)
    prof = []
    for x in xs:
        colm = np.where(alpha[:, x] > 0.5)[0]
        prof.append(round(float(colm[0]) / h, 4) if len(colm) else 1.0)
    return prof


def terrain_env(env, spec):
    cam = T.look_at(*spec["cam"])
    P = mkP(**spec["P"])
    Pn = P.copy()
    Pn[2] = P[2] + 3
    az, el = spec["sun"]["dir"]
    sd = T.sun_dir(az, el)
    s = spec["sun"]
    sun = np.array([*sd, *s["color"], s["intensity"], s.get("disk", 0.010), s.get("power", 8.0)], np.float64)
    sky = np.array([*spec["sky"]["zenith"], *spec["sky"]["horizon"], *spec["sky"].get("ground", (0.02, 0.02, 0.03))], np.float64)
    f = spec["fog"]
    fog = np.array([f["density"], f["falloff"], *f["base"], *f["sun"], f.get("mie", 10.0), f.get("ambient", 0.35)], np.float64)
    c = spec.get("cloud")
    cloud = np.array(
        [c["y"], c["scale"], c["coverage"], c["seed"], c["opacity"], *c["shadow"], c.get("lit", 1.0), math.radians(c.get("gap", 0.0)), c.get("absorb", 1.0), c.get("soft", 0.32)]
        if c
        else [5, 5, 0.5, 1, 0.0, 0, 0, 0, 1, 0, 1, 0.32],
        np.float64,
    )
    m = spec["mat"]
    mat = [*m["color"], m.get("snow", -100.0), m.get("rim", 1.2), m.get("direct", 1.0), s.get("core", 1.0)]
    layers = T.render_layers(W, H, cam, P, sun, sky, fog, cloud, mat, spec["splits"], Pn)
    expo = spec.get("exposure", 1.0)
    meta = {"capas": []}
    sun_xy = project(cam, sd, W, H)
    if sun_xy is not None:
        meta["luz"] = [round(sun_xy[0] / W, 4), round(sun_xy[1] / H, 4)]
    n = len(layers)
    for k, (rgb, alpha, tt) in enumerate(layers):
        last = k == n - 1
        if last and spec.get("stars"):
            skym = (tt > 1e8).astype(np.float32)
            st = stars(H, W, int(spec["stars"] * SCALE * SCALE + 50), seed=5, max_size=1.6 * SCALE + 0.6)
            ys = np.linspace(0, 1, H, dtype=np.float32)[:, None]
            rgb = rgb + (st * skym * smoothstep(0.62, 0.2, ys))[..., None] * col("#cfd8ff") * spec.get("star_gain", 0.5)
        img = tonemap(rgb, expo)
        name = f"capa{k}"
        if last:
            save_rgb(out(env, f"{name}.jpg"), img, 93)
            meta["capas"].append(f"{name}.jpg")
        else:
            a = blur(alpha, 0.8 * SCALE + 0.2)
            save_rgba(out(env, f"{name}.webp"), img, a, 92)
            meta["capas"].append(f"{name}.webp")
            meta[f"suelo{k}"] = ground_line(alpha)
    if spec.get("rock"):
        meta.update(foreground_rock(env, meta.get("luz", [0.6, 0.35])))
        meta["capas"] = ["roca.webp"] + meta["capas"]
    # rayos volumétricos en espacio de pantalla desde el sol
    if spec.get("rays") and sun_xy is not None:
        rgb, alpha, tt = layers[-1]
        lum = tonemap(rgb, expo).mean(axis=2)
        skym = (tt > 1e8).astype(np.float32)
        # oclusión por capas cercanas
        occ = np.ones_like(skym)
        for k in range(n - 1):
            occ *= 1 - layers[k][1]
        bright = np.clip((lum - spec["rays"].get("threshold", 0.45)) / 0.5, 0, 1) * skym * occ
        sx, sy = sun_xy
        small = cv2.resize(bright, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        r = god_rays(small, sx / 2, sy / 2, samples=96, decay=spec["rays"].get("decay", 0.986), density=1.0)
        r = cv2.resize(r, (W, H), interpolation=cv2.INTER_CUBIC)
        r = np.clip(r * spec["rays"].get("gain", 2.0), 0, 1)
        rcol = np.ones((H, W, 3), np.float32) * (C_GOLD * 0.8 + C_WHITE * 0.3)
        save_rgba(out(env, "rayos.webp"), rcol, r ** 1.1 * spec["rays"].get("opacity", 0.8), 90)
        meta["rayos"] = "rayos.webp"
    return meta


def foreground_rock(env, luz, edge_x=0.43, edge_y=0.79):
    """Roca de primer plano (2D) con borde iluminado hacia la luz; devuelve el punto donde se para la figura."""
    ex, ey = W * edge_x, H * edge_y
    xs = np.linspace(0, ex, 400)
    top = ey + (1 - xs / ex) * H * 0.035 + (noise1d(400, 14, 6, 51, persistence=0.55) - 0.5) * H * 0.03
    top[-12:] = np.linspace(top[-12], ey, 12)
    ys = np.linspace(ey, H * 1.02, 200)
    face = ex - (ys - ey) * 0.32 + (noise1d(200, 10, 6, 52, persistence=0.6) - 0.5) * W * 0.03
    pts = [(0, H * 1.02), (0, top[0])] + list(zip(xs, top)) + list(zip(face, ys))
    pts = np.array([[int(px * 4), int(py * 4)] for px, py in pts], np.int32)
    big = np.zeros((H * 4 // 4 * 1, W), np.uint8)
    big = np.zeros((H, W), np.uint8)
    cv2.fillPoly(big, [pts], 255, lineType=cv2.LINE_AA, shift=2)
    a = blur(big.astype(np.float32) / 255, 0.6)
    tex = fbm(W, H, 50, 6, seed=53)
    cracks = 1 - np.abs(fbm(W, H, 18, 5, seed=54) * 2 - 1)
    rock = col("#05070c")[None, None, :] * (0.55 + 0.9 * tex[..., None]) * (0.75 + 0.5 * cracks[..., None] ** 4)
    lx, ly = luz[0] * W, luz[1] * H
    d = np.array([lx - ex, ly - ey], np.float32)
    d /= np.linalg.norm(d) + 1e-6
    from plates_lib import rim_light
    r = rim_light(a, (float(d[0]), float(d[1])), width=max(3, int(8 * SCALE)), sigma=1.2 * SCALE + 0.3)
    rock = rock + r[..., None] * (C_GOLD * 0.9 + C_WHITE * 0.2) * 1.1
    save_rgba(out(env, "roca.webp"), tonemap(rock), a, 92)
    fx = ex - W * 0.035
    fy = float(np.interp(fx, xs, top))
    return {"figura": [round(fx / W, 4), round(fy / H, 4)]}


# ------------------------------------------------------------------ definiciones de paisajes
def spec_horizonte():
    return {
        "cam": ((0.0, 0.3, 0.0), (0.0, 0.36, 10.0), 46),
        "P": {"scale_xz": 2.6, "scale_y": 1.3, "seed": 31, "ridge": 0.35, "erosion": 1.2, "base": -0.15, "flat": (0.0, 9.0, 0.9, 0.0, 0.0, 0.035)},
        "sun": {"dir": (4, -4.0), "color": (0.45, 0.55, 0.95), "intensity": 0.22, "disk": 0.0, "power": 9.0, "core": 0.0},
        "sky": {"zenith": (0.001, 0.0016, 0.0045), "horizon": (0.006, 0.009, 0.02)},
        "fog": {"density": 0.03, "falloff": 1.8, "base": (0.006, 0.009, 0.02), "sun": (0.05, 0.065, 0.12), "mie": 5.0, "ambient": 0.5},
        "cloud": {"y": 4.0, "scale": 7.0, "coverage": 0.36, "seed": 4, "opacity": 0.7, "shadow": (0.002, 0.003, 0.007), "lit": 0.25},
        "mat": {"color": (0.025, 0.03, 0.04), "rim": 0.6},
        "splits": [2.5, 9.0],
        "exposure": 1.0,
        "stars": 2600,
        "star_gain": 0.55,
    }


def spec_acantilado():
    return {
        "cam": ((0.0, 0.66, 0.0), (0.05, 0.6, 6.0), 50),
        "P": {"scale_xz": 2.4, "scale_y": 1.4, "seed": 12, "ridge": 0.3, "erosion": 1.1, "base": -0.25, "valley": (0.0, 2.0, 0.5)},
        "sun": {"dir": (14, 6.5), "color": (1.0, 0.76, 0.48), "intensity": 1.7, "disk": 0.007, "power": 60.0},
        "sky": {"zenith": (0.006, 0.01, 0.024), "horizon": (0.045, 0.055, 0.08)},
        "fog": {"density": 0.075, "falloff": 1.4, "base": (0.018, 0.026, 0.048), "sun": (0.42, 0.30, 0.17), "mie": 14.0, "ambient": 0.45},
        "cloud": {"y": 3.0, "scale": 3.6, "coverage": 0.66, "seed": 9, "opacity": 0.98, "shadow": (0.006, 0.009, 0.018), "lit": 1.0, "gap": 7.0, "absorb": 1.2},
        "mat": {"color": (0.035, 0.038, 0.045), "rim": 1.6},
        "splits": [6.0],
        "exposure": 1.0,
        "rays": {"threshold": 0.42, "gain": 2.4, "opacity": 0.8, "decay": 0.988},
        "rock": True,
    }


def spec_acantilado_luz():
    s = spec_acantilado()
    s["sun"] = {"dir": (8, 4.0), "color": (1.0, 0.8, 0.52), "intensity": 2.6, "disk": 0.011, "power": 30.0}
    s["cloud"].update({"coverage": 0.5, "gap": 14.0, "lit": 1.2})
    s["sky"] = {"zenith": (0.012, 0.02, 0.045), "horizon": (0.16, 0.14, 0.13)}
    s["fog"].update({"sun": (0.95, 0.68, 0.36), "base": (0.04, 0.045, 0.065), "mie": 8.0})
    s["exposure"] = 1.05
    s["rays"] = {"threshold": 0.5, "gain": 2.6, "opacity": 0.9, "decay": 0.989}
    return s


def spec_tormenta():
    return {
        "cam": ((0.0, 0.55, 0.0), (0.0, 0.92, 8.0), 56),
        "P": {"scale_xz": 2.2, "scale_y": 1.7, "seed": 41, "ridge": 0.45, "erosion": 1.0, "base": -0.35, "flat": (0.0, 3.5, 0.75, 0.0, 0.0, 0.0)},
        "sun": {"dir": (-14, 13), "color": (0.9, 0.86, 0.8), "intensity": 0.55, "disk": 0.0, "power": 60.0, "core": 0.0},
        "sky": {"zenith": (0.004, 0.005, 0.009), "horizon": (0.025, 0.028, 0.036)},
        "fog": {"density": 0.06, "falloff": 1.0, "base": (0.014, 0.017, 0.026), "sun": (0.12, 0.115, 0.11), "mie": 10.0, "ambient": 0.5},
        "cloud": {"y": 2.4, "scale": 2.8, "coverage": 0.86, "seed": 17, "opacity": 1.0, "shadow": (0.004, 0.005, 0.008), "lit": 0.4, "gap": 0.0, "absorb": 1.6, "soft": 0.45},
        "mat": {"color": (0.022, 0.024, 0.03), "rim": 0.7, "direct": 0.18},
        "splits": [3.0],
        "exposure": 1.0,
        "rays": {"threshold": 0.2, "gain": 3.0, "opacity": 0.75, "decay": 0.987},
    }


def spec_cumbre():
    return {
        "cam": ((-0.6, 0.75, -1.0), (0.4, 1.35, 6.0), 42),
        "P": {"scale_xz": 2.0, "scale_y": 1.2, "seed": 63, "ridge": 0.5, "erosion": 1.3, "base": -0.5, "peak": (0.6, 5.6, 1.4, 1.9)},
        "sun": {"dir": (58, 4.0), "color": (1.0, 0.64, 0.34), "intensity": 4.2, "disk": 0.0, "power": 30.0},
        "sky": {"zenith": (0.008, 0.014, 0.034), "horizon": (0.08, 0.075, 0.09)},
        "fog": {"density": 0.06, "falloff": 1.5, "base": (0.02, 0.03, 0.055), "sun": (0.65, 0.4, 0.2), "mie": 4.0, "ambient": 0.5},
        "cloud": {"y": 4.0, "scale": 5.0, "coverage": 0.4, "seed": 21, "opacity": 0.85, "shadow": (0.008, 0.012, 0.024), "lit": 1.0, "soft": 0.4},
        "mat": {"color": (0.05, 0.052, 0.06), "snow": 0.75, "rim": 1.0},
        "splits": [4.5],
        "exposure": 1.1,
    }


def spec_cresta():
    """Cresta para los caminantes (vista lateral, contraluz)."""
    return {
        "cam": ((0.0, 0.42, 0.0), (0.0, 0.6, 6.0), 40),
        "P": {"scale_xz": 2.8, "scale_y": 1.2, "seed": 77, "ridge": 0.2, "erosion": 1.4, "base": -0.3, "cliff": (0.0, 2.2, 1.6, 0.52)},
        "sun": {"dir": (-7, 4.5), "color": (1.0, 0.72, 0.42), "intensity": 2.2, "disk": 0.01, "power": 30.0},
        "sky": {"zenith": (0.01, 0.017, 0.04), "horizon": (0.12, 0.11, 0.12)},
        "fog": {"density": 0.05, "falloff": 1.2, "base": (0.03, 0.035, 0.05), "sun": (0.7, 0.48, 0.27), "mie": 7.0, "ambient": 0.4},
        "cloud": {"y": 3.5, "scale": 5.0, "coverage": 0.48, "seed": 33, "opacity": 0.9, "shadow": (0.01, 0.012, 0.022), "lit": 1.0, "gap": 6.0},
        "mat": {"color": (0.02, 0.022, 0.028), "rim": 2.0},
        "splits": [3.0],
        "exposure": 0.85,
        "rays": {"threshold": 0.5, "gain": 2.0, "opacity": 0.6},
    }


def spec_campo():
    """Llanura con sol bajo de frente: jóvenes caminando hacia la cámara a contraluz."""
    return {
        "cam": ((0.0, 0.12, 0.0), (0.0, 0.17, 8.0), 42),
        "P": {"scale_xz": 2.6, "scale_y": 1.2, "seed": 85, "ridge": 0.3, "erosion": 1.2, "base": -0.1, "flat": (0.0, 6.0, 0.96, 0.0, 0.0, 0.03)},
        "sun": {"dir": (0, 2.4), "color": (1.0, 0.72, 0.42), "intensity": 2.8, "disk": 0.013, "power": 20.0},
        "sky": {"zenith": (0.012, 0.02, 0.05), "horizon": (0.2, 0.15, 0.13)},
        "fog": {"density": 0.08, "falloff": 2.0, "base": (0.05, 0.05, 0.07), "sun": (1.0, 0.68, 0.36), "mie": 5.0, "ambient": 0.4},
        "cloud": {"y": 3.0, "scale": 5.0, "coverage": 0.45, "seed": 37, "opacity": 0.85, "shadow": (0.015, 0.016, 0.026), "lit": 1.1, "gap": 8.0},
        "mat": {"color": (0.03, 0.03, 0.033), "rim": 1.2},
        "splits": [6.0],
        "exposure": 1.0,
        "rays": {"threshold": 0.55, "gain": 2.0, "opacity": 0.7},
    }


def spec_rayos():
    return {
        "cam": ((0.0, 1.3, 0.0), (0.0, 2.25, 8.0), 60),
        "P": {"scale_xz": 2.6, "scale_y": 1.5, "seed": 92, "ridge": 0.35, "erosion": 1.1, "base": -0.4},
        "sun": {"dir": (6, 21), "color": (1.0, 0.84, 0.58), "intensity": 2.2, "disk": 0.0, "power": 60.0},
        "sky": {"zenith": (0.006, 0.011, 0.026), "horizon": (0.04, 0.05, 0.075)},
        "fog": {"density": 0.05, "falloff": 1.2, "base": (0.02, 0.028, 0.048), "sun": (0.3, 0.24, 0.15), "mie": 10.0, "ambient": 0.5},
        "cloud": {"y": 2.8, "scale": 2.6, "coverage": 0.68, "seed": 44, "opacity": 1.0, "shadow": (0.007, 0.01, 0.02), "lit": 1.1, "gap": 3.5, "absorb": 1.3},
        "mat": {"color": (0.035, 0.04, 0.05), "rim": 1.0},
        "splits": [],
        "exposure": 0.78,
        "rays": {"threshold": 0.3, "gain": 3.2, "opacity": 0.9, "decay": 0.991},
    }


def spec_cielo():
    """Cielo inmenso para el versículo: nubes doradas, luz alta, horizonte bajo."""
    return {
        "cam": ((0.0, 1.0, 0.0), (0.0, 2.05, 8.0), 62),
        "P": {"scale_xz": 2.8, "scale_y": 1.3, "seed": 101, "ridge": 0.3, "erosion": 1.1, "base": -0.5},
        "sun": {"dir": (0, 19), "color": (1.0, 0.8, 0.52), "intensity": 1.5, "disk": 0.0, "power": 50.0, "core": 0.5},
        "sky": {"zenith": (0.006, 0.012, 0.03), "horizon": (0.05, 0.055, 0.075)},
        "fog": {"density": 0.05, "falloff": 1.2, "base": (0.022, 0.026, 0.042), "sun": (0.38, 0.28, 0.16), "mie": 10.0, "ambient": 0.5},
        "cloud": {"y": 2.5, "scale": 3.0, "coverage": 0.66, "seed": 51, "opacity": 0.98, "shadow": (0.006, 0.008, 0.016), "lit": 1.0, "gap": 0.0, "soft": 0.4},
        "mat": {"color": (0.025, 0.028, 0.035), "rim": 1.2},
        "splits": [],
        "exposure": 0.7,
        "rays": {"threshold": 0.3, "gain": 3.0, "opacity": 0.85, "decay": 0.991},
    }


def spec_amanecer():
    return {
        "cam": ((0.0, 0.9, 0.0), (0.0, 0.84, 8.0), 50),
        "P": {"scale_xz": 2.5, "scale_y": 1.3, "seed": 118, "ridge": 0.3, "erosion": 1.2, "base": -0.25, "valley": (0.0, 1.8, 0.4)},
        "sun": {"dir": (2, 1.8), "color": (1.0, 0.68, 0.36), "intensity": 3.4, "disk": 0.015, "power": 14.0},
        "sky": {"zenith": (0.012, 0.022, 0.06), "horizon": (0.32, 0.22, 0.16)},
        "fog": {"density": 0.07, "falloff": 1.6, "base": (0.05, 0.05, 0.07), "sun": (1.2, 0.78, 0.4), "mie": 4.0, "ambient": 0.45},
        "cloud": {"y": 3.0, "scale": 5.0, "coverage": 0.42, "seed": 61, "opacity": 0.85, "shadow": (0.02, 0.02, 0.035), "lit": 1.3, "gap": 10.0},
        "mat": {"color": (0.035, 0.034, 0.038), "rim": 1.4},
        "splits": [1.6, 6.0],
        "exposure": 0.88,
        "rays": {"threshold": 0.6, "gain": 2.0, "opacity": 0.7, "decay": 0.986},
    }


TERRAIN_ENVS = {
    "horizonte": spec_horizonte,
    "acantilado": spec_acantilado,
    "acantilado_luz": spec_acantilado_luz,
    "tormenta": spec_tormenta,
    "cumbre": spec_cumbre,
    "cresta": spec_cresta,
    "campo": spec_campo,
    "rayos": spec_rayos,
    "cielo": spec_cielo,
    "amanecer": spec_amanecer,
}


def main():
    names = sys.argv[1:] or list(TERRAIN_ENVS)
    meta_path = os.path.join(OUTDIR, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for n in names:
        t0 = time.time()
        if n in TERRAIN_ENVS:
            info = terrain_env(n, TERRAIN_ENVS[n]())
        else:
            info = ENVS_2D[n]()
        meta[n] = info or {}
        print(f"{n}: {time.time() - t0:.1f}s", flush=True)
        os.makedirs(OUTDIR, exist_ok=True)
        json.dump(meta, open(meta_path, "w"), indent=1)


ENVS_2D = {}



# ================================================================== entornos 2D
def env_calle():
    """Calle nocturna en perspectiva (cámara a 1.6 m), suelo mojado y farolas de sodio."""
    env = "calle"
    rng = np.random.default_rng(12)
    f = W * 0.9
    cx, cy = W * 0.5, H * 0.47
    cam_h = 1.6

    def P3(x, y, z):
        return cx + f * x / z, cy - f * (y - cam_h) / z

    img = np.zeros((H, W, 3), np.float32)
    lights = np.zeros((H, W, 3), np.float32)
    sky = vgrad(H, W, [(0, col("#03050a")), (0.45, col("#0a1020")), (0.5, col("#1a1c28"))])
    img[:] = sky
    road_w = 6.0
    side = 2.5
    zmax = 260.0
    # suelo (calzada y aceras)
    ys = np.arange(H, dtype=np.float32)
    zrow = np.where(ys > cy + 1, f * cam_h / np.maximum(ys - cy, 1e-3), 1e9)
    ground = np.zeros((H, W, 3), np.float32)
    xs = np.arange(W, dtype=np.float32)
    X = (xs[None, :] - cx) * zrow[:, None] / f
    on_road = np.abs(X) < road_w
    asphalt = col("#07080c")
    walk = col("#0c0d12")
    ground[:] = np.where(on_road[..., None], asphalt, walk)
    lane = (np.abs(np.abs(X) - 0.0) < 0.08) & ((np.floor(zrow[:, None] / 3.0) % 2) == 0)
    ground = np.where(lane[..., None], col("#3a3a3a") * 0.5, ground)
    curb = np.abs(np.abs(X) - road_w) < 0.12
    ground = np.where(curb[..., None], col("#1a1b20"), ground)
    gmask = (ys[:, None] > cy + 1) & np.ones((1, W), bool)
    img = np.where(gmask[..., None], ground, img)
    # edificios a ambos lados (fachadas)
    for s_ in (-1, 1):
        z = 4.0
        while z < zmax:
            depth = rng.uniform(10, 26)
            bh = rng.uniform(9, 30)
            xf = (road_w + side) * s_
            pts = [P3(xf, 0, z), P3(xf, bh, z), P3(xf, bh, z + depth), P3(xf, 0, z + depth)]
            poly = np.array([[int(px * 4), int(py * 4)] for px, py in pts], np.int32)
            shade = col("#0a0c13") * (0.8 + 0.4 * rng.random())
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [poly], 1, shift=2)
            img = np.where(m[..., None] > 0, shade, img)
            # ventanas en la fachada (filas y columnas en coordenadas 3D)
            for fy in np.arange(4.0, bh - 1.5, 3.2):
                for fz in np.arange(z + 1.0, z + depth - 1.0, 2.6):
                    if rng.random() < 0.18:
                        c = np.array([1.0, 0.7, 0.38]) if rng.random() < 0.7 else np.array([0.75, 0.85, 1.0])
                        q = [P3(xf, fy, fz), P3(xf, fy + 1.4, fz), P3(xf, fy + 1.4, fz + 1.2), P3(xf, fy, fz + 1.2)]
                        qp = np.array([[int(px * 4), int(py * 4)] for px, py in q], np.int32)
                        cv2.fillPoly(lights, [qp], (c * rng.uniform(0.4, 1.0)).tolist(), shift=2)
            # escaparate a pie de calle
            if rng.random() < 0.35:
                q = [P3(xf, 0.3, z + 2), P3(xf, 3.0, z + 2), P3(xf, 3.0, z + depth - 2), P3(xf, 0.3, z + depth - 2)]
                qp = np.array([[int(px * 4), int(py * 4)] for px, py in q], np.int32)
                cv2.fillPoly(lights, [qp], (np.array([1.0, 0.8, 0.55]) * rng.uniform(0.08, 0.22)).tolist(), shift=2)
            z += depth + rng.uniform(0, 1.5)
    # farolas
    lamp_pts = []
    for s_ in (-1, 1):
        for z in np.arange(18.0 + (s_ + 1) * 6, zmax, 22.0):
            xp = (road_w + 0.6) * s_
            p0 = P3(xp, 0, z)
            p1 = P3(xp, 6.5, z)
            p2 = P3(xp - s_ * 1.6, 6.5, z)
            th = max(1, int(f * 0.14 / z))
            cv2.line(img, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), col("#050608").tolist(), th, cv2.LINE_AA)
            cv2.line(img, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), col("#050608").tolist(), th, cv2.LINE_AA)
            lamp_pts.append((p2, z))
    lamp_layer = np.zeros((H, W), np.float32)
    cone = np.zeros((H, W), np.float32)
    for (px, py), z in lamp_pts:
        r = max(2.0, f * 0.25 / z)
        cv2.circle(lamp_layer, (int(px), int(py)), int(r), 1.0, -1, cv2.LINE_AA)
        # charco de luz en el suelo (elipse en perspectiva)
        gx, gy = px, cy + f * cam_h / z
        cv2.ellipse(cone, (int(gx), int(gy)), (int(f * 1.7 / z), max(1, int(f * 0.32 / z))), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    sodium = np.array([1.0, 0.62, 0.28], np.float32)
    lamps = lamp_layer[..., None] * sodium * 6.0
    halo = blur(lamp_layer, 6 * SCALE + 2)[..., None] * sodium * 3.0 + blur(lamp_layer, 30 * SCALE + 4)[..., None] * sodium * 1.2
    pools = blur(cone, 14 * SCALE + 3)[..., None] * sodium * 0.1
    # reflejos en el suelo mojado (espejo vertical estirado)
    src = lights + lamps * 0.25 + halo * 0.3
    refl = np.zeros_like(src)
    for yy in range(int(cy) + 1, H):
        mirror = int(2 * cy - yy)
        if 0 <= mirror < H:
            refl[yy] = src[mirror]
    refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=2.0 * SCALE + 0.5, sigmaY=18 * SCALE + 3)
    wet = smoothstep(cy, H, ys)[:, None, None]
    lights = blur(lights, 0.6)
    tex = fbm(W, H, 80, 5, seed=17)
    img = img * (0.75 + 0.5 * tex[..., None])
    amb_l = blur(lamp_layer, 120 * SCALE + 10)[..., None] * sodium * 0.9
    img = img + img * amb_l * 30 + lights + lamps + halo + pools + refl * 0.5 * (0.4 + 0.6 * wet)
    # niebla de profundidad
    zfog = np.clip(np.where(gmask, zrow[:, None], 300.0) / 300.0, 0, 1)
    fogc = col("#2a2a34")
    hfog = glow(H, W, cx, cy, W * 0.5, 2.0)[..., None]
    img = img * (1 - hfog * 0.35) + fogc * hfog * 0.35 + col("#3a2a20") * hfog * 0.15
    save_rgb(out(env, "calle.jpg"), tonemap(img, 1.1), 93)
    return {"capas": ["calle.jpg"], "fuga": [0.5, round(cy / H, 4)], "suelo_figura": [0.5, 0.86]}


def env_ciudad_aerea():
    """Ciudad nocturna desde lo alto (perspectiva monumental)."""
    import city3d

    env = "ciudad_aerea"
    sky = vgrad(H, W, [(0, col("#020309")), (0.22, col("#050a16")), (0.33, col("#0e1424")), (0.38, col("#1d1c26")), (1.0, col("#0a0c12"))])
    img, z = city3d.render_city(W, H, (0.0, 520.0, -500.0), (60.0, 120.0, 1400.0), 52, seed=3, haze_col=(0.03, 0.03, 0.045), haze_dist=3800.0, sky_rgb=sky)
    save_rgb(out(env, "ciudad.jpg"), tonemap(img, 1.0), 93)
    return {"capas": ["ciudad.jpg"]}


def env_skyline():
    """Ciudad vista desde una azotea (cámara baja) con una luz lejana en el horizonte."""
    import city3d

    env = "skyline"
    hzy = 0.5
    sky = vgrad(H, W, [(0, col("#020309")), (0.35, col("#060b17")), (0.47, col("#121626")), (0.5, col("#1c1a24")), (1.0, col("#0a0c12"))])
    lx, ly = W * 0.66, H * 0.488
    sky += glow(H, W, lx, ly, W * 0.012, 2.2)[..., None] * (C_WHITE * 0.8 + C_GOLD * 0.6) * 6.0
    sky += glow(H, W, lx, ly, W * 0.08, 1.6)[..., None] * C_GOLD * 0.9
    sky += glow(H, W, lx, ly, W * 0.4, 2.0)[..., None] * col("#6a5a50") * 0.12
    img, z = city3d.render_city(W, H, (0.0, 70.0, -200.0), (0.0, 52.0, 2000.0), 46, seed=7, haze_col=(0.035, 0.035, 0.05), haze_dist=2600.0, sky_rgb=sky, downtown=(300.0, 1500.0))
    save_rgb(out(env, "skyline.jpg"), tonemap(img, 1.05), 93)
    # azotea en primer plano
    a = np.zeros((H, W), np.float32)
    ledge = H * 0.82
    a[int(ledge):, :] = 1
    for bx, bw, bh in ((0.05, 0.08, 0.14), (0.9, 0.06, 0.11)):
        a[int(ledge - H * bh) : int(ledge), int(W * bx) : int(W * (bx + bw))] = 1
    rgb = np.ones((H, W, 3), np.float32) * col("#04060a") * (0.7 + 0.6 * fbm(W, H, 40, 5, seed=95)[..., None])
    from plates_lib import rim_light
    r = rim_light(blur(a, 1.0), (0.3, -1.0), width=4, sigma=1.0)
    rgb += r[..., None] * col("#a08a70") * 0.5
    save_rgba(out(env, "azotea.webp"), tonemap(rgb), blur(a, 0.8), 92)
    return {"capas": ["azotea.webp", "skyline.jpg"], "luz": [round(lx / W, 4), round(ly / H, 4)], "azotea_y": round(ledge / H, 4)}


def env_puerta():
    """Salón de piedra monumental con una gran puerta en arco; la luz espera detrás."""
    env = "puerta"
    rng = np.random.default_rng(21)
    cx = W * 0.5
    door_w, door_h = W * 0.15, H * 0.5
    door_top = H * 0.2
    door_bot = door_top + door_h
    ys = np.arange(H, dtype=np.float32)[:, None]
    xs = np.arange(W, dtype=np.float32)[None, :]
    # muro del fondo con sillares
    wall = np.ones((H, W, 3), np.float32) * col("#0a0c12")
    blocks_h = H * 0.055
    row = np.floor(ys / blocks_h)
    offs = (row % 2) * W * 0.04
    joint_y = (np.abs((ys % blocks_h)) < 2.0 * SCALE + 0.5)
    joint_x = (np.abs(((xs + offs) % (W * 0.08))) < 2.0 * SCALE + 0.5)
    tex = fbm(W, H, 60, 6, seed=22)
    wall = wall * (0.6 + 0.8 * tex[..., None])
    wall = np.where((joint_y | joint_x)[..., None], wall * 0.45, wall)
    # suelo de losas en perspectiva (horizonte a la altura de la base de la puerta)
    floor_y = door_bot
    fm = ys > floor_y
    zrow = np.where(fm, (H * 0.9) / np.maximum(ys - floor_y, 1.0), 1e6)
    X = (xs - cx) * zrow / (W * 0.9)
    tiles = ((np.floor(X / 1.4) + np.floor(zrow / 1.4)) % 2)[..., None]
    floor = col("#07080c") * (0.85 + 0.25 * tiles) * (0.7 + 0.6 * tex[..., None])
    gl = (np.abs((X % 1.4)) < 0.03) | (np.abs((zrow % 1.4)) < 0.03 * zrow / 6)
    floor = np.where(gl[..., None], floor * 0.5, floor)
    img = np.where(fm[..., None], floor, wall)
    # arco de la puerta (agujero) y marco
    r_arch = door_w / 2
    arch_cy = door_top + r_arch
    inside = ((np.abs(xs - cx) < door_w / 2) & (ys > arch_cy) & (ys < door_bot)) | (((xs - cx) ** 2 + (ys - arch_cy) ** 2) < r_arch**2)
    frame_m = ((np.abs(xs - cx) < door_w / 2 + W * 0.018) & (ys > arch_cy) & (ys < door_bot)) | (((xs - cx) ** 2 + (ys - arch_cy) ** 2) < (r_arch + W * 0.018) ** 2)
    img = np.where((frame_m & ~inside)[..., None], img * 1.6 + col("#141820") * 0.3, img)
    wall_a = (~inside).astype(np.float32)
    # columnas en primer plano
    cols_a = np.zeros((H, W), np.float32)
    for xc, wcol in ((0.1, 0.075), (0.9, 0.075), (0.27, 0.045), (0.73, 0.045)):
        x0, x1 = int(W * (xc - wcol / 2)), int(W * (xc + wcol / 2))
        cols_a[:, x0:x1] = 1.0
    col_rgb = np.ones((H, W, 3), np.float32) * col("#05060a") * (0.6 + 0.8 * fbm(W, H, 30, 5, seed=23)[..., None])
    shade = np.clip(np.abs(xs - cx) / (W * 0.5), 0, 1)
    col_rgb *= (1.4 - shade[..., None] * 0.6)
    save_rgba(out(env, "muro.webp"), tonemap(img), wall_a, 92)
    save_rgba(out(env, "columnas.webp"), tonemap(col_rgb), blur(cols_a, 1.0), 92)
    # luz detrás de la puerta
    light = np.ones((H, W, 3), np.float32) * (C_WHITE * 1.4 + C_GOLD * 0.8)
    lg = glow(H, W, cx, door_top + door_h * 0.55, W * 0.08, 1.4)
    light = light * (0.7 + 0.8 * lg[..., None])
    save_rgb(out(env, "luz.jpg"), tonemap(light, 1.2), 92)
    # hojas de la puerta (madera con paneles y clavos)
    leaf_w, leaf_h = int(door_w / 2), int(door_h)
    wood = np.ones((leaf_h, leaf_w, 3), np.float32) * col("#120c08")
    grain = cv2.resize(fbm(max(8, leaf_w // 6), leaf_h, 20, 5, seed=24), (leaf_w, leaf_h))
    wood *= (0.6 + 0.8 * grain[..., None])
    for py in np.linspace(0.12, 0.88, 4):
        for px_ in (0.25, 0.72):
            yy, xx = int(py * leaf_h), int(px_ * leaf_w)
            cv2.rectangle(wood, (xx - int(leaf_w * 0.18), yy - int(leaf_h * 0.08)), (xx + int(leaf_w * 0.18), yy + int(leaf_h * 0.08)), (col("#0a0705") * 0.8).tolist(), max(1, int(3 * SCALE)))
    for py in np.linspace(0.05, 0.95, 14):
        for px_ in (0.08, 0.92):
            cv2.circle(wood, (int(px_ * leaf_w), int(py * leaf_h)), max(1, int(3 * SCALE)), (col("#2a2420")).tolist(), -1)
    la = np.ones((leaf_h, leaf_w), np.float32)
    # recorte superior en arco
    yy, xx = np.mgrid[0:leaf_h, 0:leaf_w].astype(np.float32)
    left = ((xx - leaf_w) ** 2 + (yy - r_arch) ** 2 > r_arch**2) & (yy < r_arch)
    right = ((xx) ** 2 + (yy - r_arch) ** 2 > r_arch**2) & (yy < r_arch)
    la_l = la.copy()
    la_l[left] = 0
    la_r = la.copy()
    la_r[right] = 0
    save_rgba(out(env, "hoja_izq.webp"), tonemap(wood), blur(la_l, 0.8), 92)
    save_rgba(out(env, "hoja_der.webp"), tonemap(wood[:, ::-1]), blur(la_r, 0.8), 92)
    # derrame de luz en el suelo (trapecio que se abre hacia la cámara)
    spill = np.zeros((H, W), np.float32)
    pts = np.array([[cx - door_w * 0.5, door_bot], [cx + door_w * 0.5, door_bot], [cx + W * 0.42, H * 1.05], [cx - W * 0.42, H * 1.05]])
    cv2.fillPoly(spill, [np.round(pts * 4).astype(np.int32)], 1.0, lineType=cv2.LINE_AA, shift=2)
    fade_s = np.clip(1 - (ys - door_bot) / (H - door_bot), 0, 1) ** 1.5
    spill = blur(spill * fade_s, 12 * SCALE + 2)
    save_rgba(out(env, "derrame.webp"), np.ones((H, W, 3), np.float32) * (C_GOLD * 0.9 + C_WHITE * 0.4), np.clip(spill, 0, 1) * 0.85, 88)
    # rayos desde la puerta
    m = inside.astype(np.float32)
    rays = god_rays(cv2.resize(m, (W // 2, H // 2)), cx / 2, (door_top + door_h * 0.5) / 2, samples=90, decay=0.985, density=1.25)
    rays = cv2.resize(rays, (W, H), interpolation=cv2.INTER_CUBIC)
    save_rgba(out(env, "rayos.webp"), np.ones((H, W, 3), np.float32) * (C_GOLD * 0.8 + C_WHITE * 0.5), np.clip(rays * 1.4, 0, 1) ** 1.3 * 0.75, 88)
    return {
        "capas": ["columnas.webp", "muro.webp", "luz.jpg"],
        "puerta": [round((cx - door_w / 2) / W, 4), round(door_top / H, 4), round(door_w / W, 4), round((door_h + 0) / H, 4)],
        "suelo": round(float(door_bot) / H, 4),
    }


ENVS_2D.update({"calle": env_calle, "ciudad_aerea": env_ciudad_aerea, "skyline": env_skyline, "puerta": env_puerta})


if __name__ == "__main__":
    main()
