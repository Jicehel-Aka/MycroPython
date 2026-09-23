# game8266.py — Couche de compatibilite pour les jeux ecrits a l'origine
# pour le module `game8266` (ESP8266 + OLED SPI 128x64 monochrome, par
# Billy Cheung) -- reimplemente au-dessus du module natif `aka` de l'AKA,
# pour permettre a breakout.py / invader.py / pong.py / snake.py de tourner
# quasiment sans modification.
#
# Resolution logique conservee a 128x64 (celle de l'OLED d'origine, sur
# laquelle toutes les positions/tailles des jeux sont calees en dur) --
# mise a l'echelle vers l'ecran AKA complet (320x240) au moment de
# l'affichage, meme principe que pour les jeux Pokitto (upygame.py).
import aka

LOGICAL_W = 128
LOGICAL_H = 64

_SCALE = min(aka.width() // LOGICAL_W, aka.height() // LOGICAL_H)
if _SCALE < 1:
    _SCALE = 1
_OFFSET_X = (aka.width() - LOGICAL_W * _SCALE) // 2
_OFFSET_Y = (aka.height() - LOGICAL_H * _SCALE) // 2

_COLOR_OFF = (0, 0, 0)       # noir, comme un OLED eteint
_COLOR_ON = (255, 255, 255)  # blanc, comme un OLED allume


def sqrt(x):
    """Racine carree pure Python (methode de Newton) -- le module math
    n'est pas disponible sur cette config MicroPython minimale (verifie
    dans mpconfig.h). Precision largement suffisante pour des calculs de
    physique de jeu (quelques iterations, pas d'usage scientifique)."""
    if x <= 0:
        return 0.0
    guess = x
    for _ in range(12):
        guess = (guess + x / guess) / 2
    return guess


class Rect:
    """Equivalent minimal du Rect pygame utilise par les 4 jeux -- x,y,
    x2,y2 (coin bas-droit inclus), move_ip(), colliderect()."""

    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.x2 = x + w - 1
        self.y2 = y + h - 1

    def move_ip(self, dx, dy):
        self.x += dx
        self.y += dy
        self.x2 += dx
        self.y2 += dy

    def colliderect(self, other):
        return (self.x <= other.x2 and self.x2 >= other.x and
                self.y <= other.y2 and self.y2 >= other.y)


class _Display:
    """Equivalent du framebuffer FrameBuffer1 (SSD1306-like) utilise par
    les jeux d'origine -- fill/rect/fill_rect/text/show, en 0 (eteint) ou
    1 (allume), mis a l'echelle vers l'ecran AKA complet."""

    width = LOGICAL_W
    height = LOGICAL_H

    def _set(self, c):
        # BUG EVITE : c accepte maintenant soit 0/1 (noir/blanc, comme sur
        # l'OLED d'origine) soit un triplet (r,g,b) directement -- l'AKA a
        # un vrai ecran couleur, autant en profiter pour les titres, HUD,
        # et etats particuliers (ex: bateau coule) sans casser la
        # compatibilite avec le code existant qui passe juste 0/1.
        if isinstance(c, tuple):
            r, g, b = c
        else:
            r, g, b = _COLOR_ON if c else _COLOR_OFF
        aka.set_color(r, g, b)

    def fill(self, c):
        # BUG TROUVE ET CORRIGE : n'effacait que la zone logique mise a
        # l'echelle -- si un element se dessine meme legerement hors de
        # cette zone (ex: un projectile a y=64 pile, avant sa suppression
        # au prochain tour), la marque restait affichee DEFINITIVEMENT,
        # plus rien ne repassant jamais dessus. Efface maintenant l'ecran
        # PHYSIQUE entier (bordures comprises), quelle que soit la zone
        # logique -- plus robuste, quelle que soit la source du
        # depassement.
        self._set(c)
        aka.fill_rect(0, 0, aka.width(), aka.height())

    def fill_rect(self, x, y, w, h, c):
        self._set(c)
        aka.fill_rect(_OFFSET_X + x * _SCALE, _OFFSET_Y + y * _SCALE, w * _SCALE, h * _SCALE)

    def rect(self, x, y, w, h, c):
        self._set(c)
        aka.rect(_OFFSET_X + x * _SCALE, _OFFSET_Y + y * _SCALE, w * _SCALE, h * _SCALE)

    def circle(self, x, y, r, c):
        self._set(c)
        aka.circle(_OFFSET_X + x * _SCALE, _OFFSET_Y + y * _SCALE, r * _SCALE)

    def fill_circle(self, x, y, r, c):
        self._set(c)
        aka.fill_circle(_OFFSET_X + x * _SCALE, _OFFSET_Y + y * _SCALE, r * _SCALE)

    def text(self, s, x, y, c):
        self._set(c)
        # Police native aka.text() a taille fixe (non mise a l'echelle,
        # comme pour les jeux Pokitto) -- seule la position l'est, pour que
        # le texte reste lisible plutot que de grossir avec les sprites.
        aka.text(_OFFSET_X + x * _SCALE, _OFFSET_Y + y * _SCALE, s)

    def show(self):
        aka.display()

    def cleanup(self):
        pass


# --- Generation de tonalites (carre, via aka.play_pcm8) --------------------
#
# Les jeux d'origine attendent des playTone()/playSound() SEQUENTIELS,
# audibles les uns apres les autres (ex: plusieurs appels de suite pour un
# petit air de victoire) -- comme aka.play_pcm8() n'est pas bloquant (lu en
# arriere-plan par la tache audio), un appel qui arrive avant la fin du
# precedent l'interromprait. playTone()/playSound() bloquent donc ici via
# aka.sleep_ms(), reproduisant le comportement synchrone d'origine (PWM sur
# l'ESP8266).
_SAMPLE_RATE = 44100

_NOTE_FREQ = {
    "c3": 130.81, "c#3": 138.59, "d3": 146.83, "d#3": 155.56, "e3": 164.81,
    "f3": 174.61, "f#3": 185.00, "g3": 196.00, "g#3": 207.65, "a3": 220.00,
    "a#3": 233.08, "b3": 246.94,
    "c4": 261.63, "c#4": 277.18, "d4": 293.66, "d#4": 311.13, "e4": 329.63,
    "f4": 349.23, "f#4": 369.99, "g4": 392.00, "g#4": 415.30, "a4": 440.00,
    "a#4": 466.16, "b4": 493.88,
    "c5": 523.25, "c#5": 554.37, "d5": 587.33, "d#5": 622.25, "e5": 659.26,
    "f5": 698.46, "f#5": 739.99, "g5": 783.99, "g#5": 830.61, "a5": 880.00,
    "a#5": 932.33, "b5": 987.77,
    "c6": 1046.50, "c#6": 1108.73, "d6": 1174.66, "d#6": 1244.51, "e6": 1318.51,
    "f6": 1396.91, "f#6": 1479.98, "g6": 1567.98, "g#6": 1661.22, "a6": 1760.00,
    "a#6": 1864.66, "b6": 1975.53,
    "c7": 2093.00, "c#7": 2217.46, "d7": 2349.32, "d#7": 2489.02, "e7": 2637.02,
    "f7": 2793.83, "f#7": 2959.96, "g7": 3135.96, "g#7": 3322.44, "a7": 3520.00,
    "a#7": 3729.31, "b7": 3951.07,
}


def _square_wave(freq_hz, duration_ms, amplitude):
    if freq_hz <= 0 or duration_ms <= 0:
        return b""
    n = (_SAMPLE_RATE * duration_ms) // 1000
    period = max(2, int(_SAMPLE_RATE / freq_hz))
    half = period // 2
    lo = 128 - amplitude
    hi = 128 + amplitude
    buf = bytearray(n)
    for i in range(n):
        buf[i] = hi if (i % period) < half else lo
    return bytes(buf)


class Game8266:
    def __init__(self):
        self.display = _Display()
        self.frameRate = 30
        self.max_vol = 4
        self.vol = 3
        self.screenW = LOGICAL_W
        self.screenH = LOGICAL_H

        self.btnU = aka.UP
        self.btnD = aka.DOWN
        self.btnL = aka.LEFT
        self.btnR = aka.RIGHT
        self.btnA = aka.A
        self.btnB = aka.B

        self._pressed_mask = 0
        self._just_pressed_mask = 0
        self._just_released_mask = 0
        self._last_frame_ms = 0
        self.menu_was_open = False

    # --- Entrees ---
    def getBtn(self):
        """Rafraichit l'etat materiel des touches -- a appeler au moins une
        fois par frame (equivalent a aka.update(), gere ici).

        BUG TROUVE ET CORRIGE : la valeur de retour d'aka.update() (qui dit
        si le menu systeme AKA a la main) etait ignoree -- le jeu
        continuait a dessiner PENDANT que le menu etait affiche, d'ou un
        clignotement genant (les deux se redessinaient en alternance).
        getBtn() bloque maintenant tant que le menu est ouvert -- des le
        retour de cet appel, c'est TOUJOURS le jeu qui a la main, sans que
        le code de chaque jeu ait besoin de verifier quoi que ce soit.

        BUG TROUVE ET CORRIGE (suite) : les jeux qui dessinent de facon
        INCREMENTALE (Tetris, Breakout -- pas de fill(0) a chaque frame,
        juste les elements qui changent) restaient avec des restes du menu
        systeme affiches par-dessus apres sa fermeture, puisque rien ne
        force un vrai redessin complet a ce moment precis. self.menu_was_open
        devient True juste apres une fermeture de menu -- a verifier et
        consommer dans les jeux concernes pour forcer un redessin total."""
        self.menu_was_open = False
        while not aka.update():
            self.menu_was_open = True
            aka.sleep_ms(16)
        self._pressed_mask = aka.buttons()
        self._just_pressed_mask = aka.pressed()
        self._just_released_mask = aka.released()

    def pressed(self, mask):
        return bool(self._pressed_mask & mask)

    def justPressed(self, mask):
        return bool(self._just_pressed_mask & mask)

    def justReleased(self, mask):
        return bool(self._just_released_mask & mask)

    def getPaddle(self):
        """Simule une entree analogique 0-1023 (paddle ESP8266) a partir du
        joystick AKA (plage brute mesuree ~0-3125, voir demo aka)."""
        jx, _jy = aka.joystick()
        v = (jx * 1023) // 3125
        if v < 0:
            v = 0
        elif v > 1023:
            v = 1023
        return v

    def setVol(self):
        """Ajuste le volume local (B maintenu + Haut/Bas) -- renvoie True
        si une variation a eu lieu ce tour-ci (le menu des jeux d'origine
        saute alors le traitement des autres touches ce tour-ci)."""
        if self.pressed(self.btnB):
            if self.justPressed(self.btnU) and self.vol < self.max_vol:
                self.vol += 1
                return True
            if self.justPressed(self.btnD) and self.vol > 0:
                self.vol -= 1
                return True
        return False

    # --- Aleatoire ---
    def random(self, a, b):
        if b <= a:
            return a
        import urandom
        return a + urandom.getrandbits(16) % (b - a + 1)

    def sleep_ms(self, ms):
        aka.sleep_ms(ms)

    def ticks_ms(self):
        return aka.ticks_ms()

    def set_controls(self, lines):
        """Personnalise le texte du menu systeme AKA \"Commandes\" pour CE
        jeu (remplace le texte generique par defaut, tant que ce jeu
        tourne). Garder chaque ligne courte (~20 caracteres) -- le cadre
        du menu est etroit, un texte trop long deborde a l'affichage."""
        aka.set_controls(lines)

    # --- Son ---
    def playTone(self, note, duration_ms):
        freq_hz = _NOTE_FREQ.get(note)
        if freq_hz is None:
            return
        self.playSound(freq_hz, duration_ms)

    def playSound(self, freq_hz, duration_ms):
        if self.vol <= 0:
            aka.sleep_ms(duration_ms)
            return
        amplitude = (self.vol * 100) // self.max_vol
        buf = _square_wave(freq_hz, duration_ms, amplitude)
        if buf:
            aka.play_pcm8(buf, False)
        aka.sleep_ms(duration_ms)

    # --- Cadence ---
    def display_and_wait(self):
        self.display.show()
        now = aka.ticks_ms()
        if self._last_frame_ms:
            target = 1000 // self.frameRate if self.frameRate > 0 else 0
            elapsed = now - self._last_frame_ms
            if target > elapsed:
                aka.sleep_ms(target - elapsed)
        self._last_frame_ms = aka.ticks_ms()
