/* modaka.c — Module MicroPython natif `aka` : expose le materiel AKA (ecran,
 * boutons, audio, temps, SD) aux scripts Python.
 *
 * IMPORTANT : ce fichier est aussi PRE-TRAITE cote hote lors de la generation
 * des QSTR/moduledefs. Il ne doit donc inclure QUE des en-tetes portables :
 * les en-tetes du dossier py, aka_hal.h (sans dependance), et la libc. Toute la mecanique materielle
 * est derriere aka_hal_* (implementee dans aka_hal.cpp, cote ESP-IDF). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>

#include "py/compile.h"
#include "py/gc.h"
#include "py/runtime.h"
#include "py/stackctrl.h"
#include "py/builtin.h"
#include "py/mperrno.h"
#include "py/stream.h"

#include "aka_hal.h"
#include "aka_keys.h"

// Marge de securite de pile laissee a MicroPython (octets). Doit rester
// inferieure a la pile de la tache app_main (cf. sdkconfig.defaults).
#define AKA_MP_STACK_LIMIT (16 * 1024)

// BUG TROUVE ET CORRIGE (cause racine du "ImportError: no module named X"
// meme quand le fichier existe bel et bien et que sys.path est correct) :
// MICROPY_VFS vaut 0 dans ce port (confirme dans mpconfig.h) -- le port DOIT
// alors fournir lui-meme mp_import_stat() (utilisee par tout le mecanisme
// d'import pour verifier si un chemin candidat existe, et si c'est un
// fichier ou un dossier). Cette fonction n'etait jamais implementee nulle
// part.
//
// PREMIERE IMPLEMENTATION (abandonnee) : basee sur stat() (<sys/stat.h>) --
// n'a pas resolu le probleme malgre une implementation syntaxiquement
// correcte, ce qui suggere que stat() n'est pas correctement cablee sur ce
// montage SD/FATFS precis (meme si d'autres fonctions POSIX le sont).
// Reecrite pour s'appuyer UNIQUEMENT sur fopen()/opendir(), deux mecanismes
// deja EPROUVES ailleurs dans ce meme fichier (aka_read_file utilise fopen
// partout ; aka_list_py utilise opendir/readdir avec succes) plutot que sur
// une fonction encore jamais testee dans ce projet precis.
// Declaration anticipee (definition plus bas dans ce fichier) -- necessaire
// car mp_lexer_new_from_file() (juste en dessous) l'utilise avant.
static char *aka_read_file(const char *path, size_t *out_len);

mp_import_stat_t mp_import_stat(const char *path) {
    DIR *dp = opendir(path);
    if (dp) {
        closedir(dp);
        return MP_IMPORT_STAT_DIR;
    }
    FILE *f = fopen(path, "rb");
    if (f) {
        fclose(f);
        return MP_IMPORT_STAT_FILE;
    }
    return MP_IMPORT_STAT_NO_EXIST;
}

// BUG TROUVE ET CORRIGE : autre point d'ancrage requis par le port des que
// MICROPY_ENABLE_EXTERNAL_IMPORT=1 -- do_load() (builtinimport.c) appelle
// mp_lexer_new_from_file() pour lire et tokeniser le .py trouve par
// mp_import_stat(). Non implementee, meme categorie de manque que
// mp_import_stat() juste au-dessus. Reutilise aka_read_file() (deja
// eprouvee, utilisee pour le script principal) plutot qu'une nouvelle
// mecanique de lecture.
mp_lexer_t *mp_lexer_new_from_file(qstr filename) {
    const char *path = qstr_str(filename);
    size_t len = 0;
    char *src = aka_read_file(path, &len);
    if (!src) {
        mp_raise_OSError(MP_ENOENT);
    }
    // free_len = len : le lexer devient proprietaire du buffer et le
    // liberera lui-meme (aka_read_file alloue via malloc, compatible).
    return mp_lexer_new_from_str_len(filename, src, len, len);
}

// BUG TROUVE ET CORRIGE : mp_builtin_open() n'etait pas fournie (ce port n'a
// pas de VFS -- MICROPY_VFS=0). Sans elle, AUCUN programme MicroPython
// "standard" utilisant open()/with ne peut fonctionner -- pas seulement
// upygame/umachine, n'importe quel script qui fait de la lecture/ecriture
// de fichier normale. Implementee ici plutot que de continuer a contourner
// au cas par cas (comme aka.file_read/file_write, qui restent disponibles
// mais ne couvraient que notre propre umachine.py).
//
// Modelisee directement sur py/objstringio.c (StringIO/BytesIO, deja
// present dans ce meme build) : le "protocole de flux" (mp_stream_p_t)
// fournit juste les callbacks bas niveau read/write/ioctl, et
// mp_stream_read_obj/write_obj/close_obj (py/stream.c, deja disponibles)
// fournissent les methodes Python correspondantes automatiquement -- pas
// besoin de les reimplementer nous-memes.
typedef struct _aka_file_obj_t {
    mp_obj_base_t base;
    FILE *fp;
} aka_file_obj_t;

static mp_uint_t aka_file_read_stream(mp_obj_t self_in, void *buf, mp_uint_t size, int *errcode) {
    aka_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->fp) { *errcode = MP_EBADF; return MP_STREAM_ERROR; }
    size_t n = fread(buf, 1, size, self->fp);
    if (n == 0 && ferror(self->fp)) { *errcode = MP_EIO; return MP_STREAM_ERROR; }
    return n;
}

static mp_uint_t aka_file_write_stream(mp_obj_t self_in, const void *buf, mp_uint_t size, int *errcode) {
    aka_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->fp) { *errcode = MP_EBADF; return MP_STREAM_ERROR; }
    size_t n = fwrite(buf, 1, size, self->fp);
    if (n == 0 && size != 0) { *errcode = MP_EIO; return MP_STREAM_ERROR; }
    return n;
}

static mp_uint_t aka_file_ioctl(mp_obj_t self_in, mp_uint_t request, uintptr_t arg, int *errcode) {
    aka_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)arg;
    if (request == MP_STREAM_CLOSE) {
        if (self->fp) { fclose(self->fp); self->fp = NULL; }
        return 0;
    }
    if (request == MP_STREAM_FLUSH) {
        if (self->fp) fflush(self->fp);
        return 0;
    }
    *errcode = MP_EINVAL;
    return MP_STREAM_ERROR;
}

static void aka_file_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    (void)kind;
    aka_file_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "<aka.file %p>", self->fp);
}

static const mp_rom_map_elem_t aka_file_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mp_stream_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_readline), MP_ROM_PTR(&mp_stream_unbuffered_readline_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mp_stream_write_obj) },
    { MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&mp_stream_close_obj) },
    { MP_ROM_QSTR(MP_QSTR___enter__), MP_ROM_PTR(&mp_identity_obj) },
    { MP_ROM_QSTR(MP_QSTR___exit__), MP_ROM_PTR(&mp_stream___exit___obj) },
};
static MP_DEFINE_CONST_DICT(aka_file_locals_dict, aka_file_locals_dict_table);

static const mp_stream_p_t aka_file_stream_p = {
    .read = aka_file_read_stream,
    .write = aka_file_write_stream,
    .ioctl = aka_file_ioctl,
};

MP_DEFINE_CONST_OBJ_TYPE(
    aka_type_file,
    MP_QSTR_TextIOWrapper,
    MP_TYPE_FLAG_ITER_IS_STREAM,
    print, aka_file_print,
    protocol, &aka_file_stream_p,
    locals_dict, &aka_file_locals_dict
    );

mp_obj_t mp_builtin_open(size_t n_args, const mp_obj_t *args, mp_map_t *kwargs) {
    (void)kwargs;
    const char *path = mp_obj_str_get_str(args[0]);
    const char *mode = (n_args > 1) ? mp_obj_str_get_str(args[1]) : "r";

    // Traduction simplifiee mode Python -> fopen : premiere lettre
    // (r/w/a/x) + toujours binaire cote C (le "b" ou non du mode Python
    // n'affecte que l'encodage texte, non gere ici -- coherent avec
    // l'usage prevu, echange de bytes/bytearray plutot que de texte
    // encode).
    char fmode[3] = "rb";
    if (mode[0] == 'w') fmode[0] = 'w';
    else if (mode[0] == 'a') fmode[0] = 'a';
    else if (mode[0] == 'x') fmode[0] = 'w';
    else fmode[0] = 'r';
    fmode[1] = 'b';
    fmode[2] = '\0';

    FILE *fp = fopen(path, fmode);
    if (!fp) {
        mp_raise_OSError(MP_ENOENT);
    }
    aka_file_obj_t *o = mp_obj_malloc(aka_file_obj_t, &aka_type_file);
    o->fp = fp;
    return MP_OBJ_FROM_PTR(o);
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_builtin_open_obj, 1, mp_builtin_open);

// ---------------------------------------------------------------------------
// Amorcage : init de la VM + execution d'un fichier .py depuis la SD.
// ---------------------------------------------------------------------------
void aka_boot_init(void *heap, size_t heap_size) {
    mp_stack_ctrl_init();
    mp_stack_set_limit(AKA_MP_STACK_LIMIT);
    gc_init(heap, (uint8_t *)heap + heap_size);
    mp_init();
}

// Compile puis execute un texte source ; affiche l'exception si non rattrapee.
static void aka_exec_named(const char *name, const char *src, size_t len) {
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        mp_lexer_t *lex = mp_lexer_new_from_str_len(qstr_from_str(name), src, len, 0);
        qstr source_name = lex->source_name;
        mp_parse_tree_t parse_tree = mp_parse(lex, MP_PARSE_FILE_INPUT);
        mp_obj_t module_fun = mp_compile(&parse_tree, source_name, true);
        mp_call_function_0(module_fun);
        nlr_pop();
    } else {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
    }
}

// Lit tout un fichier en memoire (heap C) ; renvoie NULL si echec.
static char *aka_read_file(const char *path, size_t *out_len) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n < 0) { fclose(f); return NULL; }
    char *buf = (char *)malloc((size_t)n + 1);
    if (!buf) { fclose(f); return NULL; }
    size_t rd = fread(buf, 1, (size_t)n, f);
    fclose(f);
    buf[rd] = '\0';
    if (out_len) *out_len = rd;
    return buf;
}

// BUG TROUVE ET CORRIGE : sys.path n'etait jamais configure -- "import
// upygame" (ou tout module place a cote du script principal) echouait
// systematiquement avec ImportError des qu'un jeu est place dans SON PROPRE
// dossier (/sdcard/<jeu>/), puisque MicroPython ne cherche par defaut que
// dans ses chemins integres (aucun chemin SD).
//
// PREMIERE TENTATIVE (abandonnee) : manipuler directement mp_sys_path /
// MP_STATE_VM(sys_mutable[...]) depuis le C -- cette structure interne
// s'est averee incoherente entre les en-tetes generes (runtime.h attend un
// champ "sys_mutable" que mpstate.h ne definit pas dans cette configuration
// precise).
//
// DEUXIEME TENTATIVE (abandonnee) : executer "import sys; sys.path.insert
// (...)" via un aka_exec_named() SEPARE, AVANT celui du script principal --
// confirme par diagnostic (fichier bien trouve sur la carte, insertion
// executee sans erreur) que le probleme n'est ni le fichier ni la logique
// de recherche, mais l'ISOLATION entre deux appels aka_exec_named()
// distincts : chaque compilation/execution semble reinitialiser son propre
// contexte, la modification de sys.path faite dans le premier appel ne
// survit pas jusqu'au second.
//
// FIX ACTUEL : ne plus faire DEUX executions separees. Construire le prefixe
// Python (sys.path.insert...) et le PREPENDRE directement au contenu du
// fichier avant compilation -- les deux s'executent alors comme UNE SEULE
// unite, partageant necessairement le meme contexte. Effet de bord mineur :
// les numeros de ligne dans les tracebacks d'erreur du jeu seront decales
// de +1 (le prefixe tient sur une seule ligne). Acceptable au vu du confort
// de developpement -- a garder en tete si un "line N" semble incoherent.
static size_t aka_build_path_prefix(const char *path, char *out, size_t out_cap) {
    const char *slash = strrchr(path, '/');
    if (!slash) return 0;
    size_t dir_len = (size_t)(slash - path);
    if (dir_len == 0) return 0;

    char dir[256];
    if (dir_len >= sizeof(dir)) dir_len = sizeof(dir) - 1;
    memcpy(dir, path, dir_len);
    dir[dir_len] = '\0';

    int n = snprintf(out, out_cap,
                      "import sys; sys.path.insert(0, \"%s\")\n", dir);
    if (n <= 0 || (size_t)n >= out_cap) return 0;
    return (size_t)n;
}

static void aka_exec_file(const char *path) {
    size_t len = 0;
    char *src = aka_read_file(path, &len);
    if (!src) {
        mp_printf(&mp_plat_print, "aka: fichier introuvable: %s\n", path);
        aka_hal_set_color(aka_hal_color(255, 0, 0));
        aka_hal_text(8, 8, "Fichier .py introuvable:");
        aka_hal_text(8, 24, path);
        aka_hal_display();
        return;
    }

    char prefix[320];
    size_t prefix_len = aka_build_path_prefix(path, prefix, sizeof(prefix));

    if (prefix_len == 0) {
        // Pas de repertoire dans le chemin (rare) -- execute tel quel.
        aka_exec_named(path, src, len);
    } else {
        // Concatene prefixe + contenu du fichier dans UN SEUL buffer, execute
        // comme une seule unite (cf. commentaire au-dessus de
        // aka_build_path_prefix -- necessaire pour que sys.path.insert()
        // survive jusqu'au reste du script).
        char *combined = (char *)malloc(prefix_len + len + 1);
        if (combined) {
            memcpy(combined, prefix, prefix_len);
            memcpy(combined + prefix_len, src, len);
            combined[prefix_len + len] = '\0';
            aka_exec_named(path, combined, prefix_len + len);
            free(combined);
        } else {
            aka_exec_named(path, src, len);   // echec allocation -- tente quand meme sans le prefixe
        }
    }

    free(src);
}

// Appele par main.cpp apres aka_boot_init.
void aka_boot_exec(const char *path) { aka_exec_file(path); }

// ---------------------------------------------------------------------------
// Fonctions du module `aka`.
// ---------------------------------------------------------------------------
static mp_obj_t aka_color(mp_obj_t r, mp_obj_t g, mp_obj_t b) {
    return mp_obj_new_int(aka_hal_color(
        (uint8_t)mp_obj_get_int(r), (uint8_t)mp_obj_get_int(g), (uint8_t)mp_obj_get_int(b)));
}
static MP_DEFINE_CONST_FUN_OBJ_3(aka_color_obj, aka_color);

static mp_obj_t aka_set_color(mp_obj_t r, mp_obj_t g, mp_obj_t b) {
    aka_hal_set_color(aka_hal_color(
        (uint8_t)mp_obj_get_int(r), (uint8_t)mp_obj_get_int(g), (uint8_t)mp_obj_get_int(b)));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(aka_set_color_obj, aka_set_color);

static mp_obj_t aka_clear(size_t n_args, const mp_obj_t *args) {
    if (n_args == 3) {
        aka_hal_clear(aka_hal_color((uint8_t)mp_obj_get_int(args[0]),
                                    (uint8_t)mp_obj_get_int(args[1]),
                                    (uint8_t)mp_obj_get_int(args[2])));
    } else {
        aka_hal_clear(aka_hal_color(0, 0, 0));
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(aka_clear_obj, 0, 3, aka_clear);

static mp_obj_t aka_pixel(mp_obj_t x, mp_obj_t y) {
    aka_hal_pixel(mp_obj_get_int(x), mp_obj_get_int(y));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(aka_pixel_obj, aka_pixel);

static mp_obj_t aka_hline(mp_obj_t x, mp_obj_t y, mp_obj_t w) {
    aka_hal_hline(mp_obj_get_int(x), mp_obj_get_int(y), mp_obj_get_int(w));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(aka_hline_obj, aka_hline);

static mp_obj_t aka_vline(mp_obj_t x, mp_obj_t y, mp_obj_t h) {
    aka_hal_vline(mp_obj_get_int(x), mp_obj_get_int(y), mp_obj_get_int(h));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(aka_vline_obj, aka_vline);

static mp_obj_t aka_line(size_t n_args, const mp_obj_t *args) {
    aka_hal_line(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]),
                 mp_obj_get_int(args[2]), mp_obj_get_int(args[3]));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(aka_line_obj, 4, 4, aka_line);

static mp_obj_t aka_rect(size_t n_args, const mp_obj_t *args) {
    aka_hal_rect(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]),
                 mp_obj_get_int(args[2]), mp_obj_get_int(args[3]));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(aka_rect_obj, 4, 4, aka_rect);

static mp_obj_t aka_fill_rect(size_t n_args, const mp_obj_t *args) {
    aka_hal_fill_rect(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]),
                      mp_obj_get_int(args[2]), mp_obj_get_int(args[3]));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(aka_fill_rect_obj, 4, 4, aka_fill_rect);

static mp_obj_t aka_circle(mp_obj_t x, mp_obj_t y, mp_obj_t r) {
    aka_hal_circle(mp_obj_get_int(x), mp_obj_get_int(y), mp_obj_get_int(r));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(aka_circle_obj, aka_circle);

static mp_obj_t aka_fill_circle(mp_obj_t x, mp_obj_t y, mp_obj_t r) {
    aka_hal_fill_circle(mp_obj_get_int(x), mp_obj_get_int(y), mp_obj_get_int(r));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(aka_fill_circle_obj, aka_fill_circle);

static mp_obj_t aka_triangle(size_t n_args, const mp_obj_t *args) {
    aka_hal_triangle(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]),
                     mp_obj_get_int(args[2]), mp_obj_get_int(args[3]),
                     mp_obj_get_int(args[4]), mp_obj_get_int(args[5]));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(aka_triangle_obj, 6, 6, aka_triangle);

static mp_obj_t aka_fill_triangle(size_t n_args, const mp_obj_t *args) {
    aka_hal_fill_triangle(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]),
                          mp_obj_get_int(args[2]), mp_obj_get_int(args[3]),
                          mp_obj_get_int(args[4]), mp_obj_get_int(args[5]));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(aka_fill_triangle_obj, 6, 6, aka_fill_triangle);

static mp_obj_t aka_text(mp_obj_t x, mp_obj_t y, mp_obj_t s) {
    aka_hal_text(mp_obj_get_int(x), mp_obj_get_int(y), mp_obj_str_get_str(s));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(aka_text_obj, aka_text);

static mp_obj_t aka_display(void) { aka_hal_display(); return mp_const_none; }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_display_obj, aka_display);

static mp_obj_t aka_width(void)  { return mp_obj_new_int(aka_hal_width()); }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_width_obj, aka_width);
static mp_obj_t aka_height(void) { return mp_obj_new_int(aka_hal_height()); }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_height_obj, aka_height);

static mp_obj_t aka_update(void)   { return mp_obj_new_bool(aka_hal_update()); }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_update_obj, aka_update);
static mp_obj_t aka_buttons(void)  { return mp_obj_new_int_from_uint(aka_hal_buttons()); }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_buttons_obj, aka_buttons);
static mp_obj_t aka_pressed(void)  { return mp_obj_new_int_from_uint(aka_hal_pressed()); }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_pressed_obj, aka_pressed);
static mp_obj_t aka_released(void) { return mp_obj_new_int_from_uint(aka_hal_released()); }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_released_obj, aka_released);

static mp_obj_t aka_joystick(void) {
    int x = 0, y = 0;
    aka_hal_joystick(&x, &y);
    mp_obj_t t[2] = { mp_obj_new_int(x), mp_obj_new_int(y) };
    return mp_obj_new_tuple(2, t);
}
static MP_DEFINE_CONST_FUN_OBJ_0(aka_joystick_obj, aka_joystick);

static mp_obj_t aka_ticks_ms(void) { return mp_obj_new_int_from_uint(aka_hal_ticks_ms()); }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_ticks_ms_obj, aka_ticks_ms);

static mp_obj_t aka_sleep_ms(mp_obj_t ms) {
    aka_hal_sleep_ms((uint32_t)mp_obj_get_int(ms));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(aka_sleep_ms_obj, aka_sleep_ms);

static mp_obj_t aka_vibrate(mp_obj_t ms) {
    aka_hal_vibrate((uint32_t)mp_obj_get_int(ms));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(aka_vibrate_obj, aka_vibrate);

static mp_obj_t aka_is_vibrating(void) {
    return mp_obj_new_bool(aka_hal_is_vibrating());
}
static MP_DEFINE_CONST_FUN_OBJ_0(aka_is_vibrating_obj, aka_is_vibrating);

static mp_obj_t aka_language(void) {
    const char *l = aka_hal_language();
    return mp_obj_new_str(l, strlen(l));
}
static MP_DEFINE_CONST_FUN_OBJ_0(aka_language_obj, aka_language);

static mp_obj_t aka_tr(mp_obj_t key) {
    const char *v = aka_hal_tr(mp_obj_str_get_str(key));
    return mp_obj_new_str(v, strlen(v));
}
static MP_DEFINE_CONST_FUN_OBJ_1(aka_tr_obj, aka_tr);

static mp_obj_t aka_screenshot(void) { return mp_obj_new_bool(aka_hal_screenshot()); }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_screenshot_obj, aka_screenshot);

// Écran interactif "Recevoir un code" (protocole AKAT, voir docs/PROTOCOLE_TRANSFERT.md du dépôt
// AKA-Love) : bloque jusqu'à ce que l'utilisateur appuie sur MENU pour sortir.
static mp_obj_t aka_receive_code(void) { aka_hal_receive_code(); return mp_const_none; }
static MP_DEFINE_CONST_FUN_OBJ_0(aka_receive_code_obj, aka_receive_code);

// aka.file_read(path) -> bytes ou None si absent. Reutilise aka_read_file()
// (deja eprouvee -- utilisee pour charger le script principal et les
// modules importes) plutot que d'implementer un type "fichier" Python
// complet (open() n'est pas fourni par ce port -- voir umachine.py, qui
// s'appuie sur ces deux fonctions plutot que sur open()/with).
static mp_obj_t aka_file_read(mp_obj_t path_obj) {
    const char *path = mp_obj_str_get_str(path_obj);
    size_t len = 0;
    char *buf = aka_read_file(path, &len);
    if (!buf) {
        return mp_const_none;
    }
    mp_obj_t result = mp_obj_new_bytes((const byte *)buf, len);
    free(buf);
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_1(aka_file_read_obj, aka_file_read);

// aka.file_write(path, data) -> True/False. data : bytes/bytearray/str.
static mp_obj_t aka_file_write(mp_obj_t path_obj, mp_obj_t data_obj) {
    const char *path = mp_obj_str_get_str(path_obj);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);
    FILE *f = fopen(path, "wb");
    if (!f) {
        return mp_const_false;
    }
    size_t written = fwrite(bufinfo.buf, 1, bufinfo.len, f);
    fclose(f);
    return mp_obj_new_bool(written == bufinfo.len);
}
static MP_DEFINE_CONST_FUN_OBJ_2(aka_file_write_obj, aka_file_write);

static mp_obj_t aka_run_file(mp_obj_t path) {
    aka_exec_file(mp_obj_str_get_str(path));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(aka_run_file_obj, aka_run_file);

// aka.play_pcm8(data, loop=False) -- data : bytes/bytearray PCM 8 bits non
// signe (0..255, 128=silence), convention des jeux MicroPython Pokitto.
static mp_obj_t aka_play_pcm8(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[0], &bufinfo, MP_BUFFER_READ);
    int loop = (n_args > 1) && mp_obj_is_true(args[1]);
    aka_hal_play_pcm8((const uint8_t *)bufinfo.buf, bufinfo.len, loop);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(aka_play_pcm8_obj, 1, 2, aka_play_pcm8);

static mp_obj_t aka_is_sound_playing(void) {
    return mp_obj_new_bool(aka_hal_is_sound_playing());
}
static MP_DEFINE_CONST_FUN_OBJ_0(aka_is_sound_playing_obj, aka_is_sound_playing);

static mp_obj_t aka_set_controls(mp_obj_t lines) {
    size_t n = 0;
    mp_obj_t *items = NULL;
    mp_obj_get_array(lines, &n, &items);
    const char *buf[12];
    if (n > 12) n = 12;
    for (size_t i = 0; i < n; ++i) buf[i] = mp_obj_str_get_str(items[i]);
    aka_hal_set_controls(buf, (int)n);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(aka_set_controls_obj, aka_set_controls);

static mp_obj_t aka_set_credits(size_t n_args, const mp_obj_t *args) {
    aka_hal_set_credits(mp_obj_str_get_str(args[0]), mp_obj_str_get_str(args[1]),
                        mp_obj_str_get_str(args[2]), mp_obj_str_get_str(args[3]));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(aka_set_credits_obj, 4, 4, aka_set_credits);

static mp_obj_t aka_list_py(mp_obj_t dir) {
    const char *d = mp_obj_str_get_str(dir);
    mp_obj_t list = mp_obj_new_list(0, NULL);
    DIR *dp = opendir(d);
    if (dp) {
        struct dirent *e;
        while ((e = readdir(dp)) != NULL) {
            size_t l = strlen(e->d_name);
            if (l > 3 && strcmp(e->d_name + l - 3, ".py") == 0) {
                mp_obj_list_append(list, mp_obj_new_str(e->d_name, l));
            }
        }
        closedir(dp);
    }
    return list;
}
static MP_DEFINE_CONST_FUN_OBJ_1(aka_list_py_obj, aka_list_py);

// ---------------------------------------------------------------------------
// Table du module.
// ---------------------------------------------------------------------------
// BUG TROUVE ET CORRIGE : MP_QSTR___path__ est utilisee par builtinimport.c
// (coeur MicroPython, pour la detection paquet/sous-module) -- mais ce
// fichier n'est apparemment PAS scanne par la generation des QSTR (seul
// modaka.c l'est explicitement, voir embed.mk : "SRC_QSTR += modaka.c").
// Resultat : "MP_QSTR___path__ undeclared" des que MICROPY_ENABLE_EXTERNAL_
// IMPORT active ce code. Fix standard pour ce type de situation : forcer
// l'enregistrement de la QSTR via une reference INERTE ici (jamais
// executee), dans un fichier qui EST scanne.
static const qstr aka_force_qstr_path __attribute__((unused)) = MP_QSTR___path__;

// RAPPEL : toute nouvelle fonction ajoutee ci-dessous (nouveau MP_QSTR_xxx)
// necessite de relancer ./build_micropython_embed.sh AVANT idf.py build --
// les QSTR sont pre-generees cote hote, une simple recompilation ESP-IDF ne
// suffit pas si la liste des fonctions exposees a change.
static const mp_rom_map_elem_t aka_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__),     MP_ROM_QSTR(MP_QSTR_aka) },
    // graphismes
    { MP_ROM_QSTR(MP_QSTR_color),        MP_ROM_PTR(&aka_color_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_color),    MP_ROM_PTR(&aka_set_color_obj) },
    { MP_ROM_QSTR(MP_QSTR_clear),        MP_ROM_PTR(&aka_clear_obj) },
    { MP_ROM_QSTR(MP_QSTR_pixel),        MP_ROM_PTR(&aka_pixel_obj) },
    { MP_ROM_QSTR(MP_QSTR_hline),        MP_ROM_PTR(&aka_hline_obj) },
    { MP_ROM_QSTR(MP_QSTR_vline),        MP_ROM_PTR(&aka_vline_obj) },
    { MP_ROM_QSTR(MP_QSTR_line),         MP_ROM_PTR(&aka_line_obj) },
    { MP_ROM_QSTR(MP_QSTR_rect),         MP_ROM_PTR(&aka_rect_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill_rect),    MP_ROM_PTR(&aka_fill_rect_obj) },
    { MP_ROM_QSTR(MP_QSTR_circle),       MP_ROM_PTR(&aka_circle_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill_circle),  MP_ROM_PTR(&aka_fill_circle_obj) },
    { MP_ROM_QSTR(MP_QSTR_triangle),     MP_ROM_PTR(&aka_triangle_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill_triangle),MP_ROM_PTR(&aka_fill_triangle_obj) },
    { MP_ROM_QSTR(MP_QSTR_text),         MP_ROM_PTR(&aka_text_obj) },
    { MP_ROM_QSTR(MP_QSTR_display),      MP_ROM_PTR(&aka_display_obj) },
    { MP_ROM_QSTR(MP_QSTR_width),        MP_ROM_PTR(&aka_width_obj) },
    { MP_ROM_QSTR(MP_QSTR_height),       MP_ROM_PTR(&aka_height_obj) },
    // entrees
    { MP_ROM_QSTR(MP_QSTR_update),       MP_ROM_PTR(&aka_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_buttons),      MP_ROM_PTR(&aka_buttons_obj) },
    { MP_ROM_QSTR(MP_QSTR_pressed),      MP_ROM_PTR(&aka_pressed_obj) },
    { MP_ROM_QSTR(MP_QSTR_released),     MP_ROM_PTR(&aka_released_obj) },
    { MP_ROM_QSTR(MP_QSTR_joystick),     MP_ROM_PTR(&aka_joystick_obj) },
    // temps / divers
    { MP_ROM_QSTR(MP_QSTR_ticks_ms),     MP_ROM_PTR(&aka_ticks_ms_obj) },
    { MP_ROM_QSTR(MP_QSTR_sleep_ms),     MP_ROM_PTR(&aka_sleep_ms_obj) },
    { MP_ROM_QSTR(MP_QSTR_vibrate),      MP_ROM_PTR(&aka_vibrate_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_vibrating), MP_ROM_PTR(&aka_is_vibrating_obj) },
    { MP_ROM_QSTR(MP_QSTR_play_pcm8),    MP_ROM_PTR(&aka_play_pcm8_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_sound_playing), MP_ROM_PTR(&aka_is_sound_playing_obj) },
    { MP_ROM_QSTR(MP_QSTR_language),     MP_ROM_PTR(&aka_language_obj) },
    { MP_ROM_QSTR(MP_QSTR_tr),           MP_ROM_PTR(&aka_tr_obj) },
    { MP_ROM_QSTR(MP_QSTR_screenshot),   MP_ROM_PTR(&aka_screenshot_obj) },
    { MP_ROM_QSTR(MP_QSTR_receive_code), MP_ROM_PTR(&aka_receive_code_obj) },
    { MP_ROM_QSTR(MP_QSTR_run_file),     MP_ROM_PTR(&aka_run_file_obj) },
    { MP_ROM_QSTR(MP_QSTR_file_read),    MP_ROM_PTR(&aka_file_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_file_write),   MP_ROM_PTR(&aka_file_write_obj) },
    { MP_ROM_QSTR(MP_QSTR_list_py),      MP_ROM_PTR(&aka_list_py_obj) },
    // aide integree au menu systeme
    { MP_ROM_QSTR(MP_QSTR_set_controls), MP_ROM_PTR(&aka_set_controls_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_credits),  MP_ROM_PTR(&aka_set_credits_obj) },
    // constantes touches
    { MP_ROM_QSTR(MP_QSTR_UP),    MP_ROM_INT(AKA_KEY_UP) },
    { MP_ROM_QSTR(MP_QSTR_DOWN),  MP_ROM_INT(AKA_KEY_DOWN) },
    { MP_ROM_QSTR(MP_QSTR_LEFT),  MP_ROM_INT(AKA_KEY_LEFT) },
    { MP_ROM_QSTR(MP_QSTR_RIGHT), MP_ROM_INT(AKA_KEY_RIGHT) },
    { MP_ROM_QSTR(MP_QSTR_A),     MP_ROM_INT(AKA_KEY_A) },
    { MP_ROM_QSTR(MP_QSTR_B),     MP_ROM_INT(AKA_KEY_B) },
    { MP_ROM_QSTR(MP_QSTR_C),     MP_ROM_INT(AKA_KEY_C) },
    { MP_ROM_QSTR(MP_QSTR_D),     MP_ROM_INT(AKA_KEY_D) },
    { MP_ROM_QSTR(MP_QSTR_RUN),   MP_ROM_INT(AKA_KEY_RUN) },
    { MP_ROM_QSTR(MP_QSTR_MENU),  MP_ROM_INT(AKA_KEY_MENU) },
    { MP_ROM_QSTR(MP_QSTR_L1),    MP_ROM_INT(AKA_KEY_L1) },
    { MP_ROM_QSTR(MP_QSTR_R1),    MP_ROM_INT(AKA_KEY_R1) },
};
static MP_DEFINE_CONST_DICT(aka_module_globals, aka_module_globals_table);

const mp_obj_module_t aka_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&aka_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_aka, aka_module);
