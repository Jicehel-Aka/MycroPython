# embed.mk — Genere le paquet C autonome `micropython_embed/` a partir du port
# `embed` de MicroPython, EN AJOUTANT notre module natif modaka.c au scan des
# QSTR et des definitions de modules (MP_REGISTER_MODULE).
#
# Usage (depuis ce dossier) :
#   MICROPYTHON_TOP=/chemin/vers/micropython make -f embed.mk
# ou via le script build_micropython_embed.sh a la racine du projet.
#
# NB : SRC_QSTR doit etre etendu AVANT l'inclusion de embed.mk (qui inclut
# py/mkrules.mk ou la regle qstr.i.last fige la liste des prerequis).

MICROPYTHON_TOP ?= /c/Perso/micropython

# Ajoute notre glue au scan (QSTR + moduledefs). Pas besoin de la compiler ici :
# la cible du port embed ne fait que generer des en-tetes, pas d'objets.
SRC_QSTR += modaka.c

include $(MICROPYTHON_TOP)/ports/embed/embed.mk
