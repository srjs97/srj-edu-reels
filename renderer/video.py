"""Render a 9:16 'This vs That' text reel (no voice) as raw frames piped to ffmpeg."""
import json, math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BOLD = "/usr/share/fonts/opentype/malayalam/Manjari-Bold.otf"
REG = "/usr/share/fonts/opentype/malayalam/Manjari-Regular.otf"
sys.path.insert(0, __import__("os").path.dirname(__file__))
import illus
rng = np.random.default_rng(3)

spec = json.load(open(sys.argv[1]))
SPEC_DIR = __import__("os").path.dirname(__import__("os").path.abspath(sys.argv[1]))
A_COL = tuple(spec["colA"])
B_COL = tuple(spec["colB"])
YEL = (255, 214, 64)
WHITE = (255, 255, 255)
GREY = (170, 178, 200)
LIGHT = bool(spec.get("light"))
illus.LIGHT_MODE = LIGHT
INK, ACCENT, SOFT = (34, 34, 72), (214, 84, 16), (96, 96, 124)
def deepen(c, target=110):
    lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    k = min(1.0, target / max(lum, 1))
    return tuple(int(v * k) for v in c)
if LIGHT:
    A_COL, B_COL = deepen(A_COL), deepen(B_COL)

def ink(color):
    """Map dark-theme text colours to light-theme ones."""
    color = tuple(color)
    if not LIGHT:
        return color
    return {WHITE: INK, YEL: ACCENT, GREY: SOFT}.get(color, deepen(color))


