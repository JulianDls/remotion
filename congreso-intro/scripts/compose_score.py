"""Compone la banda sonora original y el diseño sonoro, sincronizados con config/intro.config.json.

Salida (48 kHz, estéreo, float):
  .cache/stems/music.wav  - música (cuerdas, metales, coro, percusión, piano, sintetizadores)
  .cache/stems/sfx.wav    - diseño sonoro (impactos, whooshes, risers, viento, pasos, truenos, focos)
La mezcla final con la voz (y la compresión por sidechain) la hace scripts/mix_audio.py.

Tonalidad: Re menor -> Re mayor en la revelación. Tempo de referencia 120 BPM (compás = 2 s).
Instrumentos sampleados: VS Chamber Orchestra 2 Community Edition (CC0).
"""

import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import find_peaks

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp  # noqa: E402
import score_lib as L  # noqa: E402
from common import ROOT, SAMPLES, load_config  # noqa: E402

SR = dsp.SR
CFG = load_config()
SYNC = CFG["sincronia"]
DUR = CFG["video"]["duracionSegundos"]
N = int((DUR + 0.0) * SR)
OUT = os.path.join(ROOT, ".cache", "stems")

RX = r"_(?P<note>[A-G]#?)(?P<oct>-?\d)_v(?P<vel>\d)(?:_(?:rr|RR)(?P<rr>\d))?"

# ------------------------------------------------------------------ buses
BUS_NAMES = ["strings", "brass", "choir", "perc", "keys", "synth", "sfx"]
dry = {k: np.zeros((N + 8 * SR, 2)) for k in BUS_NAMES}
send_hall = np.zeros((N + 8 * SR, 2))  # reverb de sala para la música
send_big = np.zeros((N + 8 * SR, 2))  # reverb enorme para impactos / título
send_room = np.zeros((N + 8 * SR, 2))  # reverb corta (pasos, focos)


def place(bus, x, t, gain=1.0, pan=0.0, hall=0.0, big=0.0, room=0.0):
    if x.ndim == 1:
        x = dsp.pan(x, pan)
    dsp.add_at(dry[bus], x, t, gain=gain)
    if hall:
        dsp.add_at(send_hall, x, t, gain=gain * hall)
    if big:
        dsp.add_at(send_big, x, t, gain=gain * big)
    if room:
        dsp.add_at(send_room, x, t, gain=gain * room)


# ------------------------------------------------------------------ instrumentos
def S(folder, gain=1.0):
    return L.Sampler(folder, RX, gain=gain)


vln = S("Strings/Violin Section/susVib", 0.9)
vln_trem = S("Strings/Violin Section/Trem", 0.8)
vln_spic = S("Strings/Violin Section/Spic", 0.9)
vla = S("Strings/Viola Section/susvib", 0.9)
vla_spic = S("Strings/Viola Section/spic", 0.9)
vla_trem = S("Strings/Viola Section/trem", 0.8)
vc = S("Strings/Cello Section/susvib", 1.0)
vc_spic = S("Strings/Cello Section/spic", 1.0)
vc_trem = S("Strings/Cello Section/trem", 0.9)
cb = S("Strings/Solo Contrabass/SusNV", 1.2)
cb_spic = S("Strings/Solo Contrabass/Spic", 1.2)
hn = S("Brass/F Horn/sus", 0.9)
hn_stac = S("Brass/F Horn/stac", 0.9)
tbn = S("Brass/Tenor Trombone/sus", 0.9)
tbn_stac = S("Brass/Tenor Trombone/stac", 0.9)
tuba = S("Brass/Tuba/sus", 1.0)
tuba_stac = S("Brass/Tuba/stac", 1.0)

P = os.path.join(SAMPLES, "Percussion")


def ld(rel):
    return L.load_sample(os.path.join(P, rel))


def estimate_f0(x):
    seg = x[int(0.05 * SR) : int(0.6 * SR)]
    n = 1 << 18
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    f = np.fft.rfftfreq(n, 1 / SR)
    lo, hi = np.searchsorted(f, 40), np.searchsorted(f, 400)
    return f[lo + np.argmax(X[lo:hi])]


TIMP = {}
for drum in range(1, 6):
    x = ld(f"Timpani/Timpani{drum}_Hit_v3_rr1_Sum.wav")
    TIMP[drum] = estimate_f0(x)


def timp_hit(midi, vel=0.8, rr=1):
    target = L.mtof(midi)
    drum = min(TIMP, key=lambda d: abs(np.log2(TIMP[d] / target)))
    layer = 1 if vel < 0.45 else (3 if vel < 0.8 else 4)
    if drum == 1 and layer == 4:
        layer = 3
    path = f"Timpani/Timpani{drum}_Hit_v{layer}_rr{rr}_Sum.wav"
    if not os.path.exists(os.path.join(P, path)):
        path = f"Timpani/Timpani{drum}_Hit_v3_rr1_Sum.wav"
    x = ld(path)
    semis = 12 * np.log2(target / TIMP[drum])
    return dsp.pitch_shift_resample(x, semis) * (0.4 + 0.6 * vel)


def timp_roll(dur, vel=0.7, drum=2):
    v = 5 if vel > 0.6 else 3
    x = ld(f"Timpani/Rolls/Timpani{drum}_Roll_v{v}_rr1_Sum.wav")
    x = L.loop_extend(x, int(dur * SR) + SR, xfade=0.3, start=0.5)
    x = x[: int(dur * SR)]
    t = np.linspace(0, 1, len(x))
    return x * (0.15 + 0.85 * t**1.5) * vel


def bdrum(vel=0.8, rr=1):
    v = int(np.clip(round(vel * 7), 1, 7))
    return ld(f"BDrumNewhit_v{v}_rr{rr}_Sum.wav")


