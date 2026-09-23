/* aka_hal.h — Interface C SANS dependance materielle entre la glue MicroPython
 * (modaka.c) et l'implementation gamebuino (aka_hal.cpp).
 *
 * modaka.c ne doit inclure QUE cet en-tete (et les en-tetes du dossier py) : ainsi il se
 * pre-traite proprement cote hote pendant la generation des QSTR, sans les
 * en-tetes ESP-IDF/gamebuino. Toute la mecanique reelle (gb_graphics, gb_core,
 * aka_runtime...) vit dans aka_hal.cpp, compile uniquement sous ESP-IDF. */
#ifndef AKA_HAL_H
#define AKA_HAL_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// --- Cycle de vie MicroPython (appeles par main.cpp) ---
void aka_boot_init(void *heap, size_t heap_size);   // stack + GC + mp_init
void aka_boot_exec(const char *path);               // lit et execute un fichier .py

// --- Graphismes (couleur RGB565 via aka_hal_color) ---
uint16_t aka_hal_color(uint8_t r, uint8_t g, uint8_t b);
void aka_hal_set_color(uint16_t c);
void aka_hal_clear(uint16_t c);
void aka_hal_pixel(int x, int y);
void aka_hal_hline(int x, int y, int w);
void aka_hal_vline(int x, int y, int h);
void aka_hal_line(int x0, int y0, int x1, int y1);
void aka_hal_rect(int x, int y, int w, int h);
void aka_hal_fill_rect(int x, int y, int w, int h);
void aka_hal_circle(int x, int y, int r);
void aka_hal_fill_circle(int x, int y, int r);
void aka_hal_triangle(int x0, int y0, int x1, int y1, int x2, int y2);
void aka_hal_fill_triangle(int x0, int y0, int x1, int y1, int x2, int y2);
void aka_hal_text(int x, int y, const char *s);
void aka_hal_display(void);
int  aka_hal_width(void);
int  aka_hal_height(void);

// --- Entrees / cycle de frame ---
// Sert une frame : lit les boutons et laisse le menu systeme AKA prendre la
// main si besoin. Renvoie 1 si le jeu doit tourner cette frame, 0 sinon.
int      aka_hal_update(void);
uint32_t aka_hal_buttons(void);
uint32_t aka_hal_pressed(void);
uint32_t aka_hal_released(void);
void     aka_hal_joystick(int *x, int *y);

// --- Temps / divers ---
uint32_t aka_hal_ticks_ms(void);
void     aka_hal_sleep_ms(uint32_t ms);
void     aka_hal_vibrate(uint32_t ms);
// Suivi de duree fait ICI (pas dans gb_audio_player, dont u32_vibrator_delay
// est prive) : simple bookkeeping local, aucune modification du composant
// partage gamebuino necessaire.
int      aka_hal_is_vibrating(void);
const char *aka_hal_language(void);
const char *aka_hal_tr(const char *key);
int      aka_hal_screenshot(void);

// --- Son : lecture d'un echantillon PCM 8 bits NON SIGNE (convention des
// jeux MicroPython Pokitto : upygame.mixer.Sound().play_sfx(data, len, loop))
// -- convertit en interne vers le format attendu par gb_audio_track_wav
// (PCM 16 bits signe) et COPIE les donnees (le pointeur Python ne doit pas
// etre suppose valide au-dela de l'appel).
void aka_hal_play_pcm8(const uint8_t *data, size_t len, int loop);
int  aka_hal_is_sound_playing(void);
// Appelee a chaque frame (par aka_hal_update() lui-meme) : relance la
// lecture si un bouclage a ete demande et que la piste vient de s'arreter.
// Ne pas appeler directement depuis modaka.c/Python -- interne au HAL.
void aka_hal_sound_service(void);

// --- Aide integree au menu systeme AKA ---
// Lignes d'aide affichees dans l'ecran "Commandes" du menu (touche MENU).
void aka_hal_set_controls(const char *const *lines, int n);
// Renseigne l'ecran "Credits" du menu.
void aka_hal_set_credits(const char *title, const char *author,
                         const char *license, const char *url);

// --- Transfert de fichiers depuis un PC (protocole "AKAT" v1.1, voir docs/PROTOCOLE_TRANSFERT.md du
// depot AKA-Love -- protocole COMMUN a plusieurs firmwares AKA, pas specifique a MicroPython) ---
// Ecran plein ecran, bloquant : attend un transfert USB indefiniment (jusqu'a MENU pour sortir). Si le
// fichier vise existe deja, demande a l'utilisateur (A: Ecraser, D: Renommer, B: Annuler ce fichier,
// 30 s puis Annuler par defaut). Le dossier de destination vient de AKA/languages.csv sur la carte SD
// (repli sur /sdcard/py si absent) -- voir components/micropython/transfer.cpp.
void aka_hal_receive_code(void);

#ifdef __cplusplus
}
#endif

#endif // AKA_HAL_H
