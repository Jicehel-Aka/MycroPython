/* aka_hal_sdl.c — couche PC FENÊTRÉE (SDL2) du simulateur MicroPython-AKA.
 *
 * Alternative à aka_hal_headless.c : même moteur de rendu logiciel (aka_gfx.c),
 * même main() (main_sim.c), seule la couche « matérielle » change. Elle ouvre
 * une vraie fenêtre, affiche le framebuffer 320x240 mis à l'échelle, lit le
 * clavier (mêmes touches que akalove-play pour rester cohérent entre les deux
 * simulateurs) et joue réellement le son (aka.play_pcm8).
 *
 * Fidèle aux limites AKA : 320x240 RGB565 (packing lcd_color_rgb via aka_gfx),
 * horloge « jeu » virtuelle (un pas de 33 ms par frame, ~30 fps comme la
 * console) cadencée en temps réel, une seule piste d'effet sonore (comme le
 * HAL ESP qui n'a qu'une s_sfx_track pour play_pcm8).
 *
 * Clavier :
 *   Flèches          = D-Pad
 *   Espace / Entrée  = A        X = B        C = C        V = D
 *   Maj gauche = L1              Maj droite = R1
 *   Tab              = MENU (bouton système ; position identique AZERTY/QWERTY)
 *   I J K L          = stick analogique (aka.joystick)
 *   Échap            = quitter
 * On n'utilise JAMAIS SDL_SCANCODE_M pour MENU : SDL lit la POSITION physique,
 * et le M QWERTY tombe sur « , » en AZERTY. Tab est au même endroit partout.
 */
#define SDL_MAIN_HANDLED
#include <SDL.h>

#include "aka_hal.h"
#include "aka_gfx.h"
#include "aka_keys.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- Fenêtre / rendu ----------------------------------------------------- */
static int            g_scale = 2;             /* 320x240 -> 640x480 */
static SDL_Window    *g_win = NULL;
static SDL_Renderer  *g_ren = NULL;
static SDL_Texture   *g_tex = NULL;
static uint32_t       g_rgba[AKA_W * AKA_H];   /* tampon de conversion RGBA8888 */
static int            g_inited = 0;

/* ---- Horloge « jeu » (déterministe, cadencée en temps réel) -------------- */
static uint32_t       g_vclock_ms = 0;
static const uint32_t kFrameMs = 33;           /* ~30 fps, comme la console */

/* ---- Entrées ------------------------------------------------------------- */
static uint32_t       g_buttons = 0;
static uint32_t       g_prev = 0;
static int            g_jx = 1562, g_jy = 1562;  /* centre ~JOYX_MID (plage 0..3125) */

/* ---- Vibration (suivi local, comme le HAL ESP) --------------------------- */
static uint32_t       g_vibrate_end = 0;

/* ---- Audio : une seule piste d'effet (PCM 8 bits non signé -> S16 mono) --- */
static SDL_AudioDeviceID g_audio = 0;
static int16_t       *g_snd = NULL;
static Uint32         g_snd_len = 0;           /* en échantillons */
static Uint32         g_snd_pos = 0;
static int            g_snd_playing = 0;
static int            g_snd_loop = 0;

static void mix_callback(void *u, Uint8 *stream, int bytes) {
    (void)u;
    memset(stream, 0, (size_t)bytes);
    int16_t *out = (int16_t *)stream;
    int n = bytes / (int)sizeof(int16_t);
    if (!g_snd_playing || !g_snd || g_snd_len == 0) return;
    for (int i = 0; i < n; ++i) {
        if (g_snd_pos >= g_snd_len) {
            if (g_snd_loop) g_snd_pos = 0;
            else { g_snd_playing = 0; break; }
        }
        out[i] = g_snd[g_snd_pos++];
    }
}

static void audio_init(void) {
    SDL_AudioSpec want, have;
    SDL_zero(want);
    want.freq = 44100;                 /* = GB_AUDIO_SAMPLE_RATE ; play_raw joue 1:1 */
    want.format = AUDIO_S16SYS;
    want.channels = 1;                 /* le HAL ESP ne gère qu'une piste mono */
    want.samples = 1024;
    want.callback = mix_callback;
    g_audio = SDL_OpenAudioDevice(NULL, 0, &want, &have, 0);
    if (g_audio) SDL_PauseAudioDevice(g_audio, 0);
}