def crash(level="ff", rr=1):
    return ld(f"cymbal-crash1_{level}_rr{rr}.wav")


def gong(level="fff"):
    return ld(f"gongHit_{level}.wav")


def sus_cresc(kind="Long"):
    return ld(f"susCymb1-cresc-{kind}_v1.wav")


def snare_roll(dur, vel=0.7):
    v = 5 if vel > 0.6 else (3 if vel > 0.3 else 1)
    x = ld(f"Snare2-rollSN_v{v}_rr1_Sum.wav")
    x = L.loop_extend(x, int(dur * SR) + SR, xfade=0.25, start=0.4)[: int(dur * SR)]
    t = np.linspace(0, 1, len(x))
    return x * (0.05 + 0.95 * t**2.2) * vel


def snare_hit(vel=0.8, rr=1):
    v = [1, 3, 5, 7, 9][int(np.clip(vel * 5, 0, 4.99))]
    return ld(f"Snare2-HitSN_v{v}_rr{rr}_Sum.wav")


# Piano vertical (archivos cada 4 semitonos desde La0 = 21)
PIANO = os.path.join(SAMPLES, "Keys", "Upright Piano")


def piano(midi, vel=0.4, dur=4.0):
    idx = int(round((midi - 21) / 4))
    idx = int(np.clip(idx, 0, 22))
    key = 21 + idx * 4
    dyn = 1 if vel < 0.4 else (2 if vel < 0.75 else 3)
    x = L.load_sample(os.path.join(PIANO, f"Player_dyn{dyn}_rr1_{idx * 2:03d}.wav"))
    x = dsp.pitch_shift_resample(x, midi - key)
    x = x[: int((dur + 1.5) * SR)].copy()
    k = int(dur * SR)
    if len(x) > k:
        x[k:] *= np.cos(np.linspace(0, np.pi / 2, len(x) - k)) ** 2
    return x * (0.5 + 0.5 * vel)


GLOCK = {}
for f in os.listdir(os.path.join(P, "Glock")):
    x = L.load_sample(os.path.join(P, "Glock", f))
    GLOCK[f] = (x, estimate_f0(x[: int(0.5 * SR)]) if False else None)


def glock(midi, vel=0.4):
    # notas disponibles: G4 C5 G5 C6 G6 C7 (nomenclatura VSCO); elegir la más cercana y transponer
    names = {"glock_medium_G4.wav": 67 + 12, "glock_medium_C5.wav": 72 + 12, "glock_medium_G5.wav": 79 + 12,
             "glock_medium_C6.wav": 84 + 12, "glock_medium_G6.wav": 91 + 12, "glock_medium_C7.wav": 96 + 12}
    fname = min(names, key=lambda k: abs(names[k] - midi))
    x = GLOCK[fname][0]
    return dsp.pitch_shift_resample(x, midi - names[fname]) * vel


# ------------------------------------------------------------------ armonía
CH = {
    "Dm": {"root": 38, "low": [45, 50, 53], "mid": [57, 62, 65], "high": [69, 74, 77]},
    "Bb": {"root": 34, "low": [46, 50, 53], "mid": [58, 62, 65], "high": [70, 74, 77]},
    "F": {"root": 41, "low": [45, 48, 53], "mid": [57, 60, 65], "high": [69, 72, 77]},
    "F/A": {"root": 33, "low": [45, 48, 53], "mid": [57, 60, 65], "high": [69, 72, 77]},
    "C": {"root": 36, "low": [48, 52, 55], "mid": [60, 64, 67], "high": [72, 76, 79]},
    "Gm": {"root": 43, "low": [46, 50, 55], "mid": [58, 62, 67], "high": [70, 74, 79]},
    "A": {"root": 33, "low": [45, 49, 52], "mid": [57, 61, 64], "high": [69, 73, 76]},
    "Asus": {"root": 33, "low": [45, 50, 52], "mid": [57, 62, 64], "high": [69, 74, 76]},
    "D": {"root": 38, "low": [45, 50, 54], "mid": [57, 62, 66], "high": [69, 74, 78]},
    "G/D": {"root": 38, "low": [47, 50, 55], "mid": [59, 62, 67], "high": [71, 74, 79]},
}


def strings_chord(t, dur, ch, vel=0.5, attack=1.0, release=1.5, layers=("cb", "vc", "vla", "vln"), high=False, gain=1.0, hall=0.35):
    c = CH[ch]
    if "cb" in layers:
        place("strings", cb.note(c["root"] if c["root"] >= 28 else c["root"] + 12, dur, vel, attack, release), t, 0.9 * gain, -0.1, hall)
    if "vc" in layers:
        for m in c["low"][:2]:
            place("strings", vc.note(m, dur, vel, attack, release), t, 0.6 * gain, -0.35, hall)
    if "vla" in layers:
        for m in c["mid"][:2]:
            place("strings", vla.note(m, dur, vel, attack, release), t, 0.5 * gain, 0.3, hall)
    if "vln" in layers:
        notes = c["mid"][1:] + (c["high"][:2] if high else [])
        for i, m in enumerate(notes):
            place("strings", vln.note(m, dur, vel, attack, release), t, 0.42 * gain, -0.5 + 0.25 * i, hall)


def trem_chord(t, dur, ch, vel=0.5, attack=1.5, release=1.2, gain=1.0, high=True):
    c = CH[ch]
    for i, m in enumerate(c["mid"] + (c["high"][:2] if high else [])):
        inst = vln_trem if m >= 55 else vla_trem
        place("strings", inst.note(m, dur, vel, attack, release), t, 0.35 * gain, -0.6 + 0.3 * i, 0.45)


