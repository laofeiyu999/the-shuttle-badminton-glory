# -*- coding: utf-8 -*-
"""A_energy.py 的后处理：标定 0/100% 位置，输出 data/A_energy.csv 与 data/A_energy_events.csv。
六个稳定档位的游标 x（条带坐标）= 30.75, 106.96, 183.11, 259.0, 335.2, 411.2 → 间距 76.1 px = 20%。
"""
import numpy as np, os, tempfile, csv
FPS = 60.0
o = np.load(os.path.join(tempfile.gettempdir(), 'A_energy_raw.npy'))
x = o[:, 0].astype(float); v = o[:, 1]
NF = len(x)
ok = v >= 18
XL, XR = 30.75, 411.2
e = (x - XL) / (XR - XL)
e[~ok] = np.nan
# 剔除孤立跳点：与前后 5 帧中位数差 > 0.08 且不成段
from scipy.ndimage import median_filter
ef = e.copy()
idx = np.arange(NF)
good = ~np.isnan(ef)
ef_i = np.interp(idx, idx[good], ef[good])
med = median_filter(ef_i, 7, mode='nearest')
spike = good & (np.abs(ef_i - med) > 0.06)
print('spikes', spike.sum())
good2 = good & ~spike
ef_i = np.interp(idx, idx[good2], ef[good2])
ef_i = np.clip(ef_i, 0, 1)
lvl = np.round(ef_i * 5) / 5
stable = np.abs(ef_i - lvl) < 0.012
D = os.path.join(os.path.dirname(__file__), '..', 'data')
with open(os.path.join(D, 'A_energy.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['frame', 't_s', 'fill_0_1', 'level_pct_nearest', 'is_stable', 'measured(1)/interpolated(0)', 'marker_x_px_screen', 'barR_25', 'barB_25', 'barR_92', 'barB_92'])
    for i in range(NF):
        w.writerow([i, '%.4f' % (i / FPS), '%.4f' % ef_i[i], int(round(lvl[i] * 100)), int(stable[i]), int(good2[i]),
                    '%.1f' % (x[i] + 730) if good2[i] else '', int(o[i, 2]), int(o[i, 3]), int(o[i, 6]), int(o[i, 7])])
# 事件：稳定档位变化
ev = []
i = 0
cur = lvl[0]
# 找每段稳定区间
segs = []
s = None
for i in range(NF):
    if stable[i]:
        if s is None: s = i
    else:
        if s is not None:
            if i - s >= 4: segs.append((s, i - 1, float(np.median(lvl[s:i]))))
            s = None
if s is not None: segs.append((s, NF - 1, float(np.median(lvl[s:]))))
# 合并相邻同档
m = [segs[0]]
for a, b, l in segs[1:]:
    if abs(l - m[-1][2]) < 1e-6: m[-1] = (m[-1][0], b, l)
    else: m.append((a, b, l))
with open(os.path.join(D, 'A_energy_events.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['change_start_frame', 'change_end_frame', 't_start_s', 't_end_s', 'dur_frames', 'from_pct', 'to_pct', 'delta_pct'])
    for k in range(1, len(m)):
        a = m[k - 1][1]; b = m[k][0]
        w.writerow([a, b, '%.3f' % (a / FPS), '%.3f' % (b / FPS), b - a, int(m[k - 1][2] * 100), int(m[k][2] * 100), int(round((m[k][2] - m[k - 1][2]) * 100))])
        print('%5d-%5d  %7.2f-%7.2f  %3d f  %3d -> %3d' % (a, b, a / FPS, b / FPS, b - a, m[k - 1][2] * 100, m[k][2] * 100))
print('segments', len(m))
