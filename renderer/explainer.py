"""Explainer-style 9:16 reel (optional voiceover via spec "voice"): one idea per scene, a big code-drawn diagram,
an English heading on top and a Malayalam subtitle box at the bottom.
usage: explainer.py spec.json out_silent.mp4 cues.json   (FRAMES=1,5.5 renders PNGs only)
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import illus

W, H, FPS = 1080, 1920, 30
ML_BOLD = "/usr/share/fonts/opentype/malayalam/Manjari-Bold.otf"
EN_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"

spec = json.load(open(sys.argv[1]))
SCENES = spec["scenes"]
COLA = tuple(spec.get("colA", (255, 90, 80)))
COLB = tuple(spec.get("colB", (70, 150, 255)))

DARK_INK = (30, 26, 70)
WHITE = (255, 255, 255)
YEL = (255, 196, 40)
ORANGE = (255, 150, 30)
TEAL = (40, 200, 170)
GREEN = (30, 190, 120)
RED = (240, 70, 80)


def col(c, default):
    return tuple(c) if c else default


# ---------------- easing ----------------
def clamp(x):
    return min(max(x, 0.0), 1.0)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def back(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


# ---------------- text ----------------
_fonts = {}


def is_ml(s):
    return any("ഀ" <= ch <= "ൿ" for ch in s)


SYM_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"   # has arrows and ≤ ≥ that Noto Sans lacks


def fnt(size, ml):
    k = (size, ml)
    if k not in _fonts:
        path = ML_BOLD if ml is True else SYM_BOLD if ml == "sym" else EN_BOLD
        _fonts[k] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fonts[k]


_tc = {}


def txt(s, size, color, maxw=980, shadow=False, stroke=0, stroke_col=(0, 0, 0)):
    k = (s, size, tuple(color), maxw, shadow, stroke, tuple(stroke_col))
    if k in _tc:
        return _tc[k]
    ml = is_ml(s) or ("sym" if any(ch in "≤≥↑↗←→" for ch in s) else False)
    while True:
        f = fnt(size, ml)
        bb = f.getbbox(s, stroke_width=stroke)
        if bb[2] - bb[0] <= maxw or size <= 22:
            break
        size -= 2
    pad = 16
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    org = (pad - bb[0], pad - bb[1])
    if shadow:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((org[0], org[1] + 4), s, font=f, fill=(0, 0, 0, 110))
        im = Image.alpha_composite(im, g.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(im).text(org, s, font=f, fill=tuple(color) + (255,), stroke_width=stroke, stroke_fill=tuple(stroke_col) + (255,))
    _tc[k] = im
    return im


def paste(fr, im, cx, cy, scale=1.0, alpha=1.0, rot=0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def pill(s, bg, fg=WHITE, size=44, padx=30, pady=14, shadow=True):
    k = ("pill", s, tuple(bg), tuple(fg), size)
    if k in _tc:
        return _tc[k]
    t = txt(s, size, fg, maxw=900)
    t = t.crop(t.getbbox())
    w, h = t.width + 2 * padx, t.height + 2 * pady
    im = Image.new("RGBA", (w + 20, h + 24), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((10, 16, w + 10, h + 16), h // 2, fill=(0, 0, 0, 70))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(im).rounded_rectangle((10, 8, w + 10, h + 8), h // 2, fill=tuple(bg) + (255,))
    im.alpha_composite(t, (10 + padx, 8 + pady))
    _tc[k] = im
    return im


# ---------------- icons ----------------
def make_rock(size, seed, base=(120, 112, 104), craters=6):
    r = np.random.default_rng(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    n = 22
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rad = size * 0.42 * (1 + 0.18 * np.sin(ang * 2 + r.random() * 6) + 0.08 * r.standard_normal(n))
    d.polygon([(size / 2 + rr * math.cos(a), size / 2 + rr * math.sin(a) * 0.82) for a, rr in zip(ang, rad)], fill=base + (255,))
    for _ in range(craters):
        cx, cy = size / 2 + r.uniform(-0.26, 0.26) * size, size / 2 + r.uniform(-0.2, 0.2) * size
        cr = size * r.uniform(0.04, 0.1)
        d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=tuple(int(c * 0.7) for c in base) + (255,))
    arr = np.array(im).astype(float)
    yy, xx = np.mgrid[0:size, 0:size] / size
    arr[..., :3] *= (1.25 - 0.9 * ((xx + yy) / 2))[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def make_frags(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for i, (s, x, y) in enumerate([(0.36, 0.3, 0.3), (0.26, 0.72, 0.28), (0.22, 0.5, 0.62), (0.3, 0.25, 0.75), (0.18, 0.8, 0.7)]):
        r = make_rock(int(size * s), 100 + i, base=(150, 120, 95), craters=2)
        im.alpha_composite(r, (int(size * x - r.width / 2), int(size * y - r.height / 2)))
    return im


_ic = {}


def icon(name, size):
    k = (name, size)
    if k in _ic:
        return _ic[k]
    if name == "rock:asteroid":
        im = make_rock(size, 11, craters=9)
    elif name == "rock:meteoroids":
        im = make_frags(size)
    elif name == "rock:small":
        im = make_rock(size, 101, base=(150, 120, 95), craters=3)
    else:
        im = illus.emoji_img(name, size)
    _ic[k] = im
    return im


def glow(r, c, a=150):
    k = ("glow", r, tuple(c), a)
    if k not in _ic:
        s = r * 4
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=tuple(c) + (a,))
        _ic[k] = im.filter(ImageFilter.GaussianBlur(r * 0.5))
    return _ic[k]


# ---------------- backgrounds ----------------
def _bg(kind):
    y = np.linspace(0, 1, H)[:, None, None]
    x = np.linspace(0, 1, W)[None, :, None]
    if kind == "dark":
        top, bot = np.array([22, 16, 56]), np.array([46, 28, 104])
        blobs = [(0.2, 0.28, 0.45, (70, 40, 150), 0.45), (0.9, 0.8, 0.5, (90, 50, 170), 0.4)]
    else:
        top, bot = np.array([255, 246, 222]), np.array([255, 222, 178])
        blobs = [(0.15, 0.35, 0.4, (255, 252, 240), 0.6), (0.9, 0.85, 0.45, (255, 200, 150), 0.45)]
    g = top * (1 - y) + bot * y
    for cx, cy, r, c, s in blobs:
        d = np.exp(-(((x - cx) ** 2 + ((y - cy) * 0.56) ** 2) / (r * r * 0.3)))
        g = g * (1 - s * d) + np.array(c) * s * d
    im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    if kind == "dark":
        d = ImageDraw.Draw(im)
        rs = np.random.default_rng(5)
        for _ in range(90):
            sx, sy, a = rs.random() * W, rs.random() * H, int(40 + 90 * rs.random())
            d.ellipse((sx - 2, sy - 2, sx + 2, sy + 2), fill=(255, 255, 255, a))
    return im


BGS = {"dark": _bg("dark"), "light": _bg("light")}


def ink(kind):
    return WHITE if kind == "dark" else DARK_INK


# ---------------- caption box ----------------
def caption_img(s):
    k = ("cap", s)
    if k in _tc:
        return _tc[k]
    size, maxw = 58, 860
    f = fnt(size, True)
    toks = []
    for i, part in enumerate(s.split("**")):
        for wd in part.split():
            toks.append((wd, i % 2 == 1))
    lines, cur, cw = [], [], 0
    sp = f.getlength(" ")
    for wd, hl in toks:
        wl = f.getlength(wd)
        if cur and cw + sp + wl > maxw:
            lines.append((cur, cw)); cur, cw = [], 0
        cw += (sp if cur else 0) + wl
        cur.append((wd, hl, wl))
    if cur:
        lines.append((cur, cw))
    lh = int(size * 1.45)
    bw = int(max(c for _, c in lines)) + 110
    bh = lh * len(lines) + 70
    im = Image.new("RGBA", (bw + 30, bh + 34), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((15, 24, bw + 15, bh + 24), 38, fill=(0, 0, 0, 90))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((15, 12, bw + 15, bh + 12), 38, fill=(22, 18, 44, 250), outline=(40, 170, 150, 255), width=4)
    y = 12 + 35
    for words, cwid in lines:
        x = 15 + (bw - cwid) / 2
        for wd, hl, wl in words:
            d.text((x, y), wd, font=f, fill=(YEL if hl else WHITE) + (255,))
            x += wl + sp
        y += lh
    _tc[k] = im
    return im


# ---------------- primitives ----------------
def tri(u):
    u = u % 2.0
    return u if u < 1 else 2 - u


def particles(d, x0, y0, x1, y1, n, speed, tl, seed, dot, r=10):
    rs = np.random.default_rng(seed)
    p = rs.random((n, 2))
    v = (rs.random((n, 2)) - 0.5) * 2
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    for i in range(n):
        px = x0 + r + (x1 - x0 - 2 * r) * tri(p[i, 0] + v[i, 0] * speed * tl * 0.35)
        py = y0 + r + (y1 - y0 - 2 * r) * tri(p[i, 1] + v[i, 1] * speed * tl * 0.35 * 0.6)
        d.ellipse((px - r - 4, py - r - 4, px + r + 4, py + r + 4), fill=tuple(dot) + (70,))
        d.ellipse((px - r, py - r, px + r, py + r), fill=tuple(dot) + (255,))


def beaker(fr, cx, cy, w, h, liquid, dot, speed, n, tl, seed, level=0.72, steam=False, shape="beaker", kind="dark"):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    rad = 30 if shape == "beaker" else 22
    d.rounded_rectangle((x0, y0, x1, y1), rad, fill=(255, 255, 255, 40 if kind == "dark" else 120))
    top = y1 - (y1 - y0) * level
    if shape == "box":
        top = y0
    # liquid with wave
    pts = [(x0 + 6, y1 - 6)]
    for i in range(41):
        xx = x0 + 6 + (w - 12) * i / 40
        pts.append((xx, top + 8 * math.sin(i / 40 * 2 * math.pi * 2 + tl * 3)))
    pts.append((x1 - 6, y1 - 6))
    liq = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(liq).polygon(pts, fill=tuple(liquid) + (235,))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((x0 + 6, y0 + 6, x1 - 6, y1 - 6), rad - 6, fill=255)
    lay.paste(liq, (0, 0), Image.composite(liq, Image.new("RGBA", (W, H)), mask).getchannel("A"))
    d = ImageDraw.Draw(lay)
    particles(d, x0 + 14, top + 16, x1 - 14, y1 - 14, n, speed, tl, seed, dot)
    edge = (245, 245, 255, 255)
    d.rounded_rectangle((x0, y0, x1, y1), rad, outline=edge, width=8)
    if shape == "beaker":
        d.line((x0 - 22, y0 + 2, x1 + 22, y0 + 2), fill=edge, width=10)
        for k in range(4):
            yy = y0 + (y1 - y0) * (0.2 + 0.18 * k)
            d.line((x0 + 22, yy, x0 + 62, yy), fill=(255, 255, 255, 180), width=5)
        d.rectangle((x0 + 26, y0 + 60, x0 + 46, y1 - 24), fill=(255, 255, 255, 50))
    if steam:
        for k in range(3):
            sx = cx - w * 0.25 + k * w * 0.25
            ph = tl * 1.4 + k
            a = int(140 * (0.5 + 0.5 * math.sin(ph * 2)))
            pts = [(sx + 14 * math.sin(j / 3 + ph * 2), y0 - 30 - j * 9) for j in range(12)]
            d.line(pts, fill=(200, 200, 230, a), width=7, joint="curve")
    fr.alpha_composite(lay)


# ---------------- visuals ----------------
def V_hero(fr, v, tl, kind, ent):
    items = v["items"]
    n = len(items)
    xs = [W / 2] if n == 1 else [W * 0.28, W * 0.72] if n == 2 else [W * 0.2, W * 0.5, W * 0.8]
    cy = v.get("y", 830)
    for i, it in enumerate(items):
        e = back((tl + ent - 0.15 * i) / 0.45)
        sz = int(it.get("size", 520 if n == 1 else 400 if n == 2 else 280))
        bob = 12 * math.sin(tl * 2.2 + i)
        gc = col(it.get("glow"), (255, 170, 60))
        paste(fr, glow(int(sz * 0.42), gc, 120 if kind == "dark" else 90), xs[i], cy, e)
        paste(fr, icon(it["icon"], sz), xs[i], cy + bob, e, rot=4 * math.sin(tl * 1.6 + i))
        if it.get("label"):
            lc = col(it.get("labelCol"), RED if i == 0 else (70, 150, 255))
            paste(fr, pill(it["label"], lc, size=46), xs[i], cy + sz * 0.62, back((tl + ent - 0.3 - 0.15 * i) / 0.4))
        if it.get("name"):
            nc = col(it.get("nameCol"), COLA if i == 0 else COLB)
            paste(fr, txt(it["name"], 70, nc, maxw=480, shadow=kind == "dark"), xs[i], cy + sz * 0.62 + (90 if it.get("label") else 10), back((tl + ent - 0.35) / 0.4))
    if v.get("vs") and n == 2:
        paste(fr, vs_badge(), W / 2, cy, back((tl + ent - 0.3) / 0.4) * (1 + 0.06 * abs(math.sin(tl * 4))))


def vs_badge():
    k = "vs"
    if k not in _ic:
        im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((20, 20, 180, 180), fill=ORANGE + (255,), outline=WHITE + (255,), width=8)
        t = txt("VS", 64, WHITE)
        t = t.crop(t.getbbox())
        im.alpha_composite(t, ((200 - t.width) // 2, (200 - t.height) // 2 - 4))
        _ic[k] = im
    return _ic[k]


def card(w, h, fill=(255, 255, 255, 250)):
    k = ("card", w, h, fill)
    if k not in _ic:
        im = Image.new("RGBA", (w + 40, h + 50), (0, 0, 0, 0))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((20, 32, w + 20, h + 32), 40, fill=(0, 0, 0, 60))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(12)))
        ImageDraw.Draw(im).rounded_rectangle((20, 20, w + 20, h + 20), 40, fill=fill)
        _ic[k] = im
    return _ic[k]


def V_bars(fr, v, tl, kind, ent):
    cards = v["cards"]
    cw, ch = 470, 800
    xs = [W * 0.27, W * 0.73]
    cy = 830
    for i, c in enumerate(cards):
        e = ease_out((tl + ent - 0.12 * i) / 0.4)
        x = xs[i]
        y = cy + 60 * (1 - e)
        paste(fr, card(cw, ch), x, y, 1, e)
        if c.get("icon"):
            paste(fr, icon(c["icon"], 230), x, y - ch / 2 + 170 + 8 * math.sin(tl * 2 + i), e)
        if c.get("title"):
            paste(fr, txt(c["title"], 48, COLA if i == 0 else COLB, maxw=420), x, y - ch / 2 + 320, e)
        bars = c["bars"]
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        bw, bh = 120, 360
        base = y + ch / 2 - 90
        for j, b in enumerate(bars):
            bx = x + (j - (len(bars) - 1) / 2) * 175
            d.rounded_rectangle((bx - bw / 2, base - bh, bx + bw / 2, base), 22, fill=(232, 232, 240, int(255 * e)))
            g = ease_out((tl + ent - 0.6 - 0.25 * j - 0.2 * i) / 0.9) * b["value"]
            hh = max(26, bh * g)
            bc = col(b.get("col"), RED if j == 0 else ORANGE)
            d.rounded_rectangle((bx - bw / 2, base - hh, bx + bw / 2, base), 22, fill=bc + (int(255 * e),))
            fr.alpha_composite(lay); lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            paste(fr, txt(b["label"], 36, DARK_INK), bx, base + 40, 1, e)
            if b.get("text"):
                paste(fr, txt(b["text"], 38, bc), bx, base - hh - 32, 1, clamp((tl + ent - 1.2 - 0.25 * j) / 0.3))
    if v.get("badge"):
        paste(fr, pill(v["badge"], ORANGE, size=60, padx=26), W / 2, cy - 400, back((tl + ent - 1.0) / 0.4) * (1 + 0.05 * math.sin(tl * 5)))


def V_particles(fr, v, tl, kind, ent):
    boxes = v["boxes"]
    n = len(boxes)
    xs = [W / 2] if n == 1 else [W * 0.27, W * 0.73]
    bw = 760 if n == 1 else 400
    bh = v.get("h", 520 if n == 1 else 480)
    cy = v.get("y", 760)
    for i, b in enumerate(boxes):
        e = ease_out((tl + ent - 0.12 * i) / 0.4)
        if e <= 0.02:
            continue
        lq = col(b.get("liquid"), (220, 70, 60) if i == 0 else (50, 90, 200))
        dot = col(b.get("dot"), (255, 190, 90) if i == 0 else (150, 210, 255))
        beaker(fr, xs[i], cy + 50 * (1 - e), bw, bh, lq, dot, b.get("speed", 1.0), b.get("n", 18), tl, 7 + i,
               level=b.get("level", 0.78), steam=b.get("steam", False), shape=b.get("shape", "beaker"), kind=kind)
        if b.get("label"):
            paste(fr, pill(b["label"], col(b.get("labelCol"), RED if i == 0 else (70, 150, 255)), size=48),
                  xs[i], cy + bh / 2 + 80, back((tl + ent - 0.35 - 0.12 * i) / 0.4))
        if b.get("sub"):
            paste(fr, txt(b["sub"], 40, ink(kind)), xs[i], cy + bh / 2 + 165, 1, clamp((tl + ent - 0.6) / 0.3))
    if v.get("chip"):
        paste(fr, pill(v["chip"], WHITE, DARK_INK, size=46), W / 2, cy + bh / 2 + (250 if any(b.get("sub") for b in boxes) else 180),
              back((tl + ent - 0.8) / 0.4))


def fmt_num(x, dec):
    return f"{x:,.{dec}f}"


def V_number(fr, v, tl, kind, ent):
    items = v["items"]
    n = len(items)
    xs = [W / 2] if n == 1 else [W * 0.28, W * 0.72]
    cy = v.get("y", 900)
    for i, it in enumerate(items):
        e = back((tl + ent - 0.15 * i) / 0.4)
        if it.get("icon"):
            paste(fr, icon(it["icon"], 340 if n == 1 else 220), xs[i], cy - 290, e)
        p = ease_out((tl + ent - 0.2) / 1.4)
        val = it["value"] * p
        s = it.get("prefix", "") + fmt_num(val, it.get("dec", 0)) + it.get("suffix", "")
        c = col(it.get("col"), YEL if kind == "dark" else (230, 90, 20))
        paste(fr, txt(s, 150 if n == 1 else 96, c, maxw=980 if n == 1 else 480, shadow=True), xs[i], cy, e)
        if it.get("label"):
            paste(fr, txt(it["label"], 56, ink(kind), maxw=900 if n == 1 else 470), xs[i], cy + 130, 1, clamp((tl + ent - 0.5) / 0.3))


def V_scale(fr, v, tl, kind, ent):
    items = v["items"]
    base = v.get("y", 1080)
    big = 640
    xs = [W * 0.27, W * 0.7]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).line((60, base + 6, W - 60, base + 6), fill=ink(kind) + (120,), width=6)
    fr.alpha_composite(lay)
    for i, it in enumerate(items):
        e = back((tl + ent - 0.25 * i) / 0.5)
        sz = max(60, int(big * it.get("size", 1.0)))
        paste(fr, icon(it["icon"], sz), xs[i], base - sz * 0.45 * e - 6 + 6 * math.sin(tl * 2 + i), e)
        if it.get("label"):
            paste(fr, pill(it["label"], col(it.get("labelCol"), COLA if i == 0 else COLB), size=44), xs[i], base + 80,
                  back((tl + ent - 0.4 - 0.2 * i) / 0.4))
        if it.get("name"):
            paste(fr, txt(it["name"], 56, col(it.get("nameCol"), COLA if i == 0 else COLB), maxw=480, shadow=kind == "dark"),
                  xs[i], base + 175, 1, clamp((tl + ent - 0.5) / 0.3))


def V_flow(fr, v, tl, kind, ent):
    items = v["items"]
    n = len(items)
    cy = v.get("y", 820)
    xs = [W * (0.5 + (i - (n - 1) / 2) * (0.33 if n == 3 else 0.44)) for i in range(n)]
    sz = 270 if n == 3 else 360
    for i, it in enumerate(items):
        e = back((tl + ent - 0.55 * i) / 0.45)
        paste(fr, glow(int(sz * 0.4), col(it.get("glow"), (255, 170, 60)), 110), xs[i], cy, e)
        paste(fr, icon(it["icon"], sz), xs[i], cy + 8 * math.sin(tl * 2 + i), e)
        if it.get("label"):
            paste(fr, pill(it["label"], col(it.get("labelCol"), [COLA, ORANGE, COLB][i % 3]), size=42, padx=22), xs[i], cy + sz * 0.65,
                  back((tl + ent - 0.55 * i - 0.2) / 0.4))
        if it.get("sub"):
            paste(fr, txt(it["sub"], 44, ink(kind), maxw=330), xs[i], cy + sz * 0.65 + 85, 1, clamp((tl + ent - 0.55 * i - 0.3) / 0.3))
        if i < n - 1:
            a = ease_out((tl + ent - 0.55 * i - 0.3) / 0.3)
            if a > 0.02:
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                ax0 = xs[i] + sz * 0.45
                ax1 = ax0 + (xs[i + 1] - sz * 0.45 - ax0) * a
                d.line((ax0, cy, ax1 - 16, cy), fill=YEL + (255,), width=12)
                d.polygon([(ax1, cy), (ax1 - 30, cy - 22), (ax1 - 30, cy + 22)], fill=YEL + (255,))
                fr.alpha_composite(lay)


def V_table(fr, v, tl, kind, ent):
    rows = v["rows"]
    top = v.get("y", 470)
    cw = 980
    rh = 175
    h = 130 + rh * len(rows)
    e = ease_out((tl + ent) / 0.4)
    paste(fr, card(cw, h, (255, 255, 255, 248)), W / 2, top + h / 2, 1, e)
    c1, c2, c3 = W / 2 - 360, W / 2 - 40, W / 2 + 310
    paste(fr, txt(spec["thingA"].upper(), 46, COLA, maxw=300), c2, top + 70, 1, e)
    paste(fr, txt(spec["thingB"].upper(), 46, COLB, maxw=300), c3, top + 70, 1, e)
    for i, r in enumerate(rows):
        a = ease_out((tl + ent - 0.4 - 0.45 * i) / 0.35)
        y = top + 130 + rh * i + rh / 2
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).line((W / 2 - cw / 2 + 30, y - rh / 2, W / 2 + cw / 2 - 30, y - rh / 2), fill=(220, 220, 232, int(255 * e)), width=3)
        fr.alpha_composite(lay)
        paste(fr, txt(r[0], 44, (110, 110, 140), maxw=220), c1, y, 1, a)
        paste(fr, txt(r[1], 50, DARK_INK, maxw=320), c2 + 30 * (1 - a), y, 1, a)
        paste(fr, txt(r[2], 50, DARK_INK, maxw=330), c3 + 30 * (1 - a), y, 1, a)


def V_remember(fr, v, tl, kind, ent):
    cy = v.get("y", 860)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    R = 1400
    for k in range(18):
        a0 = tl * 0.25 + k * 2 * math.pi / 18
        a1 = a0 + math.pi / 18
        d.polygon([(W / 2, cy), (W / 2 + R * math.cos(a0), cy + R * math.sin(a0)), (W / 2 + R * math.cos(a1), cy + R * math.sin(a1))],
                  fill=(255, 150, 40, 70))
    fr.alpha_composite(lay)
    e = back((tl + ent) / 0.45)
    paste(fr, pill(v.get("text", "REMEMBER!"), YEL, DARK_INK, size=96, padx=50, pady=26), W / 2, cy, e * (1 + 0.03 * math.sin(tl * 5)), rot=6)
    paste(fr, pill(v.get("tag", "KEY IDEA"), RED, size=40), W / 2 - 120, cy - 150, back((tl + ent - 0.3) / 0.4), rot=6)


def V_quiz(fr, v, tl, kind, ent, dur):
    qy = v.get("y", 520)
    for j, line in enumerate(v["question"]):
        paste(fr, txt(line, 62, ink(kind), maxw=960), W / 2, qy + j * 90, 1, ease_out((tl + ent - 0.1 * j) / 0.35))
    reveal = dur - 2.4
    opts = v["options"]
    oy = qy + 90 * len(v["question"]) + 290
    for i, o in enumerate(opts):
        x = W * (0.27 if i == 0 else 0.73)
        e = back((tl + ent - 0.4 - 0.15 * i) / 0.4)
        right = i == v["correct"]
        done = tl >= reveal
        cimg = card(420, 380)
        a = 1.0 if (not done or right) else 0.35
        sc = e * (1 + (0.06 * back((tl - reveal) / 0.35) if done and right else 0))
        paste(fr, cimg, x, oy, sc, a)
        if o.get("icon"):
            paste(fr, icon(o["icon"], 190), x, oy - 50, sc, a)
        paste(fr, txt(o["text"], 46, COLA if i == 0 else COLB, maxw=380), x, oy + 120, sc, a)
        if done and right:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lay).rounded_rectangle((x - 225 * sc, oy - 205 * sc, x + 225 * sc, oy + 205 * sc), 44, outline=GREEN + (255,), width=12)
            fr.alpha_composite(lay)
            paste(fr, pill("CORRECT!", GREEN, size=40), x, oy - 230, back((tl - reveal) / 0.35))
    # countdown
    cd0 = ent + 1.2
    if tl < reveal:
        left = reveal - tl
        num = int(math.ceil(min(left, v.get("countdown", 3))))
        if left <= v.get("countdown", 3):
            frac = left - math.floor(left)
            paste(fr, pill(str(num), RED, size=90, padx=40), W / 2, oy, 1 + 0.25 * frac)
        elif v.get("prompt"):
            paste(fr, pill(v["prompt"], ORANGE, size=40), W / 2, oy - 260, back((tl + ent - 1.0) / 0.4))


def V_outro(fr, v, tl, kind, ent):
    paste(fr, txt("SRJ", 190, WHITE, shadow=True), W / 2, 560, back((tl + ent) / 0.45))
    paste(fr, txt("EDU APP", 110, TEAL, shadow=True), W / 2, 720, back((tl + ent - 0.15) / 0.45))
    paste(fr, txt("Learn Something Extraordinary", 50, WHITE), W / 2, 850, 1, clamp((tl + ent - 0.4) / 0.3))
    paste(fr, txt("Every Day!", 50, YEL), W / 2, 920, 1, clamp((tl + ent - 0.5) / 0.3))
    paste(fr, pill("FOLLOW", GREEN, size=64, padx=50), W / 2, 1080, back((tl + ent - 0.7) / 0.4) * (1 + 0.06 * abs(math.sin(tl * 4))))
    paste(fr, pill("Save ചെയ്യൂ", RED, size=40), W * 0.3, 1230, back((tl + ent - 1.2) / 0.4))
    paste(fr, pill("Share ചെയ്യൂ", (60, 130, 230), size=40), W * 0.7, 1230, back((tl + ent - 1.4) / 0.4))


# ---------------- motion / physics diagrams ----------------
def _arrow(d, x0, y0, x1, y1, c, w=14, head=36):
    ang = math.atan2(y1 - y0, x1 - x0)
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 2:
        return
    hb = min(head, L)
    bx, by = x1 - hb * 0.8 * math.cos(ang), y1 - hb * 0.8 * math.sin(ang)
    d.line((x0, y0, bx, by), fill=c, width=w)
    pa = ang + math.pi * 0.82
    pb = ang - math.pi * 0.82
    d.polygon([(x1, y1), (x1 + hb * math.cos(pa), y1 + hb * math.sin(pa)), (x1 + hb * math.cos(pb), y1 + hb * math.sin(pb))], fill=c)


def _polyline_upto(pts, p):
    """return the polyline points covering fraction p of its length, and the tip point."""
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    tot = sum(seg)
    want = tot * clamp(p)
    out = [pts[0]]
    for i, L in enumerate(seg):
        if want <= L:
            f = want / L if L else 0
            tip = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)
            out.append(tip)
            return out, tip
        want -= L
        out.append(pts[i + 1])
    return out, pts[-1]


def _dot(d, x, y, r, c, outline=WHITE):
    d.ellipse((x - r, y - r, x + r, y + r), fill=c + (255,), outline=outline + (255,), width=6)


DIST_C = (255, 150, 30)    # distance = orange
DISP_C = (60, 150, 255)    # displacement = blue

# wiggly path from start to end
_ws = []
for k in range(41):
    u = k / 40
    _ws.append((180 + 720 * u, 900 + 190 * math.sin(u * math.pi * 2.6) - 120 * u))
WIGGLE = _ws


def V_path(fr, v, tl, kind, ent):
    """wiggly route A->B. mode 'distance' traces the route; mode 'displacement' greys it and shoots the straight arrow."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    mode = v.get("mode", "distance")
    pts = WIGGLE
    a, b = pts[0], pts[-1]
    if mode == "distance":
        p = ease_out((tl + ent - 0.3) / 2.2)
        d.line(pts, fill=ink(kind) + (60,), width=10, joint="curve")
        part, tip = _polyline_upto(pts, p)
        if len(part) > 1:
            d.line(part, fill=DIST_C + (255,), width=16, joint="curve")
        _dot(d, *a, 26, GREEN)
        _dot(d, *b, 26, RED)
        fr.alpha_composite(lay)
        paste(fr, icon("🚶", 120), tip[0], tip[1] - 80, 1)
        paste(fr, pill(v.get("label", "TOTAL PATH LENGTH"), DIST_C, size=46), W / 2, 1210, back((tl + ent - 2.0) / 0.4))
    else:
        d.line(pts, fill=DIST_C + (110,), width=12, joint="curve")
        _dot(d, *a, 26, GREEN)
        _dot(d, *b, 26, RED)
        p = ease_out((tl + ent - 0.4) / 0.9)
        _arrow(d, a[0], a[1], a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p, DISP_C + (255,), w=18, head=48)
        fr.alpha_composite(lay)
        paste(fr, pill(v.get("label", "SHORTEST STRAIGHT LINE"), DISP_C, size=46), W / 2, 1210, back((tl + ent - 1.3) / 0.4))
        paste(fr, pill("+ DIRECTION", YEL, DARK_INK, size=40), W / 2, 1310, back((tl + ent - 1.8) / 0.4))
    paste(fr, txt("START", 36, GREEN, shadow=kind == "dark"), a[0], a[1] + 60, 1, ease_out((tl + ent) / 0.3))
    paste(fr, txt("END", 36, RED, shadow=kind == "dark"), b[0], b[1] - 60, 1, ease_out((tl + ent) / 0.3))


