# Mode d'emploi — MicroPython sur l'AKA (français)

Cette app transforme l'AKA en console **programmable en Python**. Tu écris ton
jeu dans un fichier `.py` sur la carte SD, sans recompiler le firmware.

*English version: [MANUAL.md](MANUAL.md).*

---

## 1. Installation

1. Flashe l'app `micropython` sur la console (voir [README.md](README.md)).
2. Copie le dossier `sdcard_files/py/` à la racine de ta carte SD. Le firmware
   exécute au démarrage le fichier **`/sdcard/py/main.py`**.
3. Par défaut, `main.py` est un **sélecteur de jeu** : il liste tous les
   `.py` présents dans `/sdcard/py/` et les lance à la demande (voir §7).
   `demo.py` (dans le même dossier) est un test matériel complet
   (boutons, joystick, vibration) si tu veux vérifier que tout fonctionne.

Au démarrage, l'AKA lance automatiquement `/sdcard/py/main.py`.

---

## 2. Ton premier jeu

```python
import aka

W = aka.width()      # 320
H = aka.height()     # 240
x, y = W // 2, H // 2

while True:
    if aka.update():                    # OBLIGATOIRE une fois par frame
        aka.clear(0, 0, 0)              # efface l'écran en noir

        b = aka.buttons()
        if b & aka.LEFT:  x -= 3
        if b & aka.RIGHT: x += 3
        if b & aka.UP:    y -= 3
        if b & aka.DOWN:  y += 3

        aka.set_color(0, 220, 0)
        aka.fill_circle(x, y, 12)

        aka.display()                   # affiche la frame
    aka.sleep_ms(16)                    # ~60 images/seconde
```

### La boucle de jeu

Une frame se construit toujours ainsi :

1. **`aka.update()`** — à appeler en premier. Lit les boutons **et** laisse le
   menu système AKA prendre la main si le joueur appuie sur MENU. Renvoie `True`
   si ton jeu doit tourner cette frame, `False` pendant que le menu est affiché
   (dans ce cas, ne dessine rien).
2. Dessine (voir §4).
3. **`aka.display()`** — envoie l'image à l'écran.
4. **`aka.sleep_ms(16)`** — cadence.

---

## 3. Les boutons

`aka.buttons()` renvoie un entier : un « masque de bits ». Teste un bouton avec
l'opérateur `&` :

```python
b = aka.buttons()
if b & aka.A:
    tirer()
```

| Constante | Bouton                |
|-----------|-----------------------|
| `aka.UP` `aka.DOWN` `aka.LEFT` `aka.RIGHT` | croix directionnelle |
| `aka.A` `aka.B` `aka.C` `aka.D` | boutons d'action |
| `aka.L1` `aka.R1` | gâchettes |
| `aka.RUN` `aka.MENU` | boutons système |

- `aka.pressed()` — boutons **tout juste enfoncés** cette frame (front montant).
- `aka.released()` — boutons **tout juste relâchés** cette frame.
- `aka.joystick()` — renvoie un tuple `(x, y)` (position analogique).

> RUN + MENU maintenus reviennent toujours au menu de la console (loader) — c'est
> géré automatiquement, tu n'as rien à faire.

---

## 4. Dessiner

L'écran fait **320 × 240** pixels, en couleur. L'origine `(0, 0)` est en haut à
gauche. Les couleurs se donnent en RVB (0-255).

| Fonction | Effet |
|----------|-------|
| `aka.set_color(r, g, b)` | choisit la couleur du « pinceau » courant |
| `aka.color(r, g, b)` | renvoie l'entier couleur (RGB565) sans changer le pinceau |
| `aka.clear()` / `aka.clear(r, g, b)` | efface tout l'écran (noir, ou couleur) |
| `aka.pixel(x, y)` | un pixel |
| `aka.line(x0, y0, x1, y1)` | une ligne |
| `aka.hline(x, y, w)` / `aka.vline(x, y, h)` | ligne horizontale / verticale |
| `aka.rect(x, y, w, h)` / `aka.fill_rect(...)` | rectangle (contour / plein) |
| `aka.circle(x, y, r)` / `aka.fill_circle(...)` | cercle (contour / plein) |
| `aka.triangle(x0,y0,x1,y1,x2,y2)` / `aka.fill_triangle(...)` | triangle |
| `aka.text(x, y, "texte")` | écrit du texte à la couleur courante |
| `aka.display()` | affiche la frame construite |
| `aka.width()` / `aka.height()` | dimensions de l'écran |

