// main.cpp — Point d'entree de l'app AKA "MicroPython".
// Initialise le materiel (ecran, bus, carte SD) et le socle aka_runtime, demarre
// la VM MicroPython puis execute /sdcard/py/main.py. Le module natif `aka`
// (composant micropython) donne au script Python l'acces a l'ecran, aux
// boutons, a l'audio, au temps et a la SD.
#include "gb_core.h"
#include "gb_graphics.h"
#include "gb_audio_player.h"
#include "core/input.h"
#include "aka_runtime/aka_runtime.h"
#include "aka_hal.h"                 // aka_boot_init / aka_boot_exec / aka_hal_set_*

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "esp_heap_caps.h"
#include "esp_log.h"

// Instances globales uniques, partagees avec aka_runtime, input et aka_hal.
gb_core         g_core;
gb_graphics     gfx;
gb_audio_player g_audio_player;

static const char *TAG = "mpy_aka";

// Chemin du script principal execute au demarrage.
#define AKA_MAIN_PY "/sdcard/py/main.py"

// Taille du tas GC MicroPython : de preference en PSRAM (large), repli en RAM
// interne si la PSRAM est absente.
#define AKA_HEAP_PSRAM (2 * 1024 * 1024)
#define AKA_HEAP_INTERNAL (128 * 1024)

static void audio_mix_task(void *) {
    for (;;) {
        g_audio_player.pool();
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

extern "C" void app_main(void) {
    // 1) Materiel : ecran, bus I2C/ADC, expander, CARTE SD (montee ici), audio.
    g_core.init();
    gfx.set_backlight_percent(80);
    gfx.set_refresh_rate(60);
    input_init();

    // 2) Socle AKA : cree /sdcard/micropython/, charge langue + volumes.
    akaRuntime.begin("micropython");
    static auto applyVolume = [](uint8_t musicVol, uint8_t /*sfxVol*/) {
        g_audio_player.set_master_volume((uint8_t)((uint16_t)musicVol * 200 / 100));
    };
    akaRuntime.setVolumeChangedCallback(applyVolume);

    // Aide/credits par defaut (un script .py peut les remplacer via
    // aka.set_controls([...]) / aka.set_credits(...)).
    // BUG TROUVE ET CORRIGE : ce texte par defaut depassait le cadre du
    // menu "Commandes" (boite de 240px, texte a partir de x=52 -- les
    // lignes les plus longues, ex: "MENU (long) : capture ecran", debordaient
    // a l'affichage). Raccourci. De toute facon, chaque jeu (breakout,
    // invader, pong, snake, tetris, puissance4, bataille_navale) definit
    // maintenant ses propres commandes via aka.set_controls([...]) des son
    // demarrage -- ce texte-ci ne sert que de repli, avant qu'un jeu ne
    // soit choisi dans le selecteur.
    static const char *const kControls[] = {
        "Fleches : bouger",
        "A/B : action",
        "MENU : ce menu",
        "RUN+MENU : quitter",
        nullptr
    };
    aka_hal_set_controls(kControls, 4);
    aka_hal_set_credits("MicroPython AKA", "MicroPython + AKA Port Studio",
                        "MIT", "micropython.org");

    g_audio_player.set_master_volume((uint8_t)((uint16_t)akaRuntime.getMusicVolume() * 200 / 100));
    xTaskCreatePinnedToCore(audio_mix_task, "AudioMixTask", 4096, nullptr, 5, nullptr, 1);

    // 3) Tas GC MicroPython.
    size_t heap_size = AKA_HEAP_PSRAM;
    void  *heap = heap_caps_malloc(heap_size, MALLOC_CAP_SPIRAM);
    if (!heap) {
        heap_size = AKA_HEAP_INTERNAL;
        heap = heap_caps_malloc(heap_size, MALLOC_CAP_8BIT);
    }
    ESP_LOGI(TAG, "MicroPython : tas = %u octets @ %p", (unsigned)heap_size, heap);

    // 4) Demarrage de la VM + execution du script principal.
    aka_boot_init(heap, heap_size);
    ESP_LOGI(TAG, "Execution de %s", AKA_MAIN_PY);
    aka_boot_exec(AKA_MAIN_PY);

    // 5) Si le script rend la main (retour de sa boucle), on continue de servir
    // le menu systeme pour que RUN+MENU ramene toujours au loader.
    ESP_LOGW(TAG, "Le script principal s'est termine ; boucle de veille.");
    while (true) {
        input_poll(g_keys);
        akaRuntime.update(g_keys);
        vTaskDelay(pdMS_TO_TICKS(16));
    }
}