def V_walk(fr, v, tl, kind, ent):
    """4 m east then 3 m north on a grid; 'result' adds the 5 m displacement arrow + chips."""
    u = 150                         # px per metre
    ox, oy = W / 2 - 2 * u, 1060    # start point
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    gc = ink(kind) + (40,)
    for i in range(-1, 6):
        d.line((ox + i * u, oy - 4 * u, ox + i * u, oy + u), fill=gc, width=3)
    for j in range(-1, 5):
        d.line((ox - u, oy - j * u, ox + 5 * u, oy - j * u), fill=gc, width=3)
    res = v.get("result", False)
    e1 = 1.0 if res else ease_out((tl + ent - 0.3) / 1.3)
    e2 = 1.0 if res else ease_out((tl + ent - 2.0) / 1.0)
    _arrow(d, ox, oy, ox + 4 * u * e1, oy, DIST_C + (255,), w=16, head=42)
    if e2 > 0.01:
        _arrow(d, ox + 4 * u, oy, ox + 4 * u, oy - 3 * u * e2, DIST_C + (255,), w=16, head=42)
    if res:
        p = ease_out((tl + ent - 0.4) / 0.8)
        _arrow(d, ox, oy, ox + 4 * u * p, oy - 3 * u * p, DISP_C + (255,), w=18, head=48)
    _dot(d, ox, oy, 22, GREEN)
    if e2 >= 0.99 or res:
        _dot(d, ox + 4 * u, oy - 3 * u, 22, RED)
    fr.alpha_composite(lay)
    paste(fr, txt("4 m EAST", 46, DIST_C, shadow=kind == "dark"), ox + 2 * u, oy + 60, 1, clamp((tl + ent - 0.8) / 0.3) if not res else 1)
    paste(fr, txt("3 m", 46, DIST_C, shadow=kind == "dark"), ox + 4 * u + 80, oy - 1.6 * u, 1, clamp((tl + ent - 2.4) / 0.3) if not res else 1)
    paste(fr, txt("NORTH", 34, DIST_C, shadow=kind == "dark"), ox + 4 * u + 80, oy - 1.6 * u + 50, 1, clamp((tl + ent - 2.4) / 0.3) if not res else 1)
    paste(fr, txt("N ↑", 40, ink(kind)), ox - 0.6 * u, oy - 3.6 * u, 1, ease_out((tl + ent) / 0.3))
    if res:
        paste(fr, txt("5 m", 60, DISP_C, shadow=kind == "dark"), ox + 1.7 * u, oy - 2.1 * u, 1, clamp((tl + ent - 1.0) / 0.3))
        paste(fr, pill("DISTANCE = 4 + 3 = 7 m", DIST_C, size=44), W / 2, oy + 175, back((tl + ent - 0.2) / 0.4))
        paste(fr, pill("DISPLACEMENT = 5 m", DISP_C, size=44), W / 2, oy + 175 + 0 if False else oy + 280, back((tl + ent - v.get("dispAt", 2.2)) / 0.4))


