// transfer.cpp — réception de fichiers depuis un PC, protocole "AKAT" v1.1 (voir docs/PROTOCOLE_
// TRANSFERT.md du dépôt AKA-Love, qui fait foi pour le format). Portage quasi verbatim de
// components/akalove/transfer.cpp (dépôt AKA-Love, lui testé par 18 contrôles automatiques sur
// simulateur), adapté à aka_hal.h au lieu de la couche hal::/gfx:: d'AKA-Love : mêmes règles, mêmes
// codes de statut, même dialogue de conflit (A: Ecraser, D: Renommer, B: Annuler) -- pensé pour rester
// un protocole UNIQUE, commun à tous les firmwares AKA.
//
// STATUT : écrit et relu avec soin (vérifié en isolation avec `g++ -fsyntax-only` contre le vrai
// aka_hal.h, qui n'a aucune dépendance ESP-IDF/gamebuino), mais JAMAIS COMPILÉ dans le firmware complet
// ni exécuté (pas de simulateur ici, contrairement à AKA-Love) : le premier `idf.py build` est le vrai
// test. Point le plus incertain : la lecture non bloquante de l'entrée standard (mêmes hypothèses que
// hal_aka.cpp du dépôt AKA-Love, jamais vérifiées sur cette carte non plus).
#include "aka_hal.h"
#include "aka_keys.h"
#include "core/input.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {

constexpr uint8_t MAGIC[4] = {'A', 'K', 'A', 'T'};
constexpr uint8_t VERSION = 1;
constexpr uint8_t CMD_PING = 0x01;
constexpr uint8_t CMD_PUT = 0x02;
constexpr uint8_t ST_OK = 0, ST_BAD_LANG = 1, ST_BAD_PATH = 2, ST_CRC_MISMATCH = 3, ST_WRITE_ERROR = 4,
                  ST_TOO_LARGE = 5, ST_OK_RENAMED = 6, ST_CANCELLED = 7;
constexpr uint32_t MAX_PATH = 220, MAX_DATA = 512u * 1024u;
// device_id 1 = MicroPython AKA (0 = AKA-Love, voir PROTOCOLE_TRANSFERT.md) ; un PC qui parle aux deux
// firmwares distingue ainsi lequel a répondu, sans avoir à le deviner autrement.
constexpr uint8_t DEVICE_ID = 1;
// lang_id que CE firmware sait recevoir (le sien) : tout autre lang_id -> BAD_LANG, comme AKA-Love ne
// traite que le lang_id 0. Doit rester en phase avec la ligne "1,py,..." de AKA/languages.csv.
constexpr uint8_t OWN_LANG_ID = 1;
constexpr const char* DEFAULT_SCRIPTS_ROOT = "py";   // repli si AKA/languages.csv est absent/invalide
constexpr uint32_t DECISION_TIMEOUT_MS = 30000;

// --- Entrée/sortie "série" : lecture non bloquante de stdin, écriture sur stdout (même canal que la
// console série utilisée pour idf.py monitor -- voir la remarque de statut en tête de fichier).
int serial_read(uint8_t* buf, int max) {
    static bool nonblock_set = false;
    if (!nonblock_set) {
        int flags = fcntl(0, F_GETFL, 0);
        if (flags >= 0) fcntl(0, F_SETFL, flags | O_NONBLOCK);
        nonblock_set = true;
    }
    int r = (int)read(0, buf, (size_t)max);
    return r > 0 ? r : 0;
}
void serial_write(const uint8_t* buf, int len) { fwrite(buf, 1, (size_t)len, stdout); fflush(stdout); }

bool read_exact(uint8_t* buf, uint32_t n, uint32_t deadline_ms) {
    uint32_t got = 0;
    while (got < n) {
        if (aka_hal_ticks_ms() >= deadline_ms) return false;
        int r = serial_read(buf + got, (int)(n - got));
        if (r > 0) got += (uint32_t)r;
        else aka_hal_sleep_ms(1);
    }
    return true;
}
uint16_t rd_u16(const uint8_t* p) { return (uint16_t)(p[0] | (p[1] << 8)); }
uint32_t rd_u32(const uint8_t* p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
void wr_u16(uint8_t* p, uint16_t v) {
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}

uint32_t crc32(const uint8_t* data, uint32_t len) {
    uint32_t crc = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int b = 0; b < 8; ++b) crc = (crc >> 1) ^ (0xEDB88320u & (uint32_t)(-(int32_t)(crc & 1)));
    }
    return ~crc;
}

