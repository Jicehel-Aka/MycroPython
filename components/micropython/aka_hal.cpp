/* aka_hal.cpp — Implementation de aka_hal.h au-dessus de gamebuino + aka_runtime.
 * Compile UNIQUEMENT sous ESP-IDF (jamais scanne par la generation QSTR). */
#include "aka_hal.h"
#include "aka_keys.h"

#include "gb_core.h"
#include "gb_graphics.h"
#include "gb_common.h"        // SCREEN_WIDTH/HEIGHT, GB_KEY_*
#include "gb_ll_common.h"     // EXPANDER_KEY_*, JOYX_MID
#include "gb_audio_player.h"
#include "gb_audio_track_wav.h"
#include "core/input.h"
#include "aka_runtime/aka_runtime.h"

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "esp_timer.h"
#include <cstring>          // strncpy
#include <cstdlib>          // realloc

// Instances globales uniques, definies dans main.cpp.
extern gb_core         g_core;
extern gb_graphics     gfx;
extern gb_audio_player g_audio_player;

// Garantit que aka_keys.h (sans dependance) reste aligne sur le SDK.
static_assert(AKA_KEY_RUN   == EXPANDER_KEY_RUN,   "AKA_KEY_RUN != EXPANDER_KEY_RUN");
static_assert(AKA_KEY_MENU  == EXPANDER_KEY_MENU,  "AKA_KEY_MENU != EXPANDER_KEY_MENU");
static_assert(AKA_KEY_UP    == EXPANDER_KEY_UP,    "AKA_KEY_UP != EXPANDER_KEY_UP");
static_assert(AKA_KEY_DOWN  == EXPANDER_KEY_DOWN,  "AKA_KEY_DOWN != EXPANDER_KEY_DOWN");
static_assert(AKA_KEY_LEFT  == EXPANDER_KEY_LEFT,  "AKA_KEY_LEFT != EXPANDER_KEY_LEFT");
static_assert(AKA_KEY_RIGHT == EXPANDER_KEY_RIGHT, "AKA_KEY_RIGHT != EXPANDER_KEY_RIGHT");
static_assert(AKA_KEY_A     == EXPANDER_KEY_A,     "AKA_KEY_A != EXPANDER_KEY_A");
static_assert(AKA_KEY_B     == EXPANDER_KEY_B,     "AKA_KEY_B != EXPANDER_KEY_B");
static_assert(AKA_KEY_C     == EXPANDER_KEY_C,     "AKA_KEY_C != EXPANDER_KEY_C");
static_assert(AKA_KEY_D     == EXPANDER_KEY_D,     "AKA_KEY_D != EXPANDER_KEY_D");
static_assert(AKA_KEY_L1    == EXPANDER_KEY_L1,    "AKA_KEY_L1 != EXPANDER_KEY_L1");
static_assert(AKA_KEY_R1    == EXPANDER_KEY_R1,    "AKA_KEY_R1 != EXPANDER_KEY_R1");