def V_sv(fr, v, tl, kind, ent):
    """scalar vs vector cards."""
    cw, ch = 460, 620
    xs = [W * 0.27, W * 0.73]
    cy = 830
    data = [("DISTANCE", "SCALAR", "SIZE ONLY", DIST_C), ("DISPLACEMENT", "VECTOR", "SIZE + DIRECTION", DISP_C)]
    for i, (nm, kindtxt, sub, c) in enumerate(data):
        e = ease_out((tl + ent - v.get("at", [0, 2.6])[i]) / 0.4)
        if e <= 0.01:
            continue
        y = cy + 60 * (1 - e)
        paste(fr, card(cw, ch), xs[i], y, 1, e)
        paste(fr, txt(nm, 42, c, maxw=420), xs[i], y - 230, 1, e)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        x, yy = xs[i], y - 50
        if i == 0:
            # plain measuring bar (no arrow head)
            d.rounded_rectangle((x - 160, yy - 14, x + 160, yy + 14), 12, fill=c + (int(255 * e),))
            for k in range(9):
                d.line((x - 160 + k * 40, yy - 34, x - 160 + k * 40, yy - 14), fill=DARK_INK + (int(200 * e),), width=4)
            d.text((x, yy + 60), "5 m", fill=DARK_INK + (int(255 * e),), font=fnt(48, False), anchor="mm")
        else:
            ang = -0.6 + 0.15 * math.sin(tl * 2)
            L = 170
            _arrow(d, x - L * math.cos(ang), yy - L * math.sin(ang), x + L * math.cos(ang), yy + L * math.sin(ang), c + (int(255 * e),), w=22, head=56)
            d.text((x, yy + 110), "5 m ↗", fill=DARK_INK + (int(255 * e),), font=fnt(48, "sym"), anchor="mm")
        fr.alpha_composite(lay)
        paste(fr, pill(kindtxt, c, size=54), xs[i], y + 150, back((tl + ent - v.get("at", [0, 2.6])[i] - 0.3) / 0.4))
        paste(fr, txt(sub, 34, (110, 110, 140), maxw=420), xs[i], y + 245, 1, e)


