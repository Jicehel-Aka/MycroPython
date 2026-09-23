# User Manual — MicroPython on the AKA (English)

This app turns the AKA into a console you can **program in Python**. You write
your game in a `.py` file on the SD card — no need to recompile the firmware.

*Version française : [MANUEL.md](MANUEL.md).*

---

## 1. Installation

1. Flash the `micropython` app onto the console (see [README.md](README.md)).
2. Copy the `sdcard_files/py/` folder to the root of your SD card. At boot the
   firmware runs **`/sdcard/py/main.py`**.
3. By default, `main.py` is a **game selector**: it lists every `.py` file
   present in `/sdcard/py/` and launches whichever one you pick (see §7).
   `demo.py` (same folder) is a full hardware test (buttons, joystick,
   vibration) if you want to check everything works.

On power-up, the AKA automatically launches `/sdcard/py/main.py`.

---

## 2. Your first game

```python
import aka

W = aka.width()      # 320
H = aka.height()     # 240
x, y = W // 2, H // 2

while True:
    if aka.update():                    # REQUIRED once per frame
        aka.clear(0, 0, 0)             # clear the screen to black

        b = aka.buttons()
        if b & aka.LEFT:  x -= 3
        if b & aka.RIGHT: x += 3
        if b & aka.UP:    y -= 3
        if b & aka.DOWN:  y += 3

        aka.set_color(0, 220, 0)
        aka.fill_circle(x, y, 12)

        aka.display()                   # show the frame
    aka.sleep_ms(16)                    # ~60 frames per second
```

### The game loop

A frame is always built like this:

1. **`aka.update()`** — call it first. Reads the buttons **and** lets the AKA
   system menu take over if the player presses MENU. Returns `True` if your game
   should run this frame, `False` while the menu is showing (draw nothing then).
2. Draw (see §4).
3. **`aka.display()`** — send the image to the screen.
4. **`aka.sleep_ms(16)`** — pacing.

---

## 3. Buttons

`aka.buttons()` returns an integer "bit mask". Test a button with `&`:

```python
b = aka.buttons()
if b & aka.A:
    shoot()
```

| Constant | Button                |
|----------|-----------------------|
| `aka.UP` `aka.DOWN` `aka.LEFT` `aka.RIGHT` | D-pad |
| `aka.A` `aka.B` `aka.C` `aka.D` | action buttons |
| `aka.L1` `aka.R1` | shoulder triggers |
| `aka.RUN` `aka.MENU` | system buttons |

- `aka.pressed()` — buttons **just pressed** this frame (rising edge).
- `aka.released()` — buttons **just released** this frame.
- `aka.joystick()` — returns a tuple `(x, y)` (analog position).

> Holding RUN + MENU always returns to the console launcher — handled
> automatically, you don't need to do anything.

---

## 4. Drawing

The screen is **320 × 240** pixels, in color. Origin `(0, 0)` is top-left.
Colors are given as RGB (0-255).

| Function | Effect |
|----------|--------|
| `aka.set_color(r, g, b)` | set the current "pen" color |
| `aka.color(r, g, b)` | return the packed color (RGB565) without changing the pen |
| `aka.clear()` / `aka.clear(r, g, b)` | clear the whole screen (black, or a color) |
| `aka.pixel(x, y)` | one pixel |
| `aka.line(x0, y0, x1, y1)` | a line |
| `aka.hline(x, y, w)` / `aka.vline(x, y, h)` | horizontal / vertical line |
| `aka.rect(x, y, w, h)` / `aka.fill_rect(...)` | rectangle (outline / filled) |
| `aka.circle(x, y, r)` / `aka.fill_circle(...)` | circle (outline / filled) |
| `aka.triangle(x0,y0,x1,y1,x2,y2)` / `aka.fill_triangle(...)` | triangle |
| `aka.text(x, y, "text")` | draw text in the current color |
| `aka.display()` | show the built frame |
| `aka.width()` / `aka.height()` | screen size |

