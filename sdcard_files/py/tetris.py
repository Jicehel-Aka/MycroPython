# tetris.py -- adapte pour l'AKA (ecran 320x240, module aka natif) depuis
# la version originale ESP8266/ESP32 (D1 mini + OLED SPI) de Billy Cheung.
# Toute la logique de jeu (formes, rotation, lignes completes) est
# INCHANGEE -- seule la couche materielle differe.
#
# BUG EVITE : math.sqrt n'est pas disponible sur cette config MicroPython
# minimale -- non utilise ici de toute facon (import present dans
# l'original mais jamais appele), retire silencieusement.
#
# Simplifie : le systeme de musique de fond (bgm/startSong/stopSong, avec
# ses 3 airs entiers encodes note par note) n'existe pas dans game8266.py
# -- feature separee, plus complexe qu'un simple playTone(), non portee ici.
# Le menu "L Music" est retire en consequence (L reste inutilise).
from game8266 import Game8266, Rect
g=Game8266()
g.set_controls(["G/D : bouger", "A/U : pivoter", "B : pause"])

g.frameRate = 30

# size = width, height = 200, 400
# BUG TROUVE ET CORRIGE / AMELIORATION : sqrsize=3 sur 10 colonnes x 20
# lignes rendait chaque bloc minuscule. Grille legerement reduite en
# hauteur (16 lignes au lieu de 20 -- toujours largement jouable) pour
# permettre des blocs 33% plus grands (4px au lieu de 3).
size = width, height = 40, 60
color ={'black': 0, 'white':1}
sqrsize = 4
PREVIEW_X = width + 12   # decale a droite du plateau desormais plus large

# AMELIORATION : une couleur distincte par type de piece, comme dans le
# vrai Tetris (au lieu du blanc unique d'origine, monochrome-only).
SHAPE_COLORS = {
    'S': (60, 220, 60),
    'O': (255, 220, 0),
    'I': (0, 200, 255),
    'L': (255, 140, 0),
    'T': (200, 60, 220),
}
shape_color = (255, 255, 255)
occupied_squares = []
top_of_screen = (2, 2)
top_x, top_y = top_of_screen[0], top_of_screen[1]
num_block = 4
pen_size = 1
mov_delay, r_delay = 200, 50
board_centre = int(width/2)+2
no_move = 0
score = 0
life = 0
shape_blcks = []
shape_name = ""
new_shape_blcks = []
new_shape_name = ""
occupied_squares = []

def reset_board():
    global shape_blcks, shape_name, occupied_squares
    shape_blcks = []
    shape_name = ""
    occupied_squares = []
    g.display.fill(0)
    g.display.rect(top_x-1, top_y-1, width+2, height+2,1)
    # BUG TROUVE ET CORRIGE : le score et le titre etaient positionnes en
    # dur SUR le plateau (x=40, qui touchait desormais son bord droit).
    # Deplaces dans une vraie colonne laterale, a droite du plateau (qui
    # n'utilise que 40px sur les 128 disponibles).
    g.display.text('TETRIS', PREVIEW_X, 2, (255, 220, 0))

def drawScore () :
  global score, life
  g.display.text('S:{}'.format (score), PREVIEW_X, 14, (0, 200, 255))
  g.display.text('L:{}'.format (life), PREVIEW_X, 24, (0, 200, 255))

def redraw_all():
    """Redessine TOUT depuis l'etat courant (plateau + score + piece qui
    tombe), SANS rien reinitialiser -- contrairement a reset_board().
    BUG EVITE : Tetris dessine de facon incrementale (pas de fill(0) a
    chaque frame) -- apres une fermeture du menu systeme AKA, rien ne
    forcait un vrai redessin complet, laissant des restes du menu affiches.
    A appeler quand g.menu_was_open vient de passer a True."""
    g.display.fill(0)
    g.display.rect(top_x-1, top_y-1, width+2, height+2, 1)
    g.display.text('TETRIS', PREVIEW_X, 2, (255, 220, 0))
    drawScore()
    for sqr in occupied_squares:
        g.display.rect(sqr[0], sqr[1], sqrsize, sqrsize, sqr[2])
    draw_shape()
    g.display.show()

def draw_shape():
    '''this draws list of blocks or a block to the background and blits
background to screen'''
    if isinstance(shape_blcks,list):
        for blck in shape_blcks:
            g.display.rect(blck[0], blck[1], sqrsize, sqrsize, shape_color)
    else:
        g.display.rect(shape_blcks[0], shape_blcks[1], sqrsize, sqrsize, shape_color)

