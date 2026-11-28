"""Render a maths reel: python3 -m maths.make <topic_slug> <out.mp4> [--preview 1.0,5.5,...]

Output: 1080x1920, 30 fps, H.264 + AAC 48 kHz stereo, faststart (fits IG Reels / YT Shorts / FB Reels).
"""
import argparse, importlib, os, subprocess, tempfile
from maths import engine, sound


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug"); ap.add_argument("out")
    ap.add_argument("--preview", help="comma-separated seconds: write PNG stills instead of a video")
    a = ap.parse_args()
    topic = importlib.import_module(f"maths.topics.{a.slug}")
    if a.preview:
        engine.render(topic, a.out, [float(x) for x in a.preview.split(",")])
        return
    with tempfile.TemporaryDirectory() as td:
        silent, wav = os.path.join(td, "v.mp4"), os.path.join(td, "a.wav")
        from maths import template
        events = template.sfx(topic) if hasattr(topic, "scene") else topic.sfx()
        sound.mix(topic.DURATION, events, getattr(topic, "WOW_AT", None),
                  getattr(topic, "MUSIC_SEED", 0), wav)
        engine.render(topic, silent)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
            "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "3000k", "-bufsize", "6000k",
            "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "30",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-shortest", a.out], check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
