"""Synthesize background music + SFX and mix them to a WAV. No external assets."""
import json, sys, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(7)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def lowpass(x, alpha):
    # one-pole lowpass; alpha may be array
    y = np.zeros_like(x)
    a = np.broadcast_to(alpha, x.shape)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def lp_fast(x, cutoff):
    # FFT brickwall-ish lowpass (fast, static cutoff)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def hp_fast(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 - 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


# ---------------- SFX ----------------

def sfx_whoosh(dur=0.45, up=True):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    t = np.linspace(0, 1, n)
    sweep = (t if up else 1 - t)
    alpha = 0.02 + 0.25 * sweep ** 2
    y = lowpass(noise, alpha)
    y = y - lowpass(y, 0.01)
    env = np.sin(np.pi * t) ** 1.5
    y *= env
    return 0.9 * y / (np.abs(y).max() + 1e-9)


def sfx_pop(dur=0.09, f0=900, f1=220):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.geomspace(f0, f1, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * env_exp(n, 0.025)
    return 0.8 * y


def sfx_ding(dur=1.4, f=1318.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.01 * t) * env_exp(n, 0.15)
         + 0.25 * np.sin(2 * np.pi * f * 3.0 * t) * env_exp(n, 0.08))
    y *= env_exp(n, 0.45)
    y[:80] *= np.linspace(0, 1, 80)
    return 0.45 * y


def sfx_boom(dur=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 40 + 90 * np.exp(-t / 0.05)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.35)
    nz = lp_fast(rng.standard_normal(n), 1500) * env_exp(n, 0.06)
    y = y + 0.6 * nz / (np.abs(nz).max() + 1e-9)
    return 0.95 * np.tanh(1.6 * y)


def sfx_tick(dur=0.05):
    n = int(dur * SR)
    y = hp_fast(rng.standard_normal(n), 3000) * env_exp(n, 0.008)
    t = np.arange(n) / SR
    y += 0.6 * np.sin(2 * np.pi * 2200 * t) * env_exp(n, 0.012)
    return 0.6 * y / (np.abs(y).max() + 1e-9)


def sfx_riser(dur=2.0):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    y = lowpass(noise, 0.01 + 0.4 * t ** 2.5)
    tone = np.sin(2 * np.pi * np.cumsum(np.geomspace(200, 1200, n)) / SR)
    y = y / (np.abs(y).max() + 1e-9) + 0.15 * tone
    return 0.5 * y * t ** 2


def sfx_streak(dur=0.9):
    # fiery meteor streak: descending filtered noise + crackle
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    y = lowpass(rng.standard_normal(n), 0.35 - 0.3 * t)
    crackle = (rng.random(n) > 0.997) * rng.standard_normal(n) * 3
    y = y / (np.abs(y).max() + 1e-9) + crackle
    y *= np.sin(np.pi * t) ** 0.8
    return 0.7 * y / (np.abs(y).max() + 1e-9)


def sfx_hum(dur=2.5):
    # soft mains-style hum (100 Hz + harmonics), slow fade in/out
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 200 * t) + 0.25 * np.sin(2 * np.pi * 300 * t)
    env = np.minimum(1, np.minimum(t / 0.4, (dur - t) / 0.6))
    return 0.5 * y * env / 1.75


def sfx_zap(dur=0.35):
    # short electric pulse: buzzy saw chirp + noise burst
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 9) + 120
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = 2 * ((ph / (2 * np.pi)) % 1) - 1
    y = y + 0.4 * rng.standard_normal(n) * np.exp(-t * 30)
    return 0.6 * y * np.exp(-t * 10)


SFX = {
    "whoosh": lambda: sfx_whoosh(),
    "whoosh_down": lambda: sfx_whoosh(up=False),
    "pop": lambda: sfx_pop(),
    "pop_hi": lambda: sfx_pop(f0=1400, f1=500),
    "ding": lambda: sfx_ding(),
    "boom": lambda: sfx_boom(),
    "tick": lambda: sfx_tick(),
    "riser": lambda: sfx_riser(),
    "streak": lambda: sfx_streak(),
    "hum": lambda: sfx_hum(),
    "zap": lambda: sfx_zap(),
}

# ---------------- MUSIC ----------------

def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def synth_pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):
            ff = f * 2 ** (det / 12)
            for h in range(1, 6):
                y += np.sin(2 * np.pi * ff * h * t + rng.random() * 6.28) / (h ** 1.6)
    att = np.minimum(1, t / 0.6)
    rel = np.minimum(1, (dur - t) / 0.6)
    return y * att * rel / (len(freqs) * 3)


def synth_kick():
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    f = 45 + 120 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.12)


def synth_clap():
    n = int(0.25 * SR)
    y = hp_fast(rng.standard_normal(n), 900) * env_exp(n, 0.05)
    return 0.5 * y / np.abs(y).max()