def _cell_occupied(x, y):
    """Renvoie True si (x,y) est occupee, sans tenir compte de la couleur
    (occupied_squares stocke maintenant des triplets (x,y,couleur) --
    "in occupied_squares" exigerait une correspondance EXACTE, couleur
    comprise, ce qui casserait la detection)."""
    for sqr in occupied_squares:
        if sqr[0] == x and sqr[1] == y:
            return True
    return False


def row_filled(row_no):
    global occupied_squares
    '''check if a row is fully occupied by a shape block'''
    for x_coord in range(top_x, width+top_x, sqrsize):
        if _cell_occupied(x_coord, row_no):
            continue
        else:
            return False
    return True

def delete_row(row_no):
    '''removes all squares on a row from the occupied_squares list and then
moves all square positions which have y-axis coord less than row_no down
board'''
    global occupied_squares
    g.display.fill(0)
    g.display.rect(top_x-1, top_y-1, width+2, height+2,1)
    new_buffer = []
    x_coord, y_coord = 0, 1
    for sqr in occupied_squares:
        if sqr[y_coord] != row_no:
            new_buffer.append(sqr)
    occupied_squares = new_buffer
    for index in range(len(occupied_squares)):
        if occupied_squares[index][y_coord] < row_no:
            occupied_squares[index] = (occupied_squares[index][x_coord],
                                    occupied_squares[index][y_coord] + sqrsize,
                                    occupied_squares[index][2])
    for sqr in occupied_squares:
        g.display.rect(sqr[x_coord], sqr[y_coord], sqrsize, sqrsize, sqr[2])

def move(direction):
    global shape_blcks
    '''input:- list of blocks making up a tetris shape
output:- list of blocks making up a tetris shape
function moves the input list of blocks that make up shape and then checks
that the list of blocks are all in positions that are valide. position is
valid if it has not been occupied previously and is within the tetris board.
If move is successful, function returns the moved shape and if move is not
possible, function returns a false'''
    directs = {'down':(no_move, sqrsize), 'left':(-sqrsize, no_move),
        'right':(sqrsize, no_move), 'pause': (no_move, no_move)}
    delta_x, delta_y = directs[direction]
    for index in range(num_block):
        shape_blcks[index] = [shape_blcks[index][0] + delta_x, shape_blcks[index][1]+ delta_y]
    if legal(shape_blcks):
        for index in range(num_block):
            #erase previous positions of block
            g.display.fill_rect(shape_blcks[index][0]-delta_x, shape_blcks[index][1]-delta_y, sqrsize, sqrsize, 0)
        return True
    else:
        # undo the move, as it's not legal (being blocked by existing blocks)
        for index in range(num_block):
            shape_blcks[index] = [shape_blcks[index][0]-delta_x, shape_blcks[index][1]- delta_y]
        return False

def legal(blcks):
    '''input: list of shape blocks
checks whether a shape is in a legal portion of the board as defined in the
doc of 'move' function'''
    for index in range(num_block):
        new_x = blcks[index][0]
        new_y = blcks[index][1]
        if ((_cell_occupied(new_x, new_y) or new_y >= height) or
(new_x >= width or new_x < top_x)):
            return False
    return True