TRACK = []
for k in range(121):
    a = k / 120 * 2 * math.pi
    # stadium-ish oval, start at bottom centre, run anticlockwise on screen
    TRACK.append((W / 2 + 330 * math.sin(a), 860 + 300 * math.cos(a)))


def V_track(fr, v, tl, kind, ent):
    """running track: runner does one lap; distance counter climbs to 400 m, displacement shows 0."""
    lap0, lapT = v.get("lap", [0.3, 3.2])
    p = ease_out((tl + ent - lap0) / lapT) if not v.get("done") else 1.0
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse((W / 2 - 400, 860 - 370, W / 2 + 400, 860 + 370), fill=(200, 90, 70, 255))
    d.ellipse((W / 2 - 260, 860 - 230, W / 2 + 260, 860 + 230), fill=(60, 160, 90, 255))
    d.line(TRACK, fill=(255, 255, 255, 120), width=4)
    part, tip = _polyline_upto(TRACK, p)
    if len(part) > 1:
        d.line(part, fill=DIST_C + (255,), width=14, joint="curve")
    sx, sy = TRACK[0]
    d.line((sx, sy - 70, sx, sy + 70), fill=(255, 255, 255, 255), width=10)
    fr.alpha_composite(lay)
    paste(fr, icon("🏃", 130), tip[0], tip[1] - 40, 1)
    paste(fr, pill(f"DISTANCE  {int(round(400 * p))} m", DIST_C, size=46), W / 2, 790, back((tl + ent - 0.2) / 0.4))
    if p >= 0.999:
        k = tl + ent - lap0 - lapT if not v.get("done") else tl + ent
        paste(fr, pill("DISPLACEMENT  0 m", DISP_C, size=46), W / 2, 900, back((k - v.get("dispDelay", 0.2)) / 0.4) * (1 + 0.05 * abs(math.sin(tl * 4))))


