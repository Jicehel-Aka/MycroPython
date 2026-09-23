# puissance4.py -- Puissance 4 (Connect Four), jeu original ecrit pour
# l'AKA, meme style que les autres jeux du dossier py/ (menu, boutons,
# sons via game8266.py). Pas un portage -- construit de zero.
#
# Regles : grille 7 colonnes x 6 lignes, on fait tomber un jeton dans une
# colonne (gravite), premier a aligner 4 jetons (horizontal, vertical ou
# diagonal) gagne. 2 joueurs en local (meme appareil) ou 1 joueur contre
# une IA simple.
from game8266 import Game8266, Rect
g = Game8266()
g.set_controls(["G/D : colonne", "A : jouer", "L : quitter"])

COLS = 7
ROWS = 6
# BUG TROUVE ET CORRIGE : CELL=9 + MARGIN_Y=10 faisait toucher le bas de
# la grille EXACTEMENT au bord de l'ecran logique (64px) -- le texte de
# statut (tour du joueur) se retrouvait ecrit PAR-DESSUS la derniere
# ligne de jetons. Grille reduite pour degager le titre en haut ET une
# bande de texte en dessous (8 titre + 42 grille + 8 message = 58, sur 64
# disponibles).
CELL = 7
MARGIN_X = (g.screenW - COLS * CELL) // 2
MARGIN_Y = 9

EMPTY = 0
P1 = 1
P2 = 2


def new_board():
    return [[EMPTY] * ROWS for _ in range(COLS)]


def drop(board, col, player):
    """Pose un jeton au bas de la colonne col. Renvoie la ligne atteinte,
    ou None si la colonne est pleine."""
    for row in range(ROWS - 1, -1, -1):
        if board[col][row] == EMPTY:
            board[col][row] = player
            return row
    return None


def column_full(board, col):
    return board[col][0] != EMPTY


def board_full(board):
    for col in range(COLS):
        if not column_full(board, col):
            return False
    return True


_DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1))


def check_win(board, col, row, player):
    """Verifie un alignement de 4 passant par (col,row), dans les 4
    directions (chacune comptee dans les deux sens)."""
    for dc, dr in _DIRECTIONS:
        count = 1
        c, r = col + dc, row + dr
        while 0 <= c < COLS and 0 <= r < ROWS and board[c][r] == player:
            count += 1
            c += dc
            r += dr
        c, r = col - dc, row - dr
        while 0 <= c < COLS and 0 <= r < ROWS and board[c][r] == player:
            count += 1
            c -= dc
            r -= dr
        if count >= 4:
            return True
    return False


