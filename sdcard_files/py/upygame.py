# upygame.py — sous-ensemble compatible upygame (API "micro-pygame" de
# Pokitto) implemente en pur Python par-dessus le module natif `aka`.
#
# STATUT : v1, correction avant vitesse. Surface.blit() dessine pixel par
# pixel via aka.pixel()/aka.set_color() (natif, mais appele une fois par
# pixel) -- fonctionnellement correct, mais potentiellement lent pour de
# GRANDS sprites ou BEAUCOUP de sprites par frame. Si les mesures sur
# materiel reel montrent un probleme de fluidite, la prochaine etape est
# d'ajouter une fonction native aka.blit_indexed(x,y,w,h,pixels,palette)
# qui fait tout le travail cote C -- l'API Python ci-dessous n'aurait pas
# a changer, seule l'implementation de Surface.blit() serait remplacee par
# un unique appel natif.
#
# Formats de donnees (verifies sur le code source reel de MrRobot/Pandemic/
# Mars Attack, Hannu Viitala, Pokitto Punk Gamejam + PokittoLib) :
#   - Palette : liste de 16 entiers RGB565 (meme format que
#     display.set_palette_16bit() sur Pokitto).
#   - Pixels de Surface/Tilemap : 4 bits par pixel (indice de palette
#     0-15), 2 pixels par octet, nibble HAUT = premier pixel de la paire
#     -- CONFIRME (pas suppose) : perf_test.py de PokittoLib reference
#     explicitement framebuf.GS4_HMSB (le format standard MicroPython
#     "grayscale 4 bits, nibble haut = bit de poids fort"), meme format
#     que celui utilise ici. Chaque ligne occupe ceil(largeur/2) octets
#     (pas de bourrage si largeur paire).
import aka

