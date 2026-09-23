# bataille_navale.py -- Bataille navale (Battleship), jeu original ecrit
# pour l'AKA, meme style que les autres jeux du dossier py/ (menu,
# boutons, sons via game8266.py). Pas un portage -- construit de zero.
#
# Regles simplifiees : grille 8x8 (plus petite que la version classique
# 10x10, pour rester lisible sur l'ecran), joueur contre IA. Placement des
# bateaux automatique/aleatoire des deux cotes (pas d'interface de
# placement manuel, pour rester simple). Le joueur vise sur la grille de
# droite (ses tirs), l'IA vise automatiquement sur la grille de gauche
# (les bateaux du joueur) apres chaque tour.
from game8266 import Game8266, Rect
g = Game8266()
g.set_controls(["Fleches : viser", "A : tirer", "L : quitter"])

SIZE = 8
SHIPS = [4, 3, 2, 2]   # longueurs des bateaux (4+3+2+2 = 11 cases sur 64)

# BUG TROUVE ET CORRIGE : CELL=6 + GRID_Y=14 faisait toucher le bas de la
# grille EXACTEMENT au bord de l'ecran logique (64px) -- aucune place pour
# le texte de statut, qui se retrouvait ecrit PAR-DESSUS la grille.
# Reduit et replace pour degager une vraie bande de texte en bas.
CELL = 5
GAP = 8
LEFT_X = 4
RIGHT_X = LEFT_X + SIZE * CELL + GAP
GRID_Y = 12

EMPTY = 0
SHIP = 1
HIT = 2
MISS = 3
SUNK = 4

TITLE_COLOR = (255, 220, 0)
HIT_COLOR = (255, 60, 60)
SUNK_COLOR = (120, 120, 120)


def new_grid():
    return [[EMPTY] * SIZE for _ in range(SIZE)]


def can_place(grid, x, y, length, horizontal):
    for i in range(length):
        cx = x + (i if horizontal else 0)
        cy = y + (0 if horizontal else i)
        if cx < 0 or cx >= SIZE or cy < 0 or cy >= SIZE:
            return False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < SIZE and 0 <= ny < SIZE and grid[nx][ny] == SHIP:
                    return False
    return True


def place_ships(grid):
    """Place les bateaux et renvoie la liste des bateaux poses -- chacun
    une liste de cases (x,y) -- necessaire pour detecter individuellement
    quand UN bateau precis est coule (pas juste compter les cases au total)."""
    ships = []
    for length in SHIPS:
        placed = False
        attempts = 0
        while not placed and attempts < 200:
            attempts += 1
            horizontal = g.random(0, 1) == 0
            x = g.random(0, SIZE - 1)
            y = g.random(0, SIZE - 1)
            if can_place(grid, x, y, length, horizontal):
                cells = []
                for i in range(length):
                    cx = x + (i if horizontal else 0)
                    cy = y + (0 if horizontal else i)
                    grid[cx][cy] = SHIP
                    cells.append((cx, cy))
                ships.append(cells)
                placed = True
    return ships


def all_sunk(ships):
    for cells, sunk in ships:
        if not sunk:
            return False
    return True


def find_ship(ships, x, y):
    for i, (cells, sunk) in enumerate(ships):
        if (x, y) in cells:
            return i
    return None


def ship_fully_hit(grid, cells):
    """Equivalent de all(grid[x][y]==HIT for x,y in cells), en boucle
    explicite -- all()+expression generatrice n'est pas garanti disponible
    sur cette config MicroPython minimale (comme d'autres fonctions deja
    rencontrees)."""
    for cx, cy in cells:
        if grid[cx][cy] != HIT:
            return False
    return True


def already_fired(grid, x, y):
    return grid[x][y] in (HIT, MISS, SUNK)


class AI:
    """IA simple : tir aleatoire, avec un mode 'chasse' apres un coup au
    but (essaie les cases voisines jusqu'a couler le bateau)."""

    def __init__(self):
        self.hunt_stack = []

    def choose_target(self, grid):
        while self.hunt_stack:
            x, y = self.hunt_stack.pop()
            if 0 <= x < SIZE and 0 <= y < SIZE and not already_fired(grid, x, y):
                return x, y
        attempts = 0
        while attempts < 500:
            attempts += 1
            x = g.random(0, SIZE - 1)
            y = g.random(0, SIZE - 1)
            if not already_fired(grid, x, y):
                return x, y
        return None

    def report(self, x, y, hit):
        if hit:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                self.hunt_stack.append((x + dx, y + dy))