def V_homequiz(fr, v, tl, kind, ent, dur):
    """home -> school 2 km and back; countdown then reveal 0 km."""
    hx, sx, y = 220, 860, 900
    reveal = v.get("reveal", dur - 2.4)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((hx, y + 70, sx, y + 100), 14, fill=ink(kind) + (70,))
    go = ease_out((tl + ent - 0.8) / 1.6)
    back_ = ease_out((tl + ent - 2.6) / 1.6)
    if go > 0.01:
        _arrow(d, hx + 60, y - 120, hx + 60 + (sx - hx - 120) * go, y - 120, DIST_C + (255,), w=12, head=34)
    if back_ > 0.01:
        _arrow(d, sx - 60, y - 40, sx - 60 - (sx - hx - 120) * back_, y - 40, DIST_C + (255,), w=12, head=34)
    fr.alpha_composite(lay)
    paste(fr, icon("🏠", 200), hx, y + 10, back((tl + ent) / 0.4))
    paste(fr, icon("🏫", 200), sx, y + 10, back((tl + ent - 0.2) / 0.4))
    paste(fr, pill("2 km", ORANGE, size=44), W / 2, y + 160, back((tl + ent - 0.5) / 0.4))
    paste(fr, txt("DISPLACEMENT = ?", 70, ink(kind), shadow=kind == "dark"), W / 2, 560, back((tl + ent - 0.1) / 0.4))
    cd = v.get("countdown", 3)
    if tl < reveal:
        left = reveal - tl
        if left <= cd:
            frac = left - math.floor(left)
            paste(fr, pill(str(int(math.ceil(left))), RED, size=90, padx=40), W / 2, 1180, 1 + 0.25 * frac)
        elif tl > 4.4:
            paste(fr, pill("COMMENT ചെയ്യൂ!", ORANGE, size=44), W / 2, 1180, back((tl - 4.4) / 0.4))
    else:
        paste(fr, pill("ANSWER: 0 km", GREEN, size=70, padx=44), W / 2, 1190, back((tl - reveal) / 0.35))
        paste(fr, txt("DISTANCE = 4 km", 44, DIST_C, shadow=kind == "dark"), W / 2, 1310, 1, clamp((tl - reveal - 0.4) / 0.3))


