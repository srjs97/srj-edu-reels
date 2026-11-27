"""Procedural audio for maths reels: original ambient music + synced SFX. No samples, no copyrighted audio.

sfx events: (name, time_s, gain[, pitch_semitones])
names: click, pop, tick, whoosh, chime, boom, riser, sparkle
"""
import wave
import numpy as np

SR = 44100


def _env(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def _fade(y, a=0.004, b=0.02):
    na, nb = int(a * SR), int(b * SR)
    if na: y[:na] *= np.linspace(0, 1, na)
    if nb: y[-nb:] *= np.linspace(1, 0, nb)
    return y


def _lp(x, cutoff):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / cutoff) ** 4), len(x))


def _bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = (1 / (1 + (f / hi) ** 4)) * (1 - 1 / (1 + (f / lo) ** 4))
    return np.fft.irfft(X * m, len(x))


def _reverb(x, decay=2.2, mix=0.3, seed=3):
    rng = np.random.default_rng(seed)
    n = int(decay * SR)
    ir = rng.standard_normal(n) * _env(n, decay / 6.9)
    ir = _lp(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(x)]
    return (1 - mix) * x + mix * wet


rng = np.random.default_rng(11)


def sfx(name, pitch=0.0):
    k = 2 ** (pitch / 12)
    if name == "click":
        n = int(0.04 * SR); t = np.arange(n) / SR
        y = np.sin(2 * np.pi * 2400 * k * t) * _env(n, 0.006) + 0.3 * rng.standard_normal(n) * _env(n, 0.002)
        return _fade(0.5 * y, 0.0005, 0.005)
    if name == "tick":
        n = int(0.03 * SR); t = np.arange(n) / SR
        return _fade(0.35 * np.sin(2 * np.pi * 3800 * k * t) * _env(n, 0.004), 0.0005, 0.005)
    if name == "pop":
        n = int(0.16 * SR); t = np.arange(n) / SR
        f = 520 * k * (1 + 0.9 * np.exp(-t / 0.012))
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.045)
        return _fade(0.7 * y, 0.0008, 0.02)
    if name == "chime":
        n = int(2.2 * SR); t = np.arange(n) / SR
        f = 880 * k
        y = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * f * 2.0 * t) * _env(n, 0.4)
             + 0.25 * np.sin(2 * np.pi * f * 3.01 * t) * _env(n, 0.2)
             + 0.5 * np.sin(2 * np.pi * f * 1.5 * t) * _env(n, 0.6)) * _env(n, 0.7)
        return _fade(0.32 * y, 0.002, 0.2)
    if name == "sparkle":
        out = np.zeros(int(1.2 * SR))
        for i, st in enumerate([0, 4, 7, 12, 16]):
            s = sfx("tick", pitch + st - 12)
            o = int(i * 0.06 * SR); out[o:o + len(s)] += s * 0.8
        return out
    if name == "whoosh":
        n = int(0.6 * SR); t = np.linspace(0, 1, n)
        env = np.sin(np.pi * t ** 0.8) ** 3
        y = _bp(rng.standard_normal(n), 250, 1800) * env
        y = _lp(y, 2200)
        return _fade(0.45 * y / (np.abs(y).max() + 1e-9), 0.02, 0.05)
    if name == "boom":
        n = int(2.0 * SR); t = np.arange(n) / SR
        f = 38 + 70 * np.exp(-t / 0.08)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.6)
        nz = _lp(rng.standard_normal(n), 900) * _env(n, 0.12)
        y = y + 0.5 * nz / (np.abs(nz).max() + 1e-9)
        return _fade(0.9 * np.tanh(1.4 * y), 0.001, 0.3)
    if name == "riser":
        n = int(2.0 * SR); t = np.linspace(0, 1, n)
        f = 180 * k * 2 ** (2.5 * t ** 2)
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
        nz = _bp(rng.standard_normal(n), 800, 7000) * 0.25
        y = (tone + nz * t) * t ** 2
        return _fade(0.55 * y / (np.abs(y).max() + 1e-9), 0.05, 0.02)
    raise ValueError(name)


# ---------------- music ----------------

