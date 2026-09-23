# invaders.py -- adapte pour l'AKA (ecran 320x240, module aka natif) depuis
# la version originale ESP8266 (D1 mini + OLED SPI) de Billy Cheung, 2019.
# Toute la logique de jeu est INCHANGEE -- seule la couche materielle
# (game8266.py, reimplementee au-dessus du module aka) differe.
#
# BUG EVITE : const() n'est pas garanti disponible sur cette config
# MicroPython minimale (verifie sur d'autres fonctionnalites du meme
# genre) -- repli trivial, sans effet si const existe deja reellement.
def const(x): return x

# all dislplay, buttons, paddle, sound logics are in game8266.py module
from game8266 import Game8266, Rect
g=Game8266()
g.set_controls(["G/D : viser", "A/B : tirer", "L : quitter"])

g.frameRate = 30
xMargin = const (5)
yMargin = const(10)
screenL = const (5)
screenR = const(117)
screenT = const (10)
screenB = const (58)
dx = 5
vc = 3
gunW= const(5)
gunH = const (5)
invaderSize = const(4)
invaders_rows = const(5)
invaders_per_row = const(11)



def setUpInvaders ():
    y = yMargin
    while y < yMargin + (invaderSize+2) * invaders_rows :
      x = xMargin
      while x < xMargin + (invaderSize+2) * invaders_per_row :
        invaders.append(Rect(x,y,invaderSize, invaderSize))
        x = x + invaderSize + 2
      y = y + invaderSize + 2

def drawSpaceships (posture) :
  if posture :
    for i in spaceships :
      g.display.fill_rect(i.x+2, i.y, 5 , 3, 1)
      g.display.fill_rect(i.x, i.y+1, 9, 1, 1)
      g.display.fill_rect(i.x+1, i.y+1, 2, 1, 0)
  else :
    for i in spaceships :
      g.display.fill_rect(i.x+2, i.y, 5 , 3, 1)
      g.display.fill_rect(i.x, i.y+1, 9, 1, 1)
      g.display.fill_rect(i.x+5, i.y+1, 2, 1, 0)

def drawInvaders (posture) :
  if posture :
    for i in invaders :
        g.display.fill_rect(i.x, i.y, invaderSize , invaderSize, 1)
        g.display.fill_rect(i.x+1, i.y+2, invaderSize-2, invaderSize-2, 0)
  else :
      for i in invaders :
        g.display.fill_rect(i.x, i.y, invaderSize , invaderSize, 1)
        g.display.fill_rect(i.x+1, i.y, invaderSize-2, invaderSize-2, 0)
def drawGun () :
  g.display.fill_rect(gun.x+2, gun.y, 1, 2,1)
  g.display.fill_rect(gun.x, gun.y+2, gunW, 3,1)

def drawBullets () :
  for b in bullets:
    g.display.fill_rect(b.x, b.y, 2,3,1)

def drawAbullets () :
  for b in aBullets:
    g.display.fill_rect(b.x, b.y, 1,3,1)

def drawScore () :
  g.display.text('S:{}'.format (score), 0,0,(0, 200, 255))
  g.display.text('L:{}'.format (level), 50,0,(0, 200, 255))
  for i in range (0, life) :
    g.display.fill_rect(92 + (gunW+2)*i, 0, 1, 2,1)
    g.display.fill_rect(90 + (gunW+2)*i, 2, gunW, 3,1)



exitGame = False

