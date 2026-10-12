# Simulateur PC de MicroPython-AKA

Le dossier [`sim/`](../sim) contient un **simulateur PC** de l'interpréteur
MicroPython de l'AKA : il exécute sur Windows ou Linux, **sans matériel**, les
mêmes scripts `.py` que la console. Même principe que le simulateur d'AKA-Love
(`akalove-sim` / `akalove-play`) : on réutilise la glue portable
[`modaka.c`](../components/micropython/modaka.c) et on fournit une
implémentation PC de l'interface matérielle
[`aka_hal.h`](../components/micropython/aka_hal.h).

Ce qui tourne dans le simulateur tourne sur l'AKA, et inversement : même
interpréteur (MicroPython + module natif `aka`), même écran 320×240 RGB565,
mêmes boutons, mêmes limites.

## Les deux binaires

| Binaire | Rôle |
|---|---|
| `aka-py-sim` | **Fenêtré, avec le son réel** (SDL2). Pour jouer et tester. C'est le binaire lancé par **AKA-IDE** quand on exécute un projet MicroPython. |
| `aka-py-sim-headless` | **Sans fenêtre** (sortie image PPM, entrées scriptées par variables d'environnement). Pour les tests automatisés et la CI. |

## Architecture

Le simulateur ne recompile pas le module `aka` : il réutilise tel quel le code
portable et remplace seulement la couche matérielle.

```
sim/
 ├─ aka_gfx.{c,h}        moteur de rendu LOGICIEL : framebuffer 320x240 RGB565
 │                       (packing identique à la console : lcd_color_rgb),
 │                       texte font8x8 — implémente les fonctions GRAPHIQUES
 │                       de aka_hal.h (partagé par les deux binaires)
 ├─ font8x8_basic.h      police 8x8 (copie de components/gamebuino, domaine public)
 ├─ aka_hal_sdl.c        couche FENÊTRÉE : fenêtre + clavier + son réel (SDL2)
 ├─ aka_hal_headless.c   couche SANS fenêtre : horloge virtuelle, entrées
 │                       scriptées, capture PPM, arrêt borné
 ├─ main_sim.c           main() commun : alloue le tas, aka_boot_init/exec
 └─ CMakeLists.txt       deux cibles (aka-py-sim + aka-py-sim-headless)

components/micropython/
 ├─ modaka.c             module `aka` + amorçage — PORTABLE, réutilisé tel quel
 ├─ aka_hal.h            contrat C (ce que sim/ et aka_hal.cpp implémentent)
 └─ micropython_embed/   cœur MicroPython généré (voir plus bas)
```

La console implémente `aka_hal.h` dans `aka_hal.cpp` (par-dessus gamebuino) ; le
simulateur l'implémente dans `aka_gfx.c` (graphismes) + `aka_hal_sdl.c` ou
`aka_hal_headless.c` (le reste). `modaka.c` ne voit que `aka_hal.h` et ignore
donc totalement sur quelle plateforme il tourne.

## Compiler

Prérequis : **CMake**, un **compilateur C** (gcc/clang/MinGW), et **SDL2**
(`libsdl2-dev` sur Debian/Ubuntu ; `mingw-w64-x86_64-SDL2` sous MSYS2) pour la
cible fenêtrée. Il faut d'abord générer le cœur MicroPython « embed » (comme
pour le firmware) :

```bash
git clone --depth 1 https://github.com/micropython/micropython.git /tmp/micropython
MICROPYTHON_TOP=/tmp/micropython MAKE_BIN=make PYTHON_BIN=python3 ./build_micropython_embed.sh

cmake -S sim -B build-sim -DCMAKE_BUILD_TYPE=Release
cmake --build build-sim -j
```

On obtient `build-sim/aka-py-sim` (si SDL2 est présent) et
`build-sim/aka-py-sim-headless`. Si SDL2 est introuvable, seule la cible
sans fenêtre est bâtie (la cible fenêtrée est simplement ignorée).

## Jouer

```bash
./build-sim/aka-py-sim  sdcard_files/py/pong.py
```

Le script et les modules qu'il importe (`game8266`, `upygame`, …) doivent être
dans le même dossier, exactement comme sur la carte SD (`/py`).

Clavier : **flèches** = D-Pad · **Espace/Entrée** = A · **X** = B · **C** = C ·
**V** = D · **Maj gauche/droite** = L1/R1 · **Tab** = MENU · **I J K L** =
manette analogique · **Échap** = quitter. (On évite la touche « M » pour le
menu : SDL lit la position physique et le « M » QWERTY tombe sur « , » en
AZERTY ; Tab est au même endroit partout.) Voir aussi [`sim/LISEZMOI.txt`](../sim/LISEZMOI.txt),
livré dans les zips PC.

## Tests

`tests/run_tests.py` lance le binaire sans fenêtre sur chaque jeu d'exemple,
capture le framebuffer et vérifie l'absence de crash, une image valide et non
vide, et l'écran de menu du Pong :

```bash
python3 tests/run_tests.py
```

La CI (`.github/workflows/release.yml`, job `pc`) exécute ces tests sous Linux
et compile le simulateur sous Linux et Windows ; les zips
`micropython-aka-sim-<os>.zip` (binaires + jeux + doc) sont joints à chaque
release.

## Intégration AKA-IDE

AKA-IDE lance `aka-py-sim` pour exécuter un projet MicroPython (symétrique de
`akalove-play` pour un projet Love2D). Le binaire attend un seul argument : le
chemin du script `.py` à exécuter.