def brass_chord(t, dur, ch, vel=0.6, attack=0.6, release=1.2, gain=1.0, low=True):
    c = CH[ch]
    for i, m in enumerate(c["low"][:3]):
        place("brass", hn.note(m + 12 if m < 45 else m, dur, vel, attack, release), t, 0.45 * gain, -0.4 + 0.4 * i, 0.4)
    if low:
        place("brass", tbn.note(c["low"][0] - 12 if c["low"][0] - 12 >= 34 else c["low"][0], dur, vel, attack, release), t, 0.45 * gain, 0.25, 0.35)
        place("brass", tuba.note(c["root"] if c["root"] >= 34 else c["root"] + 12, dur, vel, attack, release), t, 0.55 * gain, 0.0, 0.3)


def brass_stab(t, ch, vel=0.95, gain=1.0):
    c = CH[ch]
    for i, m in enumerate(c["low"]):
        place("brass", hn_stac.note(m + 12 if m < 45 else m, None, vel), t, 0.55 * gain, -0.4 + 0.4 * i, 0.4, 0.15)
    place("brass", tbn_stac.note(c["low"][0], None, vel), t, 0.6 * gain, 0.2, 0.3, 0.1)
    place("brass", tuba_stac.note(c["root"] if c["root"] >= 34 else c["root"] + 12, None, vel), t, 0.7 * gain, 0, 0.3, 0.1)


def low_string_stab(t, ch, vel=0.95, gain=1.0):
    c = CH[ch]
    place("strings", cb_spic.note(c["root"] if c["root"] >= 28 else c["root"] + 12, None, vel), t, 0.9 * gain, 0, 0.3)
    place("strings", vc_spic.note(c["low"][0], None, vel), t, 0.7 * gain, -0.3, 0.3)
    place("strings", vc_spic.note(c["low"][0] - 12 if c["low"][0] - 12 >= 36 else c["low"][0], None, vel), t, 0.6 * gain, 0.3, 0.3)


def choir(t, dur, ch, vel=0.5, vowel="a", attack=1.5, release=2.5, high=False, gain=1.0, seed=0):
    c = CH[ch]
    notes = c["low"][1:] + c["mid"][:2] + (c["high"][:1] if high else [])
    x = L.choir_chord(notes, dur, vel, vowel, attack, release, seed=seed + int(t * 10))
    place("choir", x, t, gain, hall=0.8)


def ostinato(t0, t1, ch_seq, inst_low=vc_spic, inst_mid=vla_spic, vel=0.7, pattern=None, gain=1.0, eighth=0.25, accent=None, high_inst=None):
    """Ostinato de corcheas (120 BPM). ch_seq: lista de (t_inicio, acorde)."""
    pattern = pattern or [0, 0, 2, 0, 1, 0, 2, 1]
    accent = accent or [1.0, 0.55, 0.8, 0.55, 0.9, 0.55, 0.8, 0.65]
    t = t0
    k = 0
    rr = 1
    while t < t1 - 1e-6:
        ch = [c for (ts, c) in ch_seq if ts <= t + 1e-6][-1]
        tones = CH[ch]["low"]
        m = tones[pattern[k % len(pattern)]]
        v = vel * accent[k % len(accent)]
        place("strings", inst_low.note(m, None, v), t, 0.55 * gain, -0.3, 0.25)
        place("strings", inst_mid.note(m + 12, None, v * 0.9), t, 0.4 * gain, 0.3, 0.25)
        if high_inst is not None:
            place("strings", high_inst.note(m + 24, None, v * 0.85), t, 0.32 * gain, 0.1, 0.3)
        t += eighth
        k += 1
        rr = 3 - rr


def trailer_hit(t, vel=1.0, gong_level=None, crash_level="ff", boom_low=28, big=0.5, seed=0):
    place("sfx", L.boom(vel, 64, boom_low, 2.8, seed=seed), t, 0.7, big=big * 0.5)
    place("perc", bdrum(vel, 1), t, 1.0, hall=0.3, big=big * 0.5)
    place("perc", timp_hit(38, vel), t, 0.9, hall=0.35, big=big * 0.4)
    if crash_level:
        place("perc", crash(crash_level, 1), t, 0.45, 0.2, hall=0.3, big=big * 0.3)
    if gong_level:
        place("perc", gong(gong_level), t, 0.6, -0.1, hall=0.2, big=big * 0.5)


def whoosh_at(t_center, dur=0.9, vel=0.5, seed=0, direction=1, bright=1.0):
    x = L.whoosh(dur, vel, seed, direction, bright)
    place("sfx", x, t_center - dur * 0.62, 1.0, hall=0.0, big=0.25)


def reverse_crash_into(t_land, level="mf", length=2.5, gain=0.5):
    x = crash(level, 2)[: int(length * SR)]
    x = dsp.fade(x, 0.0, 0.05)[::-1]
    place("perc", x, t_land - len(x) / SR, gain, 0.0, hall=0.3)


def riser_into(t_land, dur=4.0, vel=0.6, seed=0, shepard=True):
    x = L.riser(dur, vel, seed, shepard=shepard)
    place("sfx", x, t_land - dur, 1.0, big=0.2)


