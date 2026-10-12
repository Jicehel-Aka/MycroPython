/* aka_gfx.c — implémentation des fonctions graphiques de aka_hal.h pour le
 * simulateur PC, via un framebuffer logiciel 320x240 RGB565 (packing identique
 * à la console : (r>>3)|((g>>2)<<5)|((b>>3)<<11)). Fidèle au rendu gamebuino :
 * texte font8x8 (bit de poids faible = colonne de gauche, avance de 8 px). */
#include "aka_gfx.h"
#include "aka_hal.h"
#include "font8x8_basic.h"

static uint16_t g_fb[AKA_W * AKA_H];
static uint16_t g_pen = 0xFFFF;

uint16_t *aka_gfx_fb(void) { return g_fb; }

void aka_gfx_rgb(uint16_t c, uint8_t *r, uint8_t *g, uint8_t *b) {
    uint8_t r5 = c & 0x1F, g6 = (c >> 5) & 0x3F, b5 = (c >> 11) & 0x1F;
    *r = (uint8_t)((r5 << 3) | (r5 >> 2));
    *g = (uint8_t)((g6 << 2) | (g6 >> 4));
    *b = (uint8_t)((b5 << 3) | (b5 >> 2));
}

static inline void put(int x, int y) {
    if (x >= 0 && x < AKA_W && y >= 0 && y < AKA_H) g_fb[y * AKA_W + x] = g_pen;
}

uint16_t aka_hal_color(uint8_t r, uint8_t g, uint8_t b) {
    return (uint16_t)((r >> 3) | ((g >> 2) << 5) | ((b >> 3) << 11));
}
void aka_hal_set_color(uint16_t c) { g_pen = c; }
int aka_hal_width(void) { return AKA_W; }
int aka_hal_height(void) { return AKA_H; }

void aka_hal_clear(uint16_t c) {
    for (int i = 0; i < AKA_W * AKA_H; ++i) g_fb[i] = c;
}
void aka_hal_pixel(int x, int y) { put(x, y); }

void aka_hal_hline(int x, int y, int w) {
    if (w < 0) { x += w; w = -w; }
    for (int i = 0; i < w; ++i) put(x + i, y);
}
void aka_hal_vline(int x, int y, int h) {
    if (h < 0) { y += h; h = -h; }
    for (int i = 0; i < h; ++i) put(x, y + i);
}
void aka_hal_line(int x0, int y0, int x1, int y1) {
    int dx = x1 - x0, dy = y1 - y0;
    int sx = dx < 0 ? -1 : 1, sy = dy < 0 ? -1 : 1;
    dx = dx < 0 ? -dx : dx; dy = dy < 0 ? -dy : dy;
    int err = (dx > dy ? dx : -dy) / 2, e2;
    for (;;) {
        put(x0, y0);
        if (x0 == x1 && y0 == y1) break;
        e2 = err;
        if (e2 > -dx) { err -= dy; x0 += sx; }
        if (e2 <  dy) { err += dx; y0 += sy; }
    }
}
void aka_hal_rect(int x, int y, int w, int h) {
    aka_hal_hline(x, y, w); aka_hal_hline(x, y + h - 1, w);
    aka_hal_vline(x, y, h); aka_hal_vline(x + w - 1, y, h);
}
void aka_hal_fill_rect(int x, int y, int w, int h) {
    for (int j = 0; j < h; ++j) aka_hal_hline(x, y + j, w);
}
void aka_hal_circle(int x0, int y0, int r) {
    int x = r, y = 0, err = 1 - r;
    while (x >= y) {
        put(x0 + x, y0 + y); put(x0 + y, y0 + x);
        put(x0 - y, y0 + x); put(x0 - x, y0 + y);
        put(x0 - x, y0 - y); put(x0 - y, y0 - x);
        put(x0 + y, y0 - x); put(x0 + x, y0 - y);
        y++;
        if (err < 0) err += 2 * y + 1;
        else { x--; err += 2 * (y - x) + 1; }
    }
}
void aka_hal_fill_circle(int x0, int y0, int r) {
    for (int y = -r; y <= r; ++y) {
        for (int x = -r; x <= r; ++x)
            if (x * x + y * y <= r * r) put(x0 + x, y0 + y);
    }
}
static void fill_tri(int x0,int y0,int x1,int y1,int x2,int y2){
    int miny = y0 < y1 ? (y0 < y2 ? y0 : y2) : (y1 < y2 ? y1 : y2);
    int maxy = y0 > y1 ? (y0 > y2 ? y0 : y2) : (y1 > y2 ? y1 : y2);
    for (int y = miny; y <= maxy; ++y) {
        int xs[2], n = 0;
        int ex[3] = {x0,x1,x2}, ey[3] = {y0,y1,y2};
        for (int e = 0; e < 3; ++e) {
            int ax = ex[e], ay = ey[e], bx = ex[(e+1)%3], by = ey[(e+1)%3];
            if ((ay <= y && by > y) || (by <= y && ay > y)) {
                int x = ax + (int)((long)(y - ay) * (bx - ax) / (by - ay));
                if (n < 2) xs[n++] = x;
            }
        }
        if (n == 2) { if (xs[0] > xs[1]) { int t = xs[0]; xs[0] = xs[1]; xs[1] = t; }
                      aka_hal_hline(xs[0], y, xs[1] - xs[0] + 1); }
    }
}
void aka_hal_triangle(int x0,int y0,int x1,int y1,int x2,int y2){
    aka_hal_line(x0,y0,x1,y1); aka_hal_line(x1,y1,x2,y2); aka_hal_line(x2,y2,x0,y0);
}
void aka_hal_fill_triangle(int x0,int y0,int x1,int y1,int x2,int y2){
    fill_tri(x0,y0,x1,y1,x2,y2);
}
void aka_hal_text(int x, int y, const char *s) {
    int cx = x, cy = y;
    for (; *s; ++s) {
        unsigned char c = (unsigned char)*s;
        if (c == '\n') { cx = x; cy += 8; continue; }
        if (c == '\r') { cx = x; continue; }
        if (c < 128) {
            const unsigned char *g = (const unsigned char *)font8x8_basic[c];
            for (int dy = 0; dy < 8; ++dy) {
                unsigned char line = g[dy];
                for (int dx = 0; dx < 8; ++dx) {
                    if (line & 1) put(cx + dx, cy + dy);
                    line >>= 1;
                }
            }
        }
        cx += 8;
        if (cx >= AKA_W) { cx = x; cy += 8; }
    }
}
