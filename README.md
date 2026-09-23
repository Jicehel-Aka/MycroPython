# MicroPython pour l'AKA

App **AKA** (ESP32-S3) qui embarque l'interpréteur **MicroPython** et exécute des
jeux écrits en **Python** (`.py`) depuis la carte SD, via un module natif `aka`
qui expose l'écran, les boutons, l'audio, le temps et la SD.

- 📖 Mode d'emploi utilisateur : **[MANUEL.md](MANUEL.md)** (français) · **[MANUAL.md](MANUAL.md)** (English)
- ⚖️ Licences : code du projet sous [MIT](LICENSE) ; cœur MicroPython sous
  [MIT](LICENSE.micropython) (© 2013-2026 Damien P. George).

---

## Architecture

Chaque application AKA est un firmware ESP-IDF autonome bâti sur les composants
partagés `gamebuino` (matériel) et `aka_runtime` (menu système, langues,
crédits, retour au loader). Ici, l'app **n'est pas un jeu** mais un
**interpréteur** :

```
main/main.cpp          app_main : init matériel + SD, démarre la VM, exécute /sdcard/py/main.py
components/micropython/
  ├─ mpconfigport.h     configuration MicroPython (port « embed »)
  ├─ modaka.c           module natif `aka` (glue Python <-> C, sans dépendance matérielle)
  ├─ aka_hal.h/.cpp     implémentation du binding au-dessus de gamebuino/aka_runtime
  ├─ aka_keys.h         valeurs des touches (partagées, sans dépendance)
  ├─ embed.mk           règle de génération du cœur MicroPython
  └─ micropython_embed/ cœur MicroPython GÉNÉRÉ (non versionné)
components/aka_runtime/  socle commun AKA (copie)
components/gamebuino/     couche matérielle (copie)
sdcard_files/py/main.py  jeu de démonstration (à copier sur la SD)
```

### Pourquoi le port « embed » ?

MicroPython est intégré via son port `embed` (C portable) plutôt que via le port
`esp32`. Avantage : **aucune dépendance à la version d'ESP-IDF**, et on conserve
`app_main` + tout `aka_runtime` (menu système, langues, screenshots, retour
loader). Le module `aka` est volontairement séparé en deux :

- `modaka.c` — glue MicroPython pure. Elle est aussi **pré-traitée côté hôte**
  pendant la génération des QSTR : elle n'inclut donc que les en-têtes `py/…` et
  `aka_hal.h` (sans dépendance matérielle).
- `aka_hal.cpp` — implémentation réelle (gb_graphics, gb_core, aka_runtime),
  compilée uniquement sous ESP-IDF.

---

## Construire et flasher

### Prérequis (poste de dev)

- **ESP-IDF v5.5.x** installé (ici `C:\ESP-IDF`).
- Un checkout **MicroPython** (par défaut `C:\Perso\micropython`) :
  ```bash
  git clone --depth 1 https://github.com/micropython/micropython.git /c/Perso/micropython
  ```
- Pour l'étape de génération : **GNU make**, **gcc** et **python** côté hôte
  (msys2). Aucun besoin de compiler MicroPython côté hôte, seulement de le
  pré-traiter.

### 1. Générer le cœur MicroPython (une fois, puis à chaque changement de config)

```bash
./build_micropython_embed.sh
# ou : MICROPYTHON_TOP=/chemin/vers/micropython ./build_micropython_embed.sh
```

Cela crée `components/micropython/micropython_embed/` (non versionné). À relancer
si tu modifies `mpconfigport.h` ou la liste des fonctions de `modaka.c`.

### 2. Compiler / flasher (environnement ESP-IDF)

```powershell
idf.py build
idf.py -p COMx flash monitor
```

> La table de partitions `partitions.csv` **doit** correspondre au loader AKA
> déjà flashé (partition `loader` en OTA_1). Ne la régénère pas.

### 3. Préparer la carte SD

Copie le dossier `sdcard_files/py/` à la racine de la SD, de sorte que le script
principal soit à **`/sdcard/py/main.py`**. Remplace `main.py` par ton propre jeu.

---

## En bref pour écrire un jeu

```python
import aka

while True:
    if aka.update():                 # sert le menu système AKA + lit les boutons
        aka.clear(0, 0, 0)
        aka.set_color(0, 220, 0)
        aka.fill_circle(160, 120, 20)
        if aka.buttons() & aka.A:
            aka.vibrate(50)
        aka.display()
    aka.sleep_ms(16)
```

La liste complète des fonctions du module `aka` est dans le **[MANUEL](MANUEL.md)**.
