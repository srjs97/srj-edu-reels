"""Topic: the sum of the first n odd numbers is n^2 (gnomon proof).

Facts checked: 1+3+5+7 = 16 = 4^2; 1+3+...+19 = 100 = 10^2 (10 terms);
1+3+...+99 has 50 terms ((99+1)/2) and equals 50^2 = 2500; (n+1)^2 - n^2 = 2n+1;
2+4+...+2n = n(n+1) (the ending question's answer: rectangles).
"""
import math
from maths.engine import (W, H, WHITE, DIM, ORANGE, CYAN, PINK, YELLOW, GREEN, VIOLET, SANS, MATH,
                          clamp, prog, ease, ease_out, ease_back, lerp, window)

TITLE = "Odd numbers secretly build squares"
DURATION = 46.0
WOW_AT = 35.9
MUSIC_SEED = 0

X0, Y0, CELL = 240, 600, 60
COLS = [ORANGE, CYAN, PINK, YELLOW, GREEN, VIOLET]
STARTS = {1: 3.6, 2: 6.6, 3: 9.8, 4: 13.2}
for _k in range(5, 11):
    STARTS[_k] = 19.8 + (_k - 5) * 0.85


def stagger(k):
    return 0.16 if k <= 4 else 0.05


def done_at(k):
    return STARTS[k] + (2 * k - 1) * stagger(k) + 0.2


def gnomon_cells(k):
    """Cells added to grow a (k-1)x(k-1) square into k x k, walked along the L."""
    c = [(k - 1, r) for r in range(k - 1)]        # right column, top -> down
    c.append((k - 1, k - 1))                       # corner
    c += [(col, k - 1) for col in range(k - 2, -1, -1)]  # bottom row, right -> left
    return c


def n_eff(t):
    return sum(ease(prog(t, STARTS[k], 0.9 if k <= 4 else 0.6)) for k in range(1, 11))


def zoom_for(n):
    return min(2.4, 620 / (CELL * max(n, 1)))


def camera(r, t):
    n = max(1.0, n_eff(t))
    cx, cy, z = X0 + CELL * n / 2, Y0 + CELL * n / 2, zoom_for(n)
    d = ease(prog(t, 25.6, 0.9)) * (1 - ease(prog(t, 32.6, 0.9)))  # explanation close-up on 5x5
    cx, cy, z = lerp(cx, X0 + 150, d), lerp(cy, Y0 + 190, d), lerp(z, 1.9, d)
    f = ease(prog(t, 39.6, 1.2))  # final pull-back
    z = lerp(z, 0.8, f); cy = lerp(cy, Y0 + 300 - 40, f)
    r.set_camera(cx, cy - 40 * (1 - f), z)


def draw_tiles(r, t):
    c = r.ctx
    z = r.camera[2]
    fade10 = 1 - ease(prog(t, 34.0, 0.4))
    final_dim = lerp(1, 0.0, ease(prog(t, 39.6, 0.8)))
    explain = ease(prog(t, 25.8, 0.6)) * (1 - ease(prog(t, 32.4, 0.6)))
    for k in range(1, 11):
        col = COLS[(k - 1) % len(COLS)]
        st = stagger(k)
        for i, (cx, cy) in enumerate(gnomon_cells(k)):
            p = prog(t, STARTS[k] + i * st, 0.28)
            if p <= 0:
                continue
            s = ease_back(p)
            a = clamp(p * 3) * fade10 * final_dim
            colr = col
            if explain > 0:
                if k == 5:
                    role = CYAN if cx == 4 and cy < 4 else PINK if cy == 4 and cx < 4 else YELLOW
                    colr = tuple(lerp(col[j], role[j], explain) for j in range(3))
                elif k < 5:
                    a *= lerp(1, 0.32, explain)
                else:
                    a *= lerp(1, 0.0, explain)
            x, y = X0 + cx * CELL + CELL / 2, Y0 + cy * CELL + CELL / 2
            side = (CELL - 6) * s
            r.rect(x - side / 2, y - side / 2, side, side, colr, a * 0.9, r=8)
            r.rect(x - side / 2, y - side / 2, side, side, (1, 1, 1), a * 0.35, r=8, fill=False, lw=2 / z)
        # "+odd" label beside a freshly added L (slow phase only)
        if k <= 4:
            la = window(t, STARTS[k] + 0.1, done_at(k) + 1.2, 0.3) * fade10
            if la > 0:
                lx = X0 + k * CELL + 18 / z
                ly = Y0 + k * CELL - CELL / 2
                r.text(f"+{2 * k - 1}", lx, ly, 46 / z, col, la, MATH, align="left")
    # side-length labels
    n = n_eff(t)
    nl = int(round(n))
    la = (1 - ease(prog(t, 25.4, 0.4))) * clamp(n) * fade10
    if t > 3.8 and la > 0 and abs(n - nl) < 0.25:
        side = nl * CELL
        r.text(str(nl), X0 + side / 2, Y0 + side + 40 / z, 40 / z, DIM, la * 0.9, MATH)
        r.text(str(nl), X0 - 40 / z, Y0 + side / 2, 40 / z, DIM, la * 0.9, MATH)
    # explanation labels (n, n, 1, n^2)
    if explain > 0:
        r.text("n", X0 + 5 * CELL + 26, Y0 + 2 * CELL, 52, CYAN, explain, MATH, italic=True, align="left")
        r.text("n", X0 + 2 * CELL, Y0 + 5 * CELL + 34, 52, PINK, explain, MATH, italic=True)
        r.text("1", X0 + 5 * CELL + 26, Y0 + 4.5 * CELL, 52, YELLOW, explain, MATH, align="left")
        r.text("n²", X0 + 2 * CELL, Y0 + 2 * CELL, 80, WHITE, explain, MATH, italic=True)


