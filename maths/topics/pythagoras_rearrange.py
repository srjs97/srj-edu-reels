"""Topic: Pythagoras without algebra (rearrangement proof with 4 copies of a right triangle).

Facts checked (computed in Python before rendering):
- 3-4-5 triangle: 3² + 4² = 9 + 16 = 25 = 5², right angle between the legs 3 and 4.
- Big square side a + b = 7; area (a+b)² = 49; each triangle area ab/2 = 6; 49 − 4·6 = 25 = c².
- Arrangement A: triangles at the 4 corners leave a tilted square with vertices (a,0),(a+b,a),(b,a+b),(0,b),
  side √(a²+b²) = 5, area 25.
- Arrangement B: the same 4 triangles slid (pure translations) into two a×b rectangles leave an a×a and a b×b
  square: 9 + 16 = 25. Both arrangements checked by rasterising: no overlap, free area 25 in each.
- The 25 unit tiles fit the tilted 5×5 square exactly (rotated by atan(3/4) ≈ 36.87°).
- Ending question: 5² + 12² = 25 + 144 = 169 = 13², so yes, 5-12-13 is a right triangle.
"""
import math
from maths.engine import (W, H, WHITE, DIM, ORANGE, CYAN, PINK, YELLOW, GREEN, VIOLET, SANS, MATH,
                          clamp, prog, ease, ease_out, ease_back, lerp, window)

TITLE = "Pythagoras without algebra"
DURATION = 45.0
WOW_AT = 32.0
MUSIC_SEED = 0  # topic n = 3 -> 3 mod 3

A, B = 3, 4
S = A + B
C = 5
U = 90                     # px per unit in the big square
X0, Y0 = 225, 560          # big square top-left (world coords); 630 px wide
HU, HX, HY = 120, 360, 500  # hook triangle: unit size and right-angle corner

# triangles: (right-angle corner, end of leg a, end of leg b) in units
TRI = {1: [(0, 0), (A, 0), (0, B)],
       2: [(S, 0), (S, A), (A, 0)],
       3: [(S, S), (B, S), (S, A)],
       4: [(0, S), (0, B), (B, S)]}
SHIFT = {1: (0, A), 2: (0, 0), 3: (-B, 0), 4: (A, -B)}          # arrangement A -> B
FLY_IN = {2: (5.0, (420, -260)), 3: (5.8, (420, 420)), 4: (6.6, (-420, 420))}
SLIDE = {1: 12.6, 3: 13.8, 4: 15.0}
BACK0, BACK1 = 30.0, 31.8   # slide back to A (lands just before WOW_AT)
FADE_FIG = 36.0

# unit tiles: 9 cyan in the a² gap, 16 pink in the b² gap (arrangement B), targets in the tilted square
SRC = [((x + 0.5, y + 0.5), CYAN) for y in range(A) for x in range(A)] + \
      [((A + x + 0.5, A + y + 0.5), PINK) for y in range(B) for x in range(B)]
_u = (B / C, A / C)
_v = (-A / C, B / C)
DST = [(A + (i + 0.5) * _u[0] + (j + 0.5) * _v[0], (i + 0.5) * _u[1] + (j + 0.5) * _v[1])
       for j in range(C) for i in range(C)]
THETA = math.atan2(A, B)
TILE_T = [25.4 + i * 0.14 for i in range(9)] + [27.0 + i * 0.1 for i in range(16)]


def P(ux, uy):
    return X0 + ux * U, Y0 + uy * U


def slide_amount(k, t):
    if k == 2:
        return 0.0
    out = ease(prog(t, SLIDE[k], 0.9))
    back = ease(prog(t, BACK0 + (0.3 if k == 3 else 0.6 if k == 4 else 0.0), 1.2))
    return out * (1 - back)


