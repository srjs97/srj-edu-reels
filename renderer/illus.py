"""Flat-shaded space illustrations for reel backgrounds (all procedural)."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920


def _smooth_noise(n, scale, seed):
    r = np.random.default_rng(seed)
    g = r.random((scale + 2, scale + 2))
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
    return np.asarray(im).astype(float) / 255


def sphere(r, base_fn, light=(-0.55, -0.6), glow=None, seed=0):
    """base_fn(u, v, lat, lon) -> rgb array; returns RGBA image of size 2r(+glow)."""
    pad = int(r * 0.35) if glow else 4
    n = 2 * r + 2 * pad
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    x = (xx - n / 2) / r
    y = (yy - n / 2) / r
    d2 = x * x + y * y
    inside = d2 <= 1
    z = np.sqrt(np.clip(1 - d2, 0, 1))
    lat = np.arcsin(np.clip(y, -1, 1))
    lon = np.arctan2(x, z)
    rgb = base_fn(x, y, lat, lon, n)
    lx, ly = light
    lz = math.sqrt(max(0, 1 - lx * lx - ly * ly))
    lam = np.clip(x * lx + y * ly + z * lz, 0, 1)
    shade = 0.18 + 0.95 * lam ** 0.8
    rim = np.clip(1 - z, 0, 1) ** 3 * 0.25
    out = rgb * shade[..., None] + rim[..., None] * 255 * 0.3
    a = np.clip((1 - np.sqrt(d2)) * r * 1.5, 0, 1) * 255
    img = np.dstack([np.clip(out, 0, 255), a]).astype(np.uint8)
    im = Image.fromarray(img, "RGBA")
    if glow:
        g = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((pad - 6, pad - 6, n - pad + 6, n - pad + 6), fill=glow + (190,))
        g = g.filter(ImageFilter.GaussianBlur(r * 0.12))
        g.alpha_composite(im)
        im = g
    return im


def banded(colors, wobble=0.06, seed=1, spot=None):
    cols = np.array(colors, float)
    def fn(x, y, lat, lon, n):
        nz = _smooth_noise(n, 10, seed)
        v = (y + 1) / 2 + wobble * (nz - 0.5) + 0.015 * np.sin(x * 18 + nz * 6)
        idx = np.clip(v * len(cols), 0, len(cols) - 1e-6)
        i0 = np.floor(idx).astype(int)
        i1 = np.minimum(i0 + 1, len(cols) - 1)
        f = np.clip((idx - i0) * 3 - 1, 0, 1)[..., None]
        rgb = cols[i0] * (1 - f) + cols[i1] * f
        if spot:
            sx, sy, sr, sc = spot
            m = np.exp(-(((x - sx) / (sr * 1.6)) ** 2 + ((y - sy) / sr) ** 2) * 2)
            rgb = rgb * (1 - m[..., None]) + np.array(sc) * m[..., None]
        return rgb
    return fn


def mottled(c1, c2, scale=8, seed=2, craters=0):
    def fn(x, y, lat, lon, n):
        nz = _smooth_noise(n, scale, seed) * 0.6 + _smooth_noise(n, scale * 3, seed + 1) * 0.4
        m = np.clip((nz - 0.35) * 2.5, 0, 1)[..., None]
        rgb = np.array(c1, float) * (1 - m) + np.array(c2, float) * m
        r = np.random.default_rng(seed)
        for _ in range(craters):
            cx, cy, cr = r.uniform(-0.7, 0.7), r.uniform(-0.7, 0.7), r.uniform(0.06, 0.16)
            dd = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / cr
            rgb = rgb * (1 - 0.25 * (dd < 1)[..., None]) + 25 * ((dd > 0.85) & (dd < 1.05))[..., None]
        return rgb
    return fn


def earth_fn(x, y, lat, lon, n):
    land = _smooth_noise(n, 9, 21) * 0.6 + _smooth_noise(n, 30, 22) * 0.4
    ocean = np.array([30, 110, 200], float)
    green = np.array([70, 160, 80], float)
    sand = np.array([200, 180, 110], float)
    m = np.clip((land - 0.52) * 8, 0, 1)[..., None]
    d = np.clip((land - 0.62) * 6, 0, 1)[..., None]
    rgb = ocean * (1 - m) + (green * (1 - d) + sand * d) * m
    cl = _smooth_noise(n, 12, 23) * 0.5 + _smooth_noise(n, 30, 24) * 0.5
    c = np.clip((cl - 0.58) * 5, 0, 0.85)[..., None]
    polar = np.clip((np.abs(y) - 0.82) * 8, 0, 1)[..., None]
    rgb = rgb * (1 - c) + 255 * c
    return rgb * (1 - polar) + 245 * polar


def ringed(r, colors, ring_col, tilt=0.28, seed=5):
    planet = sphere(r, banded(colors, seed=seed))
    s = planet.width
    rw, rh = int(r * 2.3), int(r * 2.3 * tilt)
    n = max(s, 2 * rw + 20)
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ring = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    c = n / 2
    for k, (fr, a) in enumerate([(1.0, 150), (0.9, 210), (0.78, 120), (0.68, 190)]):
        d.ellipse((c - rw * fr, c - rh * fr, c + rw * fr, c + rh * fr), outline=ring_col + (a,), width=max(3, int(r * 0.06)))
    back = ring.copy()
    back.paste((0, 0, 0, 0), (0, int(c), n, n))
    front = ring.copy()
    front.paste((0, 0, 0, 0), (0, 0, n, int(c)))
    im.alpha_composite(back)
    im.alpha_composite(planet, (int(c - s / 2), int(c - s / 2)))
    im.alpha_composite(front)
    return im.rotate(-14, resample=Image.BICUBIC)


def comet(length=900):
    n = length + 200
    im = Image.new("RGBA", (n, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    head = (120, 130)
    for k in range(60):
        f = k / 60
        x = head[0] + f * length
        w = 18 + 90 * f
        a = int(150 * (1 - f) ** 1.5)
        d.ellipse((x - w, head[1] - w * 0.55, x + w, head[1] + w * 0.55), fill=(150, 210, 255, a))
    im = im.filter(ImageFilter.GaussianBlur(10))
    d = ImageDraw.Draw(im)
    d.ellipse((head[0] - 34, head[1] - 34, head[0] + 34, head[1] + 34), fill=(220, 240, 255, 255))
    g = im.filter(ImageFilter.GaussianBlur(4))
    g.alpha_composite(im)
    return g


def shooting_star():
    im = Image.new("RGBA", (420, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(40):
        f = k / 40
        x = 30 + f * 360
        r = 6 * (1 - f) + 1
        d.ellipse((x - r, 30 - r, x + r, 30 + r), fill=(255, 255, 230, int(255 * (1 - f))))
    return im.filter(ImageFilter.GaussianBlur(2)).rotate(-30, expand=True, resample=Image.BICUBIC)


def vignette():
    y = np.linspace(-1, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    d = np.sqrt(x ** 2 * 0.8 + y ** 2 * 0.6)
    a = np.clip((d - 0.55) * 160, 0, 170).astype(np.uint8)
    z = np.zeros_like(a)
    return Image.fromarray(np.dstack([z, z, z + 8, a]), "RGBA")


def center_scrim():
    # soft dark band behind the text column to keep text readable over art
    y = np.linspace(-1, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    a = np.exp(-(x / 0.85) ** 4) * np.exp(-(y / 0.75) ** 6) * 70
    z = np.zeros((H, W))
    return Image.fromarray(np.dstack([z + 6, z + 6, z + 20, a]).astype(np.uint8), "RGBA")


class Scenes:
    def __init__(self):
        self.saturn = ringed(360, [(235, 190, 120), (210, 150, 90), (240, 210, 160), (190, 120, 80), (230, 180, 120)], (230, 200, 150))
        self.moon = sphere(80, mottled((190, 190, 200), (140, 140, 155), craters=8, seed=9))
        self.jupiter = sphere(340, banded([(230, 210, 180), (200, 140, 90), (240, 225, 200), (180, 110, 70), (225, 190, 150), (200, 150, 110), (235, 215, 190)], seed=3, spot=(0.3, 0.25, 0.16, (200, 90, 60))))
        self.mars = sphere(85, mottled((215, 95, 55), (160, 60, 40), seed=4), glow=(255, 120, 80))
        self.iceplanet = sphere(230, banded([(140, 220, 240), (100, 180, 230), (170, 235, 245), (90, 160, 220)], seed=7), glow=(120, 200, 255))
        self.earth = sphere(700, earth_fn, light=(-0.3, -0.75), glow=(90, 170, 255))
        self.comet = comet()
        self.shoot = shooting_star()
        self.vig = vignette()
        self.scrim = center_scrim()
        r = np.random.default_rng(12)
        self.belt = [(r.uniform(0, 2 * np.pi), r.uniform(0.85, 1.15), r.uniform(3, 10), int(r.uniform(90, 170))) for _ in range(170)]

    def _put(self, lay, im, cx, cy, alpha=1.0):
        if alpha < 0.99:
            im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        lay.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2))) if (
            0 <= int(cx - im.width / 2) and 0 <= int(cy - im.height / 2)
            and int(cx + im.width / 2) <= W and int(cy + im.height / 2) <= H) else _paste_clip(lay, im, cx, cy)

    def layer(self, name, t):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = math.sin(t * 0.3)
        if name in ("hook", "outro"):
            self._put(lay, self.saturn, 170 + 10 * dr, 1660 - t * 3, 1)
            self._put(lay, self.moon, 900, 330 + 8 * dr)
            self._shooting(lay, t, [1.2, 5.0, 57.0])
        elif name == "asteroid":
            self._put(lay, self.jupiter, 1090, 430 + 6 * dr)
            self._put(lay, self.mars, 110, 300 - 5 * dr)
            d = ImageDraw.Draw(lay)
            for ang, rr, sz, c in self.belt:
                a = ang + t * 0.05
                x = W / 2 + math.cos(a) * 640 * rr
                y = 560 + math.sin(a) * 120 * rr
                if math.sin(a) < -0.2:
                    continue
                d.ellipse((x - sz, y - sz * 0.8, x + sz, y + sz * 0.8), fill=(c, c - 10, c - 25, 230))
        elif name == "meteoroid":
            p = (t - 17.6) / 9.4
            self._put(lay, self.comet, 1300 - p * 900, 260 + p * 60, 0.95)
            self._put(lay, self.iceplanet, 980, 1790 + 6 * dr)
            self._shooting(lay, t, [21.0, 24.5])
        elif name == "recap":
            self._put(lay, self.saturn.transpose(Image.FLIP_LEFT_RIGHT), 960, 1750 - (t - 27) * 2, 0.7)
            self._put(lay, self.moon, 140, 250, 0.8)
        elif name == "earth":
            self._put(lay, self.earth, 540, 2180 - min(1, (t - 44) / 1.5) * 120)
            self._put(lay, self.moon, 930, 300 + 6 * dr)
            self._shooting(lay, t, [52.0])
        lay.alpha_composite(self.scrim)
        return lay

    def _shooting(self, lay, t, times):
        for t0 in times:
            if t0 <= t < t0 + 0.9:
                p = (t - t0) / 0.9
                self._put(lay, self.shoot, 200 + p * 700, 150 + p * 420, math.sin(p * math.pi))


def _paste_clip(lay, im, cx, cy):
    x0, y0 = int(cx - im.width / 2), int(cy - im.height / 2)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1, sy1 = min(im.width, W - x0), min(im.height, H - y0)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    lay.alpha_composite(im.crop((sx0, sy0, sx1, sy1)), (x0 + sx0, y0 + sy0))


SCENE_TIMES = [(0, 8.2, "hook"), (8.2, 17.6, "asteroid"), (17.6, 27.0, "meteoroid"), (27.0, 44.0, "recap"), (44.0, 56.0, "earth"), (56.0, 61, "outro")]


EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
_emo = {}
def emoji_img(ch, size):
    from PIL import ImageFont
    k = (ch, size)
    if k not in _emo:
        f = ImageFont.truetype(EMOJI_FONT, 109, layout_engine=ImageFont.Layout.RAQM)
        im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((90, 90), ch, font=f, embedded_color=True, anchor="mm")
        bb = im.getbbox() or (0, 0, 180, 180)
        im = im.crop(bb)
        sc = size / max(im.size)
        _emo[k] = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
    return _emo[k]


class EmojiTheme:
    """Generic background: soft floating emoji illustrations around the edges."""
    SPOTS = [(130, 330, 150), (950, 280, 130), (90, 1000, 120), (990, 900, 150), (160, 1760, 170), (930, 1740, 140), (540, 1840, 110), (540, 230, 90)]

    def __init__(self, emojis, tint=(40, 20, 90)):
        self.items = []
        for i, (x, y, s) in enumerate(self.SPOTS):
            self.items.append((emoji_img(emojis[i % len(emojis)], s), x, y, i))
        self.vig = vignette()
        self.scrim = center_scrim()

    def layer(self, t):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for im, x, y, i in self.items:
            dx = 18 * math.sin(t * 0.5 + i * 1.7)
            dy = 22 * math.cos(t * 0.4 + i)
            r = im.rotate(8 * math.sin(t * 0.6 + i), resample=Image.BICUBIC, expand=True)
            r.putalpha(r.getchannel("A").point(lambda v: int(v * 0.55)))
            _paste_clip(lay, r, x + dx, y + dy)
        lay.alpha_composite(self.scrim)
        return lay
