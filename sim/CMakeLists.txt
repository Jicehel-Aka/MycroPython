# =============================================================================
#  Simulateur PC de l'interpréteur MicroPython de l'AKA.
#
#  Deux cibles, même principe qu'akalove (akalove-sim / akalove-play) :
#    * aka-py-sim           : FENÊTRÉ + son réel (SDL2), pour JOUER sur PC.
#                             C'est le binaire lancé par AKA-IDE.
#    * aka-py-sim-headless  : SANS fenêtre (sortie PPM, entrées scriptées via
#                             variables d'environnement), pour les tests/CI.
#
#  Les deux partagent : le cœur MicroPython « embed » généré
#  (components/micropython/micropython_embed/), la glue portable modaka.c, et le
#  moteur de rendu logiciel aka_gfx.c. Seule la couche HAL diffère
#  (aka_hal_sdl.c vs aka_hal_headless.c).
#
#  PRÉALABLE : le cœur embed doit avoir été généré :
#      ./build_micropython_embed.sh        (voir le script à la racine du dépôt)
#  (fait automatiquement en CI ; le dossier généré n'est pas forcément versionné.)
#
#  Build :
#      cmake -S sim -B build-sim && cmake --build build-sim -j
# =============================================================================
cmake_minimum_required(VERSION 3.16)
project(aka_py_sim C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

set(ROOT  ${CMAKE_CURRENT_LIST_DIR}/..)
set(MP    ${ROOT}/components/micropython)
set(EMBED ${MP}/micropython_embed)
set(SIM   ${CMAKE_CURRENT_LIST_DIR})

if(NOT EXISTS ${EMBED}/py)
  message(FATAL_ERROR
    "Cœur MicroPython embed introuvable (${EMBED}/py).\n"
    "Générez-le d'abord :  ./build_micropython_embed.sh")
endif()

# --- Cœur MicroPython « embed » généré (code tiers : pas de -Werror) ---------
file(GLOB_RECURSE EMBED_SRC
  ${EMBED}/py/*.c
  ${EMBED}/shared/*.c
  ${EMBED}/port/*.c)

add_library(mpembed STATIC ${EMBED_SRC} ${MP}/modaka.c)
target_include_directories(mpembed PUBLIC ${EMBED} ${EMBED}/port ${MP} ${SIM})
target_compile_options(mpembed PRIVATE -w)   # code généré + glue : avertissements hors de notre contrôle

# --- Sources communes du simulateur -----------------------------------------
set(SIM_COMMON ${SIM}/aka_gfx.c ${SIM}/main_sim.c)

# =============================================================================
#  Cible 1 : aka-py-sim-headless (toujours bâtie)
# =============================================================================
add_executable(aka-py-sim-headless ${SIM_COMMON} ${SIM}/aka_hal_headless.c)
target_include_directories(aka-py-sim-headless PRIVATE ${EMBED} ${EMBED}/port ${MP} ${SIM})
target_compile_options(aka-py-sim-headless PRIVATE -Wall -Wextra)
target_link_libraries(aka-py-sim-headless PRIVATE mpembed m)
if(MINGW)
  target_link_options(aka-py-sim-headless PRIVATE -static)
endif()

# =============================================================================
#  Cible 2 : aka-py-sim (FENÊTRÉ + son, SDL2) — ignorée si SDL2 absent
# =============================================================================
find_package(SDL2 QUIET)
if(NOT SDL2_FOUND)   # repli pkg-config (SDL2 sans fichier *Config.cmake)
  find_package(PkgConfig QUIET)
  if(PkgConfig_FOUND)
    pkg_check_modules(SDL2PC QUIET sdl2)
  endif()
endif()

if(SDL2_FOUND OR SDL2PC_FOUND)
  add_executable(aka-py-sim ${SIM_COMMON} ${SIM}/aka_hal_sdl.c)
  target_include_directories(aka-py-sim PRIVATE ${EMBED} ${EMBED}/port ${MP} ${SIM})
  target_compile_options(aka-py-sim PRIVATE -Wall -Wextra)   # pas de -Werror : en-têtes SDL2
  target_link_libraries(aka-py-sim PRIVATE mpembed m)
  if(TARGET SDL2::SDL2)
    # On lie UNIQUEMENT SDL2::SDL2 (pas SDL2main) : notre main() est dans
    # main_sim.c (SDL_MAIN_HANDLED dans aka_hal_sdl.c) -> évite « undefined
    # reference to SDL_main » à l'édition de liens MinGW/Windows.
    target_link_libraries(aka-py-sim PRIVATE SDL2::SDL2)
  elseif(SDL2_FOUND)
    target_include_directories(aka-py-sim PRIVATE ${SDL2_INCLUDE_DIRS})
    target_link_libraries(aka-py-sim PRIVATE ${SDL2_LIBRARIES})
  else()
    target_include_directories(aka-py-sim PRIVATE ${SDL2PC_INCLUDE_DIRS})
    target_link_libraries(aka-py-sim PRIVATE ${SDL2PC_LIBRARIES})
    target_link_directories(aka-py-sim PRIVATE ${SDL2PC_LIBRARY_DIRS})
  endif()
  if(MINGW)   # SDL2 livré en DLL à côté ; on fige seulement le runtime GCC
    target_link_options(aka-py-sim PRIVATE -static-libgcc)
  endif()
  message(STATUS "aka-py-sim (SDL2, fenêtré + son) : ACTIVÉ")
else()
  message(STATUS "aka-py-sim (SDL2, fenêtré + son) : SDL2 introuvable -> cible ignorée")
endif()
