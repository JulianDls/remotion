"""Render de paisajes 3D por raymarching de un campo de alturas (CPU, numba).

Produce color lineal HDR y profundidad. Permite renderizar por rangos de distancia para
obtener capas separadas (cerca / medio / lejos) y animarlas con parallax en Remotion.
"""

import math

import numpy as np
from numba import njit, prange


# ------------------------------------------------------------------ ruido con derivadas
@njit(cache=True, inline="always")
def _hash2(ix, iy, seed):
    n = np.uint64(ix * 374761393 + iy * 668265263 + seed * 2147483647) & np.uint64(0xFFFFFFFFFFFF)
    n = (n ^ (n >> np.uint64(13))) * np.uint64(1274126177)
    n = n ^ (n >> np.uint64(16))
    return float(n & np.uint64(0xFFFFFF)) / 16777216.0


@njit(cache=True, inline="always")
def noised(x, y, seed):
    ix = math.floor(x)
    iy = math.floor(y)
    fx = x - ix
    fy = y - iy
    ux = fx * fx * fx * (fx * (fx * 6.0 - 15.0) + 10.0)
    uy = fy * fy * fy * (fy * (fy * 6.0 - 15.0) + 10.0)
    dux = 30.0 * fx * fx * (fx * (fx - 2.0) + 1.0)
    duy = 30.0 * fy * fy * (fy * (fy - 2.0) + 1.0)
    a = _hash2(int(ix), int(iy), seed)
    b = _hash2(int(ix) + 1, int(iy), seed)
    c = _hash2(int(ix), int(iy) + 1, seed)
    d = _hash2(int(ix) + 1, int(iy) + 1, seed)
    k1 = b - a
    k2 = c - a
    k4 = a - b - c + d
    v = a + k1 * ux + k2 * uy + k4 * ux * uy
    return 2.0 * v - 1.0, 2.0 * dux * (k1 + k4 * uy), 2.0 * duy * (k2 + k4 * ux)


@njit(cache=True)
def terrain_h(x, z, octaves, seed, erosion, ridge):
    """fbm con atenuación por pendiente (aspecto erosionado) y mezcla de crestas."""
    a = 0.0
    b = 1.0
    dx = 0.0
    dz = 0.0
    px = x
    pz = z
    for i in range(octaves):
        n, nx, nz = noised(px, pz, seed + i * 17)
        if ridge > 0.0:
            r = 1.0 - abs(n)
            n = n * (1.0 - ridge) + (r * 2.0 - 1.0) * ridge
        dx += nx
        dz += nz
        a += b * n / (1.0 + erosion * (dx * dx + dz * dz))
        b *= 0.5
        qx = 0.8 * px - 0.6 * pz
        qz = 0.6 * px + 0.8 * pz
        px = qx * 2.0
        pz = qz * 2.0
    return a


@njit(cache=True)
def height(x, z, P):
    # P: [scale_xz, scale_y, octaves, seed, erosion, ridge, base, valley_x, valley_w, valley_d,
    #     cliff_x, cliff_z, cliff_r, cliff_h, flat_r0, flat_r1, flat_amt, flat_cx, flat_cz, rise_per_unit]
    s = P[0]
    h = P[1] * terrain_h(x / s, z / s, int(P[2]), int(P[3]), P[4], P[5]) + P[6]
    # aplanado alrededor de un punto (llanura cercana) y subida progresiva con la distancia
    if P[16] > 0.0:
        ddx = x - P[17]
        ddz = z - P[18]
        r = math.sqrt(ddx * ddx + ddz * ddz)
        k = min(1.0, max(0.0, (r - P[14]) / max(1e-6, P[15] - P[14])))
        k = k * k * (3.0 - 2.0 * k)
        h = h * (1.0 - P[16] * (1.0 - k)) + P[19] * max(0.0, r - P[14])
    # valle opcional (canal a lo largo de z)
    if P[8] > 0.0:
        t = (x - P[7]) / P[8]
        h -= P[9] * math.exp(-t * t)
    # meseta/acantilado opcional cerca de la cámara
    if P[12] > 0.0:
        ddx = x - P[10]
        ddz = z - P[11]
        dist = math.sqrt(ddx * ddx + ddz * ddz) / P[12]
        dist *= 1.0 + 0.22 * terrain_h(x * 2.5, z * 2.5, 4, int(P[3]) + 55, 0.0, 0.0)
        if dist < 1.6:
            k = 1.0 / (1.0 + math.exp((dist - 1.0) * 14.0))
            h = h * (1.0 - k) + P[13] * k + 0.02 * terrain_h(x * 9.0, z * 9.0, 4, int(P[3]) + 99, 0.0, 0.0) * k
    # montaña principal opcional (pico gaussiano con detalle)
    if P[22] > 0.0:
        ddx = (x - P[20]) / P[22]
        ddz = (z - P[21]) / P[22]
        g = math.exp(-(ddx * ddx + ddz * ddz))
        h += P[23] * g * (1.0 + 0.25 * terrain_h(x * 1.7, z * 1.7, 5, int(P[3]) + 7, 1.0, 0.6))
    return h


