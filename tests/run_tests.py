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


def run_source(src, frames=2):
    """Exécute un script Python arbitraire (texte) et renvoie (code, stdout)."""
    import tempfile
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, dir=OUT)
    f.write(src)
    f.close()
    env = dict(os.environ, AKA_FRAMES=str(frames))
    r = subprocess.run([BIN, f.name], env=env, cwd=PYDIR,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    return r.returncode, r.stdout.decode("utf-8", "replace")


# --- Jeux qui importent game8266/upygame (ex-crash à l'import) ---------------
GAMES = ["demo", "pong", "snake", "invader", "breakout", "puissance4",
         "tetris", "bataille_navale", "calculatrice"]

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

# --- Vérif ciblée : calculatrice + tracé de courbe --------------------------
if os.path.exists(os.path.join(PYDIR, "calculatrice.py")):
    print("[calculatrice — mode courbe]")
    # D (frame 2) bascule en mode courbe ; sans expression, trace sin(x).
    code, pix = run_game("calculatrice", frames=6, press="d:2:3")
    check(code == 0, "calculatrice: pas de crash en mode courbe")
    if pix:
        yellow = sum(1 for (r, g, b) in pix if r > 200 and g > 170 and b < 90)
        check(yellow > 50, f"calculatrice: courbe jaune tracée ({yellow} px)")

# --- Vérif ciblée : module math natif (MICROPY_PY_MATH) ---------------------
print("[math — module natif]")
code, out = run_source(
    "import math\n"
    "print('S', round(math.sin(math.pi/6), 3))\n"
    "print('L', round(math.log10(1000.0), 3))\n"
    "print('Q', round(math.sqrt(2.0), 4))\n"
    "print('E', round(math.exp(1.0), 4))\n")
check(code == 0, "math: script importe et s'exécute sans erreur")
check("S 0.5" in out, "math: math.sin correct")
check("L 3.0" in out, "math: math.log10 correct (fonctions spéciales activées)")
check("Q 1.4142" in out, "math: math.sqrt correct")
check("E 2.7182" in out or "E 2.7183" in out, "math: math.exp correct")

# --- Vérif ciblée : modules standard activés --------------------------------
# Chacun doit s'importer ET exposer ses fonctions clés (pas seulement exister).
print("[modules — disponibilité]")
for m in ["math", "struct", "array", "collections", "micropython",
          "random", "json", "time"]:
    code, out = run_source("import " + m + "\nprint('IMP')\n")
    check(code == 0 and "IMP" in out, "module présent : " + m)

print("[modules — fonctions clés]")
code, out = run_source(
    "import struct, array, collections, random, json, time, micropython\n"
    "random.seed(1)\n"
    "print('ST', struct.unpack('<h', struct.pack('<h', -5))[0])\n"
    "print('AR', sum(array.array('i', [1, 2, 3])))\n"
    "print('NT', collections.namedtuple('P', ['a', 'b'])(4, 9).b)\n"
    "print('DQ', (lambda d: (d.append(1), d.popleft())[1])(collections.deque((), 4)))\n"
    "print('RI', 1 if 1 <= random.randint(1, 6) <= 6 else 0)\n"
    "print('CH', 1 if random.choice([7, 8, 9]) in (7, 8, 9) else 0)\n"
    "print('JS', json.loads(json.dumps({'k': [1, 2]}))['k'][1])\n"
    "print('TD', time.ticks_diff(time.ticks_add(time.ticks_ms(), 3), time.ticks_ms()))\n"
    "print('MC', micropython.const(5))\n")
check(code == 0, "modules: script multi-modules sans erreur")
check("ST -5" in out, "struct.pack/unpack correct")
check("AR 6" in out, "array.array correct")
check("NT 9" in out, "collections.namedtuple correct")
check("DQ 1" in out, "collections.deque correct")
check("RI 1" in out, "random.randint dans l'intervalle")
check("CH 1" in out, "random.choice correct")
check("JS 2" in out, "json round-trip correct")
check("TD 3" in out, "time.ticks_diff correct")
check("MC 5" in out, "micropython.const correct")

print(f"\n== {checks - fails}/{checks} vérifications OK ==")
sys.exit(1 if fails else 0)