def _midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def music(total, wow_at=None, seed=0, bpm=84):
    """Ambient pad + soft pulse + pluck arpeggio. Builds slightly after wow_at."""
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    # progression (A minor family, varied by seed)
    progs = [[57, 53, 48, 55], [50, 46, 53, 48], [52, 48, 55, 50]]
    roots = progs[seed % len(progs)]
    beat = 60 / bpm
    bar = 4 * beat
    chord_len = 2 * bar
    # pad
    for i in range(int(total / chord_len) + 1):
        root = roots[i % 4]
        minor = (i % 4) == 0
        notes = [root, root + (3 if minor else 4), root + 7, root + 12 + (3 if minor else 4) - 12 + 12]
        s0, s1 = int(i * chord_len * SR), min(n, int((i + 1) * chord_len * SR + 0.8 * SR))
        if s0 >= n:
            break
        tt = np.arange(s1 - s0) / SR
        seg = np.zeros(s1 - s0)
        for m in notes:
            f = _midi(m)
            for d in (-0.08, 0.08):  # detuned pair
                seg += np.sin(2 * np.pi * f * (1 + d / 100) * tt + rng.uniform(0, 6))
        a = np.minimum(1, tt / 1.2) * np.minimum(1, (len(tt) / SR - tt) / 0.8)
        out[s0:s1] += 0.045 * seg * a
    out = _lp(out, 1400)
    # pluck arpeggio (8th notes), enters after 2 s
    arp = np.zeros(n)
    k = 0
    tt0 = 2.0
    while tt0 < total - 1.5:
        i = int(tt0 / chord_len)
        root = roots[i % 4] + 12
        minor = (i % 4) == 0
        pattern = [0, 7, 12, 3 if minor else 4, 7, 12, 15 if minor else 16, 12]
        m = root + pattern[k % 8]
        L = int(0.5 * SR); s = int(tt0 * SR)
        x = np.arange(L) / SR
        f = _midi(m)
        y = (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)) * _env(L, 0.12)
        g = 0.05 if (wow_at is None or tt0 < wow_at) else 0.075
        e = min(n, s + L); arp[s:e] += g * y[:e - s]
        tt0 += beat / 2; k += 1
    out += _reverb(arp, 1.8, 0.45)
    # soft sub pulse on beats (after 3 s)
    pulse = np.zeros(n)
    tb = 3.0
    while tb < total - 1:
        i = int(tb / chord_len)
        f = _midi(roots[i % 4] - 12)
        L = int(0.45 * SR); s = int(tb * SR)
        x = np.arange(L) / SR
        y = np.sin(2 * np.pi * f * x) * _env(L, 0.15) * np.minimum(1, x / 0.01)
        g = 0.10 if (wow_at is None or tb < wow_at) else 0.16
        e = min(n, s + L); pulse[s:e] += g * y[:e - s]
        tb += beat
    out += pulse
    out = _reverb(out, 2.5, 0.2, seed=5)
    # global fades
    out *= np.minimum(1, t / 1.0) * np.minimum(1, (total - t) / 1.5)
    return out


def mix(total, events, wow_at=None, seed=0, out_path="mix.wav"):
    n = int(total * SR)
    m = music(total, wow_at, seed)
    fx = np.zeros(n)
    for ev in events:
        name, at, gain = ev[0], ev[1], ev[2]
        pitch = ev[3] if len(ev) > 3 else 0.0
        s = sfx(name, pitch)
        if name == "riser":  # riser ends at `at`
            at = at - len(s) / SR
        i = int(max(0, at) * SR)
        e = min(n, i + len(s))
        if e > i:
            fx[i:e] += gain * s[:e - i]
    fx = _reverb(fx, 1.4, 0.18, seed=9)
    # duck music under sfx a little
    envf = np.convolve(np.abs(fx), np.ones(2205) / 2205, mode="same")
    duck = 1 - 0.35 * np.clip(envf * 6, 0, 1)
    y = 0.8 * m * duck + fx
    y = np.tanh(1.2 * y) / np.tanh(1.2)
    y *= 0.89 / (np.abs(y).max() + 1e-9)  # -1 dBFS peak
    st = np.stack([y, np.roll(y, 220) * 0.98], 1)  # light stereo width
    pcm = (st * 32767).astype(np.int16)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
