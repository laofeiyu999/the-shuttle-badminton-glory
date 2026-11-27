"""Find the time offset between the two FeiYu full-match videos from their audio.

Usage: python sync_audio.py
Prints offset such that  t_side = t_main + offset  (seconds), checked on several windows.
"""
import wave
import numpy as np
from scipy.signal import correlate

AUD = __file__.replace("\\", "/").rsplit("/", 2)[0] + "/audio/"


def load(name):
    with wave.open(AUD + name, "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    return sr, x


def envelope(x, sr, hop):
    n = len(x) // hop
    e = np.abs(x[: n * hop]).reshape(n, hop).mean(axis=1)
    d = np.diff(e, prepend=e[0])
    d[d < 0] = 0  # onset strength
    return (d - d.mean()) / (d.std() + 1e-9)


def best_lag(a, b):
    c = correlate(b, a, mode="full", method="fft")
    lag = int(np.argmax(c)) - (len(a) - 1)
    peak = c.max()
    c2 = c.copy()
    i = int(np.argmax(c))
    c2[max(0, i - 50): i + 50] = 0
    return lag, peak / (np.abs(c2).max() + 1e-9)


sr, m = load("fy_main.wav")
sr2, s = load("fy_side.wav")
assert sr == sr2
hop = 40  # 5 ms at 8 kHz
em, es = envelope(m, sr, hop), envelope(s, sr, hop)
dt = hop / sr
lag, ratio = best_lag(em, es)
print(f"global: t_side = t_main + {lag * dt:+.3f} s  (peak/second-peak {ratio:.2f})")
win = int(30 / dt)
for start in range(0, len(em) - win, win):
    seg = em[start: start + win]
    lo = max(0, start + lag - int(5 / dt))
    hi = min(len(es), start + lag + win + int(5 / dt))
    l2, r2 = best_lag(seg, es[lo:hi])
    off = (lo + l2 - start) * dt
    print(f"  main {start * dt:6.1f}-{(start + win) * dt:6.1f}s: offset {off:+.3f} s (ratio {r2:.2f})")
