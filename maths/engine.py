"""SRJ EDU Maths reel engine: code-drawn frames (pycairo) piped to ffmpeg.

A topic module (maths/topics/<slug>.py) defines:
    TITLE, DURATION (seconds), draw(r, t), sfx() -> list of (name, time, gain[, pitch])
and optionally CAPTION / YT_TITLE / HASHTAGS for publishing.
"""
import math, subprocess, sys
import cairo

W, H, FPS = 1080, 1920, 30

# palette (dark, cinematic, colour-coded)
BG = (0.02, 0.02, 0.03)
WHITE = (0.96, 0.96, 0.98)
DIM = (0.55, 0.57, 0.62)
ORANGE = (1.0, 0.48, 0.10)
CYAN = (0.25, 0.82, 1.0)
GREEN = (0.45, 0.85, 0.35)
PINK = (1.0, 0.36, 0.62)
YELLOW = (1.0, 0.84, 0.25)
VIOLET = (0.62, 0.48, 1.0)

SANS = "Inter"
MATH = "DejaVu Serif"
HANDLE = "@srj_edu_app"

# ---------------- easing / timing ----------------

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, t0, dur):
    """0..1 progress of an animation that starts at t0 and lasts dur."""
    return clamp((t - t0) / dur) if dur > 0 else float(t >= t0)


def ease(x):  # smooth in-out
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x, s=1.7):
    x = clamp(x) - 1
    return 1 + x * x * ((s + 1) * x + s)


def lerp(a, b, x):
    return a + (b - a) * x


def window(t, t0, t1, fade=0.35):
    """1 inside [t0,t1], fading in/out over `fade` seconds."""
    return ease(prog(t, t0, fade)) * (1 - ease(prog(t, t1 - fade, fade)))


# ---------------- renderer ----------------

