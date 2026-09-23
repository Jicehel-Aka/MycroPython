# urandom.py — implementation MINIMALE pure Python de getrandbits(), pour ne
# pas dependre d'un module `random`/`urandom` natif dont le nom exact du
# drapeau de configuration n'est pas garanti pour ce build precis.
#
# BUG TROUVE ET CORRIGE : la version precedente utilisait un xorshift32
# classique, avec des masques comme 0xFFFFFFFF (~4,3 milliards) -- largement
# au-dela de la plage "petit entier" de cette configuration MicroPython
# minimale (pas de support des grands entiers active). Meme si ces valeurs
# n'apparaissent que DANS une fonction, MicroPython doit pouvoir les
# REPRESENTER des la compilation du module (donc des l'import), d'ou
# "OverflowError: long int not supported in this build" au tout premier
# "import urandom", avant meme d'appeler quoi que ce soit.
#
# Reecrit autour d'un xorshift 16 bits (toutes les constantes tiennent
# largement dans un petit entier) -- suffisant pour du gameplay (getrandbits
# (7) etc.), pas un usage cryptographique. Plafonne a 16 bits par tirage :
# aucun des jeux vises n'a besoin de plus, et ca evite tout risque de
# recalculer une valeur intermediaire trop grande a l'execution.
import aka

_state = 0

def _next16():
    global _state
    if _state == 0:
        _state = (aka.ticks_ms() & 0xFFFF) | 1   # jamais zero (xorshift bloquerait sinon)
    x = _state
    x ^= (x << 7) & 0xFFFF
    x ^= (x >> 9)
    x ^= (x << 8) & 0xFFFF
    x &= 0xFFFF
    _state = x
    return x

def getrandbits(n):
    """Renvoie un entier de n bits aleatoires (0 <= n <= 16)."""
    if n <= 0:
        return 0
    if n >= 16:
        return _next16()
    return _next16() >> (16 - n)

def seed(n=None):
    """Reinitialise la graine (optionnel -- appele par certains jeux)."""
    global _state
    if n is not None:
        _state = (int(n) & 0xFFFF) or 1
    else:
        _state = (aka.ticks_ms() & 0xFFFF) | 1

def randint(a, b):
    """Entier aleatoire dans [a, b] inclus (pas garanti par tous les jeux,
    fourni par completude)."""
    span = b - a + 1
    if span <= 0:
        return a
    return a + (_next16() % span)

def random():
    """Flottant aleatoire dans [0.0, 1.0) (fourni par completude)."""
    return _next16() / 65536.0
