#!/usr/bin/env bash
# Genere le coeur MicroPython (paquet embed) dans components/micropython/micropython_embed/.
# A lancer UNE FOIS avant le premier `idf.py build`, puis a chaque modification de
# mpconfigport.h ou de la liste des QSTR de modaka.c.
#
# Prerequis (deja presents sur ce poste) :
#   - un checkout MicroPython (defaut : C:/Perso/micropython) ; surcharger via
#     la variable MICROPYTHON_TOP.
#   - GNU make (msys2 : C:/msys64/usr/bin/make.exe) + gcc + python.
set -euo pipefail

MICROPYTHON_TOP="${MICROPYTHON_TOP:-/c/Perso/micropython}"
MAKE_BIN="${MAKE_BIN:-/c/msys64/usr/bin/make.exe}"
PYTHON_BIN="${PYTHON_BIN:-python}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMP_DIR="$SCRIPT_DIR/components/micropython"

# gcc/cpp pour le preprocesseur QSTR. Sous MSYS2/Windows, on force le gcc
# mingw ; sous Linux/CI (pas de /mingw64), on garde le gcc du systeme.
if [ -d /mingw64/bin ]; then
    export PATH="/mingw64/bin:$PATH"
fi

if [ ! -d "$MICROPYTHON_TOP/ports/embed" ]; then
    echo "ERREUR : MicroPython introuvable a '$MICROPYTHON_TOP'." >&2
    echo "  git clone --depth 1 https://github.com/micropython/micropython.git \"$MICROPYTHON_TOP\"" >&2
    echo "  ou : MICROPYTHON_TOP=/chemin/vers/micropython ./build_micropython_embed.sh" >&2
    exit 1
fi

echo ">> Generation du coeur MicroPython"
echo "   MicroPython : $MICROPYTHON_TOP"
echo "   Sortie      : $COMP_DIR/micropython_embed"

cd "$COMP_DIR"

# Modules extmod a embarquer (random, json, time) : le port embed ne les copie
# ni ne les scanne. On les place dans extmod_extra/ (chemin RELATIF, declare
# dans embed.mk via SRC_QSTR) AVANT la generation pour que leurs chaines QSTR et
# leur MP_REGISTER_MODULE soient collectes (le scan ignore les chemins absolus).
EXTMOD_FILES="modrandom.c modjson.c modtime.c modtime.h"
rm -rf extmod_extra
mkdir -p extmod_extra
for f in $EXTMOD_FILES; do
    cp "$MICROPYTHON_TOP/extmod/$f" "extmod_extra/$f"
done

"$MAKE_BIN" -f embed.mk \
    MICROPYTHON_TOP="$MICROPYTHON_TOP" \
    PYTHON="$PYTHON_BIN" \
    "$@"

# Le paquet genere ne contient aucun .c de extmod : on y depose ceux qu'on vient
# de faire scanner, pour qu'ils soient reellement compiles (sim PC et ESP).
echo ">> Ajout des modules extmod (random, json, time) au paquet"
EXTMOD_DST="$COMP_DIR/micropython_embed/extmod"
mkdir -p "$EXTMOD_DST"
for f in $EXTMOD_FILES; do
    cp "extmod_extra/$f" "$EXTMOD_DST/$f"
done
rm -rf extmod_extra

echo ">> OK. Tu peux maintenant lancer : idf.py build"
