/* aka_hal_headless.c — couche PC SANS fenêtre du simulateur MicroPython-AKA.
 * Entrées scriptées, horloge virtuelle, capture PPM, arrêt borné : pour les
 * tests automatisés (le jeu Python boucle, donc on borne via AKA_FRAMES).
 *
 * Options via variables d'environnement :
 *   AKA_FRAMES=N        nombre d'appels update() avant de quitter (défaut 300)
 *   AKA_SHOT=f.ppm      écrit le framebuffer en PPM
 *   AKA_SHOT_FRAME=K    frame de capture (défaut : dernière)
 *   AKA_PRESS=a:2:5,... boutons maintenus : nom:de:à (frames d'update)
 */
#include "aka_hal.h"
#include "aka_gfx.h"
#include "aka_keys.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

static int      g_frame = 0;
static int      g_max = -2;          // -2 = non initialisé
static int      g_shot_frame = -1;
static const char *g_shot = NULL;
static int      g_shot_done = 0;

#define MAXP 32
static struct { uint32_t mask; int from, to; } g_press[MAXP];
static int g_np = 0;
static uint32_t g_prev = 0;

static uint32_t name_mask(const char *n) {
    if (!strcasecmp(n, "up")) return AKA_KEY_UP;
    if (!strcasecmp(n, "down")) return AKA_KEY_DOWN;
    if (!strcasecmp(n, "left")) return AKA_KEY_LEFT;
    if (!strcasecmp(n, "right")) return AKA_KEY_RIGHT;
    if (!strcasecmp(n, "a")) return AKA_KEY_A;
    if (!strcasecmp(n, "b")) return AKA_KEY_B;
    if (!strcasecmp(n, "c")) return AKA_KEY_C;
    if (!strcasecmp(n, "d")) return AKA_KEY_D;
    if (!strcasecmp(n, "run")) return AKA_KEY_RUN;
    if (!strcasecmp(n, "menu")) return AKA_KEY_MENU;
    if (!strcasecmp(n, "l1")) return AKA_KEY_L1;
    if (!strcasecmp(n, "r1")) return AKA_KEY_R1;
    return 0;
}

static void init_opts(void) {
    const char *f = getenv("AKA_FRAMES");
    g_max = f ? atoi(f) : 300;
    g_shot = getenv("AKA_SHOT");
    const char *sf = getenv("AKA_SHOT_FRAME");
    g_shot_frame = sf ? atoi(sf) : (g_max > 0 ? g_max - 1 : -1);
    const char *p = getenv("AKA_PRESS");
    if (p && *p) {
        char buf[512]; strncpy(buf, p, sizeof buf - 1); buf[sizeof buf - 1] = 0;
        char *tok = strtok(buf, ",");
        while (tok && g_np < MAXP) {
            char name[16]; int a, b;
            if (sscanf(tok, "%15[a-zA-Z0-9]:%d:%d", name, &a, &b) == 3) {
                g_press[g_np].mask = name_mask(name);
                g_press[g_np].from = a; g_press[g_np].to = b; g_np++;
            }
            tok = strtok(NULL, ",");
        }
    }
}

static uint32_t mask_at(int frame) {
    uint32_t m = 0;
    for (int i = 0; i < g_np; ++i)
        if (frame >= g_press[i].from && frame < g_press[i].to) m |= g_press[i].mask;
    return m;
}

static void write_ppm(void) {
    if (!g_shot || g_shot_done) return;
    FILE *f = fopen(g_shot, "wb");
    if (!f) return;
    fprintf(f, "P6\n%d %d\n255\n", AKA_W, AKA_H);
    uint16_t *fb = aka_gfx_fb();
    for (int i = 0; i < AKA_W * AKA_H; ++i) {
        uint8_t r, g, b; aka_gfx_rgb(fb[i], &r, &g, &b);
        fputc(r, f); fputc(g, f); fputc(b, f);
    }
    fclose(f);
    g_shot_done = 1;
}

static void maybe_end(void) {
    if (g_max < 0) return;
    if (g_shot && g_frame >= g_shot_frame && !g_shot_done) write_ppm();
    if (g_frame >= g_max) { write_ppm(); exit(0); }
}

int aka_hal_update(void) {
    if (g_max == -2) init_opts();
    g_prev = mask_at(g_frame);
    g_frame++;
    maybe_end();
    return 1;
}
void aka_hal_display(void) {
    if (g_max == -2) init_opts();
    if (g_shot && g_frame >= g_shot_frame && !g_shot_done) write_ppm();
}
uint32_t aka_hal_buttons(void) { if (g_max == -2) init_opts(); return mask_at(g_frame); }
uint32_t aka_hal_pressed(void) { return mask_at(g_frame) & ~g_prev; }
uint32_t aka_hal_released(void) { return g_prev & ~mask_at(g_frame); }
void aka_hal_joystick(int *x, int *y) { if (x) *x = 0; if (y) *y = 0; }

uint32_t aka_hal_ticks_ms(void) { return (uint32_t)g_frame * 33u; }   // horloge virtuelle 30 fps
void aka_hal_sleep_ms(uint32_t ms) { (void)ms; }
void aka_hal_vibrate(uint32_t ms) { (void)ms; }
int aka_hal_is_vibrating(void) { return 0; }
const char *aka_hal_language(void) { return "fr"; }
const char *aka_hal_tr(const char *key) { return key; }
int aka_hal_screenshot(void) { return 0; }
void aka_hal_play_pcm8(const uint8_t *d, size_t n, int loop) { (void)d; (void)n; (void)loop; }
int aka_hal_is_sound_playing(void) { return 0; }
void aka_hal_sound_service(void) {}
void aka_hal_set_controls(const char *const *l, int n) { (void)l; (void)n; }
void aka_hal_set_credits(const char *a, const char *b, const char *c, const char *d) { (void)a;(void)b;(void)c;(void)d; }
void aka_hal_receive_code(void) {}
