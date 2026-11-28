"""SRJ EDU maths reel TEMPLATE (locked, Suraj 2026-11-28: every maths reel uses one template,
same layout and style; only the topic and its animation change). Do not change per topic.

Fixed for every reel:
  - black background + faint drifting grid + vignette (engine.Reel.background)
  - @srj_edu_app handle (y 150) and TAG line (y 215) at the top, green progress bar (y 1640)
  - captions: Inter bold 50 px, centred at y 1500 (y 1420 during the end card), white
  - wow moment: white flash at WOW_AT (topic adds riser + boom + sparkle sounds)
  - end card from QUESTION_AT: "YOUR TURN" (y 1080) + QUESTION (y 1170, yellow) + "Comment your answer below"
  - 0.4 s fade to black, same music generator (sound.music), same loudness/export (make.py)

A template topic module defines:
  TAG          short uppercase line, e.g. "ODD NUMBERS  ×  SQUARES"
  TITLE, DURATION (35-55 s), WOW_AT, MUSIC_SEED (= n mod 3), QUESTION_AT, QUESTION (<= 40 chars)
  CAPTIONS     list of (text, t0, t1); none may overlap QUESTION_AT..DURATION
  scene(r, t)  topic visuals ONLY (camera, shapes, equations, hook, formula). Must NOT call
               background(), chrome(), caption(), flash() or fade; keep y 1000-1600 clear after QUESTION_AT.
  camera(r, t) optional; sets the camera before the background is drawn.
  sfx()        list of (name, time, gain[, pitch]); template adds its own end-card sounds.
  YT_TITLE, CAPTION, HASHTAGS for publishing.
"""
from maths.engine import W, WHITE, DIM, YELLOW, SANS, prog, ease, ease_out

HANDLE_Y, TAG_Y, CAPTION_Y, END_CAPTION_Y = 150, 215, 1500, 1420
END_CTA = "Comment your answer below"


def frame(r, topic, t):
    r.set_camera()
    if hasattr(topic, "camera"):  # optional: camera(r, t) sets zoom/pan so the grid moves with the scene
        topic.camera(r, t)
    r.background(t)
    topic.scene(r, t)
    r.set_camera()
    # header tag
    r.text(topic.TAG, W / 2, TAG_Y, 30, DIM, 0.7, SANS, bold=True)
    # wow flash
    if t >= topic.WOW_AT:
        r.flash(0.55 * (1 - ease_out(prog(t, topic.WOW_AT, 0.5))))
    # captions
    qa_t = topic.QUESTION_AT
    for s, a, b in topic.CAPTIONS:
        # frame 0 is the thumbnail: a caption starting at 0 is shown fully there
        r.caption(s, (a + b) / 2 if (t < 0.001 and a <= 0) else t, a, b, y=CAPTION_Y)
    # end card
    if t >= qa_t:
        a = ease(prog(t, qa_t, 0.5))
        r.text("YOUR TURN", W / 2, 1080, 36, DIM, a, SANS, bold=True)
        size = 58
        w = r.text_width(topic.QUESTION, size, SANS, bold=True)
        if w > 940:
            size *= 940 / w
        r.glow(W / 2, 1170, 300, YELLOW, 0.12 * a)
        r.text(topic.QUESTION, W / 2, 1170, size, YELLOW, a, SANS, bold=True)
        r.caption(END_CTA, t, qa_t + 0.6, topic.DURATION + 1, y=END_CAPTION_Y)
    r.chrome(t, topic.DURATION)
    if t > topic.DURATION - 0.4:
        r.ctx.set_source_rgba(0, 0, 0, prog(t, topic.DURATION - 0.4, 0.4)); r.ctx.paint()


def sfx(topic):
    """Topic sounds + the fixed end-card sounds."""
    return list(topic.sfx()) + [("whoosh", topic.QUESTION_AT - 0.1, 0.4), ("pop", topic.QUESTION_AT + 0.05, 0.6, 7),
                                ("chime", topic.QUESTION_AT + 0.6, 0.5, 12)]


def check(topic):
    """Fail fast if a topic breaks the template contract."""
    need = ["TAG", "TITLE", "DURATION", "WOW_AT", "MUSIC_SEED", "QUESTION_AT", "QUESTION", "CAPTIONS",
            "scene", "sfx", "YT_TITLE", "CAPTION", "HASHTAGS"]
    miss = [k for k in need if not hasattr(topic, k)]
    if miss:
        raise SystemExit(f"topic is missing template fields: {miss}")
    if hasattr(topic, "draw"):
        raise SystemExit("template topics define scene(r, t), not draw(r, t)")
    if not 35 <= topic.DURATION <= 55:
        raise SystemExit("DURATION must be 35-55 s")
    if not 3 < topic.WOW_AT < topic.QUESTION_AT < topic.DURATION - 2:
        raise SystemExit("need 3 < WOW_AT < QUESTION_AT < DURATION - 2")
    for s, a, b in topic.CAPTIONS:
        if b > topic.QUESTION_AT + 0.01:
            raise SystemExit(f"caption overlaps the end card: {s!r}")
        if len(s) > 48:
            raise SystemExit(f"caption too long (max 48 chars): {s!r}")
    if len(topic.QUESTION) > 40:
        raise SystemExit("QUESTION max 40 chars")