def tri_points(k, t):
    """Screen points of triangle k at time t (world coords)."""
    if k == 1 and t < 4.4:
        m = ease(prog(t, 3.2, 1.1))
        u = lerp(HU, U, m)
        ox, oy = lerp(HX, X0, m), lerp(HY, Y0, m)
        return [(ox + x * u, oy + y * u) for x, y in TRI[1]]
    d = slide_amount(k, t)
    sx, sy = SHIFT[k][0] * d, SHIFT[k][1] * d
    dx = dy = 0.0
    if k in FLY_IN:
        t0, (fx, fy) = FLY_IN[k]
        p = 1 - ease_out(prog(t, t0, 0.7))
        dx, dy = fx * p, fy * p
    return [(X0 + (x + sx) * U + dx, Y0 + (y + sy) * U + dy) for x, y in TRI[k]]


def tri_alpha(k, t):
    a = 1.0 if k == 1 else clamp(prog(t, FLY_IN[k][0], 0.35))
    return a * lerp(1, 0.07, ease(prog(t, FADE_FIG, 0.8)))


def poly(r, pts, col, alpha):
    c = r.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*col, alpha)
    c.fill()


def draw_triangle(r, k, t, numbers=False):
    a = tri_alpha(k, t)
    if a <= 0.001:
        return
    ra, ea, eb = tri_points(k, t)
    poly(r, [ra, ea, eb], VIOLET, 0.42 * a)
    r.line(*ra, *ea, CYAN, a, lw=7)
    r.line(*ra, *eb, PINK, a, lw=7)
    r.line(*ea, *eb, YELLOW, a, lw=7)
    # right-angle mark
    q = 22 if k > 1 or t >= 4.4 else lerp(30, 22, ease(prog(t, 3.2, 1.1)))
    ux = ((ea[0] - ra[0]), (ea[1] - ra[1])); lu = math.hypot(*ux)
    vx = ((eb[0] - ra[0]), (eb[1] - ra[1])); lv = math.hypot(*vx)
    p1 = (ra[0] + ux[0] / lu * q, ra[1] + ux[1] / lu * q)
    p2 = (ra[0] + vx[0] / lv * q, ra[1] + vx[1] / lv * q)
    p3 = (p1[0] + vx[0] / lv * q, p1[1] + vx[1] / lv * q)
    r.line(*p1, *p3, WHITE, a * 0.8, lw=3); r.line(*p2, *p3, WHITE, a * 0.8, lw=3)


def draw_hook_labels(r, t):
    a = 1 - ease(prog(t, 3.0, 0.4))
    if a <= 0:
        return
    r.text("3", HX + 1.5 * HU, HY - 45, 70, CYAN, a, MATH)
    r.text("4", HX - 50, HY + 2 * HU, 70, PINK, a, MATH)
    r.text("5", HX + 1.5 * HU + 60, HY + 2 * HU + 40, 70, YELLOW, a, MATH)


def draw_square_frame(r, t):
    fig = lerp(1, 0.07, ease(prog(t, FADE_FIG, 0.8)))
    p = ease(prog(t, 4.2, 0.8))
    if p > 0:
        x1, y1 = X0 + S * U, Y0 + S * U
        for (xa, ya, xb, yb) in [(X0, Y0, x1, Y0), (x1, Y0, x1, y1), (x1, y1, X0, y1), (X0, y1, X0, Y0)]:
            r.line(xa, ya, xb, yb, WHITE, 0.55 * fig, lw=3, p=p)
    la = ease(prog(t, 7.4, 0.5)) * (1 - ease(prog(t, 29.6, 0.4)))
    if la > 0:  # top and right edges read a | b in BOTH arrangements
        r.text("a", X0 + A * U / 2, Y0 - 38, 54, CYAN, la, MATH, italic=True)
        r.text("b", X0 + (A + S) * U / 2, Y0 - 38, 54, PINK, la, MATH, italic=True)
        r.text("a", X0 + S * U + 40, Y0 + A * U / 2, 54, CYAN, la, MATH, italic=True)
        r.text("b", X0 + S * U + 40, Y0 + (A + S) * U / 2, 54, PINK, la, MATH, italic=True)


