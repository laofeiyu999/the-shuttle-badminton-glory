# -*- coding: utf-8 -*-
"""A3: 三个击球键几何。多帧取时间中位数(消除背景)→ 局部裁剪 → 径向梯度找环半径，圆心网格搜索。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
frames = [1200, 1500, 2400, 2700, 4400, 4700, 5700, 6400, 7300, 7700, 9000, 9500, 10300, 11500, 12000, 13200]
X0, Y0, CW, CH = 1322, 330, 600, 550
st = np.stack([get_frame(f, crop=(X0, Y0, CW, CH)).astype(np.float32) for f in frames])
med = np.median(st, 0)
np.save(DATA + '/A3_btn_median.npy', med.astype(np.uint8))
Image.fromarray(med.astype(np.uint8)).save(FR + '/A3_btn_median.png')
g = med.mean(-1)
init = {'gaodiao': (1729.5, 452.5), 'jinqiu': (1457, 717.5), 'yuanqiu': (1709.5, 687.5)}
def prof(cx, cy, rmax=115, hw=120):
    x0, y0 = int(cx - X0) - hw, int(cy - Y0) - hw
    sub = g[max(y0, 0):y0 + 2 * hw, max(x0, 0):x0 + 2 * hw]
    yy, xx = np.mgrid[max(y0, 0):max(y0, 0) + sub.shape[0], max(x0, 0):max(x0, 0) + sub.shape[1]]
    r = np.hypot(xx - (cx - X0), yy - (cy - Y0)); m = r < rmax
    rb = (r[m] + 0.5).astype(int)
    return np.bincount(rb, sub[m], rmax + 1) / np.maximum(np.bincount(rb, minlength=rmax + 1), 1)
for k, (cx0, cy0) in init.items():
    best = None
    for dx in np.arange(-8, 8.1, 1):
        for dy in np.arange(-8, 8.1, 1):
            p = prof(cx0 + dx, cy0 + dy)
            sc = np.abs(np.diff(p[60:110])).max()
            if best is None or sc > best[0]:
                best = (sc, cx0 + dx, cy0 + dy)
    _, cx, cy = best
    P = prof(cx, cy)
    d = np.diff(P)
    print(k, 'center', cx, cy, 'max|grad| at r=', 60 + int(np.abs(d[60:110]).argmax()), 'score %.1f' % best[0])
    print('  P r0..112 step4:', ' '.join('%d' % v for v in P[0:113:4]))
    print('  P r66..104:', ' '.join('%d' % v for v in P[66:105]))