---

## 5. Time, vibration, sound, misc

| Function | Effect |
|----------|--------|
| `aka.ticks_ms()` | milliseconds since boot (integer) |
| `aka.sleep_ms(ms)` | pause (lets the system breathe) |
| `aka.vibrate(ms)` | vibrate the console for `ms` milliseconds (`ms=0` stops immediately) |
| `aka.is_vibrating()` | `True` if the console is currently vibrating |
| `aka.screenshot()` | save a screenshot (BMP) to the SD card |
| `aka.language()` | current console language code (`"fr"`, `"en"`, …) |
| `aka.tr("KEY")` | translate a key according to the language (see aka_runtime) |
| `aka.play_pcm8(data, loop=False)` | play an unsigned 8-bit PCM sample (`bytes`/`bytearray`, 128=silence) |
| `aka.is_sound_playing()` | `True` if a sound is currently playing |

`play_pcm8` copies the data internally (no need to keep the `bytes` object
alive after the call) and handles looping itself when `loop=True`.

---

## 6. Help built into the system menu

When the player presses **MENU**, the console shows its system menu (Resume,
Controls, Language, Volume, Credits, Quit). You can fill in your game's
**"Controls"** and **"Credits"** screens:

```python
aka.set_controls([
    "Arrows: move",
    "A: jump",
    "B: shoot",
    "MENU: pause",
])
aka.set_credits("My Game", "My Name", "MIT", "github.com/me/mygame")
```

Call once at the start of the script. Up to 12 control lines.

---

## 7. The game selector (`main.py`)

`main.py` automatically lists every `.py` file in `/sdcard/py/` (except
`main.py` itself and compatibility modules like `game8266.py`/`upygame.py`),
and shows them as a navigable list:

```python
games = aka.list_py("/sdcard/py")    # list the .py files in a folder
aka.run_file("/sdcard/py/pong.py")   # run another script, returns here when it exits
```

Up/Down to choose, A to launch. When the chosen game returns control (its
own "Quit"), the selector shows the list again — no recompilation needed to
add a new game, just copy the `.py` into `/sdcard/py/`. Check the provided
`main.py` for the full code — a good starting point if you want to
customize sorting or display.

---

## 8. Writing an arcade-style game with `game8266.py`

`game8266.py` (in `sdcard_files/py/`) is a compatibility layer built for this
studio, on top of the native `aka` module. It reimplements the
`Game8266`/`Rect` API of a classic collection of ESP8266 + OLED games (Billy
Cheung — breakout/invader/pong/snake/tetris), and also underpins original
games (Connect Four, Battleship). The 7 games shipped in `sdcard_files/py/`
are all reusable examples.

### Why this layer instead of the `aka` API directly?