class Reel:
    def __init__(self):
        self.surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
        self.ctx = cairo.Context(self.surf)
        self.small = cairo.ImageSurface(cairo.FORMAT_RGB24, W // 8, H // 8)
        self.camera = (W / 2, H / 2, 1.0)  # centre x, y, zoom

    # --- camera: world coords (1080x1920 design space) -> screen
    def set_camera(self, cx=W / 2, cy=H / 2, zoom=1.0):
        self.camera = (cx, cy, zoom)

    def push_world(self):
        cx, cy, z = self.camera
        c = self.ctx
        c.save()
        c.translate(W / 2, H / 2)
        c.scale(z, z)
        c.translate(-cx, -cy)

    def pop(self):
        self.ctx.restore()

    # --- background: black, faint grid, vignette floor glow
    def background(self, t, grid_alpha=0.10):
        c = self.ctx
        c.set_source_rgb(*BG)
        c.paint()
        self.push_world()
        step = 60
        drift = (t * 6) % step
        c.set_line_width(1)
        for i in range(-20, 40):
            a = grid_alpha * (1.6 if i % 5 == 0 else 1)
            c.set_source_rgba(1, 1, 1, a)
            x = i * step
            c.move_to(x, -1000); c.line_to(x, H + 1000); c.stroke()
            y = i * step + drift
            c.move_to(-1000, y); c.line_to(W + 1000, y); c.stroke()
        self.pop()
        g = cairo.RadialGradient(W / 2, H * 0.5, 100, W / 2, H * 0.5, H * 0.75)
        g.add_color_stop_rgba(0, 0, 0, 0, 0)
        g.add_color_stop_rgba(1, 0, 0, 0, 0.85)
        c.set_source(g); c.paint()

    # --- text
    def text(self, s, x, y, size, col=WHITE, alpha=1.0, font=SANS, bold=False,
             italic=False, align="center", scale=1.0):
        """Draw text with its visual centre/left at (x, y). Returns width."""
        c = self.ctx
        if alpha <= 0.001 or not s:
            return 0
        c.save()
        c.select_font_face(font, cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL,
                           cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        c.set_font_size(size)
        ext = c.text_extents(s)
        c.translate(x, y)
        c.scale(scale, scale)
        if align == "center":
            dx = -(ext.x_advance) / 2
        elif align == "right":
            dx = -ext.x_advance
        else:
            dx = 0
        c.move_to(dx, size * 0.36)
        c.set_source_rgba(*col, alpha)
        c.show_text(s)
        c.restore()
        return ext.x_advance * scale

    def text_width(self, s, size, font=SANS, bold=False, italic=False):
        c = self.ctx
        c.save()
        c.select_font_face(font, cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL,
                           cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        c.set_font_size(size)
        w = c.text_extents(s).x_advance
        c.restore()
        return w

    def math_row(self, parts, x, y, size, alpha=1.0, align="center", sup_scale=0.6, maxw=940):
        """parts: list of (text, colour[, 'sup']) drawn in the maths serif font.
        Shrinks to fit maxw so it never leaves the safe area."""
        tw = sum(self.text_width(p[0], size * (sup_scale if len(p) > 2 else 1), MATH) for p in parts)
        if tw > maxw:
            size *= maxw / tw
        widths = []
        for p in parts:
            sz = size * (sup_scale if len(p) > 2 and p[2] == "sup" else 1)
            widths.append(self.text_width(p[0], sz, MATH))
        total = sum(widths)
        cx = x - total / 2 if align == "center" else x
        for p, w in zip(parts, widths):
            sup = len(p) > 2 and p[2] == "sup"
            sz = size * (sup_scale if sup else 1)
            yy = y - size * 0.42 if sup else y
            self.text(p[0], cx, yy, sz, p[1], alpha, MATH, align="left")
            cx += w
        return total

    # --- shapes
    def rect(self, x, y, w, h, col, alpha=1.0, r=0, fill=True, lw=3):
        c = self.ctx
        if alpha <= 0.001:
            return
        c.new_path()
        if r > 0:
            r = min(r, w / 2, h / 2)
            c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
            c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
            c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
            c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
            c.close_path()
        else:
            c.rectangle(x, y, w, h)
        c.set_source_rgba(*col, alpha)
        if fill:
            c.fill()
        else:
            c.set_line_width(lw); c.stroke()

    def line(self, x0, y0, x1, y1, col=WHITE, alpha=1.0, lw=3, p=1.0):
        if alpha <= 0.001 or p <= 0:
            return
        c = self.ctx
        c.set_source_rgba(*col, alpha)
        c.set_line_width(lw)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(x0, y0); c.line_to(lerp(x0, x1, p), lerp(y0, y1, p)); c.stroke()

    def circle(self, x, y, r, col=WHITE, alpha=1.0, fill=True, lw=3):
        if alpha <= 0.001 or r <= 0:
            return
        c = self.ctx
        c.new_path(); c.arc(x, y, r, 0, 2 * math.pi)
        c.set_source_rgba(*col, alpha)
        if fill:
            c.fill()
        else:
            c.set_line_width(lw); c.stroke()

    def glow(self, x, y, r, col=WHITE, alpha=0.5):
        if alpha <= 0.001:
            return
        g = cairo.RadialGradient(x, y, 0, x, y, r)
        g.add_color_stop_rgba(0, *col, alpha)
        g.add_color_stop_rgba(1, *col, 0)
        self.ctx.set_source(g)
        self.ctx.arc(x, y, r, 0, 2 * math.pi); self.ctx.fill()

    def flash(self, a):
        if a > 0.001:
            self.ctx.set_source_rgba(1, 1, 1, clamp(a)); self.ctx.paint()

    # --- chrome: handle, caption, progress bar
    def chrome(self, t, total):
        self.text(HANDLE, W / 2, 150, 30, DIM, 0.85, SANS, bold=True)
        # progress bar (bottom, inside safe area)
        x0, y0, w = 200, 1640, W - 400
        self.rect(x0, y0, w, 10, WHITE, 0.10, r=5)
        self.rect(x0, y0, max(10, w * clamp(t / total)), 10, GREEN, 0.95, r=5)

    def caption(self, s, t, t0, t1, y=1500, size=50, col=WHITE):
        a = window(t, t0, t1, 0.3)
        if a <= 0:
            return
        w = self.text_width(s, size, SANS, bold=True)
        if w > 960:
            size *= 960 / w
        rise = (1 - ease_out(prog(t, t0, 0.4))) * 20
        self.text(s, W / 2, y + rise, size, col, a, SANS, bold=True)

    def bloom(self, strength=0.55):
        """Cheap cinematic glow: downscale frame, upscale smoothly, add on top."""
        sc = cairo.Context(self.small)
        sc.scale(1 / 8, 1 / 8)
        sc.set_source_surface(self.surf); sc.get_source().set_filter(cairo.FILTER_GOOD)
        sc.paint()
        c = self.ctx
        c.save()
        c.scale(8, 8)
        c.set_source_surface(self.small)
        c.get_source().set_filter(cairo.FILTER_BILINEAR)
        c.set_operator(cairo.OPERATOR_ADD)
        c.paint_with_alpha(strength)
        c.restore()


def render(topic, out_path, preview_times=None):
    r = Reel()
    if hasattr(topic, "scene"):  # locked template (all new topics)
        from maths import template
        template.check(topic)
        draw = lambda rr, tt: template.frame(rr, topic, tt)
    else:  # legacy topic 1 (odd_squares) drew its own frame
        draw = topic.draw
    if preview_times:  # write PNG stills instead of video
        for tt in preview_times:
            draw(r, tt); r.bloom()
            r.surf.write_to_png(f"{out_path}_{tt:05.1f}.png")
        return
    n = int(round(topic.DURATION * FPS))
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", out_path],
        stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        draw(r, t)
        r.bloom()
        r.surf.flush()
        ff.stdin.write(bytes(r.surf.get_data()))
        if i % 150 == 0:
            print(f"frame {i}/{n}", file=sys.stderr, flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg failed")
