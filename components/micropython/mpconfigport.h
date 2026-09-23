/* mpconfigport.h — Configuration MicroPython pour l'app AKA (port `embed`).
 *
 * Ce fichier est lu DEUX fois :
 *   1) a la generation du paquet (make -f embed.mk) pour produire les QSTR ;
 *   2) a la compilation ESP-IDF des sources generees.
 * Il DOIT donc rester identique entre les deux etapes (cf. README).
 *
 * On part de la configuration minimale du port embed puis on active ce qui est
 * utile pour ecrire des jeux en Python, SANS tirer de module ayant besoin d'une
 * couche materielle supplementaire (pas de sys/io/time cote MicroPython : le
 * temps et les E/S passent par le module natif `aka`).
 */
#include <port/mpconfigport_common.h>

// Niveau de base : minimal (desactive toutes les options facultatives), on
// reactive explicitement ci-dessous.
#define MICROPY_CONFIG_ROM_LEVEL                (MICROPY_CONFIG_ROM_LEVEL_MINIMUM)

// Coeur indispensable.
#define MICROPY_ENABLE_COMPILER                 (1)
#define MICROPY_ENABLE_GC                       (1)
#define MICROPY_PY_GC                            (1)
// BUG TROUVE ET CORRIGE : desactive a l'origine (niveau de config minimal),
// mais necessaire pour sys.path (voir aka_add_script_dir_to_path dans
// modaka.c -- permet a un jeu place dans son propre dossier SD d'importer
// des modules "voisins" comme upygame.py).
#define MICROPY_PY_SYS                           (1)

// Deux sous-fonctionnalites de sys sans valeur par defaut dans mpconfig.h
// (le port doit les fournir explicitement des que MICROPY_PY_SYS=1) :
#define MICROPY_PY_SYS_PLATFORM                  "esp32"
// Invites REPL (sys.ps1/sys.ps2) -- inutile ici (pas de console interactive).
#define MICROPY_PY_SYS_PS1_PS2                   (0)

// BUG TROUVE ET CORRIGE -- LA VRAIE CAUSE RACINE de "ImportError: no module
// named X" malgre sys.path correct, fichier present sur la carte, et
// mp_import_stat() correctement implementee : DESACTIVEE par defaut a ce
// niveau de config minimal, cette macro determine si "import" utilise la
// version COMPLETE (cherche dans sys.path, appelle mp_import_stat) ou une
// version SIMPLIFIEE qui ne verifie QUE les modules integres et ne touche
// JAMAIS au systeme de fichiers (voir builtinimport.c, bloc
// "#else // MICROPY_ENABLE_EXTERNAL_IMPORT"). mp_import_stat() n'etait donc
// jamais appelee, non pas a cause d'un bug dedans, mais parce que le
// mecanisme qui aurait du l'appeler etait lui-meme absent du binaire.
#define MICROPY_ENABLE_EXTERNAL_IMPORT            (1)

// BUG TROUVE ET CORRIGE : desactive au niveau de config minimal, mais
// necessaire pour @property (utilise par upygame.py, classe Rect --
// width/height/centerx/... exposes comme attributs calcules, a la maniere
// pygame). Verifie : aucune autre fonctionnalite avancee (f-strings,
// generateurs, super(), autres decorateurs) n'est utilisee dans
// upygame.py/umachine.py/urandom.py/sprite.py -- @property etait le seul
// manque de cette categorie a ce stade.
#define MICROPY_PY_BUILTINS_PROPERTY              (1)

// BUG TROUVE ET CORRIGE : desactive au niveau de config minimal, mais
// necessaire pour bytearray() -- utilise par MrRobot (cookieData =
// bytearray(1), sauvegarde persistante) et par umachine.py/upygame.py.
// Verifie : ni bytearray ni aucun autre type/fonction usuellement gate au
// meme niveau (memoryview, enumerate, sorted, reversed, set, .format(),
// complex) n'apparaissent ailleurs dans le code du jeu ou mes fichiers de
// compatibilite -- bytearray etait le seul manque de cette categorie.
#define MICROPY_PY_BUILTINS_BYTEARRAY              (1)

// BUG TROUVE ET CORRIGE : necessaire pour le mecanisme de "protocole de
// flux" (mp_stream_p_t, mp_stream_read_obj/write_obj/close_obj...) utilise
// par notre implementation de open() (voir aka_file_open dans modaka.c) --
// meme mecanisme que py/objstringio.c (StringIO/BytesIO), pris comme
// modele.
#define MICROPY_PY_IO                              (1)

// xtensa (ESP32-S3) : pas de capture de registres native dans le port embed,
// on utilise le repli portable base sur setjmp pour le ramasse-miettes.
#define MICROPY_GCREGS_SETJMP                    (1)

// NLR via setjmp plutot que l'assembleur xtensa (nlrxtensa.c) : ce dernier fait
// un saut direct vers nlr_push_tail hors de portee d'encodage sous ESP-IDF
// ("dangerous relocation: j: cannot encode"). setjmp est portable et robuste.
#define MICROPY_NLR_SETJMP                       (1)

// Confort pour le dev de jeux (fonctionnalites purement VM, aucune dependance
// materielle -> pas de HAL supplementaire a fournir).
#define MICROPY_FLOAT_IMPL                       (MICROPY_FLOAT_IMPL_FLOAT)
#define MICROPY_ERROR_REPORTING                  (MICROPY_ERROR_REPORTING_NORMAL)
#define MICROPY_ENABLE_SOURCE_LINE               (1)
#define MICROPY_PY_BUILTINS_SLICE                (1)
#define MICROPY_PY_BUILTINS_ENUMERATE            (1)
#define MICROPY_PY_BUILTINS_REVERSED             (1)
#define MICROPY_PY_BUILTINS_MIN_MAX              (1)
#define MICROPY_PY_BUILTINS_SET                  (1)
#define MICROPY_PY_BUILTINS_ROUND_INT            (1)
#define MICROPY_PY_BUILTINS_RANGE_ATTRS          (1)