# ---------------- energy diagrams (Potential vs Kinetic) ----------------
PE_C = (255, 150, 30)     # potential = orange
KE_C = (60, 150, 255)     # kinetic = blue
TOT_C = (30, 190, 120)
GROUND_Y = 1290
CLIFF_TOP = 560
CLIFF_X = 470


def _ground(d, kind):
    d.rectangle((0, GROUND_Y, W, GROUND_Y + 60), fill=(90, 170, 80, 255))
    d.rectangle((0, GROUND_Y + 22, W, GROUND_Y + 60), fill=(120, 90, 60, 255))


def _cliff(d):
    pts = [(0, CLIFF_TOP + 10), (120, CLIFF_TOP - 10), (300, CLIFF_TOP), (CLIFF_X, CLIFF_TOP + 4),
           (CLIFF_X + 20, CLIFF_TOP + 140), (CLIFF_X - 10, CLIFF_TOP + 330), (CLIFF_X + 30, CLIFF_TOP + 520), (CLIFF_X + 10, GROUND_Y), (0, GROUND_Y)]
    d.polygon(pts, fill=(130, 105, 90, 255))
    d.polygon([(0, CLIFF_TOP + 10), (120, CLIFF_TOP - 10), (300, CLIFF_TOP), (CLIFF_X, CLIFF_TOP + 4), (CLIFF_X, CLIFF_TOP + 30), (0, CLIFF_TOP + 34)],
              fill=(95, 165, 85, 255))
    for k, (x, y) in enumerate([(120, 760), (300, 900), (180, 1080), (360, 1180), (80, 1220)]):
        d.line((x, y, x + 60, y + 18), fill=(105, 84, 72, 255), width=6)


def _meter(fr, d, x, label, frac, c, kind, top=640, h=520, w=96):
    d.rounded_rectangle((x - w / 2, top, x + w / 2, top + h), 20, fill=(255, 255, 255, 60 if kind == "dark" else 150),
                        outline=ink(kind) + (120,), width=4)
    hh = max(0, h * clamp(frac))
    if hh > 14:
        d.rounded_rectangle((x - w / 2 + 6, top + h - hh + 6, x + w / 2 - 6, top + h - 6), min(16, (hh - 12) / 2), fill=c + (255,))


def V_cliff(fr, v, tl, kind, ent):
    """stone on a cliff. mode: rest | fall | transform | heights."""
    mode = v.get("mode", "rest")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    _ground(d, kind)
    R = 70
    if mode == "heights":
        cols = [(240, 1000), (540, 800), (840, 600)]   # x, top y
        for i, (x, ty) in enumerate(cols):
            e = ease_out((tl + ent - 0.25 * i) / 0.5)
            top = GROUND_Y - (GROUND_Y - ty) * e
            d.rounded_rectangle((x - 110, top, x + 110, GROUND_Y + 2), 18, fill=(130, 105, 90, 255))
            d.rectangle((x - 110, top, x + 110, top + 22), fill=(95, 165, 85, 255))
        fr.alpha_composite(lay)
        for i, (x, ty) in enumerate(cols):
            e = ease_out((tl + ent - 0.25 * i) / 0.5)
            top = GROUND_Y - (GROUND_Y - ty) * e
            a = clamp((tl + ent - 0.6 - 0.35 * i) / 0.3)
            paste(fr, glow(60 + 25 * i, PE_C, 150), x, top - R + 10, a)
            paste(fr, icon("rock:asteroid", 2 * R), x, top - R + 14, a)
            paste(fr, pill(["PE", "MORE PE", "MAX PE"][i], PE_C, size=[34, 40, 46][i], padx=18), x, top - 2 * R - 40,
                  back((tl + ent - 0.9 - 0.4 * i) / 0.4))
        return
    _cliff(d)
    sx0, sy0 = CLIFF_X - 80, CLIFF_TOP - R + 12
    x, y, p = sx0, sy0, 0.0
    t0, T = v.get("at", 0.3), v.get("fallT", 1.6)
    if mode in ("fall", "transform"):
        u = clamp((tl + ent - t0) / T)
        # tip over the edge (first 15%) then free fall: y ~ u^2
        if u < 0.15:
            x = sx0 + 150 * (u / 0.15)
        else:
            k = (u - 0.15) / 0.85
            x = sx0 + 150 + 60 * k
            y = sy0 + (GROUND_Y - R + 8 - sy0) * k * k
            p = k
    # height arrow
    hx = 690 if (mode == "transform" or v.get("meters")) else 930
    d.line((hx, y, hx, GROUND_Y - 6), fill=YEL + (255,), width=8)
    d.polygon([(hx, y - 4), (hx - 18, y + 26), (hx + 18, y + 26)], fill=YEL + (255,))
    d.line((hx - 30, GROUND_Y - 4, hx + 30, GROUND_Y - 4), fill=YEL + (255,), width=8)
    if mode in ("fall", "transform") and p > 0.05:
        for k in range(4):
            yy = y - R - 30 - k * 46
            if yy > sy0 - R:
                d.line((x - 30 + k * 20, yy, x - 30 + k * 20, yy - 30 - 20 * p), fill=(255, 255, 255, int(200 * p)), width=5)
    fr.alpha_composite(lay)
    paste(fr, txt("h", 64, YEL, shadow=True), hx + 50, (y + GROUND_Y) / 2, 1, 1 if (y + 30 < GROUND_Y - 60) else 0)
    gl = 1 - p
    if gl > 0.05:
        paste(fr, glow(int(R * 1.3), PE_C, int(170 * gl)), x, y, 1 + 0.06 * math.sin(tl * 5))
    if p > 0.05:
        paste(fr, glow(int(R * 1.3), KE_C, int(170 * p)), x, y)
    paste(fr, icon("rock:asteroid", 2 * R), x, y, 1, rot=-200 * p if mode != "rest" else 0)
    if p >= 0.999:
        fr_d = ImageDraw.Draw(fr)
        k = tl + ent - t0 - T
        if k < 0.6:
            for j in range(8):
                a = j * math.pi / 7
                rr = 40 + 160 * k
                fr_d.ellipse((x + rr * math.cos(a) - 10, GROUND_Y - 10 - rr * math.sin(a) * 0.5 - 10,
                              x + rr * math.cos(a) + 10, GROUND_Y - 10 - rr * math.sin(a) * 0.5 + 10), fill=(200, 180, 150, int(255 * (1 - k / 0.6))))
    if mode == "rest" and v.get("label"):
        paste(fr, pill(v["label"], PE_C, size=50), 700, sy0 + 40, back((tl + ent - 0.5) / 0.4) * (1 + 0.04 * math.sin(tl * 4)))
    if mode == "fall" and v.get("label"):
        paste(fr, pill(v["label"], RED, size=50), 700, 500, back((tl + ent - t0 - T) / 0.4))
    if mode in ("transform", "gauges") or v.get("meters"):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        names = v.get("meters", ["PE", "KE"])
        if names[0] == "HEIGHT":
            vals = [1 - p, math.sqrt(p)]
        else:
            vals = [1 - p, p]
        mx = [800, 960]
        cs = [PE_C, KE_C]
        for i in range(2):
            _meter(fr, d, mx[i], names[i], vals[i], cs[i], kind)
        fr.alpha_composite(lay)
        for i in range(2):
            paste(fr, txt(names[i], 40 if len(names[i]) < 4 else 32, cs[i], shadow=kind == "dark"), mx[i], 1200)