# --- Mise a l'echelle ecran ---------------------------------------------
#
# BUG TROUVE ET CORRIGE : le jeu dessine dans les coordonnees natives
# Pokitto (220x176), mais aka.pixel()/aka.fill_rect() etc. dessinent en
# coordonnees ecran AKA BRUTES (320x240) sans aucune mise a l'echelle --
# le jeu n'occupait donc qu'un coin de l'ecran, non agrandi. _SCALE_NUM/
# _SCALE_DEN (fraction plutot que flottant, plus sur en entier pur sur
# MicroPython) etire les coordonnees/tailles des SPRITES vers l'ecran
# complet, en conservant les proportions (plus petit des deux ratios
# largeur/hauteur).
#
# Le TEXTE (draw.text) n'est PAS mis a l'echelle de la meme facon -- seule
# sa POSITION l'est, pas la police elle-meme (aka.text() dessine toujours
# avec la police native, taille fixe) -- sinon le texte grossirait autant
# que les sprites et se chevaucherait encore plus.
POKITTO_W, POKITTO_H = 220, 176
_SCALE_NUM = min(aka.width() * 100 // POKITTO_W, aka.height() * 100 // POKITTO_H)
_SCALE_DEN = 100

def _sx(v):
    return (v * _SCALE_NUM) // _SCALE_DEN

def _sy(v):
    return (v * _SCALE_NUM) // _SCALE_DEN

# --- Constantes d'evenements (memes noms que l'API Pokitto d'origine) -----

NOEVENT = 0
KEYDOWN = 1
KEYUP   = 2

K_UP    = aka.UP
K_DOWN  = aka.DOWN
K_LEFT  = aka.LEFT
K_RIGHT = aka.RIGHT
BUT_A   = aka.A
BUT_B   = aka.B
BUT_C   = aka.C
BUT_D   = aka.D

_ALL_KEYS = (K_UP, K_DOWN, K_LEFT, K_RIGHT, BUT_A, BUT_B, BUT_C, BUT_D)


# --- Rect ------------------------------------------------------------------

class Rect:
    """Rectangle simple, aucune dependance materielle."""

    def __init__(self, x, y=0, w=0, h=0):
        if hasattr(x, "x"):   # Rect(autre_rect)
            other = x
            x, y, w, h = other.x, other.y, other.w, other.h
        elif isinstance(x, (tuple, list)):   # Rect((x,y,w,h))
            x, y, w, h = x[0], x[1], x[2], x[3]
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def width(self):  return self.w
    @property
    def height(self): return self.h
    @property
    def centerx(self): return self.x + self.w // 2
    @property
    def centery(self): return self.y + self.h // 2
    @property
    def left(self):   return self.x
    @property
    def right(self):  return self.x + self.w
    @property
    def top(self):    return self.y
    @property
    def bottom(self): return self.y + self.h

    def colliderect(self, other):
        return (self.x < other.x + other.w and other.x < self.x + self.w and
                self.y < other.y + other.h and other.y < self.y + self.h)

    def __repr__(self):
        # "%d,%d,%d,%d" % (tuple) leve TypeError sur cette config MicroPython
        # minimale -- concatenation simple a la place (cf. umachine.py).
        return "Rect(" + str(self.x) + "," + str(self.y) + "," + str(self.w) + "," + str(self.h) + ")"


# --- Palette globale (16 couleurs, format identique a Pokitto) -------------

_palette_rgb565 = [0] * 16
_palette_rgb8 = [(0, 0, 0)] * 16          # (r,g,b) 0-255, deduit du RGB565
_transparent_index = 0                     # index traite comme transparent par Surface.blit()
_background_index = 0

def _rgb565_to_rgb8(v):
    r5 = (v >> 11) & 0x1F
    g6 = (v >> 5) & 0x3F
    b5 = v & 0x1F
    r8 = (r5 * 255) // 31
    g8 = (g6 * 255) // 63
    b8 = (b5 * 255) // 31
    return (r8, g8, b8)


# --- module display ---------------------------------------------------------

class _Display:
    def init(self, *_args, **_kwargs):
        pass   # aka_hal deja initialise par main.cpp, rien a faire ici

    def set_mode(self, *_args, **_kwargs):
        # BUG TROUVE ET CORRIGE : sur le vrai Pokitto, l'ecran est deja
        # efface au moment de set_mode() -- confirme sur le code source
        # reel de MrRobot, qui ne fait JAMAIS d'effacement lui-meme (juste
        # des screen.blit() de sprites, en supposant un fond deja propre).
        # Sans cet effacement ici, l'ecran AKA garde tout ce qui s'y
        # trouvait avant (ecran de demarrage "Gamebuino"), et le jeu
        # dessine par-dessus sans jamais nettoyer.
        aka.clear(0, 0, 0)
        aka.display()
        return screen

    def set_palette_16bit(self, values):
        global _palette_rgb565, _palette_rgb8
        for i in range(min(16, len(values))):
            _palette_rgb565[i] = values[i]
            _palette_rgb8[i] = _rgb565_to_rgb8(values[i])

    def flip(self):
        aka.display()

display = _Display()


# --- module draw -------------------------------------------------------------

class _Draw:
    def text(self, x, y, s, color_index=3):
        # BUG TROUVE ET CORRIGE : les jeux Pokitto utilisent parfois des
        # caracteres de controle (ex: chr(21) chez MrRobot, "Press "+chr(21)+
        # " to start") comme icones de bouton speciales, dessinees par une
        # police proprietaire Pokitto -- notre police (celle du gamebuino,
        # ASCII standard) ne les comprend pas et les rend comme du vide.
        # Substitution texte lisible pour les codes de controle courants
        # plutot que de laisser un trou dans le texte.
        s = (s.replace(chr(21), "[A]")
              .replace(chr(22), "[B]")
              .replace(chr(23), "[C]")
              .replace(chr(24), "[D]"))
        r, g, b = _palette_rgb8[color_index & 0xF]
        aka.set_color(r, g, b)
        aka.text(_sx(x), _sy(y), s)

    def set_background_color(self, idx):
        global _background_index
        _background_index = idx & 0xF

    def set_transparent_color(self, idx):
        global _transparent_index
        _transparent_index = idx & 0xF

draw = _Draw()


# --- module surface : Surface + blit ----------------------------------------

def _bytes_per_row(width):
    return (width + 1) // 2

def _get_pixel_index(pixels, width, x, y):
    row_bytes = _bytes_per_row(width)
    byte_index = y * row_bytes + (x >> 1)
    b = pixels[byte_index]
    return (b >> 4) & 0xF if (x & 1) == 0 else b & 0xF


class Surface:
    """Sprite/image en couleur indexee 4 bits (meme format que Pokitto).

    Surface(largeur, hauteur, pixels) -- pixels : bytes/bytearray, 4 bits
    par pixel, nibble haut = premier pixel de la paire.
    """

    def __init__(self, width, height, pixels):
        self.width = width
        self.height = height
        self._pixels = pixels

    def get_rect(self):
        return Rect(0, 0, self.width, self.height)

    def fill(self, color_index):
        """Remplit toute la surface avec un indice de palette (methode
        confirmee via perf_test.py de PokittoLib, meme si peu utilisee)."""
        row_bytes = _bytes_per_row(self.width)
        packed = ((color_index & 0xF) << 4) | (color_index & 0xF)
        self._pixels = bytearray([packed]) * (row_bytes * self.height)

    def blit(self, target_x, target_y, transparent=True):
        """Dessine cette surface a l'ecran, coin haut-gauche a
        (target_x, target_y) EN COORDONNEES LOGIQUES POKITTO (220x176) --
        mises a l'echelle vers l'ecran AKA complet (320x240). Les pixels
        dont l'indice de palette vaut _transparent_index sont sautes si
        transparent=True (comportement par defaut, coherent avec les
        sprites Pokitto qui utilisent toujours un fond transparent).

        Chaque pixel LOGIQUE devient un rectangle plein a l'echelle --
        les bornes exactes (debut de ce pixel jusqu'au debut du suivant)
        sont recalculees a chaque fois pour eviter tout trou/chevauchement
        du a l'arrondi (l'echelle n'est pas forcement un nombre entier)."""
        w, h = self.width, self.height
        pixels = self._pixels
        last_idx = -1
        for y in range(h):
            py0 = _sy(target_y + y)
            py1 = _sy(target_y + y + 1)
            ph = py1 - py0
            if ph <= 0:
                ph = 1
            if py0 >= aka.height() or py0 + ph <= 0:
                continue
            for x in range(w):
                idx = _get_pixel_index(pixels, w, x, y)
                if transparent and idx == _transparent_index:
                    continue
                px0 = _sx(target_x + x)
                px1 = _sx(target_x + x + 1)
                pw = px1 - px0
                if pw <= 0:
                    pw = 1
                if px0 >= aka.width() or px0 + pw <= 0:
                    continue
                if idx != last_idx:
                    r, g, b = _palette_rgb8[idx]
                    aka.set_color(r, g, b)
                    last_idx = idx
                aka.fill_rect(px0, py0, pw, ph)


class _SurfaceModule:
    Surface = Surface

surface = _SurfaceModule()


# --- ecran (objet renvoye par display.set_mode(), supporte .blit()) -------

class _Screen:
    def get_rect(self):
        return Rect(0, 0, aka.width(), aka.height())

    def blit(self, source_surface, x, y, transparent=True):
        source_surface.blit(x, y, transparent)

screen = _Screen()


# --- module mixer : Sound ----------------------------------------------------

class Sound:
    def __init__(self, *_args, **_kwargs):
        pass

    def play_sfx(self, data, length=None, loop=False):
        """data : bytes/bytearray PCM 8 bits non signe (0-255, 128=silence).
        length est accepte pour compatibilite avec l'appel Pokitto d'origine
        (sound.play_sfx(data, len(data), True)) mais ignore -- la longueur
        reelle du buffer Python est utilisee directement."""
        aka.play_pcm8(data, loop)

    def is_playing(self):
        return aka.is_sound_playing()

    def stop(self):
        aka.play_pcm8(b"\x80", False)   # relance un tampon silencieux d'1 echantillon = arret de fait


class _Mixer:
    Sound = Sound

mixer = _Mixer()


# --- module event -------------------------------------------------------------

class _Event:
    def __init__(self, etype, key):
        self.type = etype
        self.key = key


class _EventModule:
    def __init__(self):
        self._prev_mask = 0

    def poll(self):
        """Renvoie UN evenement par appel (KEYDOWN/KEYUP), ou NOEVENT s'il
        n'y en a pas en attente. Contrairement a une vraie file d'evenements,
        cette implementation se base sur aka.pressed()/aka.released() (etat
        de la frame courante) -- suffisant pour les jeux Pokitto qui pollent
        une touche a la fois par appel dans leur boucle principale.

        BUG TROUVE ET CORRIGE : les jeux Pokitto (MrRobot compris) n'appellent
        JAMAIS d'equivalent a aka.update() eux-memes -- seulement upygame.
        event.poll(). Sans l'appel a aka.update() ci-dessous, l'etat des
        touches (pressed()/released()) ne se rafraichit JAMAIS, et AUCUNE
        touche n'est plus jamais detectee, quoi qu'il arrive. C'est
        event.poll() lui-meme qui doit rafraichir le materiel, puisque rien
        d'autre dans le code du jeu ne le fait -- coherent avec le fait que
        la vraie API Pokitto gere ca en interne, elle aussi.
        BUG TROUVE ET CORRIGE (traces de sprites, ecran jamais efface entre
        deux images) : le jeu ne dessine jamais de fond, seulement des
        sprites par-dessus (transparent=True) -- sur le vrai Pokitto,
        l'ecran est visiblement efface automatiquement a un moment donne du
        cycle materiel. Comme aucune fonction du jeu n'est appelee une fois
        par frame a part event.poll(), c'est ICI que l'effacement doit se
        faire, avant que le jeu ne redessine ses sprites."""
        if not aka.update():
            return NOEVENT
        aka.clear(0, 0, 0)
        pressed = aka.pressed()
        released = aka.released()
        for k in _ALL_KEYS:
            if pressed & k:
                return _Event(KEYDOWN, k)
        for k in _ALL_KEYS:
            if released & k:
                return _Event(KEYUP, k)
        return NOEVENT

event = _EventModule()