void send_reply(uint8_t status) {
    uint8_t out[7] = {MAGIC[0], MAGIC[1], MAGIC[2], MAGIC[3], VERSION, status, DEVICE_ID};
    serial_write(out, (int)sizeof out);
}
void send_reply_renamed(const char* final_rel_path) {
    uint16_t len = (uint16_t)strlen(final_rel_path);
    uint8_t out[7] = {MAGIC[0], MAGIC[1], MAGIC[2], MAGIC[3], VERSION, ST_OK_RENAMED, DEVICE_ID};
    serial_write(out, (int)sizeof out);
    uint8_t lenbuf[2];
    wr_u16(lenbuf, len);
    serial_write(lenbuf, 2);
    serial_write((const uint8_t*)final_rel_path, (int)len);
}

bool safe_rel_path(const char* p, size_t len) {
    if (len == 0 || len >= MAX_PATH) return false;
    if (p[0] == '/' || p[0] == '\\') return false;
    for (size_t i = 0; i < len; ++i) {
        unsigned char c = (unsigned char)p[i];
        if (c < 32 || c == '\\' || c == ':') return false;
        if (p[i] == '.' && p[i + 1] == '.' && (i == 0 || p[i - 1] == '/') && (i + 2 == len || p[i + 2] == '/'))
            return false;
    }
    return true;
}

void mkdir_p(char* path) {   // POSIX (ESP-IDF/FATFS via la VFS) : identique à transfer.cpp d'AKA-Love
    for (char* p = path + 1; *p; ++p)
        if (*p == '/') {
            *p = 0;
            mkdir(path, 0777);
            *p = '/';
        }
    mkdir(path, 0777);
}

bool file_exists(const char* path) {
    struct stat st;
    return stat(path, &st) == 0;
}

// `abs_path` non constant à dessein : on modifie temporairement son dernier '/' en place (comme
// mkdir_p le fait déjà sur son propre argument) au lieu de le recopier dans un tampon séparé -- une
// copie devrait faire au moins aussi grand que le tampon RÉEL de l'appelant (MAX_PATH + 660, voir
// handle_put/find_free_name), que ce fichier n'a aucun moyen de connaître ni de garantir au compilateur.
bool write_file(char* abs_path, const uint8_t* data, uint32_t len) {
    char* slash = strrchr(abs_path, '/');
    if (slash) {
        *slash = 0;
        mkdir_p(abs_path);
        *slash = '/';
    }
    FILE* f = fopen(abs_path, "wb");
    if (!f) return false;
    size_t put = fwrite(data, 1, len, f);
    fclose(f);
    return put == len;
}

// Assemble root + "/" + rel dans out (out_n octets), SANS jamais dépendre de snprintf pour ça : le
// compilateur ESP-IDF (-Werror=format-truncation) ne peut pas prouver qu'un %s/%s tient dans un
// tampon de taille fixe quand root/rel sont eux-mêmes des tampons (pas des litéraux), et à raison —
// root peut dépasser 600 octets une fois placé après un long chemin AKA/languages.csv, rel jusqu'à
// MAX_PATH : un tampon de 790 octets peut réellement déborder, pas seulement déclencher l'avertissement.
// Renvoie false (plutôt que de tronquer en silence) si ça ne tient pas ; l'appelant traite ça comme un
// chemin invalide (BAD_PATH), jamais comme une écriture partielle à un chemin tronqué.
bool join_path(char* out, size_t out_n, const char* root, const char* rel) {
    size_t root_len = strlen(root), rel_len = strlen(rel);
    if (root_len + rel_len + 2 > out_n) return false;   // +1 '/' +1 '\0' ; que des additions, jamais de soustraction sur des size_t
    memcpy(out, root, root_len);
    out[root_len] = '/';
    memcpy(out + root_len + 1, rel, rel_len);
    out[root_len + 1 + rel_len] = '\0';
    return true;
}

bool find_free_name(const char* root, const char* rel, char* out_rel, size_t out_n) {
    char base[MAX_PATH], ext[32] = "";
    snprintf(base, sizeof base, "%s", rel);
    char* dot = strrchr(base, '.');
    char* last_slash = strrchr(base, '/');
    if (dot && (!last_slash || dot > last_slash)) {
        snprintf(ext, sizeof ext, "%s", dot);
        *dot = 0;
    }
    for (int n = 2; n <= 20; ++n) {
        char candidate[MAX_PATH + 40];
        snprintf(candidate, sizeof candidate, "%s (%d)%s", base, n, ext);   // base/ext : tampons fixes connus du compilateur, pas de troncature possible ici
        char abs_path[MAX_PATH + 660];
        if (!join_path(abs_path, sizeof abs_path, root, candidate)) continue;   // ne devrait jamais arriver (candidate < MAX_PATH+40) ; on passe au suivant plutôt que planter
        if (!file_exists(abs_path)) {
            // out_rel (fourni par l'appelant, MAX_PATH octets -- voir handle_put) peut être PLUS PETIT
            // que candidate (MAX_PATH + 40) : le compilateur ne peut pas prouver que le contenu réel
            // tient, à raison -- un candidate légitimement plus long que MAX_PATH doit être écarté, pas
            // tronqué en un nom différent de celui vérifié juste au-dessus par file_exists().
            size_t candidate_len = strlen(candidate);
            if (candidate_len >= out_n) continue;
            memcpy(out_rel, candidate, candidate_len + 1);
            return true;
        }
    }
    return false;
}