# ================================================================== COMPOSICIÓN
def compose():
    t_title = SYNC["revelacionTitulo"]
    t_cut = SYNC["corteSilencio"]
    t_final = SYNC["impactoFinal"]

    # ---------------------------------------------------------- Escena 1: EL SILENCIO (0 - 10.5)
    place("sfx", L.wind(12.0, 0.35, seed=1, base=380, spread=260), 0.0, 0.5)
    x = L.sub_bass(26, 11.0, 0.35, attack=4.0, release=1.5)
    place("synth", x, 0.3, 0.6)
    # textura oscura: plato frotado con arco, una octava abajo
    bow = dsp.pitch_shift_resample(ld("susCymb1-bow-2.wav"), -12)
    place("perc", dsp.fade(bow, 1.5, 2.0), 0.6, 0.35, -0.3, hall=0.9)
    bow2 = dsp.pitch_shift_resample(ld("susCymb1-bow-3.wav"), -7)
    place("perc", dsp.fade(bow2, 2.0, 2.5), 5.2, 0.28, 0.35, hall=0.9)
    place("strings", cb.note(38, 9.0, 0.3, attack=3.5, release=2.0), 1.5, 0.55, 0.0, 0.5)
    place("strings", vc.note(50, 7.0, 0.25, attack=3.0, release=2.0), 3.5, 0.35, -0.3, 0.6)
    place("strings", vln_trem.note(74, 5.5, 0.2, attack=3.0, release=1.5), 4.8, 0.13, 0.5, 0.9)
    place("strings", vln_trem.note(69, 5.5, 0.2, attack=3.0, release=1.5), 5.0, 0.12, -0.5, 0.9)
    # motivo de piano (muy suave, lejano)
    for tt, m, v in [(0.9, 74, 0.25), (1.55, 69, 0.22), (3.75, 65, 0.24), (4.35, 64, 0.2), (9.55, 62, 0.28)]:
        place("keys", dsp.lp(piano(m, v, 3.5), 5000), tt, 0.5, 0.1, hall=1.0)
    # brillos de partículas
    rng = np.random.default_rng(3)
    for tt in np.sort(rng.uniform(1.0, 10.0, 7)):
        place("keys", glock(int(rng.choice([86, 89, 93, 98])), 0.06), float(tt), 0.5, rng.uniform(-0.8, 0.8), hall=1.0)
    # el horizonte aparece (5.0): soplo de aire
    whoosh_at(5.6, 2.2, 0.18, seed=5, bright=0.6)
    reverse_crash_into(10.5, "pp", 2.0, 0.3)

    # ---------------------------------------------------------- Escena 2: LA BÚSQUEDA (10.5 - 25)
    place("sfx", L.boom(0.45, 50, 30, 1.8, click=0.2, seed=2), 10.5, 0.7, big=0.3)
    place("perc", timp_hit(38, 0.35), 10.5, 0.7, hall=0.4)
    t = SYNC["inicioPulso"]
    k = 0
    while t < 21.0 - 1e-6:
        v = 0.5 if k % 2 == 0 else 0.32
        place("synth", L.heartbeat(v), t, 0.95)
        if k % 2 == 0:
            place("perc", timp_hit(38 if (k // 2) % 2 == 0 else 33, 0.35, rr=1 + k % 2), t, 0.7, hall=0.35)
        t += 1.0
        k += 1
    strings_chord(11.0, 4.2, "Dm", 0.3, attack=2.0, release=1.5, layers=("cb", "vc"), gain=0.9)
    strings_chord(15.0, 4.2, "Bb", 0.32, attack=1.5, release=1.5, layers=("cb", "vc", "vla"), gain=0.9)
    strings_chord(19.0, 2.2, "Gm", 0.35, attack=1.0, release=1.0, layers=("cb", "vc", "vla"), gain=0.9)
    place("synth", L.sub_bass(38, 4.0, 0.3, attack=1.0), 11.0, 0.5)
    place("synth", L.sub_bass(34, 4.0, 0.3, attack=0.5), 15.0, 0.5)
    place("synth", L.sub_bass(31, 2.0, 0.3, attack=0.5), 19.0, 0.5)
    # arpa: arpegio de búsqueda, delicado, por encima de la voz
    harp_rx = r"_(?P<note>[A-G]#?)(?P<oct>\d)_(?:mf|f|mp)"
    harp = L.Sampler("Strings/Harp", harp_rx, gain=0.6)
    arp = [(15.0, 74), (15.5, 77), (16.0, 81), (16.5, 77), (17.0, 74), (17.5, 77), (18.0, 82), (18.5, 77),
           (19.0, 79), (19.5, 82), (20.0, 86), (20.5, 82)]
    for tt, m in arp:
        place("keys", harp.note(m, None, 0.35), tt, 0.32, 0.4, hall=0.8)
    # pasos del joven que camina (2B): sincronizados con el ciclo de marcha (periodo 1.1 s, 2 pasos)
    for i, tt in enumerate(np.arange(13.75, 18.5, 0.55)):
        place("sfx", L.footstep(0.45, seed=i, wet=0.7), float(tt), 0.55, room=0.6)
    # tensión hacia "Pero hay una voz…"
    trem_chord(18.5, 2.6, "Gm", 0.3, attack=2.2, release=0.4, gain=0.8, high=False)
    sc = sus_cresc("Median")
    place("perc", sc, SYNC["elevacionVoz"] - len(sc) / SR + 0.05, 0.35, 0.0, hall=0.4)
    whoosh_at(18.5, 0.8, 0.2, seed=8)
    # ELEVACIÓN (21.0)
    t = SYNC["elevacionVoz"]
    place("sfx", L.boom(0.5, 55, 30, 2.2, click=0.2, seed=3), t, 0.6, big=0.5)
    place("perc", timp_roll(2.0, 0.5, drum=2), t, 0.35, hall=0.4)
    strings_chord(t, 2.2, "F/A", 0.5, attack=0.5, release=1.0, high=True)
    strings_chord(t + 2.0, 2.4, "C", 0.55, attack=0.4, release=1.5, high=True)
    choir(t, 2.2, "F/A", 0.35, attack=1.0, release=1.2, seed=1)
    choir(t + 2.0, 2.6, "C", 0.4, attack=0.6, release=1.6, seed=2)
    place("brass", hn.note(60, 3.6, 0.4, attack=1.2, release=1.2), t + 0.4, 0.4, 0.3, 0.5)
    place("synth", L.sub_bass(33, 2.0, 0.35), t, 0.55)
    place("synth", L.sub_bass(36, 2.2, 0.35), t + 2.0, 0.55)
    reverse_crash_into(25.0, "mf", 2.2, 0.45)
    riser_into(25.0, 2.5, 0.25, seed=4, shepard=False)

    # ---------------------------------------------------------- Escena 3: EL LLAMADO (25 - 43)
    seq3 = [(25.0, "Dm"), (29.0, "Bb"), (33.0, "F"), (37.0, "C"), (41.0, "A")]
    trailer_hit(25.0, 0.7, crash_level="mf", big=0.4, seed=10)
    place("sfx", L.thunder(4.5, 0.55, seed=1), 25.3, 0.8, big=0.4)
    place("sfx", L.thunder(3.5, 0.4, seed=2), 27.6, 0.6, big=0.4)
    ostinato(25.0, 41.0, seq3, vel=0.55, gain=0.85)
    ostinato(33.0, 41.0, seq3, inst_low=vc_spic, inst_mid=vln_spic, vel=0.5, gain=0.5, pattern=[2, 1, 0, 1, 2, 1, 0, 2])
    for ts, ch in seq3[:-1]:
        place("strings", cb.note(CH[ch]["root"] if CH[ch]["root"] >= 28 else CH[ch]["root"] + 12, 4.0, 0.45, 0.1, 0.6), ts, 0.8, 0, 0.3)
        place("synth", L.sub_bass(CH[ch]["root"] - 12 if CH[ch]["root"] - 12 >= 24 else CH[ch]["root"], 4.0, 0.35), ts, 0.5)
    strings_chord(29.0, 4.0, "Bb", 0.4, attack=1.2, release=0.6, layers=("vla", "vln"), gain=0.8)
    strings_chord(33.0, 4.0, "F", 0.5, attack=0.8, release=0.6, layers=("vla", "vln"), high=True, gain=0.85)
    strings_chord(37.0, 4.0, "C", 0.6, attack=0.5, release=0.6, layers=("vla", "vln"), high=True, gain=0.9)
    choir(33.0, 4.0, "F", 0.35, vowel="o", attack=1.2, release=0.8, seed=3)
    choir(37.0, 4.0, "C", 0.45, vowel="a", attack=0.8, release=0.8, seed=4)
    brass_chord(37.0, 4.0, "C", 0.45, attack=1.0, release=0.8, gain=0.8)
    # percusión progresiva
    for bar in range(8):  # 25..41
        b0 = 25.0 + bar * 2
        place("perc", bdrum(0.55 + 0.04 * bar, 1 + bar % 2), b0, 0.75, hall=0.25)
        place("perc", timp_hit(CH[[c for (ts, c) in seq3 if ts <= b0][-1]]["root"] if bar < 4 else 38, 0.45 + 0.05 * bar), b0, 0.5, hall=0.35)
        if bar >= 2:
            place("perc", bdrum(0.45, 2), b0 + 0.75, 0.55, hall=0.25)
        if bar >= 4:
            place("perc", snare_hit(0.5 + 0.05 * (bar - 4), 1), b0 + 1.0, 0.35, 0.1, hall=0.4)
            place("sfx", L.taiko(0.6, 74, seed=bar), b0 + 1.5, 0.55, big=0.1)
        if bar >= 6:
            for q in (0.25, 0.5, 1.25, 1.75):
                place("sfx", L.taiko(0.45, 92, 0.4, seed=bar * 10 + int(q * 4)), b0 + q, 0.35, big=0.05)
    # cortes rápidos 37-41
    for i, tt in enumerate([29.0, 31.0, 33.0, 35.0]):
        whoosh_at(tt, 0.7, 0.22, seed=20 + i, direction=1 if i % 2 else -1)
    for i, tt in enumerate([37.0, 38.0, 39.0, 40.0]):
        whoosh_at(tt, 0.55, 0.32, seed=30 + i, direction=1 if i % 2 else -1, bright=1.2)
    # transición 41-43: dominante, redoble, riser
    strings_chord(41.0, 2.0, "Asus", 0.6, attack=0.2, release=0.2, layers=("vc", "vla"), gain=0.8)
    trem_chord(41.0, 2.0, "A", 0.55, attack=1.6, release=0.1, gain=0.8)
    place("perc", snare_roll(2.0, 0.6), 41.0, 0.45, hall=0.3)
    place("perc", timp_roll(2.0, 0.75, drum=3), 41.0, 0.55, hall=0.3)
    riser_into(43.0, 4.0, 0.5, seed=6)
    reverse_crash_into(43.0, "ff", 2.5, 0.5)

    # ---------------------------------------------------------- Escena 4: LA PALABRA Y LA PROMESA (43 - 57)
    t4 = SYNC["transicionPalabra"]
    trailer_hit(t4, 0.95, gong_level="f", crash_level="ff", big=0.7, seed=11)
    seq4 = [(43.0, "Bb", 4.0), (47.0, "F/A", 4.0), (51.0, "Gm", 2.0), (53.0, "Bb", 2.0), (55.0, "C", 2.0)]
    for ts, ch, d in seq4:
        under_vo = ts >= 51.0
        strings_chord(ts, d, ch, 0.55 if not under_vo else 0.4, attack=0.6, release=1.2, high=not under_vo, gain=0.95)
        choir(ts, d, ch, 0.5 if not under_vo else 0.32, vowel="a" if not under_vo else "o", attack=0.9, release=1.6, high=not under_vo, seed=int(ts))
        place("synth", L.sub_bass(CH[ch]["root"] - 12 if CH[ch]["root"] - 12 >= 24 else CH[ch]["root"], d, 0.35), ts, 0.5)
    brass_chord(43.0, 4.0, "Bb", 0.55, attack=0.8, release=1.0)
    brass_chord(47.0, 4.0, "F/A", 0.55, attack=0.6, release=1.2)
    # melodía noble (trompas + violines a la octava) mientras el versículo está en pantalla
    mel = [(43.4, 65, 1.6), (45.0, 70, 1.0), (46.0, 72, 1.0), (47.0, 74, 2.0), (49.0, 72, 1.0), (50.0, 69, 1.2)]
    for tt, m, d in mel:
        place("brass", hn.note(m - 12, d, 0.6, attack=0.25, release=0.8), tt, 0.55, -0.15, 0.5)
        place("strings", vln.note(m, d, 0.55, attack=0.2, release=0.8), tt, 0.4, 0.2, 0.5)
    place("perc", timp_roll(3.5, 0.5, drum=2), 43.5, 0.3, hall=0.4)
    place("perc", timp_hit(41, 0.6), 47.0, 0.6, hall=0.4)
    place("perc", sus_cresc("Long"), 47.0 - len(sus_cresc("Long")) / SR + 0.1, 0.25, hall=0.5)
    # la puerta se abre (50.6)
    place("sfx", L.stone_rumble(3.2, 0.55, seed=2), 50.6, 0.7, big=0.35)
    whoosh_at(51.4, 1.6, 0.3, seed=40, bright=0.7)
    place("perc", timp_hit(43, 0.4), 51.0, 0.5, hall=0.4)
    place("perc", bdrum(0.4, 1), 53.0, 0.5, hall=0.4)
    place("perc", timp_roll(2.0, 0.55, drum=3), 55.0, 0.45, hall=0.3)
    place("perc", snare_roll(1.9, 0.55), 55.1, 0.4, hall=0.3)
    reverse_crash_into(57.0, "ff", 2.0, 0.5)
    riser_into(57.0, 2.0, 0.35, seed=7, shepard=False)

    # ---------------------------------------------------------- Escena 5: EL DESPERTAR (57 - 75)
    statements = list(zip(SYNC["golpesDeclaracion"], ["Dm", "Bb", "C"]))
    for i, (ts, ch) in enumerate(statements):
        trailer_hit(ts, 1.0, gong_level="mf" if i == 2 else None, crash_level="ff", big=0.6, seed=20 + i)
        brass_stab(ts, ch, 0.95, 1.0)
        low_string_stab(ts, ch, 0.95)
        place("brass", L.braam(CH[ch]["root"] - 12 if CH[ch]["root"] - 12 >= 24 else CH[ch]["root"], 1.4, 0.6, seed=i), ts, 0.5, hall=0.3)
        place("synth", L.sub_bass(CH[ch]["root"] - 12 if CH[ch]["root"] - 12 >= 24 else CH[ch]["root"], 1.8, 0.45, attack=0.01), ts, 0.6)
        strings_chord(ts, 1.9, ch, 0.45, attack=0.05, release=0.3, layers=("vc", "vla", "vln"), gain=0.9)
        choir(ts + 0.02, 1.8, ch, 0.28, vowel="o", attack=0.3, release=0.6, seed=50 + i)
    # encendido de focos del auditorio (sincronizado con las filas de luces del plano 5C)
    for i, tt in enumerate([61.2, 61.5, 61.8, 62.1]):
        place("sfx", L.light_thunk(0.7, seed=i), tt, 0.32, room=0.5, big=0.15)
    place("perc", snare_roll(0.9, 0.5), 62.1, 0.4, hall=0.3)
    riser_into(63.0, 1.5, 0.3, seed=8, shepard=False)

    t5 = SYNC["inicioGroove"]
    seq5 = [(63.0, "Dm", 2.0), (65.0, "Bb", 2.0), (67.0, "F", 1.0), (68.0, "F", 1.0), (69.0, "C", 2.0), (71.0, "Gm", 1.0), (72.0, "A", 3.0)]
    trailer_hit(t5, 1.0, gong_level=None, crash_level="ff", big=0.6, seed=30)
    brass_stab(t5, "Dm", 1.0, 1.1)
    for ts, ch, d in seq5:
        strings_chord(ts, d, ch, 0.62, attack=0.15, release=0.5, high=True, gain=1.35)
        place("synth", L.sub_bass(CH[ch]["root"] - 12 if CH[ch]["root"] - 12 >= 24 else CH[ch]["root"], d, 0.45, attack=0.02), ts, 0.55)
        place("strings", cb.note(CH[ch]["root"] if CH[ch]["root"] >= 28 else CH[ch]["root"] + 12, d, 0.6, 0.05, 0.4), ts, 0.7, 0, 0.3)
    # coro y metales: crecen en las pausas de la voz
    choir(63.0, 1.2, "Dm", 0.85, vowel="a", attack=0.2, release=1.0, high=True, seed=60)
    choir(68.0, 1.3, "F", 0.9, vowel="a", attack=0.2, release=0.9, high=True, seed=61)
    choir(72.0, 3.0, "A", 0.9, vowel="a", attack=0.6, release=0.05, high=True, seed=62)
    brass_chord(68.0, 1.2, "F", 0.9, attack=0.15, release=0.6, gain=1.6)
    brass_chord(72.0, 3.0, "A", 0.85, attack=1.2, release=0.05, gain=1.6)
    # ostinato rápido (semicorcheas en violines por encima de la voz)
    seq5o = [(s, c) for s, c, _ in seq5]
    ostinato(63.0, 68.0, seq5o, vel=0.7, gain=1.2, high_inst=None)
    ostinato(69.0, 75.0, seq5o, vel=0.8, gain=1.35, high_inst=None)
    ostinato(65.0, 68.0, seq5o, inst_low=vla_spic, inst_mid=vln_spic, vel=0.55, gain=0.8, eighth=0.125,
             pattern=[2, 1, 0, 1], accent=[1.0, 0.6, 0.8, 0.6])
    ostinato(69.0, 75.0, seq5o, inst_low=vla_spic, inst_mid=vln_spic, vel=0.6, gain=0.9, eighth=0.125,
             pattern=[2, 1, 0, 1], accent=[1.0, 0.6, 0.8, 0.6])
    # groove de percusión de tráiler
    def groove_bar(b0, intensity):
        for q, v in [(0.0, 1.0), (0.75, 0.7), (1.0, 0.85), (1.5, 0.7), (1.75, 0.6)]:
            place("sfx", L.taiko(v * intensity, 70, 0.7, seed=int(b0 * 10 + q * 8)), b0 + q, 0.7, big=0.08)
            if q in (0.0, 1.0):
                place("perc", bdrum(0.75 * intensity, 1 + int(q)), b0 + q, 0.85, hall=0.2)
        for q in (0.5, 1.5):
            place("perc", snare_hit(0.8 * intensity, 1 + int(q)), b0 + q, 0.5, 0.05, hall=0.45)
        for q in np.arange(0, 2, 0.25):
            place("sfx", L.taiko(0.25 * intensity, 120, 0.25, seed=int(b0 * 100 + q * 16)), b0 + q + 0.125, 0.25, big=0.0)
    groove_bar(63.0, 0.9)
    groove_bar(65.0, 0.9)
    groove_bar(67.0, 0.95)
    # 68.0: golpe y pausa dramática (sólo cuerdas y coro) — 69.0 vuelve todo
    trailer_hit(68.0, 0.85, crash_level="mf", big=0.5, seed=31)
    trem_chord(68.0, 1.2, "F", 0.5, attack=0.05, release=0.3, gain=0.8)
    groove_bar(69.0, 1.0)
    groove_bar(71.0, 1.0)
    # construcción final 72-75
    place("perc", snare_roll(3.0, 0.8), 72.0, 0.55, hall=0.3)
    place("perc", timp_roll(3.0, 0.85, drum=2), 72.0, 0.6, hall=0.3)
    trem_chord(72.0, 3.0, "A", 0.8, attack=2.5, release=0.02, gain=1.6)
    for q in np.arange(73.0, 75.0, 0.5):
        place("sfx", L.taiko(1.0, 66, 0.6, seed=int(q * 10)), q, 0.75, big=0.1)
        place("perc", bdrum(0.9, 1), q, 0.7, hall=0.2)
    for q in np.arange(74.0, 75.0, 0.125):
        place("perc", snare_hit(0.9, 1 + int(q * 8) % 2), q, 0.35, hall=0.3)
    riser_into(t_cut, 6.0, 0.75, seed=9)
    sc = sus_cresc("Long")
    place("perc", sc[: int(4.0 * SR)], t_cut - 4.0, 0.4, hall=0.3)
    for i, tt in enumerate([64.0, 66.0, 67.0, 69.2, 71.0, 72.0]):
        whoosh_at(tt, 0.5, 0.25, seed=50 + i, direction=1 if i % 2 else -1, bright=1.2)
    for i, tt in enumerate(np.arange(73.0, 75.0, 0.5)):
        whoosh_at(float(tt), 0.35, 0.3, seed=60 + i, direction=1 if i % 2 else -1, bright=1.4)

    # ---------------------------------------------------------- Escena 6: LA REVELACIÓN
    # corte abrupto a silencio en t_cut (se aplica al final con una puerta de silencio)
    tt = t_title
    place("sfx", L.boom(1.0, 70, 26, 4.5, click=0.9, seed=40), tt, 0.75, big=0.7)
    place("perc", gong("fff"), tt, 0.75, 0.0, hall=0.3, big=0.6)
    place("perc", crash("ff", 1), tt, 0.5, -0.2, hall=0.3, big=0.4)
    place("perc", crash("ff", 2), tt + 0.01, 0.4, 0.2, hall=0.3, big=0.4)
    place("perc", bdrum(1.0, 1), tt, 1.0, hall=0.3, big=0.6)
    place("perc", timp_hit(38, 1.0), tt, 0.9, hall=0.3, big=0.5)
    brass_stab(tt, "D", 1.0, 1.1)
    low_string_stab(tt, "D", 1.0, 1.0)
    place("brass", L.braam(26, 3.0, 0.8, seed=9), tt, 0.55, hall=0.3, big=0.3)
    chord_len = t_final - tt
    strings_chord(tt, chord_len - 2.0, "D", 0.7, attack=0.08, release=2.0, high=True, gain=1.7, hall=0.5)
    choir(tt, chord_len - 2.0, "D", 0.85, vowel="a", attack=0.15, release=2.0, high=True, seed=70)
    brass_chord(tt, chord_len - 2.5, "D", 0.7, attack=0.1, release=2.0, gain=1.3)
    place("synth", L.saw_pad([50, 57, 62, 66], chord_len - 2.0, 0.9, cutoff=1500, attack=0.3, release=2.0, seed=5), tt, 1.0, hall=0.4)
    place("synth", L.sub_bass(26, chord_len - 1.5, 0.5, attack=0.01, release=1.5), tt, 0.6)
    trem_chord(tt + 0.5, 3.5, "D", 0.35, attack=1.0, release=1.5, gain=0.6)
    # cadencia plagal (Amén): D - G/D - D
    strings_chord(tt + 4.2, 2.0, "G/D", 0.5, attack=0.8, release=1.0, layers=("vla", "vln"), high=True, gain=0.8)
    choir(tt + 4.2, 2.0, "G/D", 0.45, attack=0.8, release=1.0, high=True, seed=71)
    place("brass", hn.note(62, 3.0, 0.5, attack=0.8, release=1.2), tt + 4.2, 0.4, -0.2, 0.5)
    place("brass", hn.note(66, 2.5, 0.5, attack=0.8, release=1.2), tt + 6.2, 0.4, 0.2, 0.5)
    # subtítulo: campanita
    place("keys", glock(98, 0.25), SYNC["subtitulo"], 0.6, 0.2, hall=1.0)
    place("keys", piano(86, 0.45, 4.0), SYNC["subtitulo"], 0.45, -0.1, hall=1.0)
    whoosh_at(SYNC["subtitulo"] + 0.3, 1.4, 0.15, seed=70, bright=1.3)
    rng = np.random.default_rng(9)
    for tt2 in np.sort(rng.uniform(tt + 0.3, t_final, 10)):
        place("keys", glock(int(rng.choice([86, 90, 93, 98])), 0.07), float(tt2), 0.45, rng.uniform(-0.8, 0.8), hall=1.0)
    place("perc", timp_roll(2.0, 0.55, drum=2), t_final - 2.0, 0.4, hall=0.3)
    reverse_crash_into(t_final, "ff", 2.0, 0.45)

    # ---------------------------------------------------------- Escena 7: IMPACTO FINAL
    tf = t_final
    place("sfx", L.boom(1.0, 66, 26, 4.0, click=0.9, seed=41), tf, 0.75, big=0.7)
    place("perc", gong("fff"), tf, 0.7, 0.1, hall=0.3, big=0.6)
    place("perc", crash("ff", 2), tf, 0.5, 0.0, hall=0.3, big=0.4)
    place("perc", bdrum(1.0, 2), tf, 1.0, hall=0.3, big=0.5)
    place("perc", timp_hit(38, 1.0, rr=2), tf, 0.9, hall=0.3, big=0.5)
    brass_stab(tf, "D", 1.0, 1.1)
    low_string_stab(tf, "D", 1.0)
    tail = DUR - tf
    strings_chord(tf, tail - 1.8, "D", 0.7, attack=0.05, release=1.6, high=True, gain=1.6)
    choir(tf, tail - 1.8, "D", 0.8, attack=0.1, release=1.6, high=True, seed=72)
    brass_chord(tf, tail - 2.0, "D", 0.75, attack=0.1, release=1.6, gain=1.3)
    place("synth", L.saw_pad([50, 57, 62, 66, 69], tail - 1.8, 0.9, cutoff=1800, attack=0.1, release=1.6, seed=6), tf, 1.0, hall=0.4)
    place("synth", L.sub_bass(26, tail - 1.5, 0.45, attack=0.01, release=1.3), tf, 0.6)


def render():
    os.makedirs(OUT, exist_ok=True)
    compose()
    hall = dsp.make_ir(3.4, predelay_ms=25, damping_hz=7000, low_cut=160, seed=11)
    big = dsp.make_ir(6.5, predelay_ms=35, damping_hz=5000, low_cut=90, seed=12, width=1.2)
    room = dsp.make_ir(0.9, predelay_ms=8, damping_hz=6500, low_cut=250, seed=13)
    music = np.zeros_like(dry["strings"])
    eqs = {
        "strings": [dsp.peaking(250, -1.5, 0.8), dsp.highshelf(9000, 1.5)],
        "brass": [dsp.peaking(400, -1.0, 1.0)],
        "choir": [dsp.peaking(300, -2.0, 0.9), dsp.highshelf(8000, -2.0)],
        "perc": [dsp.lowshelf(80, 2.0)],
        "keys": [dsp.highshelf(7000, -1.0)],
        "synth": [dsp.lowshelf(60, 1.0)],
    }
    for name in ["strings", "brass", "choir", "perc", "keys", "synth"]:
        b = dry[name]
        if name in eqs:
            b = dsp.eq(b, *eqs[name])
        music += b
    wet_hall = dsp.convolve_stereo(send_hall, hall)[: music.shape[0]]
    music += wet_hall * 0.32
    wet_big = dsp.convolve_stereo(send_big, big)[: music.shape[0]]
    wet_room = dsp.convolve_stereo(send_room, room)[: music.shape[0]]
    sfx = dry["sfx"] + wet_big * 0.28 + wet_room * 0.3
    music = dsp.hp(music, 28, order=2)
    sfx = dsp.hp(sfx, 25, order=2)
    # pegamento suave en la música
    music, _ = dsp.compressor(music, threshold_db=-16, ratio=2.0, attack_ms=25, release_ms=250, knee_db=8)

    # silencio controlado entre el corte y la revelación
    t_cut, t_title = SYNC["corteSilencio"], SYNC["revelacionTitulo"]
    gate = np.ones(music.shape[0])
    a, b = int(t_cut * SR), int(t_title * SR)
    fade = int(0.012 * SR)
    gate[a : a + fade] = np.linspace(1, 0, fade)
    gate[a + fade : b] = 0.0
    music *= gate[:, None]
    sfx *= gate[:, None]
    # final: cola natural recortada a la duración total
    music = music[:N]
    sfx = sfx[:N]
    end_fade = int(1.2 * SR)
    for x in (music, sfx):
        x[-end_fade:] *= np.cos(np.linspace(0, np.pi / 2, end_fade))[:, None] ** 2
    peak = max(np.max(np.abs(music)), np.max(np.abs(sfx)))
    print(f"pico música={np.max(np.abs(music)):.3f} sfx={np.max(np.abs(sfx)):.3f}")
    sf.write(os.path.join(OUT, "music.wav"), music.astype(np.float32), SR, subtype="FLOAT")
    sf.write(os.path.join(OUT, "sfx.wav"), sfx.astype(np.float32), SR, subtype="FLOAT")
    print("Stems:", OUT, "| timbales:", {k: round(v, 1) for k, v in TIMP.items()})


if __name__ == "__main__":
    render()
