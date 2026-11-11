#!/usr/bin/env python3
"""Compose and render 'Blue Mesa Radio', the original track on the RV's radio.

An original desert-western piece written for this map - not a recording or an
arrangement of any existing theme. Everything is synthesised here from note
lists, so the file is reproducible and free to redistribute with the map.

Output: 22050 Hz, 16-bit mono PCM with a `cue ` chunk at sample 0. GoldSrc only
loops a WAV that carries a cue point, and reads the loop start from it. The
loop is rendered seamlessly: three cycles are synthesised and the middle one
kept, so the reverb and ring-out at its end flow into its own start.

Requires NumPy and SciPy.
"""
import math
import struct
from pathlib import Path

import numpy as np
from scipy import signal

SR = 22050
BPM = 78
BEAT = 60 / BPM
BARS = 12
LOOP = int(round(BARS * 4 * BEAT * SR))
RNG = np.random.default_rng(505)

# D minor, an Andalusian-style turnaround with a Gm detour in the last line.
CHORDS = ['Dm', 'C', 'Bb', 'A', 'Dm', 'C', 'Bb', 'A', 'Gm', 'Dm', 'Bb', 'A']
TONES = {'Dm': [50, 57, 62, 65], 'C': [48, 55, 60, 64], 'Bb': [46, 53, 58, 62],
         'A': [45, 52, 57, 61], 'Gm': [43, 50, 55, 58]}
BASS = {'Dm': 38, 'C': 36, 'Bb': 34, 'A': 33, 'Gm': 31}
# Lead line: (bar, beat, beats long, MIDI note, slide into it). Bars 1-2 are intro.
LEAD = [(2, 3.5, .5, 69, False),
        (3, 0, 1.5, 73, True), (3, 1.5, .5, 69, False), (3, 2, 2, 64, False),
        (4, 0, 1, 65, False), (4, 1, .5, 67, False), (4, 1.5, .5, 69, False),
        (4, 2, 1.5, 74, True), (4, 3.5, .5, 72, False),
        (5, 0, 1, 72, False), (5, 1, .5, 70, False), (5, 1.5, 2.5, 69, False),
        (6, 0, .5, 70, False), (6, .5, .5, 69, False), (6, 1, 1, 67, False),
        (6, 2, .5, 65, False), (6, 2.5, 1.5, 62, False),
        (7, 0, 1.5, 64, True), (7, 1.5, .5, 65, False), (7, 2, 2, 61, False),
        # Last line drops to the baritone register.
        (8, 0, 1, 55, False), (8, 1, .5, 58, False), (8, 1.5, .5, 62, False), (8, 2, 2, 67, True),
        (9, 0, 1.5, 69, False), (9, 1.5, .5, 65, False), (9, 2, 1, 62, False), (9, 3, 1, 57, False),
        (10, 0, 1, 58, False), (10, 1, .5, 62, False), (10, 1.5, .5, 65, False), (10, 2, 2, 70, True),
        (11, 0, 2, 69, False), (11, 2, 2, 57, True)]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pluck(f0, dur, bright=1.0, harmonics=12, ring=1.6, slide=False, tremolo=0.0):
    """Additive plucked string: bright attack, upper partials dying first."""
    n = int((dur + ring * .6) * SR)
    t = np.arange(n) / SR
    f = np.full(n, f0)
    if slide:       # slide up a whole tone into the note over 70 ms
        k = min(n, int(.07 * SR))
        f[:k] = f0 * 2 ** (np.linspace(-2, 0, k) / 12)
    f *= 1 + .0025 * np.sin(2 * math.pi * 4.8 * t) * np.clip(t / .3, 0, 1)   # late vibrato
    phase = 2 * math.pi * np.cumsum(f) / SR
    out = np.zeros(n)
    for h in range(1, harmonics + 1):
        if f0 * h > SR * .45:
            break
        amp = (1 / h ** .9) * (1 + .5 * math.sin(h * .9)) * bright ** (h - 1)
        out += amp * np.sin(h * phase) * np.exp(-t / (ring / (1 + .28 * h)))
    k = int(.008 * SR)   # pick noise
    out[:k] += RNG.normal(0, .35, k) * np.linspace(1, 0, k)
    if tremolo:
        out *= 1 - tremolo * (.5 + .5 * np.sin(2 * math.pi * 5.6 * t))
    end = int(dur * SR) + int(.25 * SR)   # damp the string after the note's length
    if end < n:
        out[end:] *= np.exp(-np.arange(n - end) / (.06 * SR))
    return out


def noise_hit(dur, lo, hi, decay):
    n = int(dur * SR)
    b, a = signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], 'band')
    x = signal.lfilter(b, a, RNG.normal(0, 1, n))
    return x * np.exp(-np.arange(n) / (decay * SR))


def kick():
    n = int(.35 * SR)
    t = np.arange(n) / SR
    f = 42 + 40 * np.exp(-t / .03)
    return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t / .12)


