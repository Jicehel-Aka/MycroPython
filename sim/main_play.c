/* main_play.c — point d'entrée du simulateur FENÊTRÉ aka-py-play.
 *
 * Contrairement au binaire sans fenêtre aka-py-sim (main_sim.c, qui exécute UN
 * script et s'arrête), aka-py-play offre un MENU de sélection de programme —
 * comme akalove-play pour le Love2D — pour choisir et CHANGER de .py sans
 * relancer :
 *   - lancé sans argument : menu des .py du dossier courant ;
 *   - lancé avec un .py (ex. depuis AKA-IDE « Tester (PC) ») : exécute ce
 *     script, puis au retour affiche le menu du dossier de ce script ;
 *   - pendant un jeu, Échap revient au menu (indépendant du code du jeu :
 *     aka.update() lève SystemExit, voir modaka.c) ; fermer la fenêtre quitte.
 *
 * Le menu est dessiné avec les mêmes primitives que les jeux (aka_hal_*), donc
 * il profite de la fenêtre SDL et du clavier déjà gérés par aka_hal_sdl.c.
 */
#include "aka_hal.h"
#include "aka_keys.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>

/* Modules de compatibilité, pas des jeux : exclus du menu (comme main.py côté SD). */
static int is_excluded(const char *name) {
    static const char *ex[] = {
        "game8266.py", "upygame.py", "urandom.py", "umachine.py", "sprite.py",
        "main.py",   /* lanceur console, pas un jeu */
        NULL
    };
    for (int i = 0; ex[i]; ++i)
        if (strcmp(name, ex[i]) == 0) return 1;
    return 0;
}

#define MAX_ENTRIES 128
#define NAME_LEN 64

static int list_py(const char *dir, char names[][NAME_LEN], int max) {
    DIR *dp = opendir(dir && *dir ? dir : ".");
    if (!dp) return 0;
    int n = 0;
    struct dirent *e;
    while ((e = readdir(dp)) && n < max) {
        const char *nm = e->d_name;
        size_t len = strlen(nm);
        if (len < 4 || strcmp(nm + len - 3, ".py") != 0) continue;
        if (is_excluded(nm)) continue;
        /* tri par insertion (ordre alphabétique) */
        int i = n;
        while (i > 0 && strcmp(names[i - 1], nm) > 0) {
            memcpy(names[i], names[i - 1], NAME_LEN);
            i--;
        }
        strncpy(names[i], nm, NAME_LEN - 1);
        names[i][NAME_LEN - 1] = 0;
        n++;
    }
    closedir(dp);
    return n;
}

/* Affiche le menu et renvoie l'indice choisi (A), ou -1 si aucun .py. Boucle
 * jusqu'au choix ; la fermeture de la fenêtre quitte l'appli (dans le HAL). */
static int choose(const char *dir, char names[][NAME_LEN], int n) {
    if (n <= 0) {
        for (;;) {
            aka_hal_update();
            aka_hal_menu_requested();            /* consomme Échap (pas de bounce) */
            aka_hal_clear(aka_hal_color(0, 0, 0));
            aka_hal_set_color(aka_hal_color(255, 255, 255));
            aka_hal_text(20, 100, "Aucun programme .py ici.");
            aka_hal_text(20, 116, "Fermez la fenetre pour quitter.");
            aka_hal_display();
        }
    }
    int sel = 0;
    const int VIS = 12;                          /* lignes visibles */
    for (;;) {
        aka_hal_update();
        aka_hal_menu_requested();                /* Échap dans le menu : ignoré */
        uint32_t p = aka_hal_pressed();
        if ((p & AKA_KEY_UP) && sel > 0) sel--;
        if ((p & AKA_KEY_DOWN) && sel < n - 1) sel++;
        if (p & AKA_KEY_A) return sel;

        int top = 0;
        if (sel >= VIS) top = sel - VIS + 1;

        aka_hal_clear(aka_hal_color(8, 10, 24));
        aka_hal_set_color(aka_hal_color(255, 220, 0));
        aka_hal_text(10, 6, "AKA MicroPython - choisir un programme");
        aka_hal_set_color(aka_hal_color(90, 100, 140));
        aka_hal_text(10, 222, "Haut/Bas: choisir   A: lancer   Echap: retour");

        int y = 26;
        for (int i = top; i < n && i < top + VIS; ++i) {
            char line[NAME_LEN + 4];
            size_t L = strlen(names[i]);
            /* enlève le .py pour l'affichage */
            char disp[NAME_LEN];
            strncpy(disp, names[i], NAME_LEN - 1);
            disp[NAME_LEN - 1] = 0;
            if (L > 3) disp[L - 3] = 0;
            if (i == sel) {
                aka_hal_set_color(aka_hal_color(255, 220, 0));
                snprintf(line, sizeof line, "> %s", disp);
            } else {
                aka_hal_set_color(aka_hal_color(220, 220, 230));
                snprintf(line, sizeof line, "  %s", disp);
            }
            aka_hal_text(24, y, line);
            y += 16;
        }
        aka_hal_display();
    }
}

static void dir_of(const char *path, char *out, size_t n) {
    strncpy(out, path, n - 1);
    out[n - 1] = 0;
    char *slash = strrchr(out, '/');
#ifdef _WIN32
    char *bslash = strrchr(out, '\\');
    if (bslash && (!slash || bslash > slash)) slash = bslash;
#endif
    if (slash) *slash = 0;
    else strcpy(out, ".");
}

int main(int argc, char **argv) {
    size_t heap = 1024 * 1024;
    void *p = malloc(heap);
    if (!p) { fprintf(stderr, "oom\n"); return 1; }
    aka_boot_init(p, heap);

    char dir[1024];
    char current[1024] = "";
    if (argc >= 2) {
        strncpy(current, argv[1], sizeof current - 1);
        current[sizeof current - 1] = 0;
        dir_of(argv[1], dir, sizeof dir);
    } else {
        strcpy(dir, ".");
    }

    char names[MAX_ENTRIES][NAME_LEN];

    /* Si un script précis est donné, on l'exécute d'abord ; sinon menu direct. */
    if (current[0] == 0) {
        int n = list_py(dir, names, MAX_ENTRIES);
        int sel = choose(dir, names, n);
        if (sel < 0) return 0;
        snprintf(current, sizeof current, "%s/%s", dir, names[sel]);
    }

    for (;;) {
        aka_boot_exec(current);                  /* tourne jusqu'à SystemExit (Échap) ou fin du script */
        int n = list_py(dir, names, MAX_ENTRIES);
        int sel = choose(dir, names, n);
        if (sel < 0) return 0;
        snprintf(current, sizeof current, "%s/%s", dir, names[sel]);
    }
    return 0;
}