def draw_grid(grid, ox, oy, show_ships, cursor=None):
    g.display.rect(ox - 1, oy - 1, SIZE * CELL + 1, SIZE * CELL + 1, 1)
    for x in range(SIZE):
        for y in range(SIZE):
            cx = ox + x * CELL
            cy = oy + y * CELL
            v = grid[x][y]
            if v == HIT:
                g.display.fill_rect(cx + 1, cy + 1, CELL - 2, CELL - 2, HIT_COLOR)
            elif v == SUNK:
                g.display.fill_rect(cx + 1, cy + 1, CELL - 2, CELL - 2, SUNK_COLOR)
            elif v == MISS:
                g.display.fill_rect(cx + CELL // 2, cy + CELL // 2, 1, 1, 1)
            elif v == SHIP and show_ships:
                g.display.rect(cx + 1, cy + 1, CELL - 2, CELL - 2, 1)
    if cursor:
        cx = ox + cursor[0] * CELL
        cy = oy + cursor[1] * CELL
        g.display.rect(cx, cy, CELL, CELL, 1)


def draw_screen(player_grid, target_grid, cursor, message):
    g.display.fill(0)
    g.display.text('Bataille Navale', 0, 0, TITLE_COLOR)
    draw_grid(player_grid, LEFT_X, GRID_Y, True)
    draw_grid(target_grid, RIGHT_X, GRID_Y, False, cursor)
    # BUG TROUVE ET CORRIGE : le texte de statut s'ecrivait par-dessus le
    # bas des grilles (voir CELL/GRID_Y ci-dessus) -- bande dediee en bas,
    # desormais sans chevauchement.
    if message:
        g.display.text(message, 2, GRID_Y + SIZE * CELL + 3, (0, 200, 255))
    g.display.show()


def play_one_game():
    player_grid = new_grid()
    target_grid = new_grid()
    player_ships = place_ships(player_grid)
    ai_ships_grid = new_grid()
    ai_ships = place_ships(ai_ships_grid)
    ai = AI()

    # ships : liste de [cellules, coule?] -- mutable pour marquer "coule"
    player_ships = [[cells, False] for cells in player_ships]
    ai_ships = [[cells, False] for cells in ai_ships]

    cursor = [SIZE // 2, SIZE // 2]
    winner = None

    draw_screen(player_grid, target_grid, cursor, "Vise et tire (A)")
    while winner is None:
        g.getBtn()
        moved = False
        if g.justPressed(g.btnL) and cursor[0] > 0:
            cursor[0] -= 1; moved = True
        elif g.justPressed(g.btnR) and cursor[0] < SIZE - 1:
            cursor[0] += 1; moved = True
        elif g.justPressed(g.btnU) and cursor[1] > 0:
            cursor[1] -= 1; moved = True
        elif g.justPressed(g.btnD) and cursor[1] < SIZE - 1:
            cursor[1] += 1; moved = True
        if moved:
            g.playTone('c4', 15)
            draw_screen(player_grid, target_grid, cursor, None)

        if g.justPressed(g.btnA):
            x, y = cursor[0], cursor[1]
            if not already_fired(target_grid, x, y):
                if ai_ships_grid[x][y] == SHIP:
                    target_grid[x][y] = HIT
                    ai_ships_grid[x][y] = HIT
                    g.playTone('e5', 40); g.playTone('c6', 40)
                    # BUG TROUVE ET CORRIGE : rien ne detectait le naufrage
                    # d'UN bateau precis -- juste le decompte global de
                    # cases touchees. Cherche maintenant a QUEL bateau
                    # appartient la case touchee, et verifie si TOUTES ses
                    # cases sont maintenant touchees.
                    ship_idx = find_ship(ai_ships, x, y)
                    ship_cells, _ = ai_ships[ship_idx]
                    if ship_fully_hit(ai_ships_grid, ship_cells):
                        ai_ships[ship_idx][1] = True
                        for cx, cy in ship_cells:
                            target_grid[cx][cy] = SUNK
                        msg = "Coule !"
                        g.playTone('c5', 60); g.playTone('g4', 60)
                    else:
                        msg = "Touche !"
                else:
                    target_grid[x][y] = MISS
                    g.playTone('c4', 60)
                    msg = "Dans l'eau."
                draw_screen(player_grid, target_grid, cursor, msg)
                g.sleep_ms(700)

                if all_sunk(ai_ships):
                    winner = 'player'
                else:
                    draw_screen(player_grid, target_grid, cursor, "L'IA vise...")
                    g.sleep_ms(400)
                    target = ai.choose_target(player_grid)
                    if target:
                        tx, ty = target
                        hit = player_grid[tx][ty] == SHIP
                        if hit:
                            player_grid[tx][ty] = HIT
                            ship_idx = find_ship(player_ships, tx, ty)
                            ship_cells, _ = player_ships[ship_idx]
                            if ship_fully_hit(player_grid, ship_cells):
                                player_ships[ship_idx][1] = True
                                for cx, cy in ship_cells:
                                    player_grid[cx][cy] = SUNK
                                ai_msg = "IA a coule un navire !"
                            else:
                                ai_msg = "IA touche !"
                        else:
                            player_grid[tx][ty] = MISS
                            ai_msg = "IA rate."
                        ai.report(tx, ty, hit)
                        g.playTone('a4', 40) if hit else g.playTone('g3', 60)
                        draw_screen(player_grid, target_grid, cursor, ai_msg)
                        g.sleep_ms(700)
                        if all_sunk(player_ships):
                            winner = 'ai'
                draw_screen(player_grid, target_grid, cursor, None)
        g.sleep_ms(20)

    if winner == 'player':
        msg = "Victoire !"
        g.playTone('c5', 100); g.playTone('e5', 100); g.playTone('g5', 150)
    else:
        msg = "Defaite..."
        g.playTone('g4', 150); g.playTone('e4', 100); g.playTone('c4', 150)
    draw_screen(player_grid, target_grid, cursor, msg)
    g.sleep_ms(2500)


exitGame = False

while not exitGame:
    while True:
        g.display.fill(0)
        g.display.text('Bataille Navale', 0, 0, TITLE_COLOR)
        g.display.rect(90, 10, g.max_vol * 4 + 2, 6, 1)
        g.display.fill_rect(91, 11, g.vol * 4, 4, 1)
        g.display.text('A:Start   L:Quitter', 0, 22, 1)
        g.display.text('Fleches: viser', 0, 34, 1)
        g.display.text('A: tirer', 0, 44, 1)
        g.display.text('B+U/D: volume', 0, 55, (0, 200, 255))
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

    if not exitGame:
        play_one_game()