def draw_gaps(r, t):
    # A: tilted c² square
    ca = ease(prog(t, 8.8, 0.5)) * (1 - ease(prog(t, 12.4, 0.3)))
    if ca > 0:
        pts = [P(A, 0), P(S, A), P(B, S), P(0, B)]
        poly(r, pts, YELLOW, 0.30 * ca)
        r.text("c²", X0 + S * U / 2, Y0 + S * U / 2, 110 * lerp(0.6, 1, ease_back(prog(t, 8.8, 0.5))),
               YELLOW, ca, MATH, italic=True)
    # B: a² and b² squares (labels give way to the tile counts)
    ga = ease(prog(t, 16.2, 0.5)) * (1 - ease(prog(t, BACK0, 0.4)))
    gb = ease(prog(t, 16.8, 0.5)) * (1 - ease(prog(t, BACK0, 0.4)))
    lab = 1 - ease(prog(t, 25.2, 0.3))
    if ga > 0:
        r.rect(X0, Y0, A * U, A * U, CYAN, 0.22 * ga)
        r.text("a²", X0 + A * U / 2, Y0 + A * U / 2, 90 * lerp(0.6, 1, ease_back(prog(t, 16.2, 0.5))),
               CYAN, ga * lab, MATH, italic=True)
    if gb > 0:
        r.rect(X0 + A * U, Y0 + A * U, B * U, B * U, PINK, 0.22 * gb)
        r.text("b²", X0 + (A + S) * U / 2, Y0 + (A + S) * U / 2,
               110 * lerp(0.6, 1, ease_back(prog(t, 16.8, 0.5))), PINK, gb * lab, MATH, italic=True)


def draw_tiles(r, t):
    if t < TILE_T[0]:
        return
    fig = lerp(1, 0.07, ease(prog(t, FADE_FIG, 0.8)))
    c = r.ctx
    for idx, ((sx, sy), col) in enumerate(SRC):
        p = prog(t, TILE_T[idx], 0.25)
        if p <= 0:
            continue
        m = ease(prog(t, BACK0 + 0.2 + idx * 0.02, 1.3))
        dx, dy = DST[idx]
        ux, uy = lerp(sx, dx, m), lerp(sy, dy, m)
        # gentle arc while flying
        uy -= math.sin(math.pi * m) * 0.8
        x, y = P(ux, uy)
        side = (U - 8) * ease_back(p)
        a = clamp(p * 3) * fig
        c.save()
        c.translate(x, y)
        c.rotate(THETA * m)
        r.rect(-side / 2, -side / 2, side, side, col, 0.85 * a, r=7)
        r.rect(-side / 2, -side / 2, side, side, (1, 1, 1), 0.35 * a, r=7, fill=False, lw=2)
        c.restore()
    # counts on the two gap squares
    na = window(t, 26.0, BACK0 + 0.2, 0.3)
    nb = window(t, 28.4, BACK0 + 0.2, 0.3)
    if na > 0:
        k = sum(1 for i in range(9) if t >= TILE_T[i])
        r.text(str(k), X0 + A * U / 2, Y0 + A * U / 2, 96, WHITE, na, MATH, bold=True)
    if nb > 0:
        r.text("16", X0 + (A + S) * U / 2, Y0 + (A + S) * U / 2, 120, WHITE, nb, MATH, bold=True)
    # count 25 on the tilted square at the wow
    wa = ease_back(prog(t, WOW_AT, 0.4)) * (1 - ease(prog(t, 35.6, 0.4)))
    if wa > 0:
        r.glow(X0 + S * U / 2, Y0 + S * U / 2, 260, YELLOW, 0.35 * clamp(wa))
        r.text("25", X0 + S * U / 2, Y0 + S * U / 2, 140 * max(wa, 0.01), WHITE, clamp(wa), MATH, bold=True)


def particles(r, t, t0, cx, cy):
    p = prog(t, t0, 1.6)
    if p <= 0 or p >= 1:
        return
    cols = [CYAN, PINK, YELLOW, ORANGE, GREEN, VIOLET]
    for i in range(72):
        ang = i * 2.399963
        sp = 280 + (i * 97 % 420)
        d = ease_out(p) * sp
        r.circle(cx + math.cos(ang) * d, cy + math.sin(ang) * d, 7 * (1 - p) + 2, cols[i % 6], (1 - p) * 0.9)