def draw_big_square(r, t):
    """Wow: 50 nested L-shapes (1+3+...+99) tile a 50x50 square in the same 600px area."""
    t0 = 34.2
    if t < t0:
        return
    a_all = lerp(1, 0.07, ease(prog(t, 39.6, 0.8)))
    cell = 600 / 50
    for k in range(1, 51):
        p = prog(t, t0 + (k - 1) * 0.032, 0.25)
        if p <= 0:
            break
        h = (k - 1) / 49
        col = tuple(lerp(ORANGE[j], CYAN[j], h) if h < 0.5 else lerp(CYAN[j], PINK[j], h) for j in range(3))
        a = ease(p) * a_all
        x = X0 + (k - 1) * cell
        r.rect(x + 1, Y0 + 1, cell - 2, k * cell - 2, col, a * 0.92)           # column arm incl. corner
        if k > 1:
            r.rect(X0 + 1, Y0 + (k - 1) * cell + 1, (k - 1) * cell - 2, cell - 2, col, a * 0.92)


def particles(r, t, t0, cx, cy):
    p = prog(t, t0, 1.6)
    if p <= 0 or p >= 1:
        return
    for i in range(70):
        ang = i * 2.399963
        sp = 300 + (i * 97 % 400)
        d = ease_out(p) * sp
        col = COLS[i % len(COLS)]
        r.circle(cx + math.cos(ang) * d, cy + math.sin(ang) * d, 7 * (1 - p) + 2, col, (1 - p) * 0.9)


def top_equation(r, t):
    """Running sum shown above the square."""
    y = 380
    if 3.4 <= t < 19.7:
        parts = []
        last = 0
        for k in range(1, 5):
            if t >= STARTS[k]:
                last = k
        for k in range(1, last + 1):
            a = ease(prog(t, STARTS[k], 0.3))
            if k > 1:
                parts.append((" + ", WHITE))
            parts.append((str(2 * k - 1), COLS[k - 1]))
        if last and t >= done_at(last):
            parts += [(" = ", WHITE), (str(last * last), WHITE), (" = ", DIM), (f"{last}²", ORANGE)]
        a = ease(prog(t, 3.4, 0.4)) * (1 - ease(prog(t, 19.3, 0.4)))
        r.math_row(parts, W / 2, y, 78, a)
    elif 19.7 <= t < 25.6:
        last = max(k for k in range(1, 11) if t >= STARTS[k] - 0.01) if t >= STARTS[5] else 4
        parts = [("1 + 3 + 5 + … + ", WHITE), (str(2 * last - 1), COLS[(last - 1) % 6])]
        if t >= done_at(10):
            parts += [(" = ", WHITE), ("100", WHITE), (" = ", DIM), ("10²", ORANGE)]
        a = ease(prog(t, 19.7, 0.3)) * (1 - ease(prog(t, 25.3, 0.3)))
        r.math_row(parts, W / 2, y, 70, a)
    elif 25.6 <= t < 32.6:
        a1 = window(t, 25.9, 29.7, 0.35)
        r.math_row([("n²", WHITE), (" + ", DIM), ("n", CYAN), (" + ", DIM), ("n", PINK), (" + ", DIM), ("1", YELLOW)],
                   W / 2, y - 40, 72, a1)
        r.math_row([("= ", DIM), ("(n + 1)²", WHITE)], W / 2, y + 60, 72, window(t, 27.6, 29.7, 0.35))
        a2 = window(t, 29.8, 32.6, 0.35)
        r.math_row([("(n + 1)²", WHITE), (" − ", DIM), ("n²", WHITE), (" = ", DIM), ("2n + 1", ORANGE)],
                   W / 2, y, 76, a2)
    elif 32.6 <= t < 39.7:
        a = ease(prog(t, 32.9, 0.4)) * (1 - ease(prog(t, 39.3, 0.4)))
        reveal = ease(prog(t, WOW_AT, 0.25))
        r.math_row([("1 + 3 + 5 + … + 99", WHITE)], W / 2, y - 30, 72, a)
        if reveal <= 0:
            pulse = 0.6 + 0.4 * math.sin(t * 8)
            r.math_row([("= ?", ORANGE)], W / 2, y + 80, 90, a * pulse)
        else:
            r.math_row([("= ", DIM), ("50²", ORANGE), (" = ", DIM), ("2500", YELLOW)], W / 2, y + 80,
                       lerp(60, 96, ease_back(prog(t, WOW_AT, 0.4))), a * reveal)