def ai_choose_column(board, ai_player, human_player):
    """IA simple : gagne si possible, sinon bloque l'adversaire, sinon joue
    une colonne valide au hasard (leger biais vers le centre)."""
    valid = [c for c in range(COLS) if not column_full(board, c)]
    if not valid:
        return None

    # Coup gagnant ?
    for c in valid:
        row = drop(board, c, ai_player)
        won = check_win(board, c, row, ai_player)
        board[c][row] = EMPTY
        if won:
            return c

    # Bloquer l'adversaire ?
    for c in valid:
        row = drop(board, c, human_player)
        would_win = check_win(board, c, row, human_player)
        board[c][row] = EMPTY
        if would_win:
            return c

    # Sinon, prefere le centre (statistiquement meilleur au Puissance 4)
    # BUG EVITE : sorted(..., key=...) n'est pas garanti disponible sur
    # cette config MicroPython minimale -- tri manuel simple (insertion)
    # par distance au centre, comme deja fait ailleurs (voir main.py).
    order = []
    for c in valid:
        dist = abs(c - COLS // 2)
        i = 0
        while i < len(order) and abs(order[i] - COLS // 2) <= dist:
            i += 1
        order.insert(i, c)
    # un peu d'alea parmi les 3 meilleurs choix pour ne pas etre 100% previsible
    top = order[:3] if len(order) >= 3 else order
    return top[g.random(0, len(top) - 1)]


def draw_board(board, cursor_col, message=None):
    g.display.fill(0)
    g.display.text('Puissance 4', 0, 0, (255, 220, 0))
    g.display.rect(MARGIN_X - 1, MARGIN_Y - 1, COLS * CELL + 1, ROWS * CELL + 1, 1)
    for c in range(COLS):
        for r in range(ROWS):
            cx = MARGIN_X + c * CELL + CELL // 2
            cy = MARGIN_Y + r * CELL + CELL // 2
            radius = CELL // 2 - 1
            v = board[c][r]
            if v == P1:
                g.display.fill_circle(cx, cy, radius, (220, 30, 30))
            elif v == P2:
                g.display.fill_circle(cx, cy, radius, (255, 210, 0))
    # curseur : petit triangle au-dessus de la colonne selectionnee
    tri_x = MARGIN_X + cursor_col * CELL + CELL // 2
    g.display.fill_rect(tri_x - 2, MARGIN_Y - 3, 4, 3, (0, 200, 255))

    if message:
        g.display.text(message, 2, MARGIN_Y + ROWS * CELL + 3, (0, 200, 255))
    g.display.show()


def play_one_game(two_players):
    board = new_board()
    cursor = COLS // 2
    turn = P1
    winner = None

    draw_board(board, cursor, "P1: gauche/droite, A")
    while winner is None and not board_full(board):
        if turn == P1 or two_players:
            g.getBtn()
            if g.justPressed(g.btnL) and cursor > 0:
                cursor -= 1
                g.playTone('c4', 20)
            elif g.justPressed(g.btnR) and cursor < COLS - 1:
                cursor += 1
                g.playTone('c4', 20)
            elif g.justPressed(g.btnA):
                if not column_full(board, cursor):
                    row = drop(board, cursor, turn)
                    g.playTone('e5', 30)
                    if check_win(board, cursor, row, turn):
                        winner = turn
                    else:
                        turn = P2 if turn == P1 else P1
            label = "P1: <- ->  A" if turn == P1 else "P2: <- ->  A"
            draw_board(board, cursor, label if winner is None else None)
            g.sleep_ms(30)
        else:
            # Tour de l'IA (joueur 2)
            draw_board(board, cursor, "IA reflechit...")
            g.sleep_ms(300)
            col = ai_choose_column(board, P2, P1)
            if col is not None:
                row = drop(board, col, P2)
                g.playTone('a4', 30)
                cursor = col
                if check_win(board, col, row, P2):
                    winner = P2
                draw_board(board, cursor)
                g.sleep_ms(400)
            turn = P1

    # Ecran de fin
    if winner == P1:
        msg = "Joueur 1 gagne !"
        g.playTone('c5', 100); g.playTone('e5', 100); g.playTone('g5', 150)
    elif winner == P2:
        msg = "Joueur 2 gagne !" if two_players else "L'IA gagne !"
        g.playTone('g4', 150); g.playTone('e4', 100); g.playTone('c4', 150)
    else:
        msg = "Match nul !"
        g.playTone('c4', 100); g.playTone('c4', 100)
    draw_board(board, cursor, msg)
    g.sleep_ms(2500)


exitGame = False
two_players = False

while not exitGame:
    # Menu
    while True:
        g.display.fill(0)
        g.display.text('Puissance 4', 0, 0, (255, 220, 0))
        g.display.rect(90, 0, g.max_vol * 4 + 2, 6, 1)
        g.display.fill_rect(91, 1, g.vol * 4, 4, 1)
        g.display.text('A:Start   L:Quitter', 0, 15, 1)
        g.display.text('D: 2 Joueurs' if two_players else 'D: 1 Joueur (IA)', 0, 28, 1)
        g.display.text('D: option', 0, 40, (0, 200, 255))
        g.display.text('B+U/D: volume', 0, 50, (0, 200, 255))
        g.display.show()

        g.getBtn()
        if g.setVol():
            pass
        elif g.justReleased(g.btnL):
            exitGame = True
            break
        elif g.justPressed(g.btnA):
            break
        elif g.justPressed(g.btnD):
            two_players = not two_players
        g.sleep_ms(10)

    if not exitGame:
        play_one_game(two_players)