while not exitGame:
  gameOver = False
  usePaddle = False
  demo = False
  life = 3

  #menu screen
  while True:
    g.display.fill(0)
    g.display.text('Invaders', 0, 0, (255, 220, 0))
    g.display.rect(90,0, g.max_vol*4+2,6,1)
    g.display.fill_rect(91,1, g.vol * 4,4,1)
    g.display.text('A:Start  L:Quitter', 0, 10,  1)
    # BUG TROUVE ET CORRIGE : ces lignes montraient l'etat courant (ex:
    # "U Button") sans jamais dire que c'est la touche U qui bascule cet
    # etat -- ajout d'une legende explicite en bas, comme demande.
    if usePaddle :
        g.display.text('U: Paddle', 0,20,  1)
    else :
        g.display.text('U: Bouton', 0,20,  1)
    if demo :
        g.display.text('D: IA', 0,30, 1)
    else :
        g.display.text('D: 1 Joueur', 0,30, 1)
    g.display.text('R: Vitesse {}'.format(g.frameRate), 0,40, 1)
    g.display.text('U/D:option R:vitesse', 0, 50, (0, 200, 255))
    g.display.text('B+U/D: volume', 0, 58, (0, 200, 255))
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
    elif g.justPressed(g.btnU) :
        usePaddle =  not usePaddle
    elif g.justPressed(g.btnD) :
        demo = not demo
    elif g.justPressed(g.btnR) :
        if g.pressed(g.btnB) :
            g.frameRate = g.frameRate - 5 if g.frameRate > 5 else 100
        else :
            g.frameRate = g.frameRate + 5 if g.frameRate < 100 else 5
  #reset the game
  score = 0
  frameCount = 0
  level = 0
  loadLevel = True
  postureA = False
  postureS = False
  # Chance from 1 to 128
  aBulletChance = 1
  spaceshipChance = 1

  while not gameOver:

    lost = False
    frameCount = (frameCount + 1 ) % 120
    g.display.fill(0)

    if loadLevel :
      loadLevel = False
      spaceships = []
      invaders = []
      bullets = []
      aBullets = []
      setUpInvaders()
      gun = Rect(screenL+int((screenR-screenL)/2), screenB, gunW, gunH)
      aBulletChance = 50 + level * 10



    #generate space ships
    if g.random (0,99) < spaceshipChance and len(spaceships) < 1 :
      spaceships.append(Rect(0,9, 9, 9))

    if len(spaceships) :
      if not frameCount % 3 :
        postureS = not postureS
        # move spaceships once every 4 frames
        # BUG TROUVE ET CORRIGE : "for i in spaceships: ... spaceships.
        # remove(i)" modifie la liste PENDANT qu'on la parcourt -- peut
        # sauter l'element suivant. Parcourt une COPIE (spaceships[:]) a
        # la place, remove() reste applique a la vraie liste.
        for i in spaceships[:]:
          i.move_ip(2,0)
          if i.x >= screenR :
            spaceships.remove(i)
      if frameCount % 20 == 10 :
        g.playTone ('e5', 20)
      elif frameCount % 20 == 0 :
        g.playTone ('c5', 20)


    if not frameCount % 15 :
      postureA = not postureA
      # move Aliens once every 15 frames
      if postureA :
          g.playSound (80, 10)
      else:
          g.playSound (120, 10)
      for i in invaders:
        if i.x > screenR or i.x < screenL :
            dx = -dx
            for alien in invaders :
              alien.move_ip (0, invaderSize)
              if alien.y2 > gun.y :
                lost = True
                loadLevel = True
                g.playTone ('f4',300)
                g.playTone ('d4',100)
                g.playTone ('c5',100)
                break
            break

      for i in invaders :
        i.move_ip (dx, 0)


    g.getBtn()

    if demo :
        if g.justPressed (g.btnB) :
            gameOver = True

        if g.random (0,1) and len(bullets) < 2:
            bullets.append(Rect(gun.x+2, gun.y-1, 2, 3))
            g.playSound (200,5)
            g.playSound (300,5)
            g.playSound (400,5)

        if g.random(0,1) :
            vc = 3
        else :
            vc = -3

        if (vc + gun.x + gunW) < g.screenW and (vc + gun.x)  >= 0 :
           gun.move_ip (vc, 0)

    # Real player
    elif g.pressed (g.btnA | g.btnB) and len(bullets) < 2:
      bullets.append(Rect(gun.x+2, gun.y-1, 2, 3))
      g.playSound (200,5)
      g.playSound (300,5)
      g.playSound (400,5)
    # move gun


    elif usePaddle :
      gun.x = int(g.getPaddle() / (1024/(screenR-screenL)))
      gun.x2 = gun.x+gunW-1
    else :
      if g.pressed (g.btnL) and gun.x - 3 > 0 :
        vc = -3
      elif g.pressed(g.btnR) and (gun.x + 3 + gunW ) < g.screenW :
        vc = 3
      else :
        vc = 0
      gun.move_ip (vc, 0)

    # move bullets

    # BUG TROUVE ET CORRIGE : "for b in bullets: ... bullets.remove(b)"
    # modifie la liste PENDANT qu'on la parcourt -- la balle SUIVANTE peut
    # alors etre sautee ce tour-ci (jamais testee contre les envahisseurs
    # cette frame-la), donnant l'impression que les tirs les traversent
    # sans les toucher. Parcourt une COPIE (bullets[:]) a la place.
    for b in bullets[:]:
      b.move_ip(0,-3)
      if b.y < 0 :
        bullets.remove(b)
      else :
        # BUG TROUVE ET CORRIGE : apres avoir touche un envahisseur (et
        # retire b de bullets), le code verifiait QUAND MEME la collision
        # avec les vaisseaux en utilisant ce MEME tir deja detruit -- un
        # seul tir pouvait ainsi detruire un envahisseur ET un vaisseau
        # d'un coup. "hit" empeche de continuer a tester ce tir une fois
        # qu'il a deja touche quelque chose.
        hit = False
        for i in invaders[:]:
          if i.colliderect(b) :
            invaders.remove(i)
            bullets.remove(b)
            score +=1
            g.playTone ('c6',10)
            hit = True
            break
        if hit:
            continue
        for i in spaceships[:] :
          if i.colliderect(b) :
            spaceships.remove(i)
            bullets.remove(b)
            score +=10
            g.playTone ('b4',30)
            g.playTone ('e5',10)
            g.playTone ('c4',30)
            break

    # Launch Alien bullets
    for i in invaders:
      if g.random (0,1000) * len (invaders) < aBulletChance and len(aBullets) < 3 :
        aBullets.append(Rect(i.x+2, i.y, 1, 3))

    # move Alien bullets
    for b in aBullets[:]:
      b.move_ip(0,3)
      if b.y > g.screenH  :
        aBullets.remove(b)
      elif b.colliderect(gun) :
        lost = True
        #print ('{} {} {} {} : {} {} {} {}'.format(b.x,b.y,b.x2,b.y2,gun.x,gun.y,gun.x2,gun.y2))
        aBullets.remove(b)
        g.playTone ('c5',30)
        g.playTone ('e4',30)
        g.playTone ('b4',30)
        break

    drawSpaceships (postureS)
    drawInvaders (postureA)
    drawGun()
    drawBullets()
    drawAbullets()
    drawScore()


    if len(invaders) == 0 :
      level += 1
      loadLevel = True
      g.playTone ('c4',100)
      g.playTone ('d4',100)
      g.playTone ('e4',100)
      g.playTone ('f4',100)
      g.playTone ('g4',100)

    if lost :
      lost = False;
      life -= 1
      if life < 0 :
        gameOver = True

    if gameOver :
      g.display.fill_rect (3, 15, 120,20,0)
      g.display.text ("GAME OVER", 5, 20, (255, 60, 60))
      g.playTone ('b4',300)
      g.playTone ('e4',100)
      g.playTone ('c4',100)
      g.display.show()
      g.sleep_ms(2000)

    g.display_and_wait()