def render():
    total = 3 * LOOP + int(3 * SR)
    lead, rhythm, bass, drums, pad = (np.zeros(total) for _ in range(5))

    def put(buf, at, x, gain):
        i = int(at * SR)
        j = min(total, i + len(x))
        buf[i:j] += gain * x[:j - i]

    for cycle in range(3):
        base = cycle * LOOP / SR
        for bar, chord in enumerate(CHORDS):
            t0 = base + bar * 4 * BEAT
            tones = TONES[chord]
            # Fingerpicked arpeggio in eighths.
            for i, k in enumerate([0, 2, 1, 2, 3, 2, 1, 2]):
                put(rhythm, t0 + i * BEAT / 2, pluck(hz(tones[k]), BEAT * .9, bright=.8, harmonics=8, ring=1.1),
                    .22 if i % 2 else .3)
            # Bass: root, a syncopated root, the fifth, a pickup root.
            r = BASS[chord]
            for beat, note, g in [(0, r, 1), (1.5, r, .6), (2, r + 7, .75), (3.5, r, .55)]:
                put(bass, t0 + beat * BEAT, pluck(hz(note), BEAT, bright=.55, harmonics=5, ring=1.0), g)
            # Kick on 1 and the and-of-3, brush on 2 and 4, shaker in eighths.
            for beat in (0, 2.5):
                put(drums, t0 + beat * BEAT, kick(), .9)
            for beat in (1, 3):
                put(drums, t0 + beat * BEAT, noise_hit(.18, 1800, 6000, .05), .22)
            for i in range(8):
                put(drums, t0 + i * BEAT / 2, noise_hit(.07, 5000, 9500, .018), .16 if i % 2 else .09)
        for bar, beat, dur, note, slide in LEAD:
            put(lead, base + (bar * 4 + beat) * BEAT, pluck(hz(note), dur * BEAT, bright=.93, slide=slide,
                                                           ring=2.2, tremolo=.32), .55)
    # Low D-A drone, breathing over two bars.
    t = np.arange(total) / SR
    swell = .55 + .45 * np.sin(2 * math.pi * t / (8 * BEAT))
    for m, g in [(38, .5), (45, .35), (50, .18)]:
        pad += g * np.sin(2 * math.pi * hz(m) * t + .3 * np.sin(2 * math.pi * .21 * t))
    pad *= swell * .16
    # Spring-style slapback on the lead, then one shared reverb.
    d = int(.118 * SR)
    lead[d:] += .32 * lead[:-d]
    dry = lead + .8 * rhythm + .9 * bass + .8 * drums + pad
    ir_n = int(1.5 * SR)
    ir = RNG.normal(0, 1, ir_n) * np.exp(-np.arange(ir_n) / (.33 * SR))
    ir = signal.lfilter(*signal.butter(1, 4000 / (SR / 2)), ir)
    ir /= np.sqrt((ir ** 2).sum())
    wet = signal.fftconvolve(lead + .6 * rhythm + .3 * drums, ir)[:total]
    mix = dry + .45 * wet
    # A radio in a camper: rolled-off lows and highs, gently saturated.
    mix = signal.lfilter(*signal.butter(2, 110 / (SR / 2), 'high'), mix)
    mix = signal.lfilter(*signal.butter(2, 6000 / (SR / 2)), mix)
    seg = mix[LOOP:2 * LOOP]          # the middle cycle: seamless at both ends
    seg = np.tanh(1.4 * seg / np.max(np.abs(seg))) / math.tanh(1.4)
    return seg * .89                  # peak about -1 dBFS


def write_wav(path, samples, loop=True):
    """16-bit mono PCM. With loop, one cue point at sample 0 - the layout
    GoldSrc loops. Without it the sound plays once, which a one-shot must:
    a cue point would make it repeat until stopped."""
    pcm = np.clip(np.round(samples * 32767), -32768, 32767).astype('<i2').tobytes()
    fmt = struct.pack('<HHIIHH', 1, 1, SR, SR * 2, 2, 16)
    body = (b'WAVE' + b'fmt ' + struct.pack('<I', len(fmt)) + fmt
            + b'data' + struct.pack('<I', len(pcm)) + pcm + (b'\0' if len(pcm) % 2 else b''))
    if loop:
        # One cue point: count, then id, position, chunk, chunk start, block
        # start, sample offset - the loop start GoldSrc reads 32 bytes in.
        cue = struct.pack('<I', 1) + struct.pack('<II4sIII', 1, 0, b'data', 0, 0, 0)
        body += b'cue ' + struct.pack('<I', len(cue)) + cue
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'RIFF' + struct.pack('<I', len(body)) + body)


def write_clip(src, dst, seconds, start=0.0):
    """Cut a short one-shot from a PCM WAV: resampled to 22050 Hz mono, `seconds`
    long from `start`, with a short fade so it ends cleanly, peak -1 dBFS."""
    import wave
    with wave.open(str(src), 'rb') as w:
        ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width == 1:
        x = (np.frombuffer(raw, np.uint8).astype(float) - 128) / 128
    elif width == 2:
        x = np.frombuffer(raw, '<i2').astype(float) / 32768
    elif width == 4:
        x = np.frombuffer(raw, '<i4').astype(float) / 2 ** 31
    else:
        raise ValueError(f'{src}: {8 * width}-bit WAV is not supported; export 16-bit')
    x = x.reshape(-1, ch).mean(axis=1)
    g = math.gcd(SR, rate)
    x = signal.resample_poly(x, SR // g, rate // g)
    # Skip leading silence so the moment starts on the sound, not before it.
    lead = np.argmax(np.abs(x) > .02 * np.max(np.abs(x)))
    x = x[lead + int(start * SR): lead + int((start + seconds) * SR)]
    fade = min(len(x), int(.08 * SR))
    x[-fade:] *= np.linspace(1, 0, fade)
    x = x / max(np.max(np.abs(x)), 1e-9) * .89
    write_wav(Path(dst), x, loop=False)
    return len(x) / SR


def write_radio(path):
    samples = render()
    write_wav(Path(path), samples)
    return len(samples) / SR


if __name__ == '__main__':
    from generate_map import SOUND_DIR
    root = Path(__file__).resolve().parents[1]
    secs = write_radio(root / 'cstrike/sound' / SOUND_DIR / 'mesa_radio.wav')
    print(f'mesa_radio.wav: {secs:.1f} s loop')
