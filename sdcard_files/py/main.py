# main.py — Selecteur de jeu, execute au demarrage par l'app AKA
# MicroPython. Liste tous les jeux presents dans /sdcard/py/, laisse
# choisir avec Haut/Bas, lance le jeu choisi avec A. Quand ce jeu rend la
# main (son propre "Quitter"), revient automatiquement ici.
#
# BUG EVITE : sorted() n'est pas garanti disponible sur cette config
# MicroPython minimale (comme d'autres fonctions "extra" deja rencontrees)
# -- tri manuel simple (insertion) plutot que de risquer une nouvelle
# surprise.
import aka

# BUG TROUVE ET CORRIGE : ce dossier /sdcard/py/ contient aussi les
# modules de compatibilite Pokitto (upygame/umachine/urandom/sprite, chantier
# separe) -- sans cette exclusion, le selecteur aurait tente de les
# "lancer" comme des jeux alors que ce sont de simples modules, sans
# boucle principale (plantage garanti).
_EXCLUDE = ("game8266.py", "main.py",
            "upygame.py", "umachine.py", "urandom.py", "sprite.py")

# Entree synthetique (n'existe pas comme fichier .py) ajoutee en tete de liste :
# ouvre l'ecran "Recevoir un code" (aka.receive_code(), voir components/micropython/
# transfer.cpp) au lieu de lancer un jeu. Meme protocole AKAT que le firmware
# AKA-Love -- voir docs/PROTOCOLE_TRANSFERT.md dans ce depot.
_RECEIVE_CODE = "[Recevoir un code]"


def _sorted_names(names):
    result = []
    for n in names:
        i = 0
        while i < len(result) and result[i] < n:
            i += 1
        result.insert(i, n)
    return result


def list_games():
    all_files = aka.list_py("/sdcard/py")
    games = [f for f in all_files if f not in _EXCLUDE]
    return [_RECEIVE_CODE] + _sorted_names(games)


def display_name(filename):
    if filename == _RECEIVE_CODE:
        return filename
    return filename[:-3] if filename.endswith(".py") else filename


aka.set_controls([
    "Haut/Bas : choisir",
    "A : lancer",
])
aka.set_credits("Selecteur de jeux", "AKA Port Studio", "MIT", "")

sel = 0
games = list_games()

while True:
    if not games:
        aka.update()
        aka.clear(0, 0, 0)
        aka.set_color(255, 255, 255)
        aka.text(10, 40, "Aucun jeu trouve dans")
        aka.text(10, 55, "/sdcard/py/")
        aka.display()
        aka.sleep_ms(200)
        games = list_games()
        continue

    if sel >= len(games):
        sel = 0

    if not aka.update():
        aka.sleep_ms(16)
        continue

    # BUG TROUVE ET CORRIGE : aka.pressed() ne prend AUCUN argument -- elle
    # renvoie le masque binaire complet, a combiner soi-meme avec "&" (voir
    # game8266.py, qui fait ca correctement). Passer aka.UP comme argument
    # ici etait faux.
    p = aka.pressed()
    if (p & aka.UP) and sel > 0:
        sel -= 1
        aka.sleep_ms(120)
    elif (p & aka.DOWN) and sel < len(games) - 1:
        sel += 1
        aka.sleep_ms(120)
    elif p & aka.A:
        if games[sel] == _RECEIVE_CODE:
            aka.receive_code()   # écran plein écran, bloquant jusqu'à MENU (voir transfer.cpp)
            aka.set_controls([
                "Haut/Bas : choisir",
                "A : lancer",
            ])
            games = list_games()
            continue
        aka.clear(0, 0, 0)
        aka.set_color(255, 255, 255)
        aka.text(60, 110, "Chargement...")
        aka.display()
        aka.sleep_ms(300)
        aka.run_file("/sdcard/py/" + games[sel])
        # Le jeu choisi a rendu la main -- redonne au selecteur son propre
        # texte d'aide (le jeu a pu le remplacer via aka.set_controls()).
        aka.set_controls([
            "Haut/Bas : choisir",
            "A : lancer",
        ])
        games = list_games()   # au cas ou la liste aurait change
        continue

    aka.clear(0, 0, 0)
    aka.set_color(255, 220, 0)
    aka.text(80, 5, "Jeux AKA")
    aka.set_color(255, 255, 255)

    y = 25
    for i, fname in enumerate(games):
        if i == sel:
            aka.set_color(255, 220, 0)
            aka.text(65, y, "> " + display_name(fname))
        else:
            aka.set_color(255, 255, 255)
            aka.text(65, y, "  " + display_name(fname))
        y += 15
        if y > 220:
            break

    aka.display()
