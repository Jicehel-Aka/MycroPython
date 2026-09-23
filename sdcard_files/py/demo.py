# main.py — Script principal execute au demarrage par l'app AKA MicroPython.
# Demo : une balle rebondissante + affichage de TOUTES les touches, du
# joystick analogique et du pave directionnel. Sert de squelette de test
# materiel complet. Copie ce dossier "py/" a la racine de la carte SD
# (-> /sdcard/py/main.py).
#
# API disponible : module natif `aka` (voir README / MANUEL).

import aka

# Aide affichee dans le menu systeme (touche MENU -> "Commandes").
aka.set_controls([
    "Fleches / pave : voir en bas d'ecran",
    "A : flash rouge",
    "B : vibration (rappuyer pour arreter)",
    "C, D, L1, R1 : bandeau de couleur",
    "MENU : menu systeme",
    "RUN + MENU : quitter",
])
aka.set_credits("Demo Materiel", "AKA Port Studio", "MIT", "micropython.org")

W = aka.width()
H = aka.height()

x = W // 2
y = H // 2
vx = 3
vy = 2
r = 12

WHITE = (255, 255, 255)
GREEN = (0, 220, 0)
RED   = (220, 40, 40)
GREY  = (90, 90, 90)
YELLOW = (255, 210, 0)
CYAN  = (0, 200, 220)
ORANGE = (255, 140, 0)
MAGENTA = (220, 60, 220)

# BUG CORRIGE : la demo precedente appelait aka.vibrate(60) a CHAQUE frame
# tant que B restait enfonce -- chaque appel relancait le delai, donnant
# l'impression d'une vibration bien plus longue que prevu tant qu'on ne
# relachait pas le bouton. Ici : un appui (front montant, aka.pressed())
# demarre une vibration de duree fixe ; un NOUVEL appui pendant qu'elle
# tourne encore l'arrete immediatement. aka.is_vibrating() interroge l'etat
# REEL cote C (pas une estimation approximative en Python).
VIBRATE_MS = 400

# Petit pave directionnel dessine en bas a gauche (zone fixe de l'ecran).
DPAD_CX, DPAD_CY, DPAD_R = 30, H - 30, 10

def draw_dpad(buttons):
    aka.set_color(*GREY)
    aka.rect(DPAD_CX - DPAD_R - 4, DPAD_CY - DPAD_R - 4, (DPAD_R + 4) * 2, (DPAD_R + 4) * 2)
    aka.set_color(*WHITE)
    aka.pixel(DPAD_CX, DPAD_CY)
    if buttons & aka.UP:
        aka.set_color(*YELLOW); aka.fill_rect(DPAD_CX - 2, DPAD_CY - DPAD_R, 4, DPAD_R - 2)
    if buttons & aka.DOWN:
        aka.set_color(*YELLOW); aka.fill_rect(DPAD_CX - 2, DPAD_CY + 2, 4, DPAD_R - 2)
    if buttons & aka.LEFT:
        aka.set_color(*YELLOW); aka.fill_rect(DPAD_CX - DPAD_R, DPAD_CY - 2, DPAD_R - 2, 4)
    if buttons & aka.RIGHT:
        aka.set_color(*YELLOW); aka.fill_rect(DPAD_CX + 2, DPAD_CY - 2, DPAD_R - 2, 4)

# Plage brute mesuree a l'usage pour aka.joystick() : 0..3125 sur les deux
# axes, ~1500-1562 au centre. Voir commentaire plus bas pour le sens de
# chaque axe (Y inverse par rapport aux pixels ecran).
JOY_MIN, JOY_MAX, JOY_CENTER = 0, 3125, 1562
STICK_R = 10

def _joy_to_pixels(v):
    d = v - JOY_CENTER
    span = JOY_MAX - JOY_CENTER
    return max(-STICK_R, min(STICK_R, (d * STICK_R) // span))

while True:
    # aka.update() lit les boutons et laisse le menu systeme AKA prendre la
    # main si besoin ; renvoie False la frame ou le menu est affiche.
    if aka.update():
        x += vx
        y += vy
        if x < r or x > W - r:
            vx = -vx
        if y < r or y > H - r:
            vy = -vy

        aka.clear(10, 10, 30)

        aka.set_color(*GREEN)
        aka.fill_circle(x, y, r)

        aka.set_color(*WHITE)
        aka.text(8, 8, "MicroPython sur AKA")
        aka.text(8, 20, "Langue: " + aka.language())

        pressed = aka.pressed()
        held = aka.buttons()

        # --- A : flash rouge tant que maintenu (comportement d'origine) ---
        if held & aka.A:
            aka.set_color(*RED)
            aka.fill_rect(0, 0, W, 6)

        # --- B : vibration demarrable/arretable (front montant uniquement) ---
        if pressed & aka.B:
            if aka.is_vibrating():
                aka.vibrate(0)   # deuxieme appui pendant la vibration -> arret immediat
            else:
                aka.vibrate(VIBRATE_MS)

        # --- C, D, L1, R1 : un bandeau de couleur different par touche ---
        bandY = 200
        if held & aka.C:
            aka.set_color(*CYAN); aka.fill_rect(0, bandY, W, 6); aka.text(8, bandY + 8, "C")
        if held & aka.D:
            aka.set_color(*ORANGE); aka.fill_rect(0, bandY, W, 6); aka.text(24, bandY + 8, "D")
        if held & aka.L1:
            aka.set_color(*MAGENTA); aka.fill_rect(0, bandY, W // 2, 6); aka.text(40, bandY + 8, "L1")
        if held & aka.R1:
            aka.set_color(*MAGENTA); aka.fill_rect(W // 2, bandY, W // 2, 6); aka.text(60, bandY + 8, "R1")

        # --- Pave directionnel (visuel, coin bas-gauche) ---
        draw_dpad(held)

        # --- Joystick analogique (position numerique + point, coin bas-droit) ---
        jx, jy = aka.joystick()
        aka.set_color(*WHITE)
        # BUG CORRIGE (affichage) : "Stick: XXXX, XXXX" etait trop large pour
        # la largeur disponible a cette position -> retour a la ligne
        # automatique, "Stick:" se retrouvant coupe sur 2 lignes de travers.
        # Fix : "Stick" seul au-dessus, les valeurs sur la ligne du dessous.
        aka.text(W - 90, H - 52, "Stick")
        aka.text(W - 90, H - 40, str(jx) + ", " + str(jy))

        stickCX, stickCY, stickR = W - 30, H - 30, STICK_R
        aka.set_color(*GREY)
        aka.rect(stickCX - stickR - 4, stickCY - stickR - 4, (stickR + 4) * 2, (stickR + 4) * 2)
        aka.set_color(*CYAN)
        # BUG CORRIGE (position du point) : aka.joystick() ne renvoie PAS de
        # petites valeurs deja centrees sur 0 comme suppose au depart -- voir
        # JOY_MIN/JOY_MAX/JOY_CENTER plus haut. Y inverse (3125=haut) par
        # rapport au sens normal des pixels ecran (y croissant vers le bas).
        px = stickCX + _joy_to_pixels(jx)
        py = stickCY - _joy_to_pixels(jy)
        aka.fill_circle(px, py, 2)

        aka.display()

    # Cadence ~60 fps.
    # Cadence ~33 fps -- gb_config.h documente l'ecran comme synchronise a
    # 70/35 fps ; 60fps (16ms) sollicitait le mecanisme de synchronisation
    # plus vite qu'il ne peut suivre, cf. gb_ll_lcd.c.
    aka.sleep_ms(30)