def create_newshape(start_x=board_centre, start_y=2):
    '''A shape is a list of four rectangular blocks.
Input:- coordinates of board at which shape is to be created
Output:- a list of the list of the coordinates of constituent blocks of each
shape relative to a reference block and shape name. Reference block has
starting coordinates of start_x and start_y. '''
    global shape_blcks, shape_name, new_shape_blcks, new_shape_name, shape_color
    shape_blcks = new_shape_blcks
    shape_name = new_shape_name
    shape_color = SHAPE_COLORS.get(shape_name, (255, 255, 255))
    shape_names = ['S', 'O', 'I', 'L', 'T']
    shapes = {'S':[(start_x + 1*sqrsize, start_y + 2*sqrsize),
(start_x, start_y), (start_x, start_y + 1*sqrsize),(start_x + 1*sqrsize,
                                                    start_y + 1*sqrsize)],
        'O':[(start_x + 1*sqrsize, start_y + 1*sqrsize), (start_x, start_y),
(start_x, start_y + 1*sqrsize), (start_x + 1*sqrsize, start_y)],
        'I':[(start_x, start_y + 3*sqrsize), (start_x, start_y),
(start_x, start_y + 2*sqrsize), (start_x, start_y + 1*sqrsize)],
        'L':[(start_x + 1*sqrsize, start_y + 2*sqrsize), (start_x, start_y),
(start_x, start_y + 2*sqrsize), (start_x, start_y + 1*sqrsize)],
        'T':[(start_x + 1*sqrsize, start_y + 1*sqrsize),(start_x, start_y),
(start_x - 1*sqrsize, start_y + 1*sqrsize),(start_x,
                                                        start_y + 1*sqrsize)]
}
    a_shape = g.random(0, 4)
    new_shape_blcks = shapes[shape_names[a_shape]]
    new_shape_name = shape_names[a_shape]
    next_color = SHAPE_COLORS.get(new_shape_name, (255, 255, 255))
    # BUG TROUVE ET CORRIGE : l'apercu de la piece suivante etait dessine a
    # x+40, qui chevauche maintenant le plateau elargi (largeur 40). Utilise
    # PREVIEW_X (colonne laterale dediee) a la place.
    g.display.text('Prochaine :', PREVIEW_X, 36, 1)
    g.display.fill_rect(PREVIEW_X, 46, 40, 18, 0)
    if isinstance(new_shape_blcks, list):
        for blck in new_shape_blcks:
            g.display.rect(blck[0] - board_centre + PREVIEW_X + 8, blck[1] + 44, sqrsize, sqrsize, next_color)
    else:
        g.display.rect(new_shape_blcks[0] - board_centre + PREVIEW_X + 8, new_shape_blcks[1] + 44, sqrsize, sqrsize, next_color)

def rotate():
    '''input:- list of shape blocks
ouput:- list of shape blocks
function tries to rotate ie change orientation of blocks in the shape
and this applied depending on the shape for example if a 'O' shape is passed
to this function, the same shape is returned because the orientation of such
shape cannot be changed according to tetris rules'''
    if shape_name == 'O':
        return shape_blcks
    else:
        #global no_move, occupied_squares, background
        ref_shape_ind = 3 # index of block along which shape is rotated
        start_x, start_y = (shape_blcks[ref_shape_ind][0],
                            shape_blcks[ref_shape_ind][1])
        save_blcks = shape_blcks
        Rshape_blcks = [(start_x + start_y-shape_blcks[0][1],
                        start_y - (start_x - shape_blcks[0][0])),
(start_x + start_y-shape_blcks[1][1],
         start_y - (start_x - shape_blcks[1][0])),
(start_x + start_y-shape_blcks[2][1],
         start_y - (start_x - shape_blcks[2][0])),
(shape_blcks[3][0], shape_blcks[3][1])]
        if legal(Rshape_blcks):
            for index in range(num_block): # erase the previous shape
                g.display.fill_rect(shape_blcks[index][0], shape_blcks[index][1],sqrsize, sqrsize, 0)
            return Rshape_blcks
        else:
            return shape_blcks

exitGame = False
demo = False

