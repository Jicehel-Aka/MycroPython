# -*- coding: utf-8 -*-
# =============================================================================
#  calculatrice.py — Calculatrice scientifique pour la console AKA
#
#  Démonstration complète : clavier à l'écran (navigation D-Pad), évaluateur
#  d'expressions (tokeniseur + shunting-yard -> RPN), fonctions scientifiques
#  en Python PUR (le module `math` n'est pas embarqué dans ce build : sin/cos/
#  tan par séries de Taylor, ln par Newton, exp/sqrt via l'opérateur `**`),
#  SPRITES (upygame.Surface, icônes calculatrice et courbe) et SONS (upygame.
#  mixer.Sound : clic, validation, erreur — ondes carrées générées à la volée),
#  plus un mode TRACÉ DE COURBES (y = f(x) avec déplacement et zoom).
#
#  Commandes :
#    Calculatrice  : D-Pad = déplacer · A = touche · B = effacer · C = tout
#                    effacer · "=" (touche) = calculer · D = mode courbe
#    Courbe        : D-Pad gauche/droite = défiler · haut/bas = zoom ·
#                    C = recentrer · D = retour calculatrice
#    MENU partout, Échap (sur PC) = quitter.
# =============================================================================
import aka
import upygame
import math            # module math désormais embarqué (MICROPY_PY_MATH=1)

# ----------------------------------------------------------------------------
#  Fonctions et constantes scientifiques (via le module math natif)
# ----------------------------------------------------------------------------
PI = math.pi
E = math.e

FUNCS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sqrt": math.sqrt, "exp": math.exp,
    "ln": math.log, "log": math.log10,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "abs": abs, "floor": math.floor, "ceil": math.ceil,
}
CONSTS = {"pi": PI, "e": E}

# ----------------------------------------------------------------------------
#  Évaluateur d'expressions : tokeniseur -> shunting-yard (RPN) -> calcul
# ----------------------------------------------------------------------------
_PREC = {"+": 2, "-": 2, "*": 3, "/": 3, "^": 4, "u-": 5}
_RIGHT = ("^", "u-")


def tokenize(src):
    toks = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == " ":
            i += 1
        elif c in "0123456789.":
            j = i
            while j < n and src[j] in "0123456789.":
                j += 1
            toks.append(("num", float(src[i:j])))
            i = j
        elif c.isalpha():
            j = i
            while j < n and src[j].isalpha():
                j += 1
            toks.append(("name", src[i:j]))
            i = j
        elif c in "+-*/^(),":
            toks.append(("op", c))
            i += 1
        else:
            raise ValueError("car '" + c + "'")
    return toks


def to_rpn(toks):
    out = []
    ops = []
    prev = None
    for t in toks:
        typ, val = t
        if typ == "num":
            out.append(t)
        elif typ == "name":
            if val in CONSTS:
                out.append(("num", CONSTS[val]))
            elif val == "x":
                out.append(("var", None))
            elif val in FUNCS:
                ops.append(("fn", val))
            else:
                raise ValueError("inconnu '" + val + "'")
        elif typ == "op":
            if val == "(":
                ops.append(t)
            elif val == ")":
                while ops and ops[-1] != ("op", "("):
                    out.append(ops.pop())
                if not ops:
                    raise ValueError("parenthese")
                ops.pop()
                if ops and ops[-1][0] == "fn":
                    out.append(ops.pop())
            else:
                o = val
                if o == "-" and (prev is None or (prev[0] == "op" and prev[1] in "+-*/^(")):
                    o = "u-"
                while ops and ops[-1][0] in ("op", "fn"):
                    top = ops[-1]
                    if top == ("op", "("):
                        break
                    if top[0] == "fn":
                        out.append(ops.pop())
                        continue
                    to = top[1]
                    if (o not in _RIGHT and _PREC[o] <= _PREC[to]) or \
                       (o in _RIGHT and _PREC[o] < _PREC[to]):
                        out.append(ops.pop())
                    else:
                        break
                ops.append(("op", o))
        prev = t
    while ops:
        top = ops.pop()
        if top == ("op", "("):
            raise ValueError("parenthese")
        out.append(top)
    return out


def eval_rpn(rpn, xval=0.0):
    st = []
    for t in rpn:
        k = t[0]
        if k == "num":
            st.append(t[1])
        elif k == "var":
            st.append(xval)
        elif k == "fn":
            st.append(FUNCS[t[1]](st.pop()))
        else:
            o = t[1]
            if o == "u-":
                st.append(-st.pop())
            else:
                b = st.pop()
                a = st.pop()
                if o == "+":
                    st.append(a + b)
                elif o == "-":
                    st.append(a - b)
                elif o == "*":
                    st.append(a * b)
                elif o == "/":
                    if b == 0.0:
                        raise ValueError("/0")
                    st.append(a / b)
                elif o == "^":
                    st.append(a ** b)
    if len(st) != 1:
        raise ValueError("expr")
    return st[0]