// --- Graphismes ---
uint16_t aka_hal_color(uint8_t r, uint8_t g, uint8_t b) { return gfx.makeColor(r, g, b); }
void aka_hal_set_color(uint16_t c) { gfx.setColor(c); }
void aka_hal_clear(uint16_t c)     { gfx.clear(c); }
void aka_hal_pixel(int x, int y)   { gfx.drawPixel((int16_t)x, (int16_t)y); }
void aka_hal_hline(int x, int y, int w) { gfx.drawFastHLine((int16_t)x, (int16_t)y, (int16_t)w); }
void aka_hal_vline(int x, int y, int h) { gfx.drawFastVLine((int16_t)x, (int16_t)y, (int16_t)h); }
void aka_hal_line(int x0, int y0, int x1, int y1) { gfx.drawLine((int16_t)x0, (int16_t)y0, (int16_t)x1, (int16_t)y1); }
void aka_hal_rect(int x, int y, int w, int h)      { gfx.drawRect((int16_t)x, (int16_t)y, (int16_t)w, (int16_t)h); }
void aka_hal_fill_rect(int x, int y, int w, int h) { gfx.fillRect((int16_t)x, (int16_t)y, (int16_t)w, (int16_t)h); }
void aka_hal_circle(int x, int y, int r)      { gfx.drawCircle((int16_t)x, (int16_t)y, (int16_t)r); }
void aka_hal_fill_circle(int x, int y, int r) { gfx.fillCircle((int16_t)x, (int16_t)y, (int16_t)r); }
void aka_hal_triangle(int x0, int y0, int x1, int y1, int x2, int y2) {
    gfx.drawTriangle((int16_t)x0, (int16_t)y0, (int16_t)x1, (int16_t)y1, (int16_t)x2, (int16_t)y2);
}
void aka_hal_fill_triangle(int x0, int y0, int x1, int y1, int x2, int y2) {
    gfx.fillTriangle((int16_t)x0, (int16_t)y0, (int16_t)x1, (int16_t)y1, (int16_t)x2, (int16_t)y2);
}
void aka_hal_text(int x, int y, const char *s) { gfx.move_cursor((uint16_t)x, (uint16_t)y); gfx.print_str(s); }
// BUG TROUVE ET CORRIGE (blocage watchdog recurrent, tache principale) :
// rien ne limitait la frequence a laquelle un script Python pouvait
// appeler aka.display() -- gb_config.h documente l'ecran comme limite a
// 35 fps (~28ms/image), mais un script MicroPython sans pacing explicite
// (comme le vrai code source de MrRobot, qui ne fait aucun sleep entre
// deux images) peut appeler display() bien plus vite que le materiel ne
// peut suivre. Chaque appel individuel finit par attendre un signal
// materiel (plusieurs boucles d'attente dans gb_ll_lcd.c/gb_graphics.cpp,
// certaines bornees a 20-40ms, une decouverte non bornee) -- repete assez
// souvent, meme des attentes bornees individuellement peuvent cumuler
// assez de temps perdu pour affamer le chien de garde global (5s).
//
// Fix structurel plutot que d'continuer a corriger chaque boucle une a
// une : impose ICI, au niveau natif (donc quel que soit le script Python
// execute), un intervalle minimum entre deux rafraichissements reels de
// l'ecran -- le jeu peut appeler display() aussi souvent qu'il veut, seul
// le RYTHME REEL envoye au materiel est regule.
#define AKA_MIN_FRAME_INTERVAL_MS 30   // ~33 fps, sous le plafond materiel documente (35 fps)

void aka_hal_display(void) {
    static uint32_t s_last_display_ms = 0;
    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000);
    uint32_t elapsed = now - s_last_display_ms;
    if (s_last_display_ms != 0 && elapsed < AKA_MIN_FRAME_INTERVAL_MS) {
        vTaskDelay(pdMS_TO_TICKS(AKA_MIN_FRAME_INTERVAL_MS - elapsed));
    }
    gfx.update();
    s_last_display_ms = (uint32_t)(esp_timer_get_time() / 1000);
}
int  aka_hal_width(void)  { return SCREEN_WIDTH; }
int  aka_hal_height(void) { return SCREEN_HEIGHT; }

// --- Entrees / frame ---
int aka_hal_update(void) {
    input_poll(g_keys);                    // seul lecteur du bus I2C/ADC
    aka_hal_sound_service();               // relance le son si bouclage demande et termine
    if (!akaRuntime.update(g_keys)) {      // menu systeme AKA a la main ?
        vTaskDelay(pdMS_TO_TICKS(16));
        return 0;
    }
    return 1;
}
uint32_t aka_hal_buttons(void)  { return g_keys.raw; }
uint32_t aka_hal_pressed(void)  { return g_keys.pressed; }
uint32_t aka_hal_released(void) { return g_keys.released; }
void aka_hal_joystick(int *x, int *y) { if (x) *x = g_keys.joxx; if (y) *y = g_keys.joxy; }

// --- Temps / divers ---
uint32_t aka_hal_ticks_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000); }
void aka_hal_sleep_ms(uint32_t ms) {
    TickType_t t = pdMS_TO_TICKS(ms);
    vTaskDelay(t ? t : 1);
}
static uint32_t s_vibrate_start_ms = 0;
static uint32_t s_vibrate_duration_ms = 0;

void aka_hal_vibrate(uint32_t ms) {
    g_audio_player.vibrator(ms);
    s_vibrate_start_ms = (uint32_t)(esp_timer_get_time() / 1000);
    s_vibrate_duration_ms = ms;   // ms=0 (arret) -> is_vibrating() renvoie faux immediatement
}

int aka_hal_is_vibrating(void) {
    if (s_vibrate_duration_ms == 0) return 0;
    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000);
    return (now - s_vibrate_start_ms) < s_vibrate_duration_ms ? 1 : 0;
}

// --- Son (upygame.mixer.Sound) ---
//
// gb_audio_track_wav::play_raw() ne fait que STOCKER le pointeur passe (pas
// de copie) -- le buffer doit donc rester valide pendant toute la lecture.
// On ne peut pas supposer que l'objet `bytes` Python cote appelant restera
// vivant/non deplace par le ramasse-miettes : on COPIE systematiquement les
// echantillons (convertis en 16 bits signe, gb_audio_track_wav l'exige)
// dans un tampon possede ici, redimensionne au besoin.
//
// Pas de bouclage natif dans gb_audio_track_wav (s'arrete tout seul en fin
// de buffer) -- gere ici via aka_hal_sound_service(), appelee a chaque frame
// depuis aka_hal_update().
static gb_audio_track_wav s_sfx_track;
static bool     s_sfx_track_added = false;
static int16_t *s_sfx_buffer = nullptr;
static size_t   s_sfx_buffer_capacity = 0;   // en echantillons
static size_t   s_sfx_sample_count = 0;
static bool     s_sfx_loop = false;