---

## 5. Temps, vibration, son, divers

| Fonction | Effet |
|----------|-------|
| `aka.ticks_ms()` | millisecondes depuis le démarrage (entier) |
| `aka.sleep_ms(ms)` | pause (laisse respirer le système) |
| `aka.vibrate(ms)` | fait vibrer la console pendant `ms` millisecondes (`ms=0` arrête immédiatement) |
| `aka.is_vibrating()` | `True` si la console est en train de vibrer |
| `aka.screenshot()` | enregistre une capture d'écran (BMP) sur la SD |
| `aka.language()` | code langue courant de la console (`"fr"`, `"en"`, …) |
| `aka.tr("CLE")` | traduit une clé selon la langue (voir aka_runtime) |
| `aka.play_pcm8(data, loop=False)` | joue un échantillon PCM 8 bits non signé (`bytes`/`bytearray`, 128=silence) |
| `aka.is_sound_playing()` | `True` si un son est en cours de lecture |

`play_pcm8` copie les données en interne (pas besoin de garder l'objet
`bytes` vivant après l'appel) et gère lui-même le rebouclage si `loop=True`.

---

## 6. Aide intégrée au menu système

Quand le joueur appuie sur **MENU**, la console affiche son menu système
(Reprendre, Commandes, Langue, Volume, Crédits, Quitter). Tu peux renseigner
l'écran **« Commandes »** et **« Crédits »** de ton jeu :

```python
aka.set_controls([
    "Fleches : deplacer",
    "A : sauter",
    "B : tirer",
    "MENU : pause",
])
aka.set_credits("Mon Jeu", "Mon Nom", "MIT", "github.com/moi/monjeu")
```

À appeler une fois au début du script. Jusqu'à 12 lignes de commandes.

---

## 7. Le sélecteur de jeu (`main.py`)

`main.py` liste automatiquement tous les fichiers `.py` de `/sdcard/py/`
(sauf `main.py` lui-même et les modules de compatibilité comme
`game8266.py`/`upygame.py`), et les affiche en liste navigable :

```python
jeux = aka.list_py("/sdcard/py")   # liste les fichiers .py d'un dossier
aka.run_file("/sdcard/py/pong.py") # execute un autre script, revient ici a sa fin
```

Haut/Bas pour choisir, A pour lancer. Quand le jeu choisi rend la main (son
propre « Quitter »), le sélecteur réaffiche la liste — aucune recompilation
nécessaire pour ajouter un nouveau jeu, il suffit de copier le `.py` dans
`/sdcard/py/`. Regarde `main.py` fourni pour le code complet ; c'est un bon
point de départ si tu veux personnaliser le tri ou l'affichage.

---

## 8. Écrire un jeu façon arcade avec `game8266.py`

`game8266.py` (dans `sdcard_files/py/`) est une couche de compatibilité
construite pour ce studio, au-dessus du module natif `aka`. Elle réimplémente
l'API `Game8266`/`Rect` d'une collection classique de jeux ESP8266 + OLED
(Billy Cheung — breakout/invader/pong/snake/tetris), et sert aussi de socle
à des jeux originaux (Puissance 4, Bataille navale). Les 7 jeux fournis dans
`sdcard_files/py/` en sont autant d'exemples réutilisables.

### Pourquoi cette couche plutôt que l'API `aka` directement ?

- Résolution logique fixe (128×64, celle de l'OLED d'origine) mise à
  l'échelle automatiquement vers l'écran AKA complet (320×240) — le jeu se
  pense en petites coordonnées, sans se soucier de l'échelle.
- Boutons, son, aléatoire, pause, réunis derrière une API compacte (`g.*`).
- Sept jeux déjà écrits avec, directement copiables comme modèles.

### Structure type d'un jeu

```python
from game8266 import Game8266, Rect
g = Game8266()
g.set_controls(["Fleches : bouger", "A : tirer", "L : quitter"])

exitGame = False
while not exitGame:
    # --- menu ---
    while True:
        g.display.fill(0)
        g.display.text('Mon Jeu', 0, 0, (255, 220, 0))
        g.display.text('A:Start  L:Quitter', 0, 10, 1)
        g.display.show()
        g.getBtn()
        if g.setVol():
            pass
        elif g.justReleased(g.btnL):
            exitGame = True
            break
        elif g.justPressed(g.btnA):
            break
        g.sleep_ms(10)

    if exitGame:
        break

    # --- partie ---
    gameOver = False
    while not gameOver:
        g.display.fill(0)
        g.getBtn()
        if g.pressed(g.btnL):
            pass   # ... logique de jeu ...
        # ... dessin ...
        g.display_and_wait()
```

### API `Game8266` (référence détaillée)

**Affichage (`g.display`)** — coordonnées logiques 128×64, `c` accepte
`0`/`1` (noir/blanc, comme l'OLED d'origine) OU un triplet `(r,g,b)`
directement (l'AKA a un vrai écran couleur, autant s'en servir : titres,
HUD, états particuliers comme un bateau coulé ou une pièce de Tetris) :

- `g.display.fill(c)` — remplit tout l'écran (physique entier, voir plus
  bas) d'une seule couleur. À appeler en tout premier à chaque frame.
