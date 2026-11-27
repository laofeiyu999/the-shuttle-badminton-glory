# -*- coding: utf-8 -*-
"""A3: 全片逐帧扫描三个击球键区域。输出 data/A3_btnscan.npy  形状 (NF, 3键, 9)：
盘内(r<78) 平均 R,G,B、盘内 min(R,G,B) 均值、盘内亮度 std、盘心(r<30) 亮度、外环背景(r 96..110) 平均 R,G,B 亮度、盘内亮度>235 的像素占比、盘内 粉红(R>200,G<150,B>150) 占比。
键心（1922x880）：高吊(1730,440) 近球(1456,719) 远球(1709,687)，外沿半径 85 px。"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
X0, Y0, CW, CH, S = 1356, 340, 480, 480, 2
C = [(1730, 440), (1456, 719), (1709, 687)]
yy, xx = np.mgrid[0:CH // S, 0:CW // S]
masks = []
for cx, cy in C:
    r = np.hypot(xx * S + S / 2 - 0.5 - (cx - X0), yy * S + S / 2 - 0.5 - (cy - Y0))
    masks.append((r < 78, r < 30, (r > 96) & (r < 110)))
out = np.zeros((NF, 3, 9), np.float32)
t0 = time.time()
for f, a in iter_frames(0, None, 1, (X0, Y0, CW, CH), (CW // S, CH // S)):
    if f >= NF: break
    a = a.astype(np.float32); lum = a.mean(-1); mn = a.min(-1)
    pink = (a[..., 0] > 200) & (a[..., 1] < 150) & (a[..., 2] > 150)
    for k, (m, mc, mo) in enumerate(masks):
        d = a[m]
        out[f, k, 0:3] = d.mean(0); out[f, k, 3] = mn[m].mean(); out[f, k, 4] = lum[m].std()
        out[f, k, 5] = lum[mc].mean(); out[f, k, 6] = lum[mo].mean()
        out[f, k, 7] = (lum[m] > 235).mean(); out[f, k, 8] = pink[m].mean()
np.save(DATA + '/A3_btnscan.npy', out)
print('done frames', f + 1, 'sec %.1f' % (time.time() - t0))
