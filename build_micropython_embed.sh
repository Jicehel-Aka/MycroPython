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

# gcc/cpp mingw pour le preprocesseur QSTR.
export PATH="/mingw64/bin:$PATH"

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
"$MAKE_BIN" -f embed.mk \
    MICROPYTHON_TOP="$MICROPYTHON_TOP" \
    PYTHON="$PYTHON_BIN" \
    "$@"

echo ">> OK. Tu peux maintenant lancer : idf.py build"