def top_equation(r, t):
    y = 400
    if t < 3.4:  # hook equation sits under the triangle
        out = ease(prog(t, 3.0, 0.4))
        a = 1 - out
        r.math_row([("3", CYAN), ("2", CYAN, "sup"), (" + ", WHITE), ("4", PINK), ("2", PINK, "sup"),
                    (" = ", WHITE), ("5", YELLOW), ("2", YELLOW, "sup")], W / 2, 1140, 110, a)
        qa = 1 if t < 0.001 else 0.6 + 0.4 * math.sin(t * 7)
        r.glow(W / 2, 1300, 150, ORANGE, 0.3 * a)
        r.math_row([("why?", ORANGE)], W / 2, 1300, 96, a * qa)
        return
    a1 = window(t, 9.2, 19.6, 0.35)
    if a1 > 0:
        r.math_row([("leftover", WHITE), (" = ", DIM), ("c²", YELLOW)], W / 2, y - 45, 70, a1)
    a2 = window(t, 17.2, 19.6, 0.35)
    if a2 > 0:
        r.math_row([("leftover", WHITE), (" = ", DIM), ("a²", CYAN), (" + ", WHITE), ("b²", PINK)],
                   W / 2, y + 55, 70, a2)
    a3 = window(t, 19.8, 25.0, 0.35)
    if a3 > 0:
        r.math_row([("(a + b)²", WHITE), (" − 4", DIM), ("△", VIOLET)], W / 2, y - 45, 64,
                   window(t, 19.8, 22.4, 0.35))
        m = ease(prog(t, 22.4, 0.5))
        size = lerp(70, 88, ease_back(m)) if m > 0 else 70
        r.math_row([("c²", YELLOW), (" = ", WHITE), ("a²", CYAN), (" + ", WHITE), ("b²", PINK)],
                   W / 2, y + 55 - 50 * m, size, a3)
    a4 = window(t, 25.2, 35.7, 0.35)
    if a4 > 0:
        parts = [("3²", CYAN), (" + ", WHITE), ("4²", PINK)]
        if t >= 26.0:
            parts += [(" = ", DIM), ("9", CYAN)]
        if t >= 28.4:
            parts += [(" + ", WHITE), ("16", PINK)]
        r.math_row(parts, W / 2, y - 65, 74, a4)
        if t < WOW_AT:
            if t >= 29.0:
                pulse = 0.6 + 0.4 * math.sin(t * 8)
                r.math_row([("= ?", ORANGE)], W / 2, y + 35, 84, a4 * pulse)
        else:
            rv = ease(prog(t, WOW_AT, 0.25))
            r.math_row([("= ", DIM), ("25", WHITE), (" = ", DIM), ("5²", YELLOW)], W / 2, y + 35,
                       lerp(60, 92, ease_back(prog(t, WOW_AT, 0.4))), a4 * rv)


def camera(r, t):
    z = 1.0
    z += 0.08 * ease(prog(t, BACK0, 2.0)) * (1 - ease(prog(t, 34.5, 1.2)))
    r.set_camera(W / 2, H / 2, z)


def scene(r, t):
    r.push_world()
    draw_square_frame(r, t)
    draw_gaps(r, t)
    for k in (1, 2, 3, 4):
        if k == 1 or t >= FLY_IN[k][0]:
            draw_triangle(r, k, t)
    draw_tiles(r, t)
    draw_hook_labels(r, t)
    particles(r, t, WOW_AT, X0 + S * U / 2, Y0 + S * U / 2)
    r.pop()
    top_equation(r, t)
    # ending formula (template draws the end card below)
    if t >= 36.4:
        a = ease(prog(t, 36.6, 0.5))
        r.glow(W / 2, 820, 420, YELLOW, 0.16 * a)
        r.math_row([("a²", CYAN), (" + ", WHITE), ("b²", PINK), (" = ", WHITE), ("c²", YELLOW)],
                   W / 2, 760, 120 * lerp(0.7, 1, ease_back(prog(t, 36.6, 0.5))), a)
        r.text("for every right triangle", W / 2, 890, 46, DIM, ease(prog(t, 37.2, 0.5)), SANS, bold=True)


