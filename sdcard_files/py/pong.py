# pong.py -- adapte pour l'AKA (ecran 320x240, module aka natif) depuis la
# version originale ESP8266 (D1 mini + OLED SPI) de Billy Cheung, 2019.
# Toute la logique de jeu est INCHANGEE -- seule la couche materielle
# (game8266.py, reimplementee au-dessus du module aka) differe.
#
# all dislplay, buttons, paddle, sound logics are in game8266.py module
from game8266 import Game8266, Rect
g=Game8266()
g.set_controls(["U/D : raquette", "L : quitter"])

scores = [0,0]
maxScore = 15
gameOver = False
exitGame = False


class bat(Rect):
  def __init__(self, velocity, up_key, down_key, *args, **kwargs):
    self.velocity = velocity
    self.up_key = up_key
    self.down_key = down_key
    self.ai_target = None   # BUG EVITE : cible IA memorisee (voir move_bat)
    super().__init__(*args, **kwargs)

  def move_bat(self, board_height, bat_HEIGHT, ballY):
    g.getBtn()
    max_y = board_height - pong.bat_HEIGHT

    if self.up_key == 0  : # use AI
      # BUG TROUVE ET CORRIGE : recalculait une position CIBLE aleatoire
      # DIFFERENTE a chaque frame et s'y teleportait directement -- d'ou le
      # tremblement. Choisit maintenant une cible de temps en temps, et se
      # deplace vers elle progressivement (a sa propre vitesse), comme un
      # vrai joueur plutot que de teleporter.
      if self.ai_target is None or g.random(0, 20) == 0:
          self.ai_target = max(0, min(ballY - bat_HEIGHT // 2 + g.random(-6, 6), max_y))
      if self.y < self.ai_target:
          self.y = min(self.y + self.velocity, self.ai_target)
      elif self.y > self.ai_target:
          self.y = max(self.y - self.velocity, self.ai_target)

    elif self.up_key == -1 : # use Paddle
      self.y = int (g.getPaddle() / (1024 / max_y)) if max_y > 0 else 0

    else :
      # BUG TROUVE ET CORRIGE : ">" strict (pas ">=") empechait la raquette
      # d'atteindre EXACTEMENT le bord haut/bas -- une balle arrivant tout
      # en haut (ou en bas) de la zone ne pouvait jamais etre bloquee.
      if g.pressed(self.up_key):
        self.y = max(0, self.y - self.velocity)

      if g.pressed(self.down_key):
        self.y = min(max_y, self.y + self.velocity)
    self.y2 = self.y + pong.bat_HEIGHT

class Ball(Rect):
    def __init__(self, velocity, *args, **kwargs):
        self.velocity = velocity
        self.angle = 0
        super().__init__(*args, **kwargs)

    def move_ball(self):
        self.x += self.velocity
        self.y += self.angle
        self.x2 = self.x + pong.BALL_WIDTH
        self.y2 = self.y + pong.BALL_WIDTH


class Pong:
    # BUG TROUVE ET CORRIGE (demande) : le titre et le score n'avaient pas
    # de vraie place -- terrain reduit et decale (PLAY_TOP) pour degager
    # une bande HUD dediee en haut (titre centre + score), sans toucher a
    # la physique (bat.y/ball.y restent en coordonnees RELATIVES au
    # terrain, PLAY_TOP n'est ajoute qu'au moment de dessiner).
    PLAY_TOP = 16
    HEIGHT = 48
    WIDTH = 128

    bat_WIDTH = 2
    bat_HEIGHT = 15
    bat_VELOCITY = 3

    BALL_WIDTH = 2
    BALL_VELOCITY = 2
    BALL_ANGLE = 0

    COLOUR = 1
    scores = [0,0]
    maxScore = 15


    def init (self, onePlayer, demo, usePaddle):
        # Setup the screen
        global scores
        scores = [0,0]
        # Create the player objects.
        self.bats = []
        self.balls = []

        if demo :
          self.bats.append(bat(  # The left bat, AI
            self.bat_VELOCITY,
            0,
            0,
            0,
            int(self.HEIGHT / 2 - self.bat_HEIGHT / 2),
            self.bat_WIDTH,
            self.bat_HEIGHT))
        elif usePaddle :
          self.bats.append(bat(  # The left bat, use Paddle
            self.bat_VELOCITY,
            -1,
            -1,
            0,
            int(self.HEIGHT / 2 - self.bat_HEIGHT / 2),
            self.bat_WIDTH,
            self.bat_HEIGHT))
        else :

          self.bats.append(bat(  # The left bat, button controlled
            self.bat_VELOCITY,
            g.btnU,
            g.btnD,
            0,
            int(self.HEIGHT / 2 - self.bat_HEIGHT / 2),
            self.bat_WIDTH,
            self.bat_HEIGHT))

        if demo or onePlayer:
          self.bats.append(bat(  # The right bat, AI
              self.bat_VELOCITY,
              0,
              0,
              self.WIDTH - self.bat_WIDTH-1,
              int(self.HEIGHT / 2 - self.bat_HEIGHT / 2),
              self.bat_WIDTH,
              self.bat_HEIGHT
              ))
        else :
           self.bats.append(bat(  # The right bat, button controlled
              self.bat_VELOCITY,
              g.btnB,
              g.btnA,
              self.WIDTH - self.bat_WIDTH-1,
              int(self.HEIGHT / 2 - self.bat_HEIGHT / 2),
              self.bat_WIDTH,
              self.bat_HEIGHT
              ))

        self.balls.append(Ball(
            self.BALL_VELOCITY,
            int(self.WIDTH / 2 - self.BALL_WIDTH / 2),
            int(self.HEIGHT / 2 - self.BALL_WIDTH / 2),
            self.BALL_WIDTH,
            self.BALL_WIDTH))


    def score(self, player, ball):
      global gameOver
      global scores
      scores[player] += 1
      ball.velocity = - ball.velocity
      ball.angle = g.random(0,3) - 2
      ball.x = int(self.WIDTH / 2 - self.BALL_WIDTH / 2)
      ball.y = int(self.HEIGHT / 2 - self.BALL_WIDTH / 2)
      ball.x2 = ball.x + self.BALL_WIDTH
      ball.y2 = ball.y + self.BALL_WIDTH
      g.playTone ('g4', 100)

      if scores[player] >= maxScore :
        gameOver = True

    def check_ball_hits_wall(self):
      for ball in self.balls:

        if ball.x < 0:
          self.score(1, ball)


        if ball.x > self.WIDTH :
          self.score(0, ball)

        if ball.y > self.HEIGHT - self.BALL_WIDTH or ball.y < 0:
          ball.angle = -ball.angle


    def check_ball_hits_bat(self):
      for ball in self.balls:
          for bat in self.bats:
            #print (' {} {} {} {} : {} {} {} {}'.format (ball.x, ball.y, ball.x2, ball.y2, bat.x,bat.y, bat.x2, bat.y2))
            if ball.colliderect(bat):
                  ball.velocity = -ball.velocity
                  ball.angle = g.random (0,3) - 2
                  g.playTone ('c6', 10)
                  break

    def game_loop(self):
      global gameOver, exitGame, scores

      exitGame = False
      while not exitGame:
        players = 1
        onePlayer = True
        usePaddle = False
        demo = False
        gameOver = False

        #menu screen
        while True:
            g.display.fill(0)
            g.display.text('Pong', 0, 0, (255, 220, 0))
            g.display.rect(90,0, g.max_vol*4+2,6,1)
            g.display.fill_rect(91,1, g.vol * 4,4,1)
            g.display.text('A:Start  L:Quitter', 0, 10,  1)
            if usePaddle :
                g.display.text('U: Paddle', 0,20,  1)
            else :
                g.display.text('U: Bouton', 0,20,  1)
            if players == 0 :
                g.display.text('D: IA vs IA', 0,30, 1)
            elif players == 1 :
                g.display.text('D: 1 Joueur', 0,30, 1)
            else :
                g.display.text('D: 2 Joueurs', 0,30, 1)
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
                if players == 0 : # demo
                    onePlayer = False
                    demo = True
                    g.display.fill(0)
                    g.display.text('DEMO', 5, 0, 1)
                    g.display.text('B to Stop', 5, 30, 1)
                    g.display.show()
                    g.sleep_ms(1000)
                elif players == 1 :
                    onePlayer = True
                    demo = False
                else :
                    onePlayer = False
                    demo = False
                break
            elif g.justPressed(g.btnU) :
                usePaddle =  not usePaddle
            elif g.justPressed(g.btnD) :
                players = (players + 1) % 3

            elif g.justPressed(g.btnR) :
                if g.pressed(g.btnB) :
                    g.frameRate = g.frameRate - 5 if g.frameRate > 5 else 100
                else :
                    g.frameRate = g.frameRate + 5 if g.frameRate < 100 else 5

        self.init(onePlayer, demo, usePaddle)

        #game loop

        while not gameOver:
          g.getBtn()
          if demo and g.justReleased(g.btnB) :
            gameOver = True

          self.check_ball_hits_bat()
          self.check_ball_hits_wall()

          # Redraw the screen.
          g.display.fill(0)
          g.display.text('Pong', 52, 0, (255, 220, 0))
          g.display.text ('{} : {}'.format (scores[0], scores[1]), 50, 9, (0, 200, 255))
          # BUG TROUVE ET CORRIGE (demande) : rien n'indiquait ou la balle
          # rebondit en haut/bas -- lignes de limite ajoutees, decalees de
          # PLAY_TOP pour laisser la place au titre/score au-dessus.
          g.display.fill_rect(0, self.PLAY_TOP, self.WIDTH, 1, (80, 80, 80))
          g.display.fill_rect(0, self.PLAY_TOP + self.HEIGHT - 1, self.WIDTH, 1, (80, 80, 80))

          for bat in self.bats:
            bat.move_bat(self.HEIGHT, self.bat_HEIGHT, self.balls[0].y)
            g.display.fill_rect(bat.x, bat.y + self.PLAY_TOP, self.bat_WIDTH, self.bat_HEIGHT, self.COLOUR)

          for ball in self.balls:
            ball.move_ball()
            g.display.fill_rect(ball.x, ball.y + self.PLAY_TOP, self.BALL_WIDTH, self.BALL_WIDTH, self.COLOUR)


          if gameOver :
            g.display.fill_rect(15,20, 100, 40,0)
            # BUG TROUVE ET CORRIGE (demande) : le jeu affichait toujours
            # le meme "Game Over" generique, meme contre l'IA -- affiche
            # maintenant Victoire/Defaite quand on joue contre l'IA (le
            # joueur, c'est toujours la raquette de gauche).
            vs_ai = demo or onePlayer
            if vs_ai and scores[0] > scores[1]:
                g.display.text ("Victoire !", 25, 30, (60, 220, 60))
            elif vs_ai:
                g.display.text ("Defaite...", 25, 30, (255, 60, 60))
            else:
                g.display.text ("Game Over", 30, 30, (255, 60, 60))
            g.display.show()
            g.playTone ('c5', 200)
            g.playTone ('g4', 200)
            g.playTone ('g4', 200)
            g.playTone ('a4', 200)
            g.playTone ('g4', 400)
            g.playTone ('b4', 200)
            g.playTone ('c5', 400)

          g.display_and_wait()


#if __name__ == '__main__':
pong = Pong()

pong.game_loop()
print ("game exit")