@njit(cache=True)
def normal_at(x, z, eps, P, Pn):
    hx1 = height(x + eps, z, Pn)
    hx0 = height(x - eps, z, Pn)
    hz1 = height(x, z + eps, Pn)
    hz0 = height(x, z - eps, Pn)
    nx = hx0 - hx1
    ny = 2.0 * eps
    nz = hz0 - hz1
    l = math.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / l, ny / l, nz / l


@njit(cache=True)
def soft_shadow(x, y, z, lx, ly, lz, P, tmax, k):
    res = 1.0
    t = 0.02
    for i in range(48):
        px = x + lx * t
        py = y + ly * t
        pz = z + lz * t
        h = py - height(px, pz, P)
        if h < 0.0:
            return 0.0
        res = min(res, k * h / t)
        t += max(0.02, h * 0.6)
        if t > tmax:
            break
    return max(0.0, min(1.0, res))


@njit(cache=True)
def cloud_density(x, z, seed, coverage, soft=0.32):
    a = 0.0
    b = 0.5
    px = x
    pz = z
    for i in range(6):
        n, _, _ = noised(px, pz, seed + 300 + i)
        a += b * n
        b *= 0.5
        qx = 0.8 * px - 0.6 * pz
        qz = 0.6 * px + 0.8 * pz
        px = qx * 2.03
        pz = qz * 2.03
    v = a * 0.5 + 0.5
    c0 = 1.0 - coverage
    t = (v - c0) / soft
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return t * t * (3.0 - 2.0 * t)


