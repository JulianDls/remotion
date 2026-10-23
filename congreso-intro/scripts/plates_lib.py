"""Biblioteca de generación procedural de fondos ("matte paintings") por capas.

Todo se genera con ruido fractal, gradientes y simulación sencilla de luz; no se usan imágenes externas.
Las imágenes se guardan en float32 lineal [0,1] y se convierten a sRGB 8-bit al exportar.
"""

import os

import cv2
import numpy as np

RNG = np.random.default_rng


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def col(h):
    """Color hex -> lineal."""
    return srgb_to_lin(hex2rgb(h))


# ------------------------------------------------------------------ ruido
def value_noise(w, h, cells_x, seed, tile=False):
    """Ruido de valor suave: rejilla aleatoria re-escalada con interpolación cúbica."""
    rng = RNG(seed)
    cells_y = max(2, int(round(cells_x * h / w)))
    cells_x = max(2, int(cells_x))
    if tile:
        g = rng.random((cells_y, cells_x)).astype(np.float32)
        pad = 3
        g = np.pad(g, pad, mode="wrap")
        big = cv2.resize(g, (w * (cells_x + 2 * pad) // cells_x, h * (cells_y + 2 * pad) // cells_y), interpolation=cv2.INTER_CUBIC)
        ox, oy = w * pad // cells_x, h * pad // cells_y
        return big[oy : oy + h, ox : ox + w]
    g = rng.random((cells_y + 3, cells_x + 3)).astype(np.float32)
    big = cv2.resize(g, (w * (cells_x + 3) // cells_x, h * (cells_y + 3) // cells_y), interpolation=cv2.INTER_CUBIC)
    ox, oy = w // cells_x, h // cells_y
    return big[oy : oy + h, ox : ox + w]


def fbm(w, h, base_cells=4, octaves=7, persistence=0.5, lacunarity=2.0, seed=0, tile=False):
    total = np.zeros((h, w), np.float32)
    amp, norm, cells = 1.0, 0.0, base_cells
    for o in range(octaves):
        if cells > min(w, h) / 2:
            break
        total += amp * value_noise(w, h, cells, seed * 101 + o * 7, tile)
        norm += amp
        amp *= persistence
        cells *= lacunarity
    return total / norm


def ridged(w, h, base_cells=4, octaves=7, seed=0):
    total = np.zeros((h, w), np.float32)
    amp, norm, cells = 1.0, 0.0, base_cells
    for o in range(octaves):
        n = value_noise(w, h, cells, seed * 131 + o * 11)
        r = 1 - np.abs(n * 2 - 1)
        total += amp * r**2
        norm += amp
        amp *= 0.5
        cells *= 2
    return total / norm


def warp(field, strength, seed, cells=3):
    """Deformación de dominio: desplaza el campo con dos ruidos de baja frecuencia."""
    h, w = field.shape
    dx = (fbm(w, h, cells, 4, seed=seed + 1) - 0.5) * strength
    dy = (fbm(w, h, cells, 4, seed=seed + 2) - 0.5) * strength
    mx, my = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(field, mx + dx, my + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def noise1d(n, base_cells, octaves, seed, persistence=0.5, ridge=False):
    rng = RNG(seed)
    out = np.zeros(n, np.float32)
    amp, norm, cells = 1.0, 0.0, base_cells
    xs = np.arange(n, dtype=np.float32)
    for o in range(octaves):
        pts = rng.random(int(cells) + 4).astype(np.float32)
        gx = np.linspace(0, n, int(cells) + 4)
        # interpolación cúbica tipo Catmull-Rom mediante np.interp sobre puntos suavizados
        v = np.interp(xs, gx, pts)
        k = max(1, int(n / cells / 2))
        v = cv2.GaussianBlur(v.reshape(1, -1), (0, 0), sigmaX=k / 2).ravel()
        if ridge:
            v = 1 - np.abs(v * 2 - 1)
        out += amp * v
        norm += amp
        amp *= persistence
        cells *= 2
    return out / norm


# ------------------------------------------------------------------ utilidades de imagen
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def vgrad(h, w, stops):
    """Gradiente vertical. stops: lista de (pos 0..1, color lineal)."""
    ys = np.linspace(0, 1, h, dtype=np.float32)
    out = np.zeros((h, 3), np.float32)
    pos = np.array([s[0] for s in stops], np.float32)
    for c in range(3):
        out[:, c] = np.interp(ys, pos, np.array([s[1][c] for s in stops], np.float32))
    return np.repeat(out[:, None, :], w, axis=1)


def radial(h, w, cx, cy, radius, power=2.0, aspect=1.0):
    mx, my = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    d = np.sqrt(((mx - cx) / aspect) ** 2 + (my - cy) ** 2) / radius
    return np.clip(1 - d, 0, 1) ** power


def glow(h, w, cx, cy, radius, falloff=2.0, aspect=1.0):
    """Halo suave tipo 1/(1+d^2)."""
    mx, my = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    d = np.sqrt(((mx - cx) / aspect) ** 2 + (my - cy) ** 2) / radius
    return 1 / (1 + d**falloff)


def blur(img, sigma):
    if sigma <= 0:
        return img
    return cv2.GaussianBlur(img, (0, 0), sigmaX=sigma, sigmaY=sigma)


def god_rays(mask, cx, cy, samples=72, decay=0.975, density=0.9, weight=1.0):
    """Dispersión volumétrica (post-proceso radial): mask = intensidad de luz visible (0..1)."""
    h, w = mask.shape[:2]
    mx, my = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    dx = (mx - cx) * density / samples
    dy = (my - cy) * density / samples
    acc = np.zeros_like(mask, dtype=np.float32)
    illum = 1.0
    sx, sy = mx.copy(), my.copy()
    small = mask.astype(np.float32)
    for _ in range(samples):
        sx -= dx
        sy -= dy
        s = cv2.remap(small, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        acc += s * illum * weight
        illum *= decay
    return acc / samples


def stars(h, w, count, seed, max_size=2.2, horizon=1.0):
    rng = RNG(seed)
    img = np.zeros((h, w), np.float32)
    xs = rng.integers(0, w, count)
    ys = (rng.random(count) ** 1.3 * h * horizon).astype(int)
    br = rng.random(count) ** 3
    for x, y, b in zip(xs, ys, br):
        img[min(y, h - 1), x] += 0.4 + 2.5 * b
    core = blur(img, 0.6)
    halo = blur(img, max_size * 1.6) * 0.5
    return core + halo


def ridge_profile(n, base_y, amp, cells, seed, octaves=8, ridge=True, persistence=0.52):
    p = noise1d(n, cells, octaves, seed, persistence=persistence, ridge=ridge)
    p = (p - p.min()) / (p.max() - p.min() + 1e-6)
    return base_y - p * amp


def fill_below(h, w, profile, soft=1.0):
    ys = np.arange(h, dtype=np.float32)[:, None]
    return np.clip((ys - profile[None, :]) / soft + 0.5, 0, 1)


def rim_light(alpha, light_dir=(0.0, -1.0), width=3.0, sigma=1.2):
    """Borde iluminado en la silueta (alpha) según dirección de la luz."""
    gx = cv2.Sobel(alpha, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(alpha, cv2.CV_32F, 0, 1, ksize=3)
    # normal hacia afuera = -gradiente
    nx, ny = -gx, -gy
    mag = np.sqrt(nx**2 + ny**2) + 1e-6
    facing = np.clip((nx * light_dir[0] + ny * light_dir[1]) / mag, 0, 1)
    edge = np.clip(mag / 4, 0, 1)
    rim = blur(edge * facing, sigma)
    # sólo dentro de la silueta
    inner = cv2.erode(alpha, np.ones((int(width), int(width)), np.uint8))
    return rim * np.clip(alpha - inner * 0.6, 0, 1)


def add_grain(img, amount, seed):
    rng = RNG(seed)
    n = rng.standard_normal(img.shape[:2]).astype(np.float32)
    n = blur(n, 0.7)
    return img + n[..., None] * amount


# ------------------------------------------------------------------ exportación
def save_rgb(path, lin_rgb, quality=92, dither=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s = lin_to_srgb(lin_rgb)
    if dither:
        s = s + (RNG(1).random(s.shape[:2], dtype=np.float32)[..., None] - 0.5) / 255
    out = np.clip(s * 255 + 0.5, 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
    if path.endswith(".jpg"):
        cv2.imwrite(path, bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    elif path.endswith(".webp"):
        cv2.imwrite(path, bgr, [cv2.IMWRITE_WEBP_QUALITY, quality])
    else:
        cv2.imwrite(path, bgr)


def save_rgba(path, lin_rgb, alpha, quality=92):
    """Guarda capa con alfa (color sin premultiplicar)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s = lin_to_srgb(lin_rgb)
    s = s + (RNG(2).random(s.shape[:2], dtype=np.float32)[..., None] - 0.5) / 255
    rgb8 = np.clip(s * 255 + 0.5, 0, 255).astype(np.uint8)
    a8 = np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)
    bgra = np.dstack([cv2.cvtColor(rgb8, cv2.COLOR_RGB2BGR), a8])
    if path.endswith(".webp"):
        cv2.imwrite(path, bgra, [cv2.IMWRITE_WEBP_QUALITY, quality])
    else:
        cv2.imwrite(path, bgra, [cv2.IMWRITE_PNG_COMPRESSION, 6])


def tonemap(x, exposure=1.0):
    """Curva fílmica suave (ACES aproximado) para comprimir altas luces."""
    x = x * exposure
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
