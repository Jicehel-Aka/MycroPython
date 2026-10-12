# -*- coding: utf-8 -*-
# =============================================================================
#  feu_artifice.py — Démo « feu d'artifice » pour la console AKA.
#
#  But : montrer, dans un seul programme, l'usage de PLUSIEURS modules standard
#  désormais embarqués (voir MANUEL.md) :
#    - math        : table de sinus/cosinus précalculée (directions d'explosion)
#    - random      : positions, couleurs, vitesses, nombre de particules
#    - time        : pas de temps réel (ticks_ms/ticks_diff) + chrono
#    - collections : namedtuple (couleur de palette) + deque (fenêtre de FPS)
#    - array       : tables trigonométriques en flottants (compact et rapide)
#    - struct      : sauvegarde binaire (lancers + record) dans un .sav
#    - json        : statistiques lisibles dans un .json
#    - micropython : const() pour les constantes
#
#  Commandes : A = lancer une fusée · C = remettre les stats à zéro ·
#              (des fusées partent aussi toutes seules) · MENU / Échap (PC).
# =============================================================================
import aka
import math
import random
import time
import struct
import json
import array
from collections import namedtuple, deque
from micropython import const

W = const(320)
H = const(240)
GROUND = const(236)
GRAVITY = const(95.0)          # px/s^2 (chute des particules)
MAX_PARTICLES = const(280)
AUTO_MS = const(900)           # une fusée automatique toutes les 0,9 s
SAVE_BIN = "feu_artifice.sav"
STATS_JSON = "feu_artifice_stats.json"

# --- Tables trigonométriques précalculées (math -> array de flottants) -------
STEPS = const(64)
SIN = array.array("f", [math.sin(i * 2.0 * math.pi / STEPS) for i in range(STEPS)])
COS = array.array("f", [math.cos(i * 2.0 * math.pi / STEPS) for i in range(STEPS)])

# --- Palette (collections.namedtuple) ----------------------------------------
Color = namedtuple("Color", ["r", "g", "b"])
PALETTE = [
    Color(255, 80, 80), Color(90, 255, 120), Color(90, 170, 255),
    Color(255, 220, 60), Color(255, 120, 240), Color(120, 255, 240),
    Color(255, 160, 50),
]

# --- État --------------------------------------------------------------------
# particule : [x, y, vx, vy, vie, vie0, couleur]   fusée : [x, y, vy, cible_y, couleur]
particles = []
rockets = []
# Fenêtre glissante des pas de temps pour lisser les FPS. Le deque de ce build
# MicroPython est minimal (append / popleft / len, PAS d'itération) : on borne
# nous-mêmes à FPS_N en retirant le plus ancien avec popleft() (qui renvoie la
# valeur retirée, ce qui permet de tenir la somme à jour sans tout reparcourir).
FPS_N = const(24)
fps_win = deque((), 64)
fps_sum = 0.0
launches = 0
best = 0                       # record de particules simultanées
runtime_ms = 0


def load_stats():
    global launches, best
    try:
        with open(SAVE_BIN, "rb") as f:
            launches, best = struct.unpack("<II", f.read(8))
    except Exception:
        launches, best = 0, 0


def save_stats():
    try:
        with open(SAVE_BIN, "wb") as f:
            f.write(struct.pack("<II", launches, best))
    except Exception:
        pass
    try:
        with open(STATS_JSON, "w") as f:
            f.write(json.dumps({"launches": launches, "best": best,
                                "runtime_s": runtime_ms // 1000}))
    except Exception:
        pass


def launch():
    """Lance une fusée depuis le bas de l'écran vers une altitude aléatoire."""
    x = random.randint(30, W - 30)
    ci = random.randrange(len(PALETTE))
    target = random.randint(40, 120)
    rockets.append([float(x), float(GROUND), -random.uniform(130.0, 170.0),
                    float(target), ci])


def explode(x, y, ci):
    """Éclate une fusée en particules réparties sur un cercle (SIN/COS)."""
    global launches, best
    n = random.randint(26, 44)
    for _ in range(n):
        a = random.randrange(STEPS)
        sp = random.uniform(45.0, 115.0)
        if len(particles) < MAX_PARTICLES:
            vie = random.uniform(0.8, 1.7)
            particles.append([x, y, COS[a] * sp, SIN[a] * sp, vie, vie, ci])
    launches += 1
    if len(particles) > best:
        best = len(particles)
    if best == len(particles) or launches % 10 == 0:
        save_stats()


def update(dt):
    # fusées
    i = len(rockets) - 1
    while i >= 0:
        r = rockets[i]
        r[1] += r[2] * dt
        r[2] += GRAVITY * 0.5 * dt      # décélère en montant
        if r[1] <= r[3] or r[2] >= 0.0:
            explode(r[0], r[1], r[4])
            rockets.pop(i)
        i -= 1
    # particules
    i = len(particles) - 1
    while i >= 0:
        p = particles[i]
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[3] += GRAVITY * dt
        p[4] -= dt
        if p[4] <= 0.0 or p[1] >= GROUND:
            particles.pop(i)
        i -= 1


def draw(fps):
    aka.clear(6, 6, 16)
    # sol
    aka.set_color(20, 24, 40)
    aka.fill_rect(0, GROUND, W, H - GROUND)
    # fusées (traînée)
    for r in rockets:
        c = PALETTE[r[4]]
        aka.set_color(c.r, c.g, c.b)
        aka.fill_rect(int(r[0]), int(r[1]), 2, 4)
    # particules (luminosité ~ vie restante)
    for p in particles:
        f = p[4] / p[5]
        c = PALETTE[p[6]]
        aka.set_color(int(c.r * f), int(c.g * f), int(c.b * f))
        aka.fill_rect(int(p[0]) - 1, int(p[1]) - 1, 2, 2)
    # HUD
    aka.set_color(255, 255, 255)
    aka.text(6, 4, "FEU D'ARTIFICE")
    aka.set_color(150, 200, 255)
    aka.text(6, 16, "Lancers: " + str(launches) + "  Record: " + str(best))
    aka.text(6, 26, "Particules: " + str(len(particles)) +
             "  FPS: " + str(int(fps)))
    aka.set_color(120, 130, 160)
    aka.text(6, H - 10, "A: fusee   C: reset stats")


# aide du menu système AKA
aka.set_controls([
    "Demo multi-modules : feu d'artifice",
    "A: lancer une fusee",
    "C: remettre les stats a zero",
    "(des fusees partent aussi toutes seules)",
])
aka.set_credits("Feu d'artifice AKA", "Jicehel", "MIT", "")


def run():
    global launches, best, runtime_ms, fps_sum
    random.seed(time.ticks_ms())      # variabilité réelle sur la console
    load_stats()
    last = time.ticks_ms()
    next_auto = last
    launch()                          # une première fusée tout de suite
    while True:
        aka.update()
        now = time.ticks_ms()
        dt = time.ticks_diff(now, last) / 1000.0
        last = now
        if dt <= 0.0 or dt > 0.1:
            dt = 0.033
        runtime_ms += int(dt * 1000)

        fps_win.append(dt)
        fps_sum += dt
        if len(fps_win) > FPS_N:       # retire le plus ancien et retranche-le
            fps_sum -= fps_win.popleft()
        fps = (len(fps_win) / fps_sum) if fps_sum > 0.0 else 0.0

        p = aka.pressed()
        if p & aka.A:
            launch()
        if p & aka.C:
            launches = 0
            best = 0
            save_stats()

        if time.ticks_diff(now, next_auto) >= 0:
            launch()
            next_auto = now + AUTO_MS

        update(dt)
        draw(fps)
        aka.display()


run()