def scene(r, t):
    # camera(r, t) is called by the template before the background
    # ---- world layer
    if t >= 3.4:
        r.push_world()
        draw_tiles(r, t)
        draw_big_square(r, t)
        particles(r, t, WOW_AT, X0 + 300, Y0 + 300)
        r.pop()
    # ---- hook
    if t < 3.6:
        out = ease(prog(t, 3.0, 0.5))
        y = lerp(860, 600, out)
        terms = ["1", "3", "5", "7", "…", "99"]
        parts = []
        for i, s in enumerate(terms):
            if t >= 0.15 + i * 0.2 or t < 0.001:
                if parts:
                    parts.append((" + ", DIM))
                parts.append((s, COLS[i % 6] if s != "…" else WHITE))
        r.math_row(parts, W / 2, y, 92, 1 - out)
        qa = (1 if t < 0.001 else ease_back(prog(t, 1.5, 0.35))) * (1 - out)
        r.glow(W / 2, y + 190, 200, ORANGE, 0.35 * qa)
        r.math_row([("= ?", ORANGE)], W / 2, y + 190, 150 * max(qa, 0.01), qa)
    top_equation(r, t)
    # ---- ending formula (the template draws the question end card below it)
    if t >= 39.8:
        a = ease(prog(t, 39.9, 0.5))
        r.glow(W / 2, 820, 420, ORANGE, 0.18 * a)
        r.math_row([("1 + 3 + 5 + … + ", WHITE), ("(2n − 1)", CYAN), (" = ", DIM), ("n²", ORANGE)],
                   W / 2, 820, 80, a)


TAG = "ODD NUMBERS  ×  SQUARES"
QUESTION_AT = 43.0
QUESTION = "What do 2 + 4 + 6 + 8 + … build?"
CAPTIONS = [
    ("Can you add these in 3 seconds?", 0.0, 3.3),
    ("Start with 1 tile", 3.7, 6.4),
    ("Add the next odd number: 3", 6.7, 9.6),
    ("Add 5... still a perfect square", 9.9, 13.0),
    ("Add 7 → a 4 × 4 square", 13.3, 16.6),
    ("Every odd number completes a bigger square", 16.7, 19.6),
    ("10 odd numbers → 10 × 10 = 100", 22.6, 25.5),
    ("A square of side n, plus two strips of n, plus 1", 25.9, 29.6),
    ("That's 2n + 1: always the next odd number", 29.8, 32.6),
    ("50 odd numbers...", 33.2, WOW_AT),
    ("...make a 50 × 50 square!", WOW_AT + 0.2, 39.5),
    ("The first n odd numbers always add to n²", 40.2, 42.9),
]


def sfx():
    ev = [("click", 0.15 + i * 0.2, 0.6, i * 2) for i in range(6)]
    ev += [("pop", 1.5, 0.8, 0), ("whoosh", 3.0, 0.5)]
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31, 33, 36, 38, 40, 43]
    for k in range(1, 11):
        tiles = 2 * k - 1
        if k <= 4:
            for i in range(tiles):
                ev.append(("pop", STARTS[k] + i * stagger(k), 0.55, scale[i] - 5 + k))
            ev.append(("chime", done_at(k), 0.6, [0, 2, 4, 7][k - 1]))
        else:
            ev.append(("sparkle", STARTS[k], 0.5, k - 5))
            ev.append(("pop", STARTS[k], 0.5, k))
    ev += [("chime", done_at(10), 0.8, 12), ("whoosh", 25.6, 0.45), ("click", 25.9, 0.5),
           ("pop", 27.6, 0.5, 5), ("whoosh", 29.7, 0.35), ("chime", 29.85, 0.6, 7),
           ("whoosh", 32.6, 0.5), ("click", 32.9, 0.5), ("riser", WOW_AT, 0.7), ("boom", WOW_AT, 0.95),
           ("sparkle", WOW_AT + 0.05, 0.6, 12), ("chime", WOW_AT + 0.1, 0.7, 12),
           ("whoosh", 39.6, 0.4), ("chime", 39.95, 0.6, 0)]
    return ev


YT_TITLE = "Odd numbers secretly build squares 🤯 1+3+5+…+99 = ? #shorts"
CAPTION = """Can you add 1 + 3 + 5 + … + 99 in 3 seconds? 🤯

Every odd number adds an L-shape that turns a square into the next bigger square.
So the first n odd numbers always add up to n².
1 + 3 + 5 + … + 99 = 50² = 2500 ✅

🧠 Your turn: what do 2 + 4 + 6 + 8 + … build? Comment below 👇

📌 Save this for your next maths exam
🔔 Follow @srj_edu_app for 2 new maths visuals every day"""
HASHTAGS = "#maths #math #mathematics #mathtricks #visualmath #oddnumbers #squarenumbers #mathproof #learnmaths #srjedu #keralastudents #psc #education #reels"