while not exitGame:

  #menu screen
  while True:
    g.display.fill(0)
    g.display.text('Tetris', 0, 0, (255, 220, 0))
    g.display.rect(90,0, g.max_vol*4+2,6,1)
    g.display.fill_rect(91,1, g.vol * 4,4,1)
    g.display.text('A:Start  L:Quitter', 0, 10, 1)
    if demo :
        g.display.text('D: IA', 0,20, 1)
    else :
        g.display.text('D: 1 Joueur', 0,20, 1)
    g.display.text('R: Vitesse {}'.format(g.frameRate), 0,30, 1)
    g.display.text('D:option R:vitesse', 0, 40, (0, 200, 255))
    g.display.text('B + U/D: volume', 0, 50, (0, 200, 255))
    g.display.show()

    g.getBtn()
    if g.setVol() :
        pass
    elif g.justReleased(g.btnL) :
        exitGame = True
        gameOver= True
        break
    elif g.justPressed(g.btnA) :
        if demo :
            g.display.fill(0)
            g.display.text('DEMO', 5, 0, 1)
            g.display.text('B to Stop', 5, 30, 1)
            g.display.show()
            g.sleep_ms(1000)
        break
    elif g.justPressed(g.btnD) :
        demo = not demo
    elif g.justPressed(g.btnR) :
        if g.pressed(g.btnB) :
            g.frameRate = g.frameRate - 5 if g.frameRate > 5 else 100
        else :
            g.frameRate = g.frameRate + 5 if g.frameRate < 100 else 5
    g.sleep_ms(10)

  life = 3
  score = 0
  reset_board()
  create_newshape()
  gameOver = False

  # game loop
  while not gameOver:
    drawScore()
    create_newshape()
    extramoves = 3
    l_of_blcks_ind = blck_x_axis = 0
    shape_name_ind = blck_y_axis = 1
    move_dir = 'down' #default move direction
    game = 'playing' #default game state play:- is game paused or playing

    if legal(shape_blcks):
        draw_shape()
    else:
        life -= 1
        if life <= 0 :
            gameOver = True
            break
        else :
           g.playTone('g4', 100)
           g.playTone('e4', 100)
           g.playTone('c4', 100)
           g.display.show()
           g.sleep_ms(2000)
           reset_board()
           continue

    # BUG TROUVE ET CORRIGE (detection des touches peu fiable) : la boucle
    # attendait mov_delay (150ms par defaut) entre deux verifications des
    # touches -- un appui bref pouvait etre presse ET relache ENTIEREMENT
    # pendant cette attente, sans jamais etre vu. Separe maintenant la
    # frequence de VERIFICATION des touches (courte, fixe, ~20ms) de la
    # frequence de CHUTE AUTOMATIQUE (mov_delay, variable) -- deux
    # minuteurs independants plutot qu'un seul.
    last_drop = g.ticks_ms()
    while True:
        move_dir = 'down'
        g.getBtn()
        if g.menu_was_open:
            redraw_all()
            last_drop = g.ticks_ms()   # evite une chute immediate au retour
        if game == 'paused':
            g.display.fill_rect(15, 25, 100, 20, 0)
            g.display.text("PAUSE", 20, 27, (255, 220, 0))
            g.display.text("B:reprendre", 20, 35, (0, 200, 255))
            g.display.text("L:quitter", 20, 42, (0, 200, 255))
            g.display.show()
            if g.justPressed(g.btnB) :
                g.playTone('c4', 100)
                g.playTone('e4', 100)
                game = 'playing'
            # BUG TROUVE ET CORRIGE (demande) : "maintenir U+D" pour
            # quitter en cours de partie est physiquement peu pratique
            # (croix directionnelle). L et R servent deja a deplacer la
            # piece pendant le jeu, donc L n'est reutilisable QUE pendant
            # la pause, ou aucun mouvement n'est possible de toute facon.
            elif g.justReleased(g.btnL) :
                gameOver = True
                break
            g.sleep_ms(20)
            continue
        else:
            if g.justPressed(g.btnB) :
                g.playTone('e4', 100)
                g.playTone('f4', 100)
                game = 'paused'
                g.sleep_ms(20)
                continue
            elif g.justPressed(g.btnA) or g.justPressed(g.btnU) :
                shape_blcks = rotate()
                draw_shape()
                g.display.show()
                g.sleep_ms(r_delay)
                continue
            elif g.pressed(g.btnL) or g.pressed(g.btnR):
                move_dir = 'left' if g.pressed(g.btnL) else 'right'
                move (move_dir)
                draw_shape()
                g.display.show()
                g.sleep_ms(50)
                continue

            # Chute automatique : seulement si le delai (accelere si Bas
            # est maintenu) est REELLEMENT ecoule -- pas juste "une
            # iteration de boucle plus tard".
            drop_delay = 10 if g.pressed(g.btnD) else 350
            now = g.ticks_ms()
            if now - last_drop < drop_delay:
                g.sleep_ms(20)
                continue
            last_drop = now

            moved = move('down')
            draw_shape()
            '''if block did not move and the direction for movement is down
then shape has come to rest so we can exit loop and then a new
shape is generated. if direction for movement is sideways and
block did not move it should be moved down rather'''
            if not moved and move_dir == 'down':
              extramoves = extramoves - 1
              if extramoves <= 0 :
                for block in shape_blcks:
                    occupied_squares.append((block[0],block[1],shape_color))
                break
            draw_shape()
            g.display.show()
            for row_no in range (height - sqrsize + top_y, 0, -sqrsize):
                if row_filled(row_no):
                    delete_row(row_no)
                    score+=10
                    drawScore()
                    g.display.show()
                    g.playTone('c4', 100)
                    g.playTone('e4', 100)
                    g.playTone('g4', 100)
                    g.playTone('e4', 100)
                    g.playTone('c4', 100)
            g.display.show()

  if gameOver :
       g.display.fill_rect(20,20, 80, 35,0)
       g.display.text("Game Over", 30,30,(255, 60, 60))
       g.display.show()
       g.playTone('c4', 100)
       g.playTone('e4', 100)
       g.playTone('g4', 100)
       g.sleep_ms(2000)