def V_roll(fr, v, tl, kind, ent):
    """ball rolling across the floor with speed lines."""
    fy = 1040
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((40, fy + 10, W - 40, fy + 34), 12, fill=ink(kind) + (140,))
    sp = v.get("speed", 520)
    x = -150 + ((tl + ent) * sp) % (W + 300)
    for k in range(5):
        yy = fy - 160 + k * 55
        L = 120 + 40 * (k % 2)
        d.rounded_rectangle((x - 140 - L, yy - 6, x - 140, yy + 6), 6, fill=KE_C + (200,))
    fr.alpha_composite(lay)
    paste(fr, glow(110, KE_C, 140), x, fy - 115)
    paste(fr, icon(v.get("icon", "⚽"), 230), x, fy - 115, 1, rot=-(tl + ent) * sp / 115 * 57.3)
    paste(fr, pill(v.get("label", "MOTION = KINETIC ENERGY"), KE_C, size=48), W / 2, 640, back((tl + ent - 0.5) / 0.4))
    paste(fr, txt("v", 70, YEL, shadow=True), W / 2, fy + 120, 1, clamp((tl + ent - 0.8) / 0.3))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = clamp((tl + ent - 0.8) / 0.3)
    _arrow(ImageDraw.Draw(lay), W / 2 + 50, fy + 120, W / 2 + 250, fy + 120, YEL + (int(255 * a),), w=12, head=36)
    fr.alpha_composite(lay)


def _formula_img(tokens, size):
    k = ("formula", tuple((s, tuple(c)) for s, c in tokens), size)
    if k in _tc:
        return _tc[k]
    f = fnt(size, False)
    ws = [f.getlength(s) for s, _ in tokens]
    w = int(sum(ws)) + 40
    h = int(size * 1.5)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 20
    for (s, c), wl in zip(tokens, ws):
        d.text((x, h / 2), s, font=f, fill=tuple(c) + (255,), anchor="lm")
        x += wl
    _tc[k] = im
    return im


def V_formula(fr, v, tl, kind, ent):
    """big formula on a white card + term rows that appear one by one (v['at'])."""
    cw, chh = 960, 900
    cy = 860
    e = ease_out((tl + ent) / 0.4)
    paste(fr, card(cw, chh), W / 2, cy + 40 * (1 - e), 1, e)
    top = cy - chh / 2
    paste(fr, pill(v.get("title", "FORMULA"), col(v.get("titleCol"), PE_C), size=44), W / 2, top + 20, back((tl + ent - 0.1) / 0.4))
    toks = [(s, col(c, DARK_INK)) for s, c in v["tokens"]]
    paste(fr, _formula_img(toks, v.get("size", 150)), W / 2, top + 210, back((tl + ent - 0.2) / 0.45))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).line((W / 2 - 400, top + 345, W / 2 + 400, top + 345), fill=(220, 220, 232, int(255 * e)), width=4)
    fr.alpha_composite(lay)
    ats = v.get("at", [0.8 + 0.8 * i for i in range(len(v["rows"]))])
    for i, (sym, c, words) in enumerate(v["rows"]):
        a = ease_out((tl + ent - ats[i]) / 0.35)
        y = top + 440 + i * 140
        c = col(c, DARK_INK)
        paste(fr, txt(sym, 80, c), W / 2 - 330, y, back((tl + ent - ats[i]) / 0.4), a)
        paste(fr, txt("=", 60, (150, 150, 170)), W / 2 - 220, y, 1, a)
        tim = txt(words, 50, DARK_INK, maxw=560)
        paste(fr, tim, W / 2 - 180 + tim.width / 2 + 30 * (1 - a), y, 1, a)


def V_pendulum(fr, v, tl, kind, ent):
    """ideal pendulum with live PE / KE / TOTAL bars."""
    px, py, L = 360, 520, 420
    th0 = math.radians(42)
    period = v.get("period", 2.6)
    th = th0 * math.cos(2 * math.pi * (tl + ent) / period)
    pe = (1 - math.cos(th)) / (1 - math.cos(th0))
    ke = 1 - pe
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    bx, by = px + L * math.sin(th), py + L * math.cos(th)
    # swing arc
    arc = [(px + L * math.sin(a), py + L * math.cos(a)) for a in np.linspace(-th0, th0, 40)]
    d.line(arc, fill=ink(kind) + (70,), width=5)
    d.rounded_rectangle((px - 140, py - 24, px + 140, py), 8, fill=ink(kind) + (200,))
    d.line((px, py, bx, by), fill=ink(kind) + (255,), width=7)
    fr.alpha_composite(lay)
    paste(fr, glow(70, KE_C if ke > pe else PE_C, 150), bx, by)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse((bx - 58, by - 58, bx + 58, by + 58), fill=(180, 185, 200, 255), outline=WHITE + (255,), width=6)
    d.ellipse((bx - 34, by - 40, bx - 6, by - 12), fill=(240, 240, 250, 200))
    names, vals, cs = ["PE", "KE", "TOTAL"], [pe, ke, 1.0], [PE_C, KE_C, TOT_C]
    xs = [770, 880, 990]
    for i in range(3):
        _meter(fr, d, xs[i], names[i], vals[i], cs[i], kind, top=560, h=600, w=84)
    fr.alpha_composite(lay)
    for i in range(3):
        paste(fr, txt(names[i], 36 if i < 2 else 28, cs[i], shadow=kind == "dark"), xs[i], 1210)
    paste(fr, pill(v.get("label", "TOTAL = CONSTANT"), TOT_C, size=46), W / 2, 1310, back((tl + ent - v.get("labelAt", 1.5)) / 0.4))


