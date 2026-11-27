# -*- coding: utf-8 -*-
"""由闪光事件生成击球候选表 data/B2_hits.csv：帧、时间、击球方、闪光中心像素、击球者脚下位置(米)、闪光中心在击球者地面点上方的高度(米)、击球者速度曲线(前后 0.6 s)。"""
import sys, os, csv
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
d = np.load(os.path.join(DATA, 'B2_post.npz')); cal = np.load(os.path.join(DATA, 'B2_calib.npz')); Hm = cal['H']; P = cal['P']
A = np.load(os.path.join(DATA, 'B2_track_raw.npy')); keys = open(os.path.join(DATA, 'B2_track_raw.csv')).readline().strip().split(','); C = {k: A[:, i] for i, k in enumerate(keys)}
ev = list(csv.DictReader(open(os.path.join(DATA, 'B2_flash_events.csv'))))
def height_at(X, Z, v):
    a = P[1, 0] * X + P[1, 2] * Z + P[1, 3]; b = P[1, 1]; c = P[2, 0] * X + P[2, 2] * Z + P[2, 3]; dd = P[2, 1]
    return (v * c - a) / (b - v * dd)
rows = []
for e in ev:
    f = int(e['f_start']); cx = float(e['cx']); cy = float(e['cy']); dur = int(e['dur_frames'])
    if dur >= 13 and 600 < cx < 1100 and cy < 980 and int(e['peak_excess_px']) in range(3000, 13500) and abs(cx - 900) < 200:
        pass
    best = None
    for s in 'LR':
        g = f
        for k in range(0, 8):
            for c in (f - k, f + k):
                if not np.isnan(C[s + '_cx'][c]): g = c; break
            else: continue
            break
        dist = np.hypot(C[s + '_cx'][g] - cx, (C[s + '_cy'][g] - cy)) if not np.isnan(C[s + '_cx'][g]) else 1e9
        if best is None or dist < best[1]: best = (s, dist)
    s, dist = best
    x = d[s + '_x'][f]; z = d[s + '_z'][f]
    k = 0
    while np.isnan(x) and k < 15:
        k += 1
        for c in (f - k, f + k):
            if not np.isnan(d[s + '_x'][c]): x = d[s + '_x'][c]; z = d[s + '_z'][c]; break
    hy = height_at(x, z, cy) if not np.isnan(x) else np.nan
    rows.append([f, '%.2f' % (f / FPS), s, '%.0f' % dist, '%.0f' % cx, '%.0f' % cy, e['dur_frames'], e['peak_excess_px'], '%.2f' % x, '%.2f' % z, '%.2f' % hy])
with open(os.path.join(DATA, 'B2_hits_auto.csv'), 'w', newline='') as fo:
    w = csv.writer(fo); w.writerow(['frame', 't', 'side', 'dist_px', 'fl_cx', 'fl_cy', 'dur', 'peak', 'x', 'z', 'flash_h']); w.writerows(rows)
print(len(rows))