- `g.display.rect(x, y, w, h, c)` — rectangle **creux** (juste le contour),
  coin haut-gauche à `(x,y)`.
- `g.display.fill_rect(x, y, w, h, c)` — rectangle **plein**.
- `g.display.circle(x, y, r, c)` — cercle creux, centré sur `(x,y)`, rayon `r`.
- `g.display.fill_circle(x, y, r, c)` — cercle plein.
- `g.display.text(s, x, y, c)` — texte `s` (chaîne), coin haut-gauche du
  texte à `(x,y)`. Police native à taille fixe (non affectée par la mise à
  l'échelle des sprites).
- `g.display.show()` — envoie le tampon dessiné vers l'écran physique
  (équivalent à `aka.display()`). Rien n'apparaît tant que `show()` n'est
  pas appelé.

**Entrées** :

- `g.getBtn()` — à appeler **une fois par frame**, avant toute lecture de
  bouton. Rafraîchit l'état matériel ; bloque en interne tant que le menu
  système AKA est ouvert (voir §3 et « Redessiner après une pause au menu
  système » plus bas), et lève `g.menu_was_open` à `True` juste après une
  fermeture de menu.
- `g.pressed(mask)` — `True` si la touche est actuellement **maintenue**.
- `g.justPressed(mask)` — `True` uniquement sur la frame où la touche
  **vient d'être pressée** (front montant, un seul déclenchement par appui).
- `g.justReleased(mask)` — pareil, mais au **relâchement** (front descendant).
- `g.btnU` / `g.btnD` / `g.btnL` / `g.btnR` / `g.btnA` / `g.btnB` —
  constantes de masque à passer aux trois fonctions ci-dessus.
- `g.getPaddle()` — renvoie un entier `0..1023`, simule un potentiomètre
  analogique (ADC de l'ESP8266 d'origine) à partir de l'axe X du joystick
  réel de l'AKA.

**Son** — les deux fonctions sont **bloquantes** (le son doit finir avant
que le code continue), pour que des enchaînements de notes restent
audibles dans l'ordre plutôt que de s'interrompre les unes les autres :

- `g.playTone(note, duree_ms)` — joue une note nommée (`'c5'`, `'a4'`,
  `'f#3'`...) pendant `duree_ms` millisecondes.
- `g.playSound(freq_hz, duree_ms)` — comme `playTone`, mais avec une
  fréquence directe en Hz plutôt qu'un nom de note.

**Divers** :

- `g.random(a, b)` — entier aléatoire dans `[a, b]` inclus.
- `g.sleep_ms(ms)` — pause de `ms` millisecondes.
- `g.ticks_ms()` — horodatage courant en millisecondes (compteur croissant,
  utile pour mesurer un délai écoulé sans dépendre du rythme des frames).
- `g.frameRate` — cadence cible en images/seconde (variable simple,
  modifiable directement : `g.frameRate = 10`). **Attention** : si ton jeu
  déplace un élément d'une case par frame, `frameRate` devient directement
  ta vitesse de déplacement (voir piège plus bas).
- `g.vol` / `g.max_vol` — volume local courant et maximum (entiers, pour
  affichage d'une barre de volume).
- `g.setVol()` — à appeler dans la boucle : ajuste `g.vol` si Bouton B est
  maintenu + Haut/Bas pressé, et renvoie `True` ce tour-ci si un ajustement
  a eu lieu (pour que l'appelant saute le traitement des autres touches).
- `g.set_controls([...])` — remplace le texte d'aide affiché dans le menu
  système AKA (touche MENU → « Commandes ») par une liste de lignes
  propres à ce jeu. À appeler une fois au démarrage du script.

**Cadence** :

- `g.display_and_wait()` — équivaut à `g.display.show()` suivi d'une pause
  calculée pour respecter `g.frameRate`.

### Pièges déjà rencontrés — à éviter dès le départ

Cette configuration MicroPython est **minimale** : beaucoup de choses
présentes sur un PC ne le sont pas ici. Tout ce qui suit a été découvert en
écrivant les 7 jeux de ce dossier, souvent après un `TypeError`/`NameError`
inattendu sur la console série :

- **Pas de module `math`** : pas de `sqrt()`, etc. Écris ta propre version
  en pur Python si besoin (voir `sqrt()` dans `game8266.py`, méthode de
  Newton, quelques lignes suffisent).
- **`const()`** (courant dans du code MicroPython ESP8266/ESP32) n'est pas
  garanti disponible — ajoute `def const(x): return x` en haut de ton
  fichier par sécurité, ça ne coûte rien si elle existe déjà.
- **`sorted(..., key=...)`** et **`all(... for ... in ...)`** (avec une
  expression génératrice) : évite-les, remplace par une boucle ou un tri
  manuel simple (voir `main.py` ou `puissance4.py` pour des exemples déjà
  écrits).
- **`aka.pressed()` / `aka.released()` / `aka.buttons()` ne prennent AUCUN
  argument** — elles renvoient le masque binaire complet. Écris
  `aka.pressed() & aka.UP`, jamais `aka.pressed(aka.UP)` (erreur facile,
  `TypeError` immédiat — `game8266.py` fait déjà ça correctement si tu
  passes par `g.pressed(...)`).
- **Ne jamais modifier une liste PENDANT qu'on la parcourt** avec
  `for x in maliste: ... maliste.remove(x)` — Python peut alors sauter
  l'élément suivant (jamais testé ce tour-ci). Symptôme typique : « on
  dirait que les tirs traversent les ennemis sans les toucher ». Parcours
  une copie à la place : `for x in maliste[:]: ...`.
- Teste toujours avec `python3 -m py_compile tonfichier.py` sur ton PC
  avant de copier sur la carte SD — ça détecte au moins les erreurs de
  syntaxe sans attendre un redémarrage complet de l'AKA.

### Redessiner après une pause au menu système

`g.getBtn()` bloque en interne tant que le menu système AKA est ouvert
(voir §3) — mais un jeu qui dessine de façon **incrémentale** (efface et
redessine seulement ce qui bouge, pas de `g.display.fill(0)` à chaque
frame — Tetris et Breakout dans ce dossier fonctionnent ainsi) garde des
restes du menu affichés par-dessus une fois celui-ci refermé, puisque rien
ne force un vrai redessin complet à cet instant précis.

`g.getBtn()` expose `g.menu_was_open` (`True` juste après une fermeture de
menu) pour ce cas précis :

```python
g.getBtn()
if g.menu_was_open:
    redraw_all()   # ta propre fonction qui redessine TOUT depuis l'etat courant
```

Si ton jeu fait déjà un `g.display.fill(0)` suivi d'un redessin complet à
CHAQUE frame (la majorité des jeux de ce dossier), tu n'as rien à faire —
le prochain tour de boucle se corrige tout seul.

### La cadence peut être ta vitesse de jeu — piège classique

Si ton jeu déplace un élément d'une case par frame (cas des jeux sur
grille, type Snake), `g.frameRate` **est directement** ta vitesse de
déplacement, pas juste la fluidité visuelle. Avec la valeur par défaut de
`Game8266` (30), ça donne 30 déplacements par seconde — injouable. Fixe un
`g.frameRate` bas et adapté dès le départ (`g.frameRate = 8`, par exemple),
quitte à laisser le joueur l'augmenter ensuite via le menu.

### Croix directionnelle : évite les combinaisons de touches opposées

Une combinaison comme « maintenir Haut ET Bas ensemble » (pour un raccourci
« quitter », par exemple) semble raisonnable en théorie, mais est souvent
**physiquement impossible ou très inconfortable** sur une vraie croix
directionnelle — les deux directions opposées sont rarement accessibles
en même temps avec un seul pouce. Préfère une touche unique et dédiée (`L`
pour quitter, par convention dans ce dossier), y compris en cours de
partie si `L`/`R` sont déjà utilisés pour le déplacement — dans ce cas,
réserve le raccourci à un état où le déplacement est de toute façon
suspendu (l'état pause, par exemple).

### Mise en page : éviter que le HUD chevauche le jeu

Erreur commise (et corrigée) sur presque tous les jeux fournis : placer un
texte de score/titre à une position qui finit par chevaucher le plateau,
une fois la grille dessinée à sa taille réelle. Avant de figer les
dimensions de ton terrain, calcule le budget vertical total : hauteur du
HUD + hauteur du terrain + marge basse ≤ 64 (résolution logique). Réserve
la bande HUD **avant** de dimensionner le reste, pas après coup.

Si ton terrain existe déjà et que sa physique (rebonds, limites) est
calée sur `0..hauteur`, inutile de tout recalculer : garde les coordonnées
de jeu (`bat.y`, `ball.y`...) **relatives au terrain** comme avant, et
ajoute un simple décalage **seulement au moment de dessiner** :

```python
PLAY_TOP = 16   # place reservee au HUD au-dessus du terrain

g.display.fill_rect(bat.x, bat.y + PLAY_TOP, bat_w, bat_h, couleur)
```

La physique ne change pas une seule ligne ; seul l'affichage se décale
(voir `pong.py` pour un exemple complet).

### `fill()` efface tout l'écran physique, pas que la zone logique

`g.display.fill(c)` efface l'écran AKA **entier**, bordures comprises — pas
seulement les 128×64 pixels logiques. C'est volontaire : si un élément se
dessine même légèrement hors de la zone logique (un projectile pile à la
limite du terrain, par exemple, avant sa suppression au tour suivant), il
doit quand même disparaître au prochain `fill()`. Ne pars pas du principe
qu'un effacement partiel suffit si tu réimplémentes ta propre logique
d'affichage par-dessus `aka` directement.

---

## 9. Porter un jeu Python Pokitto (upygame / umachine)

De nombreux jeux Pokitto écrits en MicroPython utilisent une bibliothèque de
compatibilité `pygame`-like, **uPyGame** (`import upygame as pygame` +
`import umachine`), documentée officiellement par Pokitto. Quatre fichiers
fournis dans `sdcard_files/py/` réimplémentent ce sous-ensemble par-dessus le
module `aka` :

Format des données attendu (identique à Pokitto, confirmé via le code
source officiel PokittoLib) : palette de 16 couleurs RGB565 ; pixels de
`Surface` en 4 bits par pixel, indice de palette 0-15, nibble haut =
premier pixel de la paire (format `GS4_HMSB`).

### `upygame.py`

- `Rect(x, y, w, h)` — aussi `Rect(autre_rect)` ou `Rect((x,y,w,h))`.
  Propriétés en lecture seule : `.width`, `.height`, `.centerx`,
  `.centery`, `.left`, `.right`, `.top`, `.bottom`. Méthode
  `.colliderect(autre)`.
- `display.init(...)` — ne fait rien (le matériel est déjà initialisé par
  `main.cpp`), présente pour compatibilité d'appel uniquement.
- `display.set_mode(...)` — efface l'écran et renvoie `screen`. **Important** :
  sur le vrai Pokitto l'écran est déjà propre à cet instant ; la plupart
  des jeux ne l'effacent plus jamais eux-mêmes ensuite.
- `display.set_palette_16bit(valeurs)` — charge une liste de 16 entiers
  RGB565 comme palette active.
- `display.flip()` — envoie le tampon à l'écran (équivalent `aka.display()`).
- `draw.text(x, y, s, color_index=3)` — texte à l'indice de palette donné.
  Substitue automatiquement les caractères de contrôle Pokitto utilisés
  comme icônes de bouton (`chr(21)`→`[A]`, `chr(22)`→`[B]`, etc. — la
  police AKA ne connaît pas la police propriétaire Pokitto).
- `draw.set_background_color(idx)` / `draw.set_transparent_color(idx)` —
  définit l'indice de palette utilisé comme fond / comme couleur
  transparente pour `Surface.blit()`.
- `Surface(largeur, hauteur, pixels)` — sprite en couleur indexée 4 bits.
  `.get_rect()`, `.fill(color_index)`, `.blit(x, y, transparent=True)`
  (dessine à l'écran en coordonnées logiques Pokitto 220×176, mises à
  l'échelle automatiquement — voir §8 pour le principe).
- `screen.get_rect()` / `screen.blit(surface, x, y, transparent=True)` —
  objet renvoyé par `display.set_mode()`.
- `mixer.Sound(...)` — `.play_sfx(data, length=None, loop=False)` (`data` :
  PCM 8 bits non signé, via `aka.play_pcm8`), `.is_playing()`, `.stop()`.
- `event.poll()` — renvoie **un** événement (`KEYDOWN`/`KEYUP`) ou
  `NOEVENT`. **Rafraîchit le matériel en interne** (appelle `aka.update()`
  et efface l'écran) — c'est LA fonction à appeler une fois par frame dans
  ce sous-ensemble, aucun jeu Pokitto n'appelle `aka.update()`
  explicitement de son côté.
- Constantes : `NOEVENT`, `KEYDOWN`, `KEYUP`, `K_UP`/`K_DOWN`/`K_LEFT`/
  `K_RIGHT`, `BUT_A`/`BUT_B`/`BUT_C`/`BUT_D`.

### `umachine.py`

- `time_ms()` — alias de `aka.ticks_ms()`.
- `Cookie(nom, buffer)` — sauvegarde persistante. `buffer` est un
  `bytearray` que le jeu garde et modifie directement.
  - `.load()` — remplit `buffer` depuis la sauvegarde ; ne fait rien si
    elle n'existe pas encore (première partie).
  - `.save()` — écrit `buffer` sur la sauvegarde (dans le dossier du jeu,
    déterminé automatiquement via `sys.path[0]`).

### `urandom.py`

Implémentation pure Python (xorshift 16 bits) — pas de dépendance à un
module natif `random`/`urandom` dont la disponibilité n'est pas garantie
selon le build. Plafonné à 16 bits par tirage (largement suffisant pour du
gameplay, pas un usage cryptographique).

- `getrandbits(n)` — entier de `n` bits aléatoires, `0 <= n <= 16`.
- `randint(a, b)` — entier aléatoire dans `[a, b]` inclus.
- `random()` — flottant dans `[0.0, 1.0)`.
- `seed(n=None)` — réinitialise la graine (`None` = à partir de l'horloge).

### `sprite.py`

Portage quasi-direct du vrai module `sprite.py` de pygame (licence LGPL
préservée), pour les jeux qui utilisent `sprite.Group()`/`sprite.Sprite`.

- `Sprite` — `.add(*groupes)`, `.remove(*groupes)`, `.update(*args)`,
  `.kill()`, `.groups()`, `.alive()`.
- `Group` (et `AbstractGroup`) — `.sprites()`, `.add(*sprites)`,
  `.remove(*sprites)`, `.has(*sprites)`, `.copy()`, `.update(*args)`,
  `.draw(surface)` (appelle `surface.blit()` pour chaque sprite du
  groupe), `.clear(surface, fond)`, `.empty()`.

---

**Statut actuel** : implémentation correcte-avant-rapide (dessin pixel par
pixel via `aka.pixel()`/`aka.fill_rect()`) — fonctionnelle mais
potentiellement lente pour beaucoup de sprites par frame. Si besoin,
l'étape suivante est une fonction native `aka.blit_indexed(...)` qui
ferait tout le travail côté C, sans changer l'API Python vue par les jeux.

Un jeu Pokitto peut ainsi souvent être copié presque tel quel dans
`/sdcard/py/` (ou son propre dossier, voir section suivante), à condition
qu'il n'utilise que ce sous-ensemble de l'API (pas de mode TAS, pas de
`Tilemap`, pas de sprites matériels `setHwSprite` — non couverts pour
l'instant).

---

## 10. Faire d'un jeu Python une app AKA autonome

Par défaut, cette app "MicroPython" exécute `/sdcard/py/main.py` et apparaît
dans le loader AKA comme **un seul jeu générique**. Pour qu'un jeu Python
précis apparaisse **comme sa propre app**, avec sa propre icône et son
propre nom dans le loader (exactement comme un jeu C++ classique) :

1. Copier ce projet entier (composants `micropython`/`aka_runtime`/
   `gamebuino` inclus, **non modifiés**) dans un nouveau dossier de projet.
2. Dans `main/main.cpp`, adapter seulement :
   - `akaRuntime.begin("<id_du_jeu>")` (au lieu de `"micropython"`)
   - `AKA_MAIN_PY "/sdcard/<id_du_jeu>/main.py"` (dossier propre au jeu)
   - `aka_hal_set_credits(...)` / `aka_hal_set_controls(...)` (crédits du jeu)
3. Placer les fichiers `.py` du jeu (plus `upygame.py`/`umachine.py`/
   `urandom.py`/`sprite.py` si besoin) dans `sdcard_files/<id_du_jeu>/`.
4. Donner au projet son propre `port_manifest.json`, `screen.bmp` et
   `meta.json` (voir le dossier `sdcard_files/micropython/` de ce projet
   pour l'exemple du lanceur générique lui-même).

Ce lanceur générique et les lanceurs dédiés coexistent sans conflit — les
fonctions `aka.list_py()`/`aka.run_file()` restent disponibles dans les deux
cas si un jeu veut proposer son propre sous-menu de scripts.

---

## 11. Que faire si… ?

- **Écran figé / rien ne s'affiche** : as-tu appelé `aka.display()` après avoir
  dessiné, et `aka.update()` au début de la frame ?
- **« Fichier .py introuvable »** à l'écran : vérifie que `/sdcard/py/main.py`
  existe bien (dossier `py` à la racine de la SD).
- **Erreur Python** : le message (avec le numéro de ligne) est envoyé sur la
  console série USB — branche l'AKA et ouvre `idf.py monitor` pour le lire.
- **Le jeu rame** : réduis le travail par frame, ou augmente `aka.sleep_ms`.
- **`TypeError: function takes 0 positional arguments but 1 were given`** :
  très probablement `aka.pressed(aka.UP)` au lieu de
  `aka.pressed() & aka.UP` — voir §8.
- **`NameError: name 'X' isn't defined'`** en important un module standard
  (`math`, `random`...) ou en utilisant `const()` : cette build MicroPython
  est minimale, plusieurs fonctionnalités « standard » ne sont pas
  incluses. Vérifie d'abord si `game8266.py` fournit déjà une alternative
  pure Python (ex : `sqrt`), sinon écris la tienne — voir §8.
- **Des traces/résidus graphiques ne s'effacent jamais** : vérifie que tu
  effaces bien l'écran **entier** en début de frame (pas seulement une
  zone partielle) — un élément dessiné même légèrement hors de la zone
  effacée y reste indéfiniment. Voir §8, dernière sous-section.
- **Le score/titre chevauche le terrain de jeu** : le budget vertical
  (HUD + terrain + marge) dépasse probablement la résolution logique
  (128×64 avec `game8266.py`, ou `aka.width()`/`aka.height()` directement).
  Réserve la bande HUD *avant* de dimensionner le reste — voir §8.