def synth_hat():
    n = int(0.06 * SR)
    y = hp_fast(rng.standard_normal(n), 7000) * env_exp(n, 0.012)
    return 0.25 * y / np.abs(y).max()


def synth_bass(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    e = np.minimum(1, t / 0.01) * np.exp(-t / 0.5)
    return 0.6 * y * e


def synth_pluck(f, dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * h * t) * np.exp(-t * (6 + 4 * h)) / h for h in range(1, 5))
    return 0.35 * y


def add(buf, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += gain * sig[: j - i]


PROGS = [
    [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])],
    [(50, [50, 53, 57]), (46, [50, 53, 58]), (53, [53, 57, 60]), (48, [52, 55, 60])],
    [(52, [52, 55, 59]), (48, [52, 55, 60]), (55, [55, 59, 62]), (50, [54, 57, 62])],
    [(53, [53, 57, 60]), (55, [55, 59, 62]), (52, [52, 55, 59]), (57, [57, 60, 64])],
]


BPMS = [118, 112, 122, 108]


def make_music(total, drop, seed=0, light=False):
    bpm = BPMS[seed % 4]
    beat = 60 / bpm
    bar = 4 * beat
    buf = np.zeros(int(total * SR))
    # Am - F - C - G   (2 bars each would be slow; 1 bar each)
    prog = PROGS[(seed // 4 + seed) % len(PROGS)]
    arp_pat = [[0, 2, 1, 2, 0, 2, 1, 2], [0, 1, 2, 1, 0, 1, 2, 1], [2, 1, 0, 1, 2, 0, 1, 0]][seed % 3]
    t = 0.0
    k = 0
    while t < total:
        root, chord = prog[k % 4]
        add(buf, synth_pad([note(m) for m in chord], bar + 0.3), t, 0.35)
        if light:
            for s in range(8):
                m = chord[arp_pat[s]] + 12
                add(buf, synth_pluck(note(m)), t + s * beat / 2, 0.22)
        elif t >= drop - 1e-6:
            for b in range(4):
                tb = t + b * beat
                add(buf, synth_kick(), tb, 1.0)
                if b in (1, 3):
                    add(buf, synth_clap(), tb, 0.45)
                add(buf, synth_bass(note(root - 12), beat * 0.95), tb, 0.55)
                for e in range(4):
                    add(buf, synth_hat(), tb + e * beat / 4, 0.9 if e % 2 else 0.5)
            for s in range(8):
                m = chord[arp_pat[s]] + 12
                add(buf, synth_pluck(note(m)), t + s * beat / 2, 0.5)
        k += 1
        t += bar
    # fade out
    fo = int(1.8 * SR)
    buf[-fo:] *= np.linspace(1, 0, fo)
    buf[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    return buf / (np.abs(buf).max() + 1e-9)


def load_voice(path, total):
    """voiceover wav (any rate, mono/stereo) -> mono float at SR, padded to total seconds, peak 0.8."""
    import subprocess
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.int16).astype(float) / 32768
    out = np.zeros(int(total * SR))
    out[: min(len(v), len(out))] = v[: len(out)]
    return 0.8 * out / (np.abs(out).max() + 1e-9)


def main():
    cues = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    total = cues["duration"]
    voice = load_voice(cues["voice"], total) if cues.get("voice") else None
    music = make_music(total, cues["drop"], cues.get("seed", 0), light=voice is not None)
    sfx = np.zeros_like(music)
    duck = np.ones_like(music)
    cache = {}
    for name, t0, gain in cues["sfx"]:
        if name not in cache:
            cache[name] = SFX[name]()
        add(sfx, cache[name], t0, gain)
        # gentle duck of music under each sfx
        i = int(t0 * SR); j = min(len(duck), i + int(0.35 * SR))
        duck[i:j] = np.minimum(duck[i:j], 0.6)
    # smooth duck
    k = int(0.05 * SR)
    duck = np.convolve(duck, np.ones(k) / k, mode="same")
    if voice is not None:
        # voiceover on top: music low and ducked further while the voice speaks, sfx subtle
        env = np.convolve(np.abs(voice), np.ones(int(0.3 * SR)) / int(0.3 * SR), mode="same")
        vduck = 1 - 0.55 * np.clip(env / (env.max() * 0.25 + 1e-9), 0, 1)
        mix = 0.16 * music * duck * vduck + 0.22 * sfx + 1.0 * voice
        mix = 0.95 * mix / (np.abs(mix).max() + 1e-9)
    else:
        mix = 0.40 * music * duck + 0.75 * sfx
        mix = np.tanh(1.2 * mix) / np.tanh(1.2)
    mix = 0.89 * mix / (np.abs(mix).max() + 1e-9)
    # stereo: tiny width on music
    left = mix
    right = np.roll(mix, int(0.0004 * SR))
    st = np.stack([left, right], 1)
    pcm = (st * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main()
