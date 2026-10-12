/* aka_gfx.h — moteur de rendu logiciel du simulateur PC MicroPython-AKA.
 * Framebuffer 320x240 en RGB565 (même packing que la console : lcd_color_rgb).
 * Implémente les fonctions GRAPHIQUES de aka_hal.h ; les couches headless/SDL
 * ajoutent entrées, temps, audio, display(). */
#ifndef AKA_GFX_H
#define AKA_GFX_H
#include <stdint.h>

#define AKA_W 320
#define AKA_H 240

uint16_t *aka_gfx_fb(void);                 // framebuffer AKA_W*AKA_H (RGB565)
void aka_gfx_rgb(uint16_t c, uint8_t *r, uint8_t *g, uint8_t *b);  // dépacke pour affichage

#endif
