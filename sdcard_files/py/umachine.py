# umachine.py — sous-ensemble minimal du module `umachine` de Pokitto,
# implemente en pur Python par-dessus le module natif `aka`.
#
# Utilise maintenant open()/with standard (mp_builtin_open() est fournie par
# le port depuis modaka.c -- voir MANUEL.md section 8) plutot que
# aka.file_read()/file_write() (toujours disponibles si besoin, mais open()
# est desormais le chemin normal, coherent avec du code Python standard).
import aka
import sys

def time_ms():
    """Equivalent de umachine.time_ms() (Pokitto) -- simple alias."""
    return aka.ticks_ms()


def _game_dir():
    if sys.path and sys.path[0]:
        return sys.path[0]
    return "/sdcard"   # repli improbable (script sans repertoire dans son chemin)


class Cookie:
    """Sauvegarde persistante simple, un fichier par nom de cookie.

    Usage (identique a l'API Pokitto d'origine) :
        data = bytearray(1)
        c = umachine.Cookie("MONJEU", data)
        c.load()    # remplit data depuis la sauvegarde (si elle existe)
        data[0] = 42
        c.save()    # ecrit data sur la sauvegarde
    """

    def __init__(self, name, buffer):
        self._name = name
        self._buffer = buffer   # le jeu garde sa propre reference vers ce bytearray

    def _path(self):
        # Stocke dans le dossier du jeu (deja cree par akaRuntime au
        # demarrage), determine via sys.path[0] -- pas de dossier dedie a
        # creer separement.
        return _game_dir() + "/cookie_" + self._name + ".dat"

    def load(self):
        """Remplit le buffer depuis la sauvegarde. Ne fait rien (buffer
        inchange) si le fichier n'existe pas encore (premiere partie)."""
        try:
            with open(self._path(), "rb") as f:
                data = f.read(len(self._buffer))
                n = min(len(data), len(self._buffer))
                for i in range(n):
                    self._buffer[i] = data[i]
        except OSError:
            pass   # pas de sauvegarde existante -- comportement normal au premier lancement

    def save(self):
        """Ecrit le buffer courant sur la sauvegarde."""
        try:
            with open(self._path(), "wb") as f:
                f.write(bytes(self._buffer))
        except OSError:
            pass   # echec silencieux (carte pleine/retiree) -- coherent avec le style aka_runtime
