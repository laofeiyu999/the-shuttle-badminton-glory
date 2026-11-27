# -*- coding: utf-8 -*-
"""A3: 摇杆底盘圆环检测。左下区域 (0..800, 330..880) 半分辨率，环形核 FFT 相关找圆心；先在几帧上扫半径。
用法: python A3_joy.py radius | python A3_joy.py scan(每 10 帧, 输出 data/A3_joy.csv)"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
from scipy.signal import fftconvolve
X0, Y0, CW, CH, S = 0, 300, 840, 580, 2
def kern(R):
    n = int(R + 8); yy, xx = np.mgrid[-n:n + 1, -n:n + 1]; r = np.hypot(xx, yy)
    k = np.zeros_like(r)
    ring = np.abs(r - R) < 1.6; side = (np.abs(r - R) > 3) & (np.abs(r - R) < 6.5)
    k[ring] = 1.0 / ring.sum(); k[side] = -1.0 / side.sum()
    return k
def white(a):
    a = a.astype(np.float32); return a.min(-1)
def find(a, R):
    w = white(a); c = fftconvolve(w, kern(R)[::-1, ::-1], mode='same')
    c[:int(R * 0.3)] = -9; i = np.unravel_index(c.argmax(), c.shape)
    return c[i], X0 + (i[1] + 0.5) * S, Y0 + (i[0] + 0.5) * S
if sys.argv[1] == 'radius':
    for f in (1200, 2400, 4400, 9000):
        a = get_frame(f, (X0, Y0, CW, CH), (CW // S, CH // S))
        res = [(find(a, R / S), R) for R in range(120, 161, 2)]
        b = max(res, key=lambda z: z[0][0])
        print(f, 'bestR', b[1], 'score %.1f center %.0f,%.0f' % b[0], '| scores', ' '.join('%d' % z[0][0] for z in res))
else:
    R = float(sys.argv[2]) / S; rows = []
    for f, a in iter_frames(0, None, 10, (X0, Y0, CW, CH), (CW // S, CH // S)):
        s, cx, cy = find(a, R); rows.append((f, s, cx, cy))
    with open(DATA + '/A3_joy.csv', 'w') as fo:
        fo.write('frame,score,cx,cy\n')
        for r in rows: fo.write('%d,%.1f,%.0f,%.0f\n' % r)
    print('rows', len(rows))
