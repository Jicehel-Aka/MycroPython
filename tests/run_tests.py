#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests du simulateur PC MicroPython-AKA (binaire sans fenêtre aka-py-sim-headless).

Pour chaque script de démonstration de sdcard_files/py, on lance le simulateur
headless sur quelques frames, on capture le framebuffer en PPM et on vérifie :
  * le processus se termine proprement (code 0, PAS de crash — c'était le bug
    de corruption du tas sur `import game8266` / `import upygame`) ;
  * un PPM 320x240 valide est produit ;
  * l'image n'est pas vide (plusieurs couleurs distinctes) — le jeu a bien
    dessiné quelque chose.

Plus quelques vérifications ciblées (écran de menu Pong, palette attendue).

Usage :
    python3 tests/run_tests.py [chemin/vers/aka-py-sim-headless] [chemin/vers/py]
Valeurs par défaut : build-sim/aka-py-sim-headless et sdcard_files/py.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build-sim", "aka-py-sim-headless")
PYDIR = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "sdcard_files", "py")
OUT = os.environ.get("AKA_TEST_OUT", "/tmp/aka_py_tests")
os.makedirs(OUT, exist_ok=True)

W, H = 320, 240
checks = 0
fails = 0


def check(cond, msg):
    global checks, fails
    checks += 1
    if not cond:
        fails += 1
        print(f"  FAIL: {msg}")
    return cond


def run_game(name, frames=40, press=None, lang=None):
    """Lance un script, renvoie (code, liste de pixels (r,g,b)) ou (code, None)."""
    ppm = os.path.join(OUT, name + ".ppm")
    if os.path.exists(ppm):
        os.remove(ppm)
    env = dict(os.environ, AKA_FRAMES=str(frames), AKA_SHOT=ppm)
    if press:
        env["AKA_PRESS"] = press
    if lang:
        env["AKA_LANG"] = lang
    script = os.path.join(PYDIR, name + ".py")
    r = subprocess.run([BIN, script], env=env, cwd=PYDIR,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
    pix = None
    if os.path.exists(ppm):
        with open(ppm, "rb") as f:
            assert f.readline().strip() == b"P6"
            w, h = map(int, f.readline().split())
            f.readline()
            d = f.read()
        if w == W and h == H and len(d) >= W * H * 3:
            pix = [(d[i], d[i + 1], d[i + 2]) for i in range(0, W * H * 3, 3)]
    return r.returncode, pix


def distinct(pix):
    return len(set(pix))


# --- Jeux qui importent game8266/upygame (ex-crash à l'import) ---------------
GAMES = ["demo", "pong", "snake", "invader", "breakout", "puissance4",
         "tetris", "bataille_navale"]

print("== Simulateur MicroPython-AKA : tests ==")
print(f"   binaire : {BIN}")
print(f"   scripts : {PYDIR}\n")

if not os.path.exists(BIN):
    print(f"ERREUR : binaire introuvable ({BIN}). Buildez d'abord le simulateur.")
    sys.exit(2)

for g in GAMES:
    if not os.path.exists(os.path.join(PYDIR, g + ".py")):
        continue
    print(f"[{g}]")
    code, pix = run_game(g)
    check(code == 0, f"{g}: code de sortie {code} (attendu 0 — pas de crash)")
    if check(pix is not None, f"{g}: PPM 320x240 produit"):
        check(distinct(pix) > 1, f"{g}: l'image n'est pas vide ({distinct(pix)} couleurs)")

# --- Vérif ciblée : écran de menu du Pong -----------------------------------
print("[pong — écran de menu]")
code, pix = run_game("pong", frames=20)
if pix:
    colors = set(pix)
    # Le menu utilise du blanc (texte), du cyan clair et du jaune (voir pong.py).
    has_white = (255, 255, 255) in colors
    has_cyan = any(r < 80 and g > 150 and b > 150 for (r, g, b) in colors)
    has_yellow = any(r > 200 and g > 180 and b < 80 for (r, g, b) in colors)
    check(has_white, "pong menu: texte blanc présent")
    check(has_cyan, "pong menu: accent cyan présent")
    check(has_yellow, "pong menu: titre jaune présent")
    # Fond majoritairement noir
    black = sum(1 for p in pix if p == (0, 0, 0))
    check(black > W * H * 0.5, "pong menu: fond majoritairement noir")

print(f"\n== {checks - fails}/{checks} vérifications OK ==")
sys.exit(1 if fails else 0)
