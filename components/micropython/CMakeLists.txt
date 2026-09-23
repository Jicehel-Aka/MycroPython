# Composant ESP-IDF : coeur MicroPython (paquet embed genere) + module natif `aka`.
#
# Le dossier micropython_embed/ est GENERE par build_micropython_embed.sh
# (make -f embed.mk). Il n'est pas versionne : il faut lancer la generation
# AVANT le premier `idf.py build` (cf. README).

file(GLOB MP_PY_SRCS     ${CMAKE_CURRENT_LIST_DIR}/micropython_embed/py/*.c)
file(GLOB MP_SHARED_SRCS ${CMAKE_CURRENT_LIST_DIR}/micropython_embed/shared/runtime/*.c)
file(GLOB MP_PORT_SRCS   ${CMAKE_CURRENT_LIST_DIR}/micropython_embed/port/*.c)

if(NOT MP_PY_SRCS)
    message(FATAL_ERROR
        "micropython_embed/ absent : lance d'abord ./build_micropython_embed.sh "
        "(genere le coeur MicroPython) avant idf.py build.")
endif()

idf_component_register(
    SRCS ${MP_PY_SRCS} ${MP_SHARED_SRCS} ${MP_PORT_SRCS} "modaka.c" "aka_hal.cpp" "transfer.cpp"
    INCLUDE_DIRS "." "micropython_embed"
    REQUIRES gamebuino aka_runtime)

# MicroPython est du C portable qui declenche des avertissements benins avec les
# options strictes d'ESP-IDF : on evite de transformer ces avertissements en
# erreurs pour ce composant uniquement.
target_compile_options(${COMPONENT_LIB} PRIVATE
    -Wno-error=unused-variable -Wno-error=unused-function -Wno-error=maybe-uninitialized
    -Wno-error=type-limits -Wno-error=sign-compare -Wno-error=missing-field-initializers
    -Wno-error=float-equal -Wno-error=old-style-declaration -Wno-error=cast-align
    -Wno-error=shadow -Wno-error=unused-parameter -Wno-error=array-bounds)

# NDEBUG : le port embed definit un __assert_func de repli (embed_util.c, sous
# #ifndef NDEBUG) qui entre en conflit avec celui de la newlib ESP-IDF. On le
# neutralise (les assertions du coeur MicroPython passent en no-op, standard).
target_compile_definitions(${COMPONENT_LIB} PRIVATE NDEBUG)