static void aka_hal_sound_ensure_track() {
    if (!s_sfx_track_added) {
        g_audio_player.add_track(&s_sfx_track, 1.0f);
        s_sfx_track_added = true;
    }
}

void aka_hal_play_pcm8(const uint8_t *data, size_t len, int loop) {
    if (!data || len == 0) return;
    aka_hal_sound_ensure_track();

    // (Re)alloue le tampon 16 bits si necessaire -- reutilise sinon (evite
    // de fragmenter le tas a chaque effet sonore).
    if (s_sfx_buffer_capacity < len) {
        int16_t *bigger = (int16_t *)realloc(s_sfx_buffer, len * sizeof(int16_t));
        if (!bigger) return;   // echec allocation : on abandonne silencieusement
        s_sfx_buffer = bigger;
        s_sfx_buffer_capacity = len;
    }

    // Conversion PCM 8 bits NON SIGNE (0..255, 128=silence) -> 16 bits SIGNE
    // (convention gb_audio_track_wav / gb_audio_player).
    for (size_t i = 0; i < len; ++i) {
        s_sfx_buffer[i] = (int16_t)(((int)data[i] - 128) * 256);
    }
    s_sfx_sample_count = len;
    s_sfx_loop = (loop != 0);

    s_sfx_track.play_raw(s_sfx_buffer, s_sfx_sample_count);
}

int aka_hal_is_sound_playing(void) {
    return s_sfx_track_added && s_sfx_track.is_playing() ? 1 : 0;
}

// Appelee a chaque frame (aka_hal_update) : relance la lecture si un
// bouclage a ete demande et que la piste vient de s'arreter.
void aka_hal_sound_service(void) {
    if (s_sfx_track_added && s_sfx_loop && !s_sfx_track.is_playing() && s_sfx_sample_count > 0) {
        s_sfx_track.play_raw(s_sfx_buffer, s_sfx_sample_count);
    }
}
const char *aka_hal_language(void)    { return akaRuntime.getLanguage(); }
const char *aka_hal_tr(const char *k) { return akaRuntime.translate(k); }
int aka_hal_screenshot(void)          { return akaRuntime.takeScreenshot() ? 1 : 0; }

// --- Aide integree au menu systeme ---
// aka_runtime conserve les pointeurs tels quels : on copie donc dans des
// tampons statiques a duree de vie infinie.
#define AKA_MAX_CTRL 12
#define AKA_CTRL_LEN 48
static char        s_ctrl[AKA_MAX_CTRL][AKA_CTRL_LEN];
static const char *s_ctrlPtr[AKA_MAX_CTRL + 1];

void aka_hal_set_controls(const char *const *lines, int n) {
    if (n > AKA_MAX_CTRL) n = AKA_MAX_CTRL;
    for (int i = 0; i < n; ++i) {
        strncpy(s_ctrl[i], lines[i] ? lines[i] : "", AKA_CTRL_LEN - 1);
        s_ctrl[i][AKA_CTRL_LEN - 1] = '\0';
        s_ctrlPtr[i] = s_ctrl[i];
    }
    s_ctrlPtr[n] = nullptr;
    akaRuntime.setControlsKeys(s_ctrlPtr);
}

static char s_cTitle[48], s_cAuthor[48], s_cLicense[32], s_cUrl[80];
void aka_hal_set_credits(const char *title, const char *author,
                         const char *license, const char *url) {
    strncpy(s_cTitle,   title   ? title   : "", sizeof s_cTitle   - 1);   s_cTitle[sizeof s_cTitle - 1]     = '\0';
    strncpy(s_cAuthor,  author  ? author  : "", sizeof s_cAuthor  - 1);   s_cAuthor[sizeof s_cAuthor - 1]   = '\0';
    strncpy(s_cLicense, license ? license : "", sizeof s_cLicense - 1);   s_cLicense[sizeof s_cLicense - 1] = '\0';
    strncpy(s_cUrl,     url     ? url     : "", sizeof s_cUrl     - 1);    s_cUrl[sizeof s_cUrl - 1]         = '\0';
    akaRuntime.setCredits(s_cTitle, s_cAuthor, s_cLicense, s_cUrl);
}