VIS = {"hero": V_hero, "bars": V_bars, "particles": V_particles, "number": V_number, "scale": V_scale,
       "flow": V_flow, "table": V_table, "remember": V_remember, "outro": V_outro,
       "path": V_path, "walk": V_walk, "sv": V_sv, "track": V_track,
       "cliff": V_cliff, "roll": V_roll, "formula": V_formula, "pendulum": V_pendulum}


# ---------------- confetti ----------------
_cr = np.random.default_rng(9)
CONF = [(255, 90, 90), (255, 190, 40), (60, 170, 255), (80, 200, 120), (190, 110, 255)]
CPARTS = [(_cr.uniform(-1, 1) * 900, _cr.uniform(-1700, -700), _cr.uniform(0, 6.28), CONF[k % 5], _cr.uniform(10, 20)) for k in range(100)]


def confetti(fr, tl, y0=1000):
    if not 0 <= tl < 1.8:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for vx, vy, ph, c, s in CPARTS:
        x = W / 2 + vx * tl
        y = y0 + vy * tl + 1900 * tl * tl
        if y > H + 40:
            continue
        w = s * abs(math.cos(ph + tl * 9))
        d.rectangle((x - w / 2, y - s / 3, x + w / 2, y + s / 3), fill=c + (255,))
    fr.alpha_composite(lay)


# ---------------- timeline ----------------
starts = []
t = 0.0
for s in SCENES:
    starts.append(t)
    t += s["dur"]
DUR = t
def _badge():
    t = txt("SRJ EDU APP", 34, WHITE)
    t = t.crop(t.getbbox())
    w, h = t.width + 92, t.height + 30
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w, h), h // 2, fill=(24, 20, 48, 255))
    d.ellipse((24, h / 2 - 11, 46, h / 2 + 11), fill=GREEN + (255,))
    im.alpha_composite(t, (64, 15))
    return im


BADGE = _badge()

sfx = [("boom", 0.05, 0.6)]
for i, s in enumerate(SCENES):
    if i:
        sfx.append(("whoosh", starts[i] - 0.2, 0.45))
    caps = s.get("captions", [])
    at = s.get("capAt") or [k * s["dur"] / max(1, len(caps)) for k in range(len(caps))]
    for j in range(len(caps)):
        if i or j:
            sfx.append(("pop_hi", starts[i] + at[j] + 0.02, 0.22))
    vt = s.get("visual", {}).get("type")
    if vt in ("quiz", "homequiz"):
        cd = s["visual"].get("countdown", 3)
        rv = starts[i] + s["visual"].get("reveal", s["dur"] - 2.4)
        for k in range(cd):
            sfx.append(("tick", rv - cd + k, 0.7))
        sfx.append(("ding", rv, 0.9))
    if vt == "remember":
        sfx.append(("boom", starts[i] + 0.05, 0.5))
    if vt == "number":
        sfx.append(("riser", starts[i] - 0.4, 0.4))
    if vt == "outro":
        sfx.append(("ding", starts[i] + 0.1, 0.6))
    for name, at, gain in s.get("sfx", []):
        sfx.append((name, starts[i] + at, gain))


def scene_at(t):
    for i in range(len(SCENES) - 1, -1, -1):
        if t >= starts[i]:
            return i
    return 0


def draw_scene(fr, i, tl, kind):
    s = SCENES[i]
    ent = 1.0 if i == 0 else 0.0     # first scene starts fully drawn (thumbnail frame)
    head = s.get("head")
    if head:
        if s.get("headStyle") == "pill":
            paste(fr, pill(head, col(s.get("headCol"), ORANGE), size=58), W / 2, 330, back((tl + ent) / 0.4))
        else:
            hc = col(s.get("headCol"), (ORANGE if kind == "dark" else DARK_INK))
            paste(fr, txt(head, 66, hc, maxw=980, shadow=kind == "dark"), W / 2, 330, back((tl + ent) / 0.4))
    v = s.get("visual")
    if v:
        if v["type"] == "quiz":
            V_quiz(fr, v, tl, kind, ent, s["dur"])
            confetti(fr, tl - (s["dur"] - 2.4), 900)
        elif v["type"] == "homequiz":
            V_homequiz(fr, v, tl, kind, ent, s["dur"])
            confetti(fr, tl - v.get("reveal", s["dur"] - 2.4), 900)
        else:
            VIS[v["type"]](fr, v, tl, kind, ent)
        if v["type"] == "outro":
            confetti(fr, tl - 0.1, 700)
    caps = s.get("captions", [])
    if caps:
        at = s.get("capAt") or [k * s["dur"] / len(caps) for k in range(len(caps))]
        j = max(k for k in range(len(caps)) if tl >= at[k] or k == 0)
        cl = tl - at[j] + (ent if j == 0 else 0)
        paste(fr, caption_img(caps[j]), W / 2, s.get("capY", 1480), 0.92 + 0.08 * back(cl / 0.25), clamp(cl / 0.12))


def frame(t):
    i = scene_at(t)
    s = SCENES[i]
    kind = s.get("bg", "dark")
    tl = t - starts[i]
    fr = BGS[kind].copy()
    # crossfade the background from the previous scene
    if i and tl < 0.25:
        pk = SCENES[i - 1].get("bg", "dark")
        if pk != kind:
            fr = Image.blend(BGS[pk], BGS[kind], tl / 0.25)
    draw_scene(fr, i, tl, kind)
    # quick push transition: previous scene slides out for 0.2 s
    if i and tl < 0.2:
        pf = BGS[SCENES[i - 1].get("bg", "dark")].copy()
        draw_scene(pf, i - 1, SCENES[i - 1]["dur"] - 0.01, SCENES[i - 1].get("bg", "dark"))
        p = ease_out(tl / 0.2)
        pf = pf.crop((int(W * p), 0, W, H))
        if pf.width > 2:
            fr.alpha_composite(pf, (0, 0))
    d = ImageDraw.Draw(fr)
    d.rectangle((0, 0, W, 10), fill=(0, 0, 0, 40))
    d.rectangle((0, 0, int(W * t / DUR), 10), fill=GREEN + (255,))
    fr.alpha_composite(BADGE, (30, 50))
    d = ImageDraw.Draw(fr)
    return fr.convert("RGB")


def main():
    if os.environ.get("FRAMES"):
        for ft in os.environ["FRAMES"].split(","):
            frame(float(ft)).save(os.path.splitext(sys.argv[2])[0] + f"_{ft}.png")
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", sys.argv[2]],
                         stdin=subprocess.PIPE)
    for k in range(int(DUR * FPS)):
        p.stdin.write(frame(k / FPS).tobytes())
    p.stdin.close(); p.wait()
    json.dump({"duration": DUR, "drop": SCENES[0]["dur"], "seed": int(spec.get("topicNo", 0)), "sfx": sfx, "voice": os.path.abspath(spec["voice"]) if spec.get("voice") else None}, open(sys.argv[3], "w"))


if __name__ == "__main__":
    main()
