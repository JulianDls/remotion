"""Render 3D de una ciudad nocturna (retícula de manzanas, edificios, farolas, autos y ventanas).

Rasterizado con OpenCV (algoritmo del pintor + búfer de profundidad aproximado para las luces).
"""
import math

import cv2
import numpy as np


def look(pos, target):
    pos = np.array(pos, np.float64)
    f = np.array(target, np.float64) - pos
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return pos, f, r, u


def render_city(W, H, cam_pos, cam_target, fov_deg, seed=1, extent=5200.0, downtown=(0.0, 1800.0), haze_col=(0.09, 0.08, 0.1), haze_dist=4200.0, sky_rgb=None):
    rng = np.random.default_rng(seed)
    pos, f, r, u = look(cam_pos, cam_target)
    tf = math.tan(math.radians(fov_deg) / 2)
    asp = W / H

    def proj(P):
        d = P - pos
        z = d @ f
        x = (d @ r) / np.maximum(z, 1e-3) / tf / asp
        y = (d @ u) / np.maximum(z, 1e-3) / tf
        return np.stack([(1 - x) / 2 * W, (1 - y) / 2 * H], axis=-1), z  # x invertida: r apunta a la izquierda

    img = np.zeros((H, W, 3), np.float32)
    if sky_rgb is not None:
        img[:] = sky_rgb
    zbuf = np.full((H, W), 1e9, np.float32)
    # ---- suelo
    ground_quad = np.array([[-extent, 0, 0.0], [extent, 0, 0.0], [extent, 0, extent * 1.6], [-extent, 0, extent * 1.6]])
    gq, gz = proj(ground_quad)
    # ---- manzanas
    boxes = []
    lights = []  # (x,y,z,r,g,b,intensity,size)
    block = 95.0
    road = 18.0
    avenue_every = 5
    zs = np.arange(60.0, extent * 1.5, block + road)
    xs = np.arange(-extent, extent, block + road)
    sodium = np.array([1.0, 0.62, 0.28])
    white = np.array([1.0, 0.95, 0.85])
    red = np.array([1.0, 0.15, 0.08])
    for iz, z0 in enumerate(zs):
        for ix, x0 in enumerate(xs):
            dx = (x0 + block / 2 - downtown[0])
            dz = (z0 + block / 2 - downtown[1])
            dd = math.sqrt(dx * dx + dz * dz)
            tall = math.exp(-(dd / 900.0) ** 2)
            if rng.random() < 0.06:
                continue  # parque / plaza
            nl = rng.integers(1, 4)
            cuts = np.sort(rng.uniform(0.2, 0.8, nl - 1)) if nl > 1 else np.array([])
            edges = np.concatenate([[0], cuts, [1]])
            for k in range(nl):
                a0 = x0 + edges[k] * block + 3
                a1 = x0 + edges[k + 1] * block - 3
                if a1 - a0 < 12:
                    continue
                d0 = z0 + rng.uniform(2, 12)
                d1 = z0 + block - rng.uniform(2, 12)
                h = rng.uniform(8, 30) + tall * rng.uniform(20, 220) * (1 if rng.random() < 0.7 else 0.4)
                boxes.append((a0, a1, d0, d1, h))
    # farolas a lo largo de las calles (bordes de cada vía)
    for iz, z0 in enumerate(zs):
        zr = z0 - road / 2
        wide = iz % avenue_every == 0
        for x in np.arange(-extent, extent, 28.0 if wide else 36.0):
            for side in (-1, 1):
                lights.append((x + rng.uniform(-2, 2), 7.0, zr + side * (road / 2 - 1.5), *sodium, 1.0 if wide else 0.75, 1.0))
        if wide:
            for x in np.arange(-extent, extent, 9.0):
                if rng.random() < 0.55:
                    c = white if rng.random() < 0.5 else red
                    lane = -3.5 if (c is white) else 3.5
                    lights.append((x + rng.uniform(-3, 3), 0.8, zr + lane + rng.uniform(-1, 1), *c, 0.9, 0.7))
    for ix, x0 in enumerate(xs):
        xr = x0 - road / 2
        wide = ix % avenue_every == 0
        for z in np.arange(60.0, extent * 1.5, 28.0 if wide else 36.0):
            for side in (-1, 1):
                lights.append((xr + side * (road / 2 - 1.5), 7.0, z + rng.uniform(-2, 2), *sodium, 1.0 if wide else 0.75, 1.0))
        if wide:
            for z in np.arange(60.0, extent * 1.5, 9.0):
                if rng.random() < 0.55:
                    c = white if rng.random() < 0.5 else red
                    lane = -3.5 if (c is white) else 3.5
                    lights.append((xr + lane, 0.8, z + rng.uniform(-3, 3), *c, 0.9, 0.7))
    # ---- suelo: asfalto con resplandor de farolas (se pinta luego como halo)
    poly = np.round(gq * 4).astype(np.int32)
    cv2.fillPoly(img, [poly], (0.004, 0.004, 0.006), shift=2)
    # ---- edificios (de lejos a cerca)
    B = np.array(boxes)
    centers = np.stack([(B[:, 0] + B[:, 1]) / 2, B[:, 4] / 2, (B[:, 2] + B[:, 3]) / 2], axis=1)
    dist = np.linalg.norm(centers - pos, axis=1)
    order = np.argsort(-dist)
    win_pts = []
    for bi in order:
        a0, a1, d0, d1, h = B[bi]
        if dist[bi] > extent * 1.7:
            continue
        corners = np.array([[a0, 0, d0], [a1, 0, d0], [a1, 0, d1], [a0, 0, d1], [a0, h, d0], [a1, h, d0], [a1, h, d1], [a0, h, d1]])
        pc, zc = proj(corners)
        if np.all(zc < 1):
            continue
        hz = 1 - math.exp(-dist[bi] / haze_dist)
        faces = []
        # caras visibles: techo si la cámara está por encima; laterales según posición
        if pos[1] > h:
            faces.append(([4, 5, 6, 7], 0.012))
        if pos[2] < d0:
            faces.append(([0, 1, 5, 4], 0.007))
        if pos[2] > d1:
            faces.append(([3, 2, 6, 7], 0.007))
        if pos[0] < a0:
            faces.append(([0, 3, 7, 4], 0.005))
        if pos[0] > a1:
            faces.append(([1, 2, 6, 5], 0.005))
        for idx, shade in faces:
            q = pc[idx]
            if np.any(zc[idx] < 1):
                continue
            c = np.array([shade, shade * 1.02, shade * 1.15]) * rng.uniform(0.75, 1.25)
            c = c * (1 - hz) + np.array(haze_col) * hz
            qp = np.round(q * 4).astype(np.int32)
            cv2.fillPoly(img, [qp], c.tolist(), lineType=cv2.LINE_AA, shift=2)
            cv2.fillPoly(zbuf, [qp], float(zc[idx].mean()), shift=2)
        # ventanas en caras laterales visibles
        for idx, shade in faces:
            if shade == 0.012:
                continue
            p0, p1, p2, p3 = corners[idx]
            wv = p1 - p0
            hv = p3 - p0
            wl = np.linalg.norm(wv)
            nh = int(h / 3.6)
            nw = int(wl / 3.2)
            if nh < 1 or nw < 1:
                continue
            m = rng.random((nh, nw)) < rng.uniform(0.06, 0.3)
            jj, ii = np.nonzero(m)
            if len(jj) == 0:
                continue
            P = p0[None, :] + wv[None, :] * ((ii + 0.5) / nw)[:, None] + hv[None, :] * ((jj + 0.5) / nh)[:, None]
            # desplazar ligeramente hacia la cámara para pasar la prueba de profundidad
            P = P + (pos - P) * 0.01
            for p in P:
                warm = rng.random() < 0.7
                cc = np.array([1.0, 0.72, 0.42]) if warm else np.array([0.75, 0.85, 1.0])
                win_pts.append((*p, *cc, rng.uniform(0.25, 0.8), 0.6))
    # ---- luces puntuales con prueba de profundidad
    L = np.array(lights + win_pts)
    pp, zz = proj(L[:, :3])
    ok = (zz > 5) & (pp[:, 0] >= 0) & (pp[:, 0] < W) & (pp[:, 1] >= 0) & (pp[:, 1] < H)
    pp, zz, L = pp[ok], zz[ok], L[ok]
    xi = pp[:, 0].astype(int)
    yi = pp[:, 1].astype(int)
    vis = zz <= zbuf[yi, xi] * 1.002 + 2.0
    xi, yi, zz, L = xi[vis], yi[vis], zz[vis], L[vis]
    acc = np.zeros((H, W, 3), np.float32)
    att = (1.0 / (1.0 + (zz / 900.0) ** 1.3))[:, None]
    hz = (1 - np.exp(-zz / haze_dist))[:, None]
    col_l = L[:, 3:6] * L[:, 6:7] * att * (1 - hz * 0.7)
    np.add.at(acc, (yi, xi), col_l * 2.2 * max(1.0, W / 1800.0))
    core = cv2.GaussianBlur(acc, (0, 0), 0.7 * max(1.0, W / 1800.0))
    halo = cv2.GaussianBlur(acc, (0, 0), 2.5) * 0.7 + cv2.GaussianBlur(acc, (0, 0), 10.0) * 0.55 + cv2.GaussianBlur(acc, (0, 0), 36.0) * 0.45
    img = img + core * 1.3 + halo
    # ---- bruma atmosférica por profundidad de píxel
    zfill = np.where(zbuf > 1e8, haze_dist * 2.5, zbuf)
    hzp = (1 - np.exp(-zfill / haze_dist))[..., None]
    img = img * (1 - hzp * 0.6) + np.array(haze_col, np.float32) * hzp * 0.6
    return img, zbuf