@njit(parallel=True, cache=True)
def render(W, H, cam, P, Pn, sun, sky, fog, cloud, t_range, out_col, out_t):
    """cam: [ox,oy,oz, fx,fy,fz, rx,ry,rz, ux,uy,uz, fov_tan]
    sun: [dx,dy,dz, r,g,b, intensity, disk_size, glow_power]
    sky: [zen_r,zen_g,zen_b, hor_r,hor_g,hor_b, ground_r, ground_g, ground_b]
    fog: [density, height_falloff, base_r,base_g,base_b, sun_r,sun_g,sun_b, mie_power, ambient]
    cloud: [plane_y, scale, coverage, seed, opacity, shadow_r, shadow_g, shadow_b, lit, sun_gap_rad, absorb, softness]
    t_range: [t_min, t_max, mat_r, mat_g, mat_b, snow_level, rim, direct_light, sun_core]
    """
    ox, oy, oz = cam[0], cam[1], cam[2]
    asp = W / H
    for j in prange(H):
        for i in range(W):
            u = (2.0 * (i + 0.5) / W - 1.0) * cam[12] * asp
            v = (1.0 - 2.0 * (j + 0.5) / H) * cam[12]
            dx = cam[3] + u * cam[6] + v * cam[9]
            dy = cam[4] + u * cam[7] + v * cam[10]
            dz = cam[5] + u * cam[8] + v * cam[11]
            l = math.sqrt(dx * dx + dy * dy + dz * dz)
            dx /= l
            dy /= l
            dz /= l
            # marcha
            t = t_range[0]
            hit = False
            tmax = t_range[1]
            lh = 0.0
            ly = 0.0
            for s in range(700):
                px = ox + dx * t
                py = oy + dy * t
                pz = oz + dz * t
                h = height(px, pz, P)
                d = py - h
                if d < 0.0012 * t:
                    hit = True
                    # refinamiento por bisección entre el paso anterior y el actual
                    if s > 0:
                        ta = t - lh
                        tb = t
                        for it in range(6):
                            tm = 0.5 * (ta + tb)
                            qx = ox + dx * tm
                            qy = oy + dy * tm
                            qz = oz + dz * tm
                            if qy - height(qx, qz, P) < 0.0012 * tm:
                                tb = tm
                            else:
                                ta = tm
                        t = tb
                    break
                step = max(0.003 * t, d * 0.35)
                lh = step
                ly = py
                t += step
                if t > tmax:
                    break
            sdx, sdy, sdz = sun[0], sun[1], sun[2]
            mu = dx * sdx + dy * sdy + dz * sdz
            if hit and t <= tmax:
                px = ox + dx * t
                py = oy + dy * t
                pz = oz + dz * t
                nx, ny, nz = normal_at(px, pz, 0.0015 * t + 0.001, P, Pn)
                dif = max(0.0, nx * sdx + ny * sdy + nz * sdz)
                sh = soft_shadow(px, py + 0.002, pz, sdx, sdy, sdz, P, 8.0, 10.0) if dif > 0.0 else 0.0
                amb = 0.5 + 0.5 * ny
                back = max(0.0, -(nx * sdx + nz * sdz)) * 0.0
                # material: roca con nieve opcional en pendientes suaves y altura
                mr, mg, mb = t_range[2], t_range[3], t_range[4]
                if t_range[5] > -50.0:
                    snow = max(0.0, min(1.0, (py - t_range[5]) * 6.0)) * max(0.0, min(1.0, (ny - 0.55) * 5.0))
                    mr = mr * (1 - snow) + 0.75 * snow
                    mg = mg * (1 - snow) + 0.78 * snow
                    mb = mb * (1 - snow) + 0.85 * snow
                # borde iluminado (luz rasante desde detrás)
                fres = (1.0 - max(0.0, -(nx * dx + ny * dy + nz * dz))) ** 8
                rim = t_range[6] * fres * max(0.0, mu) ** 6 * t_range[7]
                bounce = max(0.0, 1.0 - ny) * 0.5
                dl = t_range[7]
                cr = mr * (sun[3] * sun[6] * dif * sh * dl + (sky[0] * amb + sky[3] * bounce) * fog[9] + sky[6] * 0.05) + sun[3] * rim * sh
                cg = mg * (sun[4] * sun[6] * dif * sh * dl + (sky[1] * amb + sky[4] * bounce) * fog[9] + sky[7] * 0.05) + sun[4] * rim * sh
                cb = mb * (sun[5] * sun[6] * dif * sh * dl + (sky[2] * amb + sky[5] * bounce) * fog[9] + sky[8] * 0.05) + sun[5] * rim * sh
                out_t[j, i] = t
            else:
                # cielo: gradiente cenit-horizonte + halo solar en tres escalas
                yy = max(0.0, dy)
                k = math.exp(-yy * 3.2)
                cr = sky[0] * (1 - k) + sky[3] * k
                cg = sky[1] * (1 - k) + sky[4] * k
                cb = sky[2] * (1 - k) + sky[5] * k
                sd = max(0.0, mu)
                halo = sd ** 900.0 * 2.5 * t_range[8] + sd ** sun[8] * 0.35 + sd ** 4.0 * 0.03
                disk = 1.0 if mu > math.cos(sun[7]) else 0.0
                cr += sun[3] * sun[6] * halo + disk * sun[3] * 8.0
                cg += sun[4] * sun[6] * halo + disk * sun[4] * 8.0
                cb += sun[5] * sun[6] * halo + disk * sun[5] * 8.0
                # nubes en un plano, iluminadas marchando hacia el sol
                if cloud[4] > 0.0 and dy > 0.002:
                    tc = (cloud[0] - oy) / dy
                    cx = (ox + dx * tc) / cloud[1]
                    cz = (oz + dz * tc) / cloud[1]
                    den = cloud_density(cx, cz, int(cloud[3]), cloud[2], cloud[11])
                    # claro alrededor del sol (luz que rompe las nubes)
                    if cloud[9] > 0.0:
                        c_out = math.cos(cloud[9])
                        c_in = math.cos(cloud[9] * 0.35)
                        gg = max(0.0, min(1.0, (mu - c_out) / (c_in - c_out) + (den - 0.5) * 0.35))
                        den *= 1.0 - gg * gg * (3.0 - 2.0 * gg)
                    if den > 0.001:
                        hx = sdx
                        hz = sdz
                        hl = math.sqrt(hx * hx + hz * hz) + 1e-6
                        hx /= hl
                        hz /= hl
                        acc = 0.0
                        for st in range(5):
                            o = 0.025 * (st + 1)
                            acc += cloud_density(cx + hx * o, cz + hz * o, int(cloud[3]), cloud[2], cloud[11])
                        trans = math.exp(-acc * 0.9 * cloud[10])
                        g = 0.55
                        phase = (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * mu) ** 1.5) * 4.0
                        fade = min(1.0, max(0.0, (dy - 0.006) / 0.14))
                        fade = fade * fade * (3.0 - 2.0 * fade)
                        a = (1.0 - math.exp(-den * 3.2)) * cloud[4] * fade
                        amb = (1.0 - 0.55 * den)
                        litk = cloud[8] * trans * (0.18 + phase)
                        edge = den * (1.0 - den) * 4.0 * phase * 1.5 * cloud[8]
                        ccr = cloud[5] * amb + sky[3] * 0.25 * amb + sun[3] * (litk + edge) * sun[6] * 0.6
                        ccg = cloud[6] * amb + sky[4] * 0.25 * amb + sun[4] * (litk + edge) * sun[6] * 0.6
                        ccb = cloud[7] * amb + sky[5] * 0.25 * amb + sun[5] * (litk + edge) * sun[6] * 0.6
                        aer = (1.0 - fade) * 0.85
                        ccr = ccr * (1 - aer) + cr * aer
                        ccg = ccg * (1 - aer) + cg * aer
                        ccb = ccb * (1 - aer) + cb * aer
                        cr = cr * (1 - a) + ccr * a
                        cg = cg * (1 - a) + ccg * a
                        cb = cb * (1 - a) + ccb * a
                out_t[j, i] = 1e9
                t = tmax
            # niebla atmosférica (con dispersión hacia el sol)
            if hit and t <= tmax:
                fh = math.exp(-max(0.0, oy + dy * t * 0.5) * fog[1])
                ext = 1.0 - math.exp(-t * fog[0] * fh)
                sunamt = max(0.0, mu) ** fog[8]
                fr = fog[2] * (1 - sunamt) + fog[5] * sunamt
                fg = fog[3] * (1 - sunamt) + fog[6] * sunamt
                fb = fog[4] * (1 - sunamt) + fog[7] * sunamt
                cr = cr * (1 - ext) + fr * ext
                cg = cg * (1 - ext) + fg * ext
                cb = cb * (1 - ext) + fb * ext
            out_col[j, i, 0] = cr
            out_col[j, i, 1] = cg
            out_col[j, i, 2] = cb


def look_at(pos, target, fov_deg):
    pos = np.array(pos, np.float64)
    f = np.array(target, np.float64) - pos
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return np.concatenate([pos, f, r, u, [math.tan(math.radians(fov_deg) / 2)]]).astype(np.float64)


def sun_dir(azimuth_deg, elevation_deg):
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    return np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])


def render_layers(W, H, cam, P, sun, sky, fog, cloud, mat, splits, Pn=None):
    """Renderiza capas por rangos de distancia. splits: [d0, d1, ...] -> capas [0,d0], [d0,d1], ..., [dn, inf]."""
    Pn = P if Pn is None else Pn
    edges = [0.0] + list(splits) + [400.0]
    layers = []
    for k in range(len(edges) - 1):
        col = np.zeros((H, W, 3), np.float64)
        tt = np.zeros((H, W), np.float64)
        tr = np.array([edges[k], edges[k + 1]] + list(mat), np.float64)
        render(W, H, cam, P, Pn, sun, sky, fog, cloud, tr, col, tt)
        alpha = (tt < 1e8).astype(np.float64) if k < len(edges) - 2 else np.ones((H, W))
        layers.append((col.astype(np.float32), alpha.astype(np.float32), tt.astype(np.float32)))
    return layers