def ease_out_back(x, s=1.9):
    x = min(max(x, 0), 1)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def ease_out(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


_font = {}
def font(size, bold=True):
    k = (size, bold)
    if k not in _font:
        _font[k] = ImageFont.truetype(BOLD if bold else REG, size, layout_engine=ImageFont.Layout.RAQM)
    return _font[k]


_txt = {}
def text_img(s, size, color, bold=True, maxw=960, glow=True):
    color = ink(color)
    k = (s, size, color, bold, maxw, glow)
    if k in _txt:
        return _txt[k]
    while True:
        f = font(size, bold)
        bb = f.getbbox(s, stroke_width=6)
        if bb[2] - bb[0] <= maxw or size < 20:
            break
        size -= 2
    pad = 40
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    org = (pad - bb[0], pad - bb[1])
    if glow:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if LIGHT:
            ImageDraw.Draw(g).text((org[0] + 4, org[1] + 5), s, font=f, fill=(90, 60, 20, 90), stroke_width=4, stroke_fill=(90, 60, 20, 90))
            g = g.filter(ImageFilter.GaussianBlur(6))
        else:
            ImageDraw.Draw(g).text(org, s, font=f, fill=color + (170,), stroke_width=4, stroke_fill=color + (170,))
            g = g.filter(ImageFilter.GaussianBlur(14))
        im = Image.alpha_composite(im, g)
        d = ImageDraw.Draw(im)
    d.text(org, s, font=f, fill=color + (255,), stroke_width=6 if not LIGHT else 3, stroke_fill=(255, 255, 255, 255) if LIGHT else (10, 12, 30, 255))
    _txt[k] = im
    return im


def paste(frame, im, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


# ---------------- background ----------------
NSTAR = 260
stars = np.c_[rng.random(NSTAR) * W, rng.random(NSTAR) * H, rng.random(NSTAR)]

def bg_gradient():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    _th = spec.get("theme") if isinstance(spec.get("theme"), dict) else {}
    pal = spec.get("palette", {})
    top = np.array(pal.get("top", _th.get("top", [12, 10, 40]))); bot = np.array(pal.get("bottom", _th.get("bottom", [4, 4, 14])))
    if spec.get("light"):
        top = np.array(pal.get("top", [255, 248, 214])); bot = np.array(pal.get("bottom", [255, 232, 160]))
    g = top * (1 - y[..., None]) + bot * y[..., None]
    if spec.get("light"):
        for (cx, cy, r, col) in [(0.15, 0.2, 0.35, (255, 255, 255)), (0.9, 0.75, 0.4, (255, 210, 120)), (0.5, 1.05, 0.35, (255, 200, 110))]:
            d = np.exp(-(((x - cx) ** 2 + ((y - cy) * 0.56) ** 2) / (r * r * 0.3)))
            g = g * (1 - 0.5 * d[..., None]) + np.array(col)[None, None, :] * 0.5 * d[..., None]
        return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # nebula blobs
    neb = pal.get("neb", [(90, 40, 140), (20, 80, 140), (140, 60, 30)])
    for (cx, cy, r), col in zip([(0.2, 0.25, 0.35), (0.85, 0.7, 0.4), (0.5, 1.0, 0.3)], neb):
        d = np.exp(-(((x - cx) ** 2 + ((y - cy) * 0.56) ** 2) / (r * r * 0.3)))
        g = g + np.array(col)[None, None, :] * d[..., None] * pal.get("neb_strength", 0.45)
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

BG = bg_gradient()
def _scrim_img():
    y = np.linspace(0, 1, H)[:, None]
    a = (40 + 90 * np.clip((y - 0.45) / 0.3, 0, 1)) * np.ones((1, W))
    z = np.zeros((H, W))
    return Image.fromarray(np.dstack([z + 5, z + 5, z + 15, a]).astype(np.uint8), "RGBA")
SCRIM_IMG = _scrim_img()

THEME = spec.get("theme", "space")
SC = illus.Scenes() if THEME == "space" else None
ET = None if THEME == "space" else illus.EmojiTheme(THEME["emojis"])
if ET is not None:
    SC = type("V", (), {"vig": illus.vignette()})()

def scene_layer(t):
    if ET is not None:
        return ET.layer(t)
    for i, (t0, t1, name) in enumerate(illus.SCENE_TIMES):
        if t0 <= t < t1:
            lay = SC.layer(name, t)
            xf = 0.5
            if i + 1 < len(illus.SCENE_TIMES) and t > t1 - xf:
                nxt = SC.layer(illus.SCENE_TIMES[i + 1][2], t)
                lay = Image.blend(lay, nxt, (t - (t1 - xf)) / xf)
            return lay
    return None

_bgimg = {}
def image_bg(t):
    imgs = spec.get("bg_images")
    if not imgs:
        return None
    for t0, t1, name in illus.SCENE_TIMES:
        if t0 <= t < t1 and name in imgs:
            if name not in _bgimg:
                im = Image.open(__import__("os").path.join(SPEC_DIR, imgs[name])).convert("RGB")
                sc = max(W * 1.12 / im.width, H * 1.12 / im.height)
                _bgimg[name] = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
            im = _bgimg[name]
            p = (t - t0) / (t1 - t0)
            z = 1.0 + 0.10 * (1 - p)  # slow zoom out
            cw, ch = int(W * z * im.width / (W * 1.12)), int(H * z * im.height / (H * 1.12))
            cw, ch = min(im.width, int(W * 1.12 / z)), min(im.height, int(H * 1.12 / z))
            x0 = (im.width - cw) // 2; y0 = (im.height - ch) // 2
            fr = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR).convert("RGBA")
            fr.alpha_composite(SCRIM_IMG)
            return fr
    return None

def draw_bg(t):
    ib = image_bg(t)
    if ib is not None:
        return ib
    fr = BG.copy()
    d = ImageDraw.Draw(fr)
    for x, y, z in stars:
        yy = (y + t * (10 + 60 * z)) % H
        tw = 0.6 + 0.4 * math.sin(t * 3 + x)
        c = int(120 + 135 * z * tw)
        r = 1 + 2 * z
        if LIGHT:
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=(255, 200, 90, int(90 + 100 * z * tw)))
        else:
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=(c, c, min(255, c + 20), 255))
    lay = scene_layer(t)
    if lay is not None:
        fr.alpha_composite(lay)
    if not LIGHT:
        fr.alpha_composite(SC.vig)
    return fr


