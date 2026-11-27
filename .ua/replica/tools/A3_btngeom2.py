# -*- coding: utf-8 -*-
"""A3: 用已存中位数图精修三键圆心(亚像素 0.5)与环半径。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
X0, Y0 = 1322, 330
g = np.load(DATA + '/A3_btn_median.npy').astype(np.float32).mean(-1)
def prof(cx, cy, rmax=115, hw=120):
    x0, y0 = max(int(cx - X0) - hw, 0), max(int(cy - Y0) - hw, 0)
    sub = g[y0:y0 + 2 * hw, x0:x0 + 2 * hw]
    yy, xx = np.mgrid[y0:y0 + sub.shape[0], x0:x0 + sub.shape[1]]
    r = np.hypot(xx - (cx - X0), yy - (cy - Y0)); m = r < rmax
    rb = (r[m] + 0.5).astype(int)
    return np.bincount(rb, sub[m], rmax + 1) / np.maximum(np.bincount(rb, minlength=rmax + 1), 1)
for k, (cx0, cy0, rng) in {'gaodiao': (1732, 447, 14), 'jinqiu': (1456, 719.5, 3), 'yuanqiu': (1708.5, 686.5, 3)}.items():
    best = None
    for dx in np.arange(-rng, rng + .1, 0.5 if rng < 5 else 1):
        for dy in np.arange(-rng, rng + .1, 0.5 if rng < 5 else 1):
            p = prof(cx0 + dx, cy0 + dy)
            sc = np.abs(np.diff(p[70:100])).max()
            if best is None or sc > best[0]:
                best = (sc, cx0 + dx, cy0 + dy)
    _, cx, cy = best
    P = prof(cx, cy); d = np.diff(P)
    half = (P[78] + P[90]) / 2
    print(k, 'center', cx, cy, 'edge r=', 70 + int(np.abs(d[70:100]).argmax()), 'score %.1f' % best[0])
    print('  P r70..104:', ' '.join('%d' % v for v in P[70:105]))