static void sim_init(void) {
    if (g_inited) return;
    g_inited = 1;
    SDL_SetMainReady();
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_EVENTS) != 0) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        exit(1);
    }
    g_win = SDL_CreateWindow("AKA MicroPython (PC)",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        AKA_W * g_scale, AKA_H * g_scale, SDL_WINDOW_SHOWN);
    g_ren = SDL_CreateRenderer(g_win, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    SDL_RenderSetLogicalSize(g_ren, AKA_W, AKA_H);
    g_tex = SDL_CreateTexture(g_ren, SDL_PIXELFORMAT_RGBA8888,
                              SDL_TEXTUREACCESS_STREAMING, AKA_W, AKA_H);
    audio_init();
}

/* ---- Affichage ----------------------------------------------------------- */
void aka_hal_display(void) {
    sim_init();
    const uint16_t *fb = aka_gfx_fb();
    for (int i = 0; i < AKA_W * AKA_H; ++i) {
        uint8_t r, g, b; aka_gfx_rgb(fb[i], &r, &g, &b);
        g_rgba[i] = ((uint32_t)r << 24) | ((uint32_t)g << 16) | ((uint32_t)b << 8) | 0xFFu;
    }
    SDL_UpdateTexture(g_tex, NULL, g_rgba, AKA_W * (int)sizeof(uint32_t));
    SDL_RenderClear(g_ren);
    SDL_RenderCopy(g_ren, g_tex, NULL, NULL);
    SDL_RenderPresent(g_ren);
}

/* ---- Lecture clavier ----------------------------------------------------- */
static void read_keys(void) {
    const Uint8 *k = SDL_GetKeyboardState(NULL);
    uint32_t m = 0;
    if (k[SDL_SCANCODE_UP])    m |= AKA_KEY_UP;
    if (k[SDL_SCANCODE_DOWN])  m |= AKA_KEY_DOWN;
    if (k[SDL_SCANCODE_LEFT])  m |= AKA_KEY_LEFT;
    if (k[SDL_SCANCODE_RIGHT]) m |= AKA_KEY_RIGHT;
    if (k[SDL_SCANCODE_SPACE] || k[SDL_SCANCODE_RETURN]) m |= AKA_KEY_A;
    if (k[SDL_SCANCODE_X])      m |= AKA_KEY_B;
    if (k[SDL_SCANCODE_C])      m |= AKA_KEY_C;
    if (k[SDL_SCANCODE_V])      m |= AKA_KEY_D;
    if (k[SDL_SCANCODE_LSHIFT]) m |= AKA_KEY_L1;
    if (k[SDL_SCANCODE_RSHIFT]) m |= AKA_KEY_R1;
    if (k[SDL_SCANCODE_TAB])    m |= AKA_KEY_MENU;   /* Tab : même position AZERTY/QWERTY */
    g_buttons = m;

    /* Stick analogique émulé (plage 0..3125, centre 1562, Y « haut = grand ») */
    int jx = 1562, jy = 1562;
    if (k[SDL_SCANCODE_L] && !k[SDL_SCANCODE_J]) jx = 3125;
    else if (k[SDL_SCANCODE_J] && !k[SDL_SCANCODE_L]) jx = 0;
    if (k[SDL_SCANCODE_I] && !k[SDL_SCANCODE_K]) jy = 3125;
    else if (k[SDL_SCANCODE_K] && !k[SDL_SCANCODE_I]) jy = 0;
    g_jx = jx; g_jy = jy;
}