# ---------------- rocks ----------------
def make_rock(size, seed, base=(120, 112, 104), craters=6):
    r = np.random.default_rng(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    n = 22
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rad = size * 0.42 * (1 + 0.18 * np.sin(ang * 2 + r.random() * 6) + 0.08 * r.standard_normal(n))
    pts = [(size / 2 + rr * math.cos(a), size / 2 + rr * math.sin(a) * 0.82) for a, rr in zip(ang, rad)]
    d.polygon(pts, fill=base + (255,))
    for _ in range(craters):
        cx, cy = size / 2 + r.uniform(-0.26, 0.26) * size, size / 2 + r.uniform(-0.2, 0.2) * size
        cr = size * r.uniform(0.04, 0.1)
        d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=tuple(int(c * 0.7) for c in base) + (255,))
        d.ellipse((cx - cr * 0.7, cy - cr * 0.8, cx + cr * 0.6, cy + cr * 0.5), fill=tuple(int(c * 0.55) for c in base) + (255,))
    # shading: light from top-left
    arr = np.array(im).astype(float)
    yy, xx = np.mgrid[0:size, 0:size] / size
    shade = 1.25 - 0.9 * ((xx + yy) / 2)
    arr[..., :3] *= shade[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    return im

ASTEROID = make_rock(460, 11, craters=9)
FRAGS = [make_rock(int(s), 100 + i, base=(150, 120, 95), craters=2) for i, s in enumerate([120, 80, 64, 96, 52, 70])]


def glow_disc(r, col):
    s = r * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=col + (200,))
    return im.filter(ImageFilter.GaussianBlur(r * 0.6))


# ---------------- timeline ----------------
els = []     # (t_in, t_out, fn(frame, t_local, out_alpha))
sfx = []     # (name, time, gain)


def T(s, t_in, t_out, cy, size=72, color=WHITE, anim="pop", cx=W / 2, sound=None, bold=True, glow=True, gain=0.8, maxw=960):
    im = text_img(s, size, color, bold, maxw=maxw, glow=glow)
    def fn(fr, tl, oa):
        if anim == "pop":
            sc = ease_out_back(tl / 0.35); paste(fr, im, cx, cy, sc, oa * min(1, tl / 0.1))
        elif anim == "left":
            p = ease_out(tl / 0.4); paste(fr, im, cx - (1 - p) * 900, cy, 1, oa * p)
        elif anim == "right":
            p = ease_out(tl / 0.4); paste(fr, im, cx + (1 - p) * 900, cy, 1, oa * p)
        elif anim == "up":
            p = ease_out(tl / 0.45); paste(fr, im, cx, cy + (1 - p) * 80, 1, oa * p)
        elif anim == "slam":
            p = min(1, tl / 0.18); sc = 2.4 - 1.4 * ease_out(p); paste(fr, im, cx, cy, sc, oa * p)
    els.append((t_in, t_out, fn))
    if sound:
        sfx.append((sound, t_in, gain))


def shake(t, at, amp=18, dur=0.35):
    if at <= t < at + dur:
        k = 1 - (t - at) / dur
        return amp * k * math.sin(t * 90), amp * k * math.cos(t * 77)
    return 0, 0


def panel(t_in, t_out, box, col, alpha=140):
    x0, y0, x1, y1 = box
    im = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), 36, fill=(255, 255, 250, 215) if LIGHT else (14, 16, 40, alpha), outline=col + (230,), width=5)
    def fn(fr, tl, oa):
        p = ease_out(tl / 0.35)
        paste(fr, im, (x0 + x1) / 2, (y0 + y1) / 2 + (1 - p) * 60, 1, oa * p)
    els.append((t_in, t_out, fn))


def custom(t_in, t_out, fn):
    els.append((t_in, t_out, fn))