TAG = "PYTHAGORAS  ×  NO ALGEBRA"
QUESTION_AT = 41.0
QUESTION = "Does 5, 12, 13 make a right angle?"
CAPTIONS = [
    ("Why is 3² + 4² exactly 5²?", 0.0, 3.1),
    ("Make 4 copies of this right triangle", 3.6, 6.9),
    ("They fit in a square of side a + b", 7.1, 9.5),
    ("The gap in the middle is a square: c²", 9.7, 12.3),
    ("Now just slide the same 4 triangles", 12.5, 15.9),
    ("The gap becomes two squares: a² and b²", 16.1, 19.5),
    ("Same big square, same 4 triangles...", 19.8, 22.3),
    ("...so the gaps have the same area", 22.5, 25.0),
    ("For 3, 4, 5: count the tiles", 25.3, 28.9),
    ("9 + 16 tiles... slide them back", 29.1, WOW_AT),
    ("...they fill c² exactly: 25!", WOW_AT + 0.2, 36.0),
    ("This is the Pythagorean theorem", 37.0, 40.8),
]


def sfx():
    ev = [("pop", 0.1, 0.6, 0), ("click", 0.6, 0.5, 4), ("click", 1.0, 0.5, 7), ("pop", 1.6, 0.6, 12),
          ("whoosh", 3.1, 0.5), ("click", 4.3, 0.5, 0)]
    for i, k in enumerate((2, 3, 4)):
        ev += [("whoosh", FLY_IN[k][0] - 0.1, 0.35), ("pop", FLY_IN[k][0] + 0.55, 0.7, 2 + 3 * i)]
    ev += [("click", 7.4, 0.5, 5), ("chime", 8.9, 0.7, 7)]
    for i, k in enumerate((1, 3, 4)):
        ev += [("whoosh", SLIDE[k], 0.45), ("click", SLIDE[k] + 0.85, 0.55, 4 + 2 * i)]
    ev += [("chime", 16.3, 0.6, 4), ("chime", 16.9, 0.6, 9), ("whoosh", 19.7, 0.4), ("click", 19.9, 0.5, 3),
           ("pop", 22.5, 0.6, 7), ("chime", 22.6, 0.65, 12), ("whoosh", 25.2, 0.4)]
    for i, tt in enumerate(TILE_T):
        ev.append(("pop", tt, 0.45, (i % 9) + (0 if i < 9 else 5)))
    ev += [("chime", 26.7, 0.55, 4), ("chime", 28.7, 0.6, 9), ("whoosh", BACK0, 0.5),
           ("riser", WOW_AT, 0.7), ("boom", WOW_AT, 0.95), ("sparkle", WOW_AT + 0.05, 0.6, 12),
           ("chime", WOW_AT + 0.1, 0.7, 12), ("whoosh", FADE_FIG, 0.4), ("chime", 36.7, 0.6, 0)]
    return ev


YT_TITLE = "Pythagoras without algebra 🤯 Why 3² + 4² = 5² #shorts"
CAPTION = """Why is 3² + 4² exactly 5²? No algebra needed 🤯

Put 4 copies of a right triangle in a square of side a + b: the gap is c².
Slide the same 4 triangles around: the gap becomes a² + b².
Same square, same triangles, same gap → a² + b² = c² ✅
With 3, 4, 5: 9 + 16 = 25 tiles.

🧠 Your turn: does 5, 12, 13 make a right angle? Comment below 👇

📌 Save this for your next maths exam
🔔 Follow @srj_edu_app for a new maths visual every night"""
HASHTAGS = "#maths #math #mathematics #pythagoras #pythagoreantheorem #geometry #visualmath #mathproof #learnmaths #srjedu #keralastudents #psc #education #reels"