- Fixed logical resolution (128×64, the original OLED's) automatically
  scaled up to the full AKA screen (320×240) — the game thinks in small
  coordinates, without worrying about scaling.
- Buttons, sound, randomness, pacing, all unified behind a compact `g.*` API.
- Seven games already written with it, directly copyable as templates.

### Typical game structure

```python
from game8266 import Game8266, Rect
g = Game8266()
g.set_controls(["Arrows: move", "A: shoot", "L: quit"])

exitGame = False
while not exitGame:
    # --- menu ---
    while True:
        g.display.fill(0)
        g.display.text('My Game', 0, 0, (255, 220, 0))
        g.display.text('A:Start  L:Quit', 0, 10, 1)
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

    if exitGame:
        break

    # --- game ---
    gameOver = False
    while not gameOver:
        g.display.fill(0)
        g.getBtn()
        if g.pressed(g.btnL):
            pass   # ... game logic ...
        # ... drawing ...
        g.display_and_wait()
```

### `Game8266` API (detailed reference)

**Display (`g.display`)** — logical coordinates 128×64, `c` accepts `0`/`1`
(black/white, like the original OLED) OR an `(r,g,b)` tuple directly (the
AKA has a real color screen, might as well use it: titles, HUD, special
states like a sunk ship or a Tetris piece):

- `g.display.fill(c)` — fills the whole screen (entire physical screen, see
  below) with one color. Call this first thing every frame.
- `g.display.rect(x, y, w, h, c)` — **outline** rectangle only, top-left
  corner at `(x,y)`.
- `g.display.fill_rect(x, y, w, h, c)` — **filled** rectangle.
- `g.display.circle(x, y, r, c)` — outline circle, centered on `(x,y)`,
  radius `r`.
- `g.display.fill_circle(x, y, r, c)` — filled circle.
- `g.display.text(s, x, y, c)` — text `s` (string), top-left corner at
  `(x,y)`. Fixed-size native font (not affected by sprite scaling).
- `g.display.show()` — sends the drawn buffer to the physical screen
  (equivalent to `aka.display()`). Nothing appears until `show()` is called.

**Input**:

- `g.getBtn()` — call **once per frame**, before reading any button. Refreshes
  hardware state; internally blocks while the AKA system menu is open (see
  §3 and "Redrawing after a system menu pause" below), and sets
  `g.menu_was_open` to `True` right after a menu closes.
- `g.pressed(mask)` — `True` if the button is currently **held down**.
- `g.justPressed(mask)` — `True` only on the frame the button **was just
  pressed** (rising edge, fires once per press).
- `g.justReleased(mask)` — same, but on **release** (falling edge).
- `g.btnU` / `g.btnD` / `g.btnL` / `g.btnR` / `g.btnA` / `g.btnB` — bitmask
  constants to pass to the three functions above.
- `g.getPaddle()` — returns an integer `0..1023`, simulates an analog
  potentiometer (the original ESP8266's ADC) from the AKA's real joystick
  X axis.

**Sound** — both functions **block** (the sound must finish before the code
continues), so sequences of notes stay audible in order rather than
cutting each other off:

- `g.playTone(note, duration_ms)` — plays a named note (`'c5'`, `'a4'`,
  `'f#3'`...) for `duration_ms` milliseconds.
- `g.playSound(freq_hz, duration_ms)` — like `playTone`, but with a direct
  frequency in Hz instead of a note name.

**Misc**:

- `g.random(a, b)` — random integer in `[a, b]` inclusive.
- `g.sleep_ms(ms)` — pause for `ms` milliseconds.
- `g.ticks_ms()` — current timestamp in milliseconds (increasing counter,
  useful for measuring an elapsed delay independent of frame pacing).
- `g.frameRate` — target frame rate (plain variable, directly settable:
  `g.frameRate = 10`). **Careful**: if your game moves something by one
  grid cell per frame, `frameRate` directly becomes your movement speed
  (see the gotcha below).
- `g.vol` / `g.max_vol` — current and maximum local volume (integers, for
  drawing a volume bar).
- `g.setVol()` — call inside the loop: adjusts `g.vol` if Button B is held +
  Up/Down pressed, and returns `True` that frame if an adjustment happened
  (so the caller can skip handling other buttons).
- `g.set_controls([...])` — replaces the help text shown in the AKA system
  menu (MENU button → "Controls") with a list of lines specific to this
  game. Call once at script startup.

**Pacing**:

- `g.display_and_wait()` — equivalent to `g.display.show()` followed by a
  pause calculated to respect `g.frameRate`.

### Gotchas already hit — avoid them from the start

This MicroPython build is **minimal** — plenty of things present on a PC
aren't here. Everything below was discovered while writing the 7 games in
this folder, usually via an unexpected `TypeError`/`NameError` on the
serial console:

- **No `math` module**: no `sqrt()`, etc. Write your own pure-Python
  version if needed (see `sqrt()` in `game8266.py`, Newton's method, a few
  lines is enough).
- **`const()`** (common in ESP8266/ESP32 MicroPython code) isn't
  guaranteed to be available — add `def const(x): return x` at the top of
  your file just in case; harmless if it already exists.
- **`sorted(..., key=...)`** and **`all(... for ... in ...)`** (with a
  generator expression): avoid them, use a manual loop or a simple sort
  instead (see `main.py` or `puissance4.py` for working examples).
- **`aka.pressed()` / `aka.released()` / `aka.buttons()` take NO
  argument** — they return the full bitmask. Write `aka.pressed() &
  aka.UP`, never `aka.pressed(aka.UP)` (an easy mistake, immediate
  `TypeError` — `game8266.py` already does this correctly if you go
  through `g.pressed(...)`).
- **Never mutate a list WHILE iterating it** with
  `for x in mylist: ... mylist.remove(x)` — Python can then skip the next
  item (never checked this turn). Typical symptom: "it feels like shots
  pass through enemies without hitting them." Iterate over a copy instead:
  `for x in mylist[:]: ...`.
- Always test with `python3 -m py_compile yourfile.py` on your PC before
  copying to the SD card — catches at least syntax errors without waiting
  for a full AKA reboot.

### Redrawing after a system menu pause

`g.getBtn()` internally blocks while the AKA system menu is open (see §3)
— but a game that draws **incrementally** (clears and redraws only what
moves, no `g.display.fill(0)` every frame — Tetris and Breakout in this
folder work this way) keeps leftover menu graphics on screen once it
closes, since nothing forces a real full redraw at that exact moment.

`g.getBtn()` exposes `g.menu_was_open` (`True` right after a menu closes)
for exactly this case:

```python
g.getBtn()
if g.menu_was_open:
    redraw_all()   # your own function that repaints EVERYTHING from current state
```

If your game already does a `g.display.fill(0)` followed by a full redraw
every single frame (most games in this folder), you don't need to do
anything — the next loop iteration fixes itself.

### Frame rate can BE your game speed — a classic trap

If your game moves something by one grid cell per frame (grid-based games
like Snake), `g.frameRate` **directly is** your movement speed, not just
visual smoothness. With `Game8266`'s default (30), that's 30 moves per
second — unplayable. Set a low, deliberate `g.frameRate` from the start
(`g.frameRate = 8`, for example), and let the player raise it afterward
through the menu if you want.

### D-pad: avoid combos of opposite directions

A combo like "hold Up AND Down together" (for a "quit" shortcut, say)
sounds reasonable on paper, but is often **physically impossible or very
uncomfortable** on a real D-pad — opposite directions are rarely reachable
at once with a single thumb. Prefer a single, dedicated key (`L` for quit,
by convention in this folder), even during active gameplay if `L`/`R` are
already used for movement — in that case, reserve the shortcut for a state
where movement is suspended anyway (the pause state, for instance).

### Layout: keep the HUD from overlapping the game

A mistake made (and fixed) on nearly every game shipped here: placing a
score/title text at a position that ends up overlapping the play field
once the grid is drawn at its real size. Before locking in your play
field's dimensions, work out the total vertical budget: HUD height + play
field height + bottom margin ≤ 64 (logical resolution). Reserve the HUD
strip *before* sizing everything else, not as an afterthought.

If your play field already exists and its physics (bounces, bounds) is
built on `0..height`, no need to recompute everything: keep the game
coordinates (`bat.y`, `ball.y`...) **relative to the play field** as
before, and add a simple offset **only when drawing**:

```python
PLAY_TOP = 16   # room reserved for the HUD above the play field

g.display.fill_rect(bat.x, bat.y + PLAY_TOP, bat_w, bat_h, color)
```

The physics doesn't change a single line; only the display shifts (see
`pong.py` for a complete example).

### `fill()` clears the whole physical screen, not just the logical area

`g.display.fill(c)` clears the **entire** AKA screen, borders included —
not just the 128×64 logical pixels. This is deliberate: if something draws
even slightly outside the logical area (a projectile right at the play
field's edge, say, just before it gets removed next turn), it must still
disappear on the next `fill()`. Don't assume a partial clear is enough if
you reimplement your own display logic directly on top of `aka`.

------

## 9. Porting a Pokitto Python game (upygame / umachine)

Many Pokitto games written in MicroPython use a `pygame`-like compatibility
library, **uPyGame** (`import upygame as pygame` + `import umachine`),
officially documented by Pokitto. Four files provided in `sdcard_files/py/`
reimplement this subset on top of the `aka` module:

Data format expected (same as Pokitto, confirmed via the official
PokittoLib source code): 16-color RGB565 palette; `Surface` pixels are 4
bits per pixel, palette index 0-15, high nibble = first pixel of the pair
(`GS4_HMSB` format).

### `upygame.py`

- `Rect(x, y, w, h)` — also `Rect(other_rect)` or `Rect((x,y,w,h))`.
  Read-only properties: `.width`, `.height`, `.centerx`, `.centery`,
  `.left`, `.right`, `.top`, `.bottom`. Method `.colliderect(other)`.
- `display.init(...)` — does nothing (hardware is already set up by
  `main.cpp`), present for call compatibility only.
- `display.set_mode(...)` — clears the screen and returns `screen`.
  **Important**: on the real Pokitto the screen is already clean at this
  point; most games never clear it themselves again afterward.
- `display.set_palette_16bit(values)` — loads a list of 16 RGB565 integers
  as the active palette.
- `display.flip()` — sends the buffer to the screen (equivalent to
  `aka.display()`).
- `draw.text(x, y, s, color_index=3)` — text at the given palette index.
  Automatically substitutes Pokitto control characters used as button
  icons (`chr(21)`→`[A]`, `chr(22)`→`[B]`, etc. — the AKA font doesn't
  know Pokitto's proprietary font).
- `draw.set_background_color(idx)` / `draw.set_transparent_color(idx)` —
  sets the palette index used as background / as the transparent color for
  `Surface.blit()`.
- `Surface(width, height, pixels)` — 4-bit indexed color sprite.
  `.get_rect()`, `.fill(color_index)`, `.blit(x, y, transparent=True)`
  (draws to screen in logical Pokitto coordinates 220×176, automatically
  scaled — see §8 for the principle).
- `screen.get_rect()` / `screen.blit(surface, x, y, transparent=True)` —
  object returned by `display.set_mode()`.
- `mixer.Sound(...)` — `.play_sfx(data, length=None, loop=False)` (`data`:
  unsigned 8-bit PCM, via `aka.play_pcm8`), `.is_playing()`, `.stop()`.
- `event.poll()` — returns **one** event (`KEYDOWN`/`KEYUP`) or `NOEVENT`.
  **Refreshes hardware internally** (calls `aka.update()` and clears the
  screen) — this IS the function to call once per frame in this subset, no
  Pokitto game calls `aka.update()` explicitly on its own.
- Constants: `NOEVENT`, `KEYDOWN`, `KEYUP`, `K_UP`/`K_DOWN`/`K_LEFT`/
  `K_RIGHT`, `BUT_A`/`BUT_B`/`BUT_C`/`BUT_D`.

### `umachine.py`

- `time_ms()` — alias for `aka.ticks_ms()`.
- `Cookie(name, buffer)` — persistent save. `buffer` is a `bytearray` the
  game keeps and modifies directly.
  - `.load()` — fills `buffer` from the save file; does nothing if it
    doesn't exist yet (first playthrough).
  - `.save()` — writes `buffer` to the save file (in the game's own
    folder, automatically determined via `sys.path[0]`).

### `urandom.py`

Pure-Python implementation (16-bit xorshift) — no dependency on a native
`random`/`urandom` module whose availability isn't guaranteed depending on
the build. Capped at 16 bits per draw (plenty for gameplay, not a
cryptographic use case).

- `getrandbits(n)` — integer of `n` random bits, `0 <= n <= 16`.
- `randint(a, b)` — random integer in `[a, b]` inclusive.
- `random()` — float in `[0.0, 1.0)`.
- `seed(n=None)` — resets the seed (`None` = from the clock).

### `sprite.py`

Near-direct port of pygame's actual `sprite.py` module (LGPL license
preserved), for games that use `sprite.Group()`/`sprite.Sprite`.

- `Sprite` — `.add(*groups)`, `.remove(*groups)`, `.update(*args)`,
  `.kill()`, `.groups()`, `.alive()`.
- `Group` (and `AbstractGroup`) — `.sprites()`, `.add(*sprites)`,
  `.remove(*sprites)`, `.has(*sprites)`, `.copy()`, `.update(*args)`,
  `.draw(surface)` (calls `surface.blit()` for each sprite in the group),
  `.clear(surface, background)`, `.empty()`.

---

**Current status**: correctness-first implementation (pixel-by-pixel drawing
via `aka.pixel()`/`aka.fill_rect()`) — functional but potentially slow for
many sprites per frame. If needed, the next step is a native
`aka.blit_indexed(...)` function doing the work in C, without changing the
Python API games see.

A Pokitto game can often be copied almost as-is into `/sdcard/py/` (or its
own folder, see next section), as long as it only uses this API subset (no
TAS mode, no `Tilemap`, no hardware sprites via `setHwSprite` — not covered
yet).

------

## 10. Turning a Python game into a standalone AKA app

By default, this "MicroPython" app runs `/sdcard/py/main.py` and shows up in
the AKA loader as **one generic game**. For a specific Python game to appear
**as its own app**, with its own icon and name in the loader (exactly like a
regular C++ game):

1. Copy this entire project (the `micropython`/`aka_runtime`/`gamebuino`
   components included, **unmodified**) into a new project folder.
2. In `main/main.cpp`, only adapt:
   - `akaRuntime.begin("<game_id>")` (instead of `"micropython"`)
   - `AKA_MAIN_PY "/sdcard/<game_id>/main.py"` (the game's own folder)
   - `aka_hal_set_credits(...)` / `aka_hal_set_controls(...)` (game credits)
3. Place the game's `.py` files (plus `upygame.py`/`umachine.py`/
   `urandom.py`/`sprite.py` if needed) into `sdcard_files/<game_id>/`.
4. Give the project its own `port_manifest.json`, `screen.bmp` and
   `meta.json` (see this project's own `sdcard_files/micropython/` folder
   for an example, for the generic launcher itself).

This generic launcher and dedicated per-game launchers coexist without
conflict — `aka.list_py()`/`aka.run_file()` remain available in both cases
if a game wants to offer its own script submenu.

---

## 11. Troubleshooting

- **Frozen / blank screen**: did you call `aka.display()` after drawing, and
  `aka.update()` at the start of the frame?
- **"Fichier .py introuvable" on screen**: check that `/sdcard/py/main.py`
  exists (a `py` folder at the SD root).
- **Python error**: the message (with line number) is printed to the USB serial
  console — plug in the AKA and open `idf.py monitor` to read it.
- **Game is slow**: do less work per frame, or increase `aka.sleep_ms`.
- **`TypeError: function takes 0 positional arguments but 1 were given`**:
  most likely `aka.pressed(aka.UP)` instead of `aka.pressed() & aka.UP` —
  see §8.
- **`NameError: name 'X' isn't defined`** when importing a standard module
  (`math`, `random`...) or using `const()`: this MicroPython build is
  minimal, several "standard" features aren't included. Check first
  whether `game8266.py` already provides a pure-Python alternative (e.g.
  `sqrt`), otherwise write your own — see §8.
- **Graphic trails/leftovers never disappear**: make sure you clear the
  **entire** screen at the start of each frame (not just a partial area) —
  anything drawn even slightly outside the cleared zone stays there
  forever. See §8, last subsection.
- **Score/title overlaps the play field**: your vertical budget (HUD +
  play field + margin) probably exceeds the logical resolution (128×64
  with `game8266.py`, or `aka.width()`/`aka.height()` directly). Reserve
  the HUD strip *before* sizing everything else — see §8.