def pill(text, bg, fg=(255, 255, 255), size=52, emoji=None, pad=(36, 18)):
    t = text_img(text, size, fg, glow=False)
    t = t.crop(t.getbbox())
    e = illus.emoji_img(emoji, int(size * 1.25)) if emoji else None
    w = t.width + 2 * pad[0] + (e.width + 16 if e else 0)
    h = max(t.height, e.height if e else 0) + 2 * pad[1]
    im = Image.new("RGBA", (w + 12, h + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 10, w + 6, h + 10), h // 2, fill=(0, 0, 0, 50))
    d.rounded_rectangle((4, 4, w + 4, h + 4), h // 2, fill=tuple(bg) + (255,))
    x = 4 + pad[0]
    if e:
        im.alpha_composite(e, (x, 4 + (h - e.height) // 2)); x += e.width + 16
    im.alpha_composite(t, (x, 4 + (h - t.height) // 2))
    return im


def hook_icon(which, size):
    g = spec.get("graphic" + which)
    if g == "asteroid":
        return ASTEROID.resize((size, size), Image.LANCZOS)
    if g == "meteoroids":
        return FRAGS[0].resize((int(size * 0.8), int(size * 0.8)), Image.LANCZOS)
    return illus.emoji_img(spec.get("emoji" + which, "❓"), size)


_conf_rng = np.random.default_rng(9)
CONF_COLS = [(255, 90, 90), (255, 190, 40), (60, 170, 255), (80, 200, 120), (190, 110, 255)]
def confetti(t0, n=90, x0=W / 2, y0=900):
    parts = [(_conf_rng.uniform(-1, 1) * 900, _conf_rng.uniform(-1700, -700), _conf_rng.uniform(0, 6.28), CONF_COLS[k % 5], _conf_rng.uniform(10, 20)) for k in range(n)]
    def fn(fr, tl, oa):
        d = ImageDraw.Draw(fr)
        for vx, vy, ph, col, s in parts:
            x = x0 + vx * tl
            y = y0 + vy * tl + 1900 * tl * tl
            if y > H + 40:
                continue
            w = s * abs(math.cos(ph + tl * 9))
            d.rectangle((x - w / 2, y - s / 3, x + w / 2, y + s / 3), fill=col + (int(255 * oa),))
    custom(t0, t0 + 1.8, fn)


SCENE_CUTS = [4.2, 8.2, 17.6, 27.0, 35.4, 44.0, 50.5, 56.0]
def swipe_overlay(fr, t):
    for c in SCENE_CUTS:
        dt = t - (c - 0.18)
        if 0 <= dt < 0.36:
            p = dt / 0.36
            x = -400 + p * (W + 800)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            col = (ACCENT if LIGHT else YEL)
            d.polygon([(x - 260, 0), (x + 60, 0), (x - 140, H), (x - 460, H)], fill=col + (235,))
            d.polygon([(x + 90, 0), (x + 150, 0), (x - 50, H), (x - 110, H)], fill=(255, 255, 255, 200))
            fr.alpha_composite(lay)


BPM = [118, 112, 122, 108][int(spec.get("topicNo", 0)) % 4]
_bar = 4 * 60 / BPM
BEATS = [k * _bar + b * 60 / BPM for k in range(200) for b in range(4) if k * _bar >= 4.2 - 1e-6 and k * _bar + b * 60 / BPM < 59]
def beat_zoom(t):
    z = 1.0
    for bt in BEATS:
        if 0 <= t - bt < 0.25:
            z = 1.0 + 0.014 * math.exp(-(t - bt) * 14)
    return z


A, B = spec["thingA"].upper(), spec["thingB"].upper()
S = spec["scenes"]

# --- Scene 1: hook (0 - 4.2) -- frame 0 is already a full "thumbnail"
sfx.append(("boom", 0.0, 0.7))
sfx.append(("riser", 2.4, 0.6))
BANNER = pill(S.get("hook_banner", "90% പേർക്കും ഇത് അറിയില്ല!"), (225, 50, 60), size=54)
custom(-1, 4.1, lambda fr, tl, oa: paste(fr, BANNER, W / 2, 380, 1 + 0.03 * math.sin(tl * 6), oa))
ICON_A, ICON_B = hook_icon("A", 300), hook_icon("B", 300)
def g_hook_icons(fr, tl, oa):
    bob = 14 * math.sin(tl * 3)
    paste(fr, glow_disc(150, A_COL), 290, 720, 1, 0.35 * oa)
    paste(fr, glow_disc(150, B_COL), 790, 720, 1, 0.35 * oa)
    paste(fr, ICON_A.rotate(6 * math.sin(tl * 2), resample=Image.BICUBIC, expand=True), 290, 720 + bob, 1, oa)
    paste(fr, ICON_B.rotate(-6 * math.sin(tl * 2), resample=Image.BICUBIC, expand=True), 790, 720 - bob, 1, oa)
custom(-1, 4.1, g_hook_icons)
T(A, -1, 4.1, 960, 64, A_COL, "pop", cx=290, maxw=480)
T(B, -1, 4.1, 960, 64, B_COL, "pop", cx=790, maxw=480)
VS_BADGE = pill("VS", (34, 34, 72) if LIGHT else (255, 255, 255), (255, 255, 255) if LIGHT else (20, 20, 40), size=60)
custom(-1, 4.1, lambda fr, tl, oa: paste(fr, VS_BADGE, W / 2, 740, 1 + 0.08 * abs(math.sin(tl * 5)), oa))
T(S["hook2"], 1.2, 4.1, 1200, 92, YEL, "slam", sound="pop")
T(S["hook3"], 2.5, 4.1, 1380, 120, (230, 40, 60), "slam", sound="boom", gain=0.9)

# --- Scene 2: A vs B (4.2 - 8.2)
T(A, 4.25, 8.1, 640, 130, A_COL, "left", sound="whoosh")
T(spec["subA"], 4.45, 8.1, 760, 60, WHITE, "left", glow=False)
T("VS", 5.0, 8.1, 940, 150, WHITE, "slam", sound="boom", gain=0.9)
T(B, 5.7, 8.1, 1120, 130, B_COL, "right", sound="whoosh")
T(spec["subB"], 5.9, 8.1, 1240, 60, WHITE, "right", glow=False)
T(S["vs_sub"], 6.5, 8.1, 1430, 52, YEL, "up", glow=False, sound="pop_hi", gain=0.5)


def scene_card(t0, t1, title, col, bullets, graphic, sub=None):
    T(title, t0, t1, 340, 120, col, "slam", sound="boom", gain=0.6)
    if sub:
        T(sub, t0 + 0.4, t1, 460, 64, WHITE, "up", glow=False, sound="pop_hi", gain=0.4)
    custom(t0 + 0.2, t1, graphic)
    panel(t0 + 0.9, t1, (60, 1060, 1020, 1680), col)
    y = 1150
    for i, (txt, size, c) in enumerate(bullets):
        T(txt, t0 + 1.2 + i * 1.6, t1, y, size, c, "left", sound="tick", glow=False, gain=0.7)
        y += 115 if size >= 50 else 85


def g_asteroid(fr, tl, oa):
    p = ease_out_back(tl / 0.6, 1.2)
    rot = ASTEROID.rotate(tl * 14, resample=Image.BICUBIC)
    paste(fr, glow_disc(200, B_COL), W / 2, 760, 1, 0.35 * oa * p)
    paste(fr, rot, W / 2, 760 + 14 * math.sin(tl * 1.5), max(0.01, p), oa)

def g_emoji(ch, col):
    big = illus.emoji_img(ch, 380)
    halo = glow_disc(190, col)
    def fn(fr, tl, oa):
        p = ease_out_back(tl / 0.6, 1.4)
        paste(fr, halo, W / 2, 760, 1, 0.4 * oa * min(1, p))
        r = big.rotate(5 * math.sin(tl * 1.2), resample=Image.BICUBIC, expand=True)
        paste(fr, r, W / 2, 760 + 16 * math.sin(tl * 1.5), max(0.01, p), oa)
    return fn

GB = g_asteroid if spec.get("graphicB") == "asteroid" else g_emoji(spec.get("emojiB", "❓"), B_COL)
scene_card(8.2, 17.6, B, B_COL, S["b_bullets"], GB, spec.get("subB"))

frag_paths = [(-260, -120, 0.7), (180, -160, -1.0), (300, 60, 0.4), (-120, 90, -0.6), (40, -40, 1.3), (-320, 130, 0.9)]
def g_meteoroids(fr, tl, oa):
    for i, (im, (dx, dy, sp)) in enumerate(zip(FRAGS, frag_paths)):
        p = ease_out(max(0, tl - i * 0.12) / 0.6)
        x = W / 2 + dx * p + 25 * math.sin(tl * 0.9 + i)
        y = 760 + dy * p + 20 * math.cos(tl * 1.1 + i * 2)
        paste(fr, im.rotate(tl * 40 * sp, resample=Image.BICUBIC), x, y, 1, oa * min(1, p * 2))
    # dust sparkles
    d = ImageDraw.Draw(fr)
    r2 = np.random.default_rng(5)
    for k in range(40):
        ang = r2.random() * 6.28; rad = 120 + r2.random() * 330 * ease_out(tl / 1.0)
        x = W / 2 + rad * math.cos(ang + tl * 0.15); y = 760 + rad * 0.6 * math.sin(ang + tl * 0.15)
        a = int(200 * oa * (0.5 + 0.5 * math.sin(tl * 4 + k)))
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 190, 140, a))

GA = g_meteoroids if spec.get("graphicA") == "meteoroids" else g_emoji(spec.get("emojiA", "❓"), A_COL)
scene_card(17.6, 27.0, A, A_COL, S["a_bullets"], GA, spec.get("subA"))

TEASER = pill(S.get("teaser", "അവസാനം ഒരു ക്വിസ് ഉണ്ട്!"), (34, 34, 72) if LIGHT else (255, 214, 64), (255, 255, 255) if LIGHT else (20, 20, 40), size=44, emoji="👀")
custom(20.5, 26.9, lambda fr, tl, oa: paste(fr, TEASER, W / 2, 1790 + 8 * math.sin(tl * 4), ease_out_back(tl / 0.4), oa))
sfx.append(("pop_hi", 20.5, 0.6))

# --- Scene 5: recap table (27.0 - 35.4)
T(S["recap_title"], 27.0, 35.3, 330, 96, YEL, "slam", sound="boom", gain=0.6)
T(A, 27.5, 35.3, 520, 60, A_COL, "left", cx=W * 0.25, sound="whoosh", gain=0.5, maxw=470)
T(B, 27.5, 35.3, 520, 60, B_COL, "right", cx=W * 0.75, maxw=470)
y = 680
for i, (label, a_txt, b_txt) in enumerate(S["recap_rows"]):
    t = 28.4 + i * 2.1
    T(label, t, 35.3, y, 38, GREY, "up", glow=False, sound="tick", gain=0.6)
    custom(t, 35.3, (lambda yy: lambda fr, tl, oa: ImageDraw.Draw(fr).line((W / 2, yy + 50, W / 2, yy + 50 + 100 * ease_out(tl / 0.5)), fill=(255, 255, 255, int(110 * oa)), width=4))(y))
    T(a_txt, t + 0.2, 35.3, y + 95, 46, WHITE, "pop", cx=W * 0.25, glow=False, sound="pop", gain=0.5, maxw=470)
    T(b_txt, t + 0.5, 35.3, y + 95, 46, WHITE, "pop", cx=W * 0.75, glow=False, sound="pop", gain=0.5, maxw=470)
    y += 300

# --- Scene 6: quiz (35.4 - 44.0)
Q = S["quiz"]
T(Q["tag"], 35.4, 43.9, 380, 84, YEL, "slam", sound="boom", gain=0.6)
for i, line in enumerate(Q["question"]):
    T(line, 35.9 + i * 0.5, 43.9, 600 + i * 90, 56, WHITE, "up", glow=False, sound="whoosh" if i == 0 else None, gain=0.4)
panel(37.2, 43.9, (90, 860, 510, 1020), A_COL)
panel(37.4, 43.9, (570, 860, 990, 1020), B_COL)
T(A, 37.3, 43.9, 940, 52, A_COL, "pop", cx=300, glow=False, sound="pop", maxw=380)
T(B, 37.5, 43.9, 940, 52, B_COL, "pop", cx=780, glow=False, sound="pop", maxw=380)
T(Q["prompt"], 38.0, 41.2, 1130, 44, GREY, "up", glow=False)
for k, n in enumerate(["3", "2", "1"]):
    T(n, 38.4 + k, 39.35 + k, 1290, 170, WHITE, "slam", sound="tick", gain=0.9)
T(Q["answer"], 41.4, 43.9, 1280, 96, A_COL, "slam", sound="ding", gain=0.8)
T(Q["why"], 42.0, 43.9, 1420, 48, WHITE, "up", glow=False)
ANS_RING = Image.new("RGBA", (460, 200), (0, 0, 0, 0))
ImageDraw.Draw(ANS_RING).rounded_rectangle((4, 4, 455, 195), 44, outline=((30, 170, 70) if LIGHT else (120, 255, 140)) + (255,), width=10)
custom(41.4, 43.9, lambda fr, tl, oa: paste(fr, ANS_RING, 300 if Q["correct"] == "A" else 780, 940, ease_out_back(tl / 0.3), oa))

# --- Scene 7: bonus (44.0 - 50.5)
T(S["bonus_tag"], 44.0, 50.4, 430, 70, YEL, "pop", sound="pop_hi")
T(S["bonus1"], 44.5, 50.4, 640, 54, WHITE, "up", glow=False, sound="whoosh", gain=0.4)
T(S["bonus1b"], 45.4, 50.4, 780, 100, (255, 150, 60), "slam", sound="streak", gain=0.9)
T(S["bonus2"], 47.0, 50.4, 1060, 54, WHITE, "up", glow=False, sound="whoosh", gain=0.4)
T(S["bonus2b"], 47.9, 50.4, 1200, 100, (255, 110, 80), "slam", sound="boom", gain=0.8)

def g_streak(fr, tl, oa):
    p = ease_out(tl / 0.9)
    x0, y0 = W + 100, 120
    x1, y1 = x0 - p * 1500, y0 + p * 900
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(30):
        f = k / 30
        xa, ya = x1 + (x0 - x1) * f * 0.5, y1 + (y0 - y1) * f * 0.5
        r = 22 * (1 - f)
        d.ellipse((xa - r, ya - r, xa + r, ya + r), fill=(255, int(200 - 120 * f), 60, int(220 * (1 - f) * oa)))
    lay = lay.filter(ImageFilter.GaussianBlur(6))
    fr.alpha_composite(lay)
custom(45.3, 46.7, g_streak)

# --- Scene 8: fun fact (50.5 - 56.0)
F = S["fact"]
T(F["tag"], 50.5, 55.9, 520, 70, YEL, "pop", sound="pop_hi")
T(F["big"], 51.1, 55.9, 760, 150, A_COL, "slam", sound="boom", gain=0.8)
for i, line in enumerate(F["lines"]):
    T(line, 51.9 + i * 0.6, 55.9, 940 + i * 85, 54, WHITE, "up", glow=False, sound="whoosh" if i == 0 else None, gain=0.4)

confetti(41.4, y0=1000)
confetti(56.0, y0=1100)
# --- Scene 9: outro (56.0 - 60.0)
CTA1 = pill("Save ചെയ്യൂ", (225, 50, 60), size=46, emoji="📌")
CTA2 = pill("Share ചെയ്യൂ", (40, 130, 220), size=46, emoji="📤")
custom(57.8, 60.0, lambda fr, tl, oa: paste(fr, CTA1, W * 0.29, 1300, ease_out_back(tl / 0.35), oa))
custom(58.1, 60.0, lambda fr, tl, oa: paste(fr, CTA2, W * 0.71, 1300, ease_out_back(tl / 0.35), oa))
sfx.append(("pop", 57.8, 0.6)); sfx.append(("pop", 58.1, 0.6))
T(S["outro1"], 56.0, 60.0, 760, 78, WHITE, "pop", sound="ding", gain=0.9)
T(S["outro2"], 56.6, 60.0, 920, 66, YEL, "up", sound="whoosh", gain=0.4)
T(S["outro3"], 57.3, 60.0, 1080, 48, GREY, "up", glow=False, sound="pop_hi", gain=0.5)

DUR = 60.0
for _c in SCENE_CUTS:
    sfx.append(("whoosh", _c - 0.25, 0.55))
WATERMARK = text_img(spec["brand"], 40, WHITE, glow=False)
TAG = text_img(spec["tag"], 34, YEL, glow=False)


def render():
    out = sys.argv[2]
    if __import__("os").environ.get("FRAMES"):
        for ft in __import__("os").environ["FRAMES"].split(","):
            t = float(ft)
            fr = draw_bg(t)
            for t_in, t_out, fn in els:
                if t_in <= t < t_out:
                    fn(fr, t - t_in, min(1, (t_out - t) / 0.25))
            paste(fr, WATERMARK, 220, 150, 1, 0.85); paste(fr, TAG, W - 240, 150, 1, 0.9)
            fr.convert("RGB").save(out.replace(".mp4", "") + f"_{ft}.png")
        return
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    shakes = [t for name, t, g in sfx if name == "boom"]
    for i in range(n):
        t = i / FPS
        fr = draw_bg(t)
        for t_in, t_out, fn in els:
            if t_in <= t < t_out:
                oa = min(1, (t_out - t) / 0.25)
                fn(fr, t - t_in, oa)
        paste(fr, WATERMARK, 220, 150, 1, 0.85)
        paste(fr, TAG, W - 240, 150, 1, 0.9)
        # progress bar
        d = ImageDraw.Draw(fr)
        d.rectangle((0, 0, int(W * t / DUR), 10), fill=(ACCENT if LIGHT else YEL) + (255,))
        swipe_overlay(fr, t)
        dx, dy = 0, 0
        for s in shakes:
            a, b = shake(t, s); dx += a; dy += b
        img = fr.convert("RGB")
        z = beat_zoom(t)
        if z > 1.001:
            cw, ch = int(W / z), int(H / z)
            img = img.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BILINEAR)
        if dx or dy:
            img = img.transform(img.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BILINEAR)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    json.dump({"duration": DUR, "drop": 4.2, "seed": int(spec.get("topicNo", 0)), "sfx": sfx}, open(sys.argv[3], "w"))


render()
