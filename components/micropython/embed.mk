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

# Modules de extmod/ a embarquer en plus (random, json, time) : le port embed
# ne copie AUCUN .c de extmod (seulement modplatform.h) et ne les scanne donc
# pas. On les ajoute ici au scan QSTR/moduledefs pour que leurs chaines et leur
# MP_REGISTER_MODULE soient collectes. IMPORTANT : le scan n'accepte QUE des
# chemins RELATIFS (comme modaka.c) -- un chemin absolu vers l'arbre MicroPython
# n'est pas pris en compte. build_micropython_embed.sh copie donc ces .c (et
# modtime.h) dans extmod_extra/ (relatif) AVANT la generation, puis dans le
# paquet micropython_embed/extmod/ pour qu'ils soient reellement compiles
# (sim PC comme firmware ESP), et nettoie extmod_extra/ ensuite.
SRC_QSTR += extmod_extra/modrandom.c
SRC_QSTR += extmod_extra/modjson.c
SRC_QSTR += extmod_extra/modtime.c

include $(MICROPYTHON_TOP)/ports/embed/embed.mk
