/* aka_keys.h — Valeurs des bits de touches, SANS dependance aux en-tetes
 * gamebuino/ESP-IDF. Necessaire car modaka.c (glue MicroPython) est aussi
 * pre-traite cote hote lors de la generation des QSTR, ou les en-tetes
 * materiels ne sont pas disponibles. aka_hal.cpp verifie par static_assert
 * que ces valeurs correspondent bien aux EXPANDER_KEY_* du SDK. */
#ifndef AKA_KEYS_H
#define AKA_KEYS_H

#define AKA_KEY_RUN    0x0002
#define AKA_KEY_MENU   0x0004
#define AKA_KEY_R1     0x0040
#define AKA_KEY_L1     0x0080
#define AKA_KEY_RIGHT  0x0100
#define AKA_KEY_UP     0x0200
#define AKA_KEY_DOWN   0x0400
#define AKA_KEY_LEFT   0x0800
#define AKA_KEY_D      0x1000
#define AKA_KEY_B      0x2000
#define AKA_KEY_C      0x4000
#define AKA_KEY_A      0x8000

#endif // AKA_KEYS_H