def fmt(v):
    """Format court d'un flottant sans %f (indisponible dans ce build)."""
    if v != v:                       # NaN
        return "nan"
    r = round(v, 8)
    if r == int(r) and abs(r) < 1e15:
        return str(int(r))
    return str(r)


# ----------------------------------------------------------------------------
#  Palette + SPRITES (upygame.Surface, couleur indexée 4 bits)
# ----------------------------------------------------------------------------
def rgb565(r, g, b):                 # format R-haut (décodé par upygame)
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


#            0 transp  1 blanc   2 gris    3 cyan    4 jaune   5 vert
PALETTE = [rgb565(0, 0, 0), rgb565(255, 255, 255), rgb565(90, 90, 110),
           rgb565(80, 220, 255), rgb565(255, 220, 0), rgb565(60, 220, 90),
           # 6 rouge        7 bleu          8 orange        9 gris fonce
           rgb565(255, 70, 70), rgb565(70, 120, 255), rgb565(255, 150, 40),
           rgb565(40, 40, 55),
           rgb565(0, 0, 0), rgb565(0, 0, 0), rgb565(0, 0, 0),
           rgb565(0, 0, 0), rgb565(0, 0, 0), rgb565(0, 0, 0)]
upygame.display.set_palette_16bit(PALETTE)
upygame.draw.set_transparent_color(0)


def make_sprite(rows, cmap):
    """Construit une Surface depuis un dessin ASCII (une Surface 4 bits)."""
    h = len(rows)
    w = len(rows[0])
    rb = (w + 1) // 2
    data = bytearray(rb * h)
    for y in range(h):
        row = rows[y]
        for x in range(w):
            idx = cmap.get(row[x], 0) & 0xF
            bi = y * rb + (x >> 1)
            if (x & 1) == 0:
                data[bi] = (data[bi] & 0x0F) | (idx << 4)
            else:
                data[bi] = (data[bi] & 0xF0) | idx
    return upygame.surface.Surface(w, h, data)


_CALC_ICON = make_sprite([
    ".bbbbbbbb.",
    "b11111111b",
    "b1cccccc1b",
    "b1cccccc1b",
    "b11111111b",
    "b14141411b",
    "b11111111b",
    "b14141411b",
    "b11111111b",
    ".bbbbbbbb.",
], {".": 0, "b": 7, "1": 2, "c": 3, "4": 4})

_CURVE_ICON = make_sprite([
    "2........2",
    "2.......5.",
    "2......5..",
    "2....55...",
    "2..55.....",
    "255.......",
    "2.........",
    "2222222222",
], {".": 0, "2": 2, "5": 5})

# ----------------------------------------------------------------------------
#  SONS (upygame.mixer.Sound ; ondes carrées 8 bits générées à la volée)
# ----------------------------------------------------------------------------
_RATE = 44100