bool read_line(FILE* f, char* out, size_t out_n) {
    size_t n = 0;
    int c;
    bool got_any = false;
    while ((c = fgetc(f)) != EOF) {
        got_any = true;
        if (c == '\n') break;
        if (c != '\r' && n + 1 < out_n) out[n++] = (char)c;
    }
    out[n] = 0;
    return got_any;
}

// AKA/languages.csv (racine de la carte SD, PARTAGÉ avec les autres firmwares AKA -- voir
// docs/PROTOCOLE_TRANSFERT.md du dépôt AKA-Love) : ne s'intéresse qu'à la ligne pour OWN_LANG_ID (1).
bool csv_lookup(const char* sd_root, char* out, size_t out_n) {
    char csv_path[790];
    snprintf(csv_path, sizeof csv_path, "%s/AKA/languages.csv", sd_root);
    FILE* f = fopen(csv_path, "r");
    if (!f) return false;
    char line[300];
    bool found = false;
    while (!found && read_line(f, line, sizeof line)) {
        if (line[0] == '#' || line[0] == 0) continue;
        char* p = line;
        long id = strtol(p, &p, 10);
        if (*p != ',' || id < 0 || id > 255) continue;
        ++p;
        char* dir_start = p;
        char* comma = strchr(p, ',');
        if (comma) *comma = 0;
        while (*dir_start == ' ') ++dir_start;
        char* end = dir_start + strlen(dir_start);
        while (end > dir_start && end[-1] == ' ') *--end = 0;
        if ((uint8_t)id == OWN_LANG_ID && dir_start[0] && safe_rel_path(dir_start, strlen(dir_start))) {
            snprintf(out, out_n, "%s", dir_start);
            found = true;
        }
    }
    fclose(f);
    return found;
}

// Racine des scripts MicroPython : "/sdcard/py" par défaut (voir main.cpp, AKA_MAIN_PY), sauf si
// AKA/languages.csv en dit autrement pour le lang_id 1.
const char* resolve_root(char* out, size_t out_n) {
    char csv_dir[MAX_PATH];
    if (csv_lookup("/sdcard", csv_dir, sizeof csv_dir)) {
        snprintf(out, out_n, "/sdcard/%s", csv_dir);
    } else {
        snprintf(out, out_n, "/sdcard/%s", DEFAULT_SCRIPTS_ROOT);
    }
    return out;
}

// --- Écran de conflit : mêmes touches, même délai que l'écran interactif d'AKA-Love (voir transfer.cpp
// de ce dépôt), pour que l'utilisateur qui connaît l'un connaisse l'autre.
void draw_waiting(const char* line1, const char* line2) {
    aka_hal_clear(aka_hal_color(15, 20, 35));
    aka_hal_set_color(aka_hal_color(255, 255, 255));
    aka_hal_text(8, 8, "Recevoir un code");
    aka_hal_text(8, 28, line1);
    if (line2) aka_hal_text(8, 44, line2);
    aka_hal_text(8, 224, "MENU : quitter");
    aka_hal_display();
}
void draw_conflict(const char* rel_path) {
    aka_hal_clear(aka_hal_color(90, 30, 12));
    aka_hal_set_color(aka_hal_color(255, 255, 255));
    aka_hal_text(8, 8, "Ce fichier existe deja :");
    aka_hal_text(8, 24, rel_path);
    aka_hal_text(8, 90, "A : Ecraser");
    aka_hal_text(8, 106, "D : Renommer");
    aka_hal_text(8, 122, "B : Annuler ce fichier");
    aka_hal_display();
}

enum class Decision { Overwrite, Rename, Cancel };

// Lit les boutons DIRECTEMENT (input_poll), sans passer par aka_hal_update()/akaRuntime.update() : cet
// écran est son propre menu plein écran, il ne doit pas laisser le menu système AKA (MENU court, dans
// aka_runtime) prendre la main pendant qu'on attend une réponse.
Decision wait_for_decision(const char* rel_path, uint32_t deadline_ms) {
    input_poll(g_keys);
    uint32_t held = g_keys.raw;
    while (aka_hal_ticks_ms() < deadline_ms) {
        draw_conflict(rel_path);
        input_poll(g_keys);
        uint32_t now = g_keys.raw;
        uint32_t pressed = now & ~held;
        held = now;
        if (pressed & AKA_KEY_A) return Decision::Overwrite;
        if (pressed & AKA_KEY_D) return Decision::Rename;
        if (pressed & AKA_KEY_B) return Decision::Cancel;
        aka_hal_sleep_ms(10);
    }
    return Decision::Cancel;
}