/* ---- Frame : entrées + cadence + service son ----------------------------- */
int aka_hal_update(void) {
    sim_init();
    SDL_Event e;
    while (SDL_PollEvent(&e)) {
        if (e.type == SDL_QUIT) { exit(0); }                                  /* fermer la fenêtre */
        if (e.type == SDL_KEYDOWN && e.key.keysym.sym == SDLK_ESCAPE) exit(0); /* Échap = quitter */
    }
    g_prev = g_buttons;
    read_keys();
    aka_hal_sound_service();

    /* Cadence temps réel ~30 fps */
    static Uint64 last = 0;
    Uint64 freq = SDL_GetPerformanceFrequency();
    Uint64 now = SDL_GetPerformanceCounter();
    if (last != 0) {
        double ms = (double)(now - last) * 1000.0 / (double)freq;
        if (ms < (double)kFrameMs) SDL_Delay((Uint32)((double)kFrameMs - ms));
    }
    last = SDL_GetPerformanceCounter();

    g_vclock_ms += kFrameMs;
    return 1;   /* pas de menu système dans le sim : le jeu a toujours la main */
}

uint32_t aka_hal_buttons(void) { return g_buttons; }
uint32_t aka_hal_pressed(void) { return g_buttons & ~g_prev; }
uint32_t aka_hal_released(void) { return g_prev & ~g_buttons; }
void aka_hal_joystick(int *x, int *y) { if (x) *x = g_jx; if (y) *y = g_jy; }

/* ---- Temps / divers ------------------------------------------------------ */
uint32_t aka_hal_ticks_ms(void) { return g_vclock_ms; }
void aka_hal_sleep_ms(uint32_t ms) { SDL_Delay(ms); }
void aka_hal_vibrate(uint32_t ms) { g_vibrate_end = (ms == 0) ? 0 : (g_vclock_ms + ms); }
int  aka_hal_is_vibrating(void) { return (g_vibrate_end != 0 && g_vclock_ms < g_vibrate_end) ? 1 : 0; }
const char *aka_hal_language(void) { const char *e = getenv("AKA_LANG"); return (e && *e) ? e : "fr"; }
const char *aka_hal_tr(const char *key) { return key; }

int aka_hal_screenshot(void) {
    sim_init();
    const uint16_t *fb = aka_gfx_fb();
    for (int i = 0; i < AKA_W * AKA_H; ++i) {
        uint8_t r, g, b; aka_gfx_rgb(fb[i], &r, &g, &b);
        g_rgba[i] = ((uint32_t)r << 24) | ((uint32_t)g << 16) | ((uint32_t)b << 8) | 0xFFu;
    }
    SDL_Surface *s = SDL_CreateRGBSurfaceWithFormatFrom(
        g_rgba, AKA_W, AKA_H, 32, AKA_W * (int)sizeof(uint32_t), SDL_PIXELFORMAT_RGBA8888);
    if (!s) return 0;
    static int n = 0;
    char name[64]; snprintf(name, sizeof name, "screenshot_%03d.bmp", n++);
    int ok = (SDL_SaveBMP(s, name) == 0);
    SDL_FreeSurface(s);
    return ok ? 1 : 0;
}

/* ---- Son (aka.play_pcm8) ------------------------------------------------- */
void aka_hal_play_pcm8(const uint8_t *data, size_t len, int loop) {
    if (!data || len == 0) { sim_init(); return; }
    sim_init();
    int16_t *buf = (int16_t *)malloc(len * sizeof(int16_t));
    if (!buf) return;
    for (size_t i = 0; i < len; ++i)              /* 8 bits non signé (128 = silence) -> S16 */
        buf[i] = (int16_t)(((int)data[i] - 128) * 256);
    SDL_LockAudioDevice(g_audio);
    free(g_snd);
    g_snd = buf; g_snd_len = (Uint32)len; g_snd_pos = 0;
    g_snd_loop = (loop != 0); g_snd_playing = 1;
    SDL_UnlockAudioDevice(g_audio);
}
int aka_hal_is_sound_playing(void) { return g_snd_playing; }
void aka_hal_sound_service(void) { /* bouclage géré dans le callback */ }

/* ---- Menu système : non simulé (jeu toujours actif). On garde néanmoins les
 * renseignements pour un éventuel overlay futur. --------------------------- */
void aka_hal_set_controls(const char *const *lines, int n) { (void)lines; (void)n; }
void aka_hal_set_credits(const char *title, const char *author,
                         const char *license, const char *url) {
    (void)title; (void)author; (void)license; (void)url;
}
void aka_hal_receive_code(void) { /* transfert USB : hors périmètre du sim PC */ }