def _tone(freq, ms, vol=55):
    n = _RATE * ms // 1000
    half = _RATE // (2 * freq)
    if half < 1:
        half = 1
    buf = bytearray(n)
    for i in range(n):
        env = vol * (n - i) // n            # décroissance linéaire
        s = env if ((i // half) & 1) == 0 else -env
        buf[i] = 128 + s
    return buf


_snd = upygame.mixer.Sound()
_SND_CLICK = _tone(1500, 25, 38)
_SND_OK = _tone(880, 60, 48)
_SND_OK += _tone(1500, 80, 48)
_SND_ERR = _tone(150, 200, 60)


def play(data):
    _snd.play_sfx(data, len(data), False)


# ----------------------------------------------------------------------------
#  Clavier à l'écran
# ----------------------------------------------------------------------------
# chaque touche : (libellé, genre, valeur) ; genre 'i'=insérer, 'a'=action
KEYS = [
    [("7", "i", "7"), ("8", "i", "8"), ("9", "i", "9"), ("/", "i", "/"), ("sin", "i", "sin("), ("cos", "i", "cos(")],
    [("4", "i", "4"), ("5", "i", "5"), ("6", "i", "6"), ("*", "i", "*"), ("tan", "i", "tan("), ("sqrt", "i", "sqrt(")],
    [("1", "i", "1"), ("2", "i", "2"), ("3", "i", "3"), ("-", "i", "-"), ("ln", "i", "ln("), ("log", "i", "log(")],
    [("0", "i", "0"), (".", "i", "."), ("(", "i", "("), (")", "i", ")"), ("+", "i", "+"), ("^", "i", "^")],
    [("x", "i", "x"), ("pi", "i", "pi"), ("e", "i", "e"), ("<-", "a", "back"), ("C", "a", "clear"), ("=", "a", "eval")],
]
NROWS = len(KEYS)
NCOLS = len(KEYS[0])

W = aka.width()
H = aka.height()
GRID_X = 4
GRID_Y = 64
CELL_W = (W - 2 * GRID_X) // NCOLS
CELL_H = (H - GRID_Y - 4) // NROWS

# ----------------------------------------------------------------------------
#  État
# ----------------------------------------------------------------------------
MODE_CALC = 0
MODE_GRAPH = 1
mode = MODE_CALC
cur_r = 0
cur_c = 0
expr_parts = []                       # morceaux insérés (pour l'effacement)
result = ""
message = "D-Pad: deplacer  A: valider"
# fenêtre de tracé
gxmin, gxmax = -10.0, 10.0
gymin, gymax = -6.0, 6.0
graph_rpn = None
graph_err = ""


def expr_str():
    return "".join(expr_parts)


def text_c(x, y, s, idx=1):
    r, g, b = _col(idx)
    aka.set_color(r, g, b)
    aka.text(x, y, s)


def _col(idx):
    v = PALETTE[idx & 0xF]
    r5 = (v >> 11) & 0x1F
    g6 = (v >> 5) & 0x3F
    b5 = v & 0x1F
    return (r5 * 255 // 31, g6 * 255 // 63, b5 * 255 // 31)


# ----------------------------------------------------------------------------
#  Dessin — calculatrice
# ----------------------------------------------------------------------------
def draw_calc():
    aka.clear(16, 16, 24)
    # en-tête + sprite
    upygame.screen.blit(_CALC_ICON, 2, 2)
    text_c(26, 4, "CALCULATRICE", 3)
    # zone d'affichage de l'expression
    aka.set_color(*_col(9))
    aka.fill_rect(2, 20, W - 4, 20)
    aka.set_color(*_col(2))
    aka.rect(2, 20, W - 4, 20)
    e = expr_str()
    if len(e) > 38:
        e = e[-38:]
    text_c(6, 26, e if e else "0", 1)
    # résultat
    text_c(6, 44, "= " + result, 4)
    # clavier
    for r in range(NROWS):
        for c in range(NCOLS):
            x = GRID_X + c * CELL_W
            y = GRID_Y + r * CELL_H
            sel = (r == cur_r and c == cur_c)
            genre = KEYS[r][c][1]
            if sel:
                bg = 7
            elif genre == "a":
                bg = 8
            else:
                bg = 9
            aka.set_color(*_col(bg))
            aka.fill_rect(x + 1, y + 1, CELL_W - 2, CELL_H - 2)
            aka.set_color(*_col(1 if sel else 2))
            aka.rect(x + 1, y + 1, CELL_W - 2, CELL_H - 2)
            lbl = KEYS[r][c][0]
            tx = x + (CELL_W - len(lbl) * 8) // 2
            ty = y + (CELL_H - 8) // 2
            text_c(tx, ty, lbl, 1 if sel else 1)
    text_c(4, H - 9, "D: courbe  B: eff.  C: AC", 2)


# ----------------------------------------------------------------------------
#  Dessin — tracé de courbe
# ----------------------------------------------------------------------------
GTOP = 22


def gx_to_px(x):
    return int((x - gxmin) / (gxmax - gxmin) * (W - 1))


def gy_to_py(y):
    ph = H - GTOP - 1
    return GTOP + int((gymax - y) / (gymax - gymin) * ph)


def draw_graph():
    aka.clear(10, 12, 20)
    upygame.screen.blit(_CURVE_ICON, 2, 2)
    e = expr_str()
    if len(e) > 34:
        e = e[-34:]
    text_c(26, 4, "y=" + (e if e else "0"), 3)
    # grille
    aka.set_color(*_col(9))
    gstep = 1.0
    xg = int(gxmin)
    while xg <= gxmax:
        px = gx_to_px(xg)
        aka.vline(px, GTOP, H - GTOP)
        xg += 1
    yg = int(gymin)
    while yg <= gymax:
        py = gy_to_py(yg)
        aka.hline(0, py, W)
        yg += 1
    # axes
    aka.set_color(*_col(2))
    if gxmin <= 0 <= gxmax:
        aka.vline(gx_to_px(0.0), GTOP, H - GTOP)
    if gymin <= 0 <= gymax:
        aka.hline(0, gy_to_py(0.0), W)
    # courbe
    aka.set_color(*_col(4))
    prev_py = None
    for px in range(W):
        xv = gxmin + (gxmax - gxmin) * px / (W - 1)
        try:
            yv = eval_rpn(graph_rpn, xv)
        except Exception:
            prev_py = None
            continue
        if yv != yv or yv > 1e6 or yv < -1e6:
            prev_py = None
            continue
        py = gy_to_py(yv)
        if py < GTOP or py >= H:
            prev_py = None
            continue
        if prev_py is None:
            aka.pixel(px, py)
        else:
            aka.line(px - 1, prev_py, px, py)
        prev_py = py
    text_c(4, H - 9, "<>: defiler  ^v: zoom  D: retour", 2)


# ----------------------------------------------------------------------------
#  Logique d'entrée
# ----------------------------------------------------------------------------
def do_eval():
    global result, message
    e = expr_str()
    if not e:
        result = "0"
        return
    try:
        rpn = to_rpn(tokenize(e))
        v = eval_rpn(rpn, 0.0)
        result = fmt(v)
        play(_SND_OK)
    except Exception as ex:
        result = "Erreur"
        message = str(ex)
        play(_SND_ERR)


def enter_graph():
    global mode, graph_rpn, graph_err, message
    e = expr_str()
    if not e:
        e = "sin(x)"
        expr_parts.append("sin(x)")
    try:
        graph_rpn = to_rpn(tokenize(e))
        eval_rpn(graph_rpn, 0.0)         # test rapide
        mode = MODE_GRAPH
        play(_SND_OK)
    except Exception as ex:
        graph_err = str(ex)
        message = "Expr invalide: " + graph_err
        play(_SND_ERR)


def handle_calc(p):
    global cur_r, cur_c, result
    if p & aka.UP:
        cur_r = (cur_r - 1) % NROWS
        play(_SND_CLICK)
    elif p & aka.DOWN:
        cur_r = (cur_r + 1) % NROWS
        play(_SND_CLICK)
    elif p & aka.LEFT:
        cur_c = (cur_c - 1) % NCOLS
        play(_SND_CLICK)
    elif p & aka.RIGHT:
        cur_c = (cur_c + 1) % NCOLS
        play(_SND_CLICK)
    elif p & aka.A:
        lbl, genre, val = KEYS[cur_r][cur_c]
        if genre == "i":
            expr_parts.append(val)
            play(_SND_CLICK)
        elif val == "back":
            if expr_parts:
                expr_parts.pop()
            play(_SND_CLICK)
        elif val == "clear":
            del expr_parts[:]
            result = ""
            play(_SND_CLICK)
        elif val == "eval":
            do_eval()
    elif p & aka.B:
        if expr_parts:
            expr_parts.pop()
        play(_SND_CLICK)
    elif p & aka.C:
        del expr_parts[:]
        result = ""
        play(_SND_CLICK)
    elif p & aka.D:
        enter_graph()


def handle_graph(p):
    global gxmin, gxmax, gymin, gymax, mode
    dx = (gxmax - gxmin) * 0.12
    if p & aka.LEFT:
        gxmin -= dx
        gxmax -= dx
        play(_SND_CLICK)
    elif p & aka.RIGHT:
        gxmin += dx
        gxmax += dx
        play(_SND_CLICK)
    elif p & aka.UP:                     # zoom avant (fenêtre plus petite)
        cx = (gxmin + gxmax) * 0.5
        cy = (gymin + gymax) * 0.5
        gxmin = cx + (gxmin - cx) * 0.8
        gxmax = cx + (gxmax - cx) * 0.8
        gymin = cy + (gymin - cy) * 0.8
        gymax = cy + (gymax - cy) * 0.8
        play(_SND_CLICK)
    elif p & aka.DOWN:                    # zoom arrière
        cx = (gxmin + gxmax) * 0.5
        cy = (gymin + gymax) * 0.5
        gxmin = cx + (gxmin - cx) * 1.25
        gxmax = cx + (gxmax - cx) * 1.25
        gymin = cy + (gymin - cy) * 1.25
        gymax = cy + (gymax - cy) * 1.25
        play(_SND_CLICK)
    elif p & aka.C:
        gxmin, gxmax, gymin, gymax = -10.0, 10.0, -6.0, 6.0
        play(_SND_CLICK)
    elif p & aka.D:
        mode = MODE_CALC
        play(_SND_CLICK)


# aide du menu système AKA
aka.set_controls([
    "Calculatrice scientifique",
    "D-Pad: deplacer le curseur",
    "A: touche  B: effacer  C: AC",
    "= : calculer   D: tracer y=f(x)",
    "Courbe: <> defiler, ^v zoom, D retour",
])
aka.set_credits("Calculatrice AKA", "Jicehel", "MIT", "")

# ----------------------------------------------------------------------------
#  Boucle principale (dans une fonction : évite que ce build n'affiche la
#  valeur des expressions nues de premier niveau, ex. aka.update() -> True)
# ----------------------------------------------------------------------------
def run():
    while True:
        aka.update()
        p = aka.pressed()
        if mode == MODE_CALC:
            handle_calc(p)
            draw_calc()
        else:
            handle_graph(p)
            draw_graph()
        aka.display()


run()