void handle_put(const char* root, uint32_t deadline_ms) {
    uint8_t hdr[3];
    if (!read_exact(hdr, sizeof hdr, deadline_ms)) return;
    uint8_t lang = hdr[0];
    uint16_t path_len = rd_u16(hdr + 1);
    if (path_len == 0 || path_len >= MAX_PATH) {
        send_reply(ST_BAD_PATH);
        return;
    }
    char path[MAX_PATH];
    if (!read_exact((uint8_t*)path, path_len, deadline_ms)) return;
    path[path_len] = 0;
    if (!safe_rel_path(path, path_len)) {
        send_reply(ST_BAD_PATH);
        return;
    }
    if (lang != OWN_LANG_ID) {
        send_reply(ST_BAD_LANG);
        return;
    }

    uint8_t lenbuf[4];
    if (!read_exact(lenbuf, sizeof lenbuf, deadline_ms)) return;
    uint32_t data_len = rd_u32(lenbuf);
    if (data_len > MAX_DATA) {
        send_reply(ST_TOO_LARGE);
        return;
    }
    uint8_t* data = (uint8_t*)malloc(data_len ? data_len : 1);
    if (!data) {
        send_reply(ST_WRITE_ERROR);
        return;
    }
    bool ok = data_len == 0 || read_exact(data, data_len, deadline_ms);
    uint8_t crcbuf[4];
    ok = ok && read_exact(crcbuf, sizeof crcbuf, deadline_ms);
    if (!ok) {
        free(data);
        return;
    }
    if (crc32(data, data_len) != rd_u32(crcbuf)) {
        free(data);
        send_reply(ST_CRC_MISMATCH);
        return;
    }

    char final_rel[MAX_PATH];
    snprintf(final_rel, sizeof final_rel, "%s", path);
    char abs_path[MAX_PATH + 660];
    if (!join_path(abs_path, sizeof abs_path, root, final_rel)) {
        free(data);
        send_reply(ST_BAD_PATH);
        return;
    }

    if (file_exists(abs_path)) {
        Decision d = wait_for_decision(final_rel, aka_hal_ticks_ms() + DECISION_TIMEOUT_MS);
        if (d == Decision::Cancel) {
            free(data);
            send_reply(ST_CANCELLED);
            return;
        }
        if (d == Decision::Rename) {
            char renamed[MAX_PATH];
            if (!find_free_name(root, path, renamed, sizeof renamed)) {
                free(data);
                send_reply(ST_WRITE_ERROR);
                return;
            }
            snprintf(final_rel, sizeof final_rel, "%s", renamed);
            if (!join_path(abs_path, sizeof abs_path, root, final_rel)) {
                free(data);
                send_reply(ST_BAD_PATH);
                return;
            }
        }
    }

    bool wrote = write_file(abs_path, data, data_len);
    free(data);
    if (!wrote) send_reply(ST_WRITE_ERROR);
    else if (strcmp(final_rel, path) != 0) send_reply_renamed(final_rel);
    else send_reply(ST_OK);
}

}  // namespace

void aka_hal_receive_code(void) {
    char root[600];
    resolve_root(root, sizeof root);

    input_poll(g_keys);
    uint8_t sync = 0;
    for (;;) {
        input_poll(g_keys);
        if (g_keys.pressed & AKA_KEY_MENU) return;   // sortie volontaire de l'écran

        char line2[620];
        snprintf(line2, sizeof line2, "-> %s", root);
        draw_waiting("En attente d'un transfert USB...", line2);

        uint8_t b;
        int r = serial_read(&b, 1);
        if (r <= 0) {
            aka_hal_sleep_ms(16);
            continue;
        }
        if (b != MAGIC[sync]) {
            sync = (b == MAGIC[0]) ? 1 : 0;
            continue;
        }
        if (++sync < 4) continue;
        sync = 0;

        uint8_t hdr[2];
        uint32_t deadline = aka_hal_ticks_ms() + 5000;   // en-tête court : 5 s suffisent largement
        if (!read_exact(hdr, sizeof hdr, deadline)) continue;
        if (hdr[0] != VERSION) continue;
        if (hdr[1] == CMD_PING) send_reply(ST_OK);
        else if (hdr[1] == CMD_PUT) handle_put(root, aka_hal_ticks_ms() + 35000);   // corps : jusqu'à 35 s
    }
}
