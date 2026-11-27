# -*- coding: utf-8 -*-
"""A3: 弹字检测。由 A3_masks.npy 的品红(ch0)/深蓝(ch1)格计数，求 8x4 格(128x64 px)滑窗内像素数最大值及位置，
HUD 区(右下三键、左上比分条、底部能量条)屏蔽。输出 data/A3_popscan.npy (NF, 2, 3)=[窗内像素数(全分辨率换算), x, y]。"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
mm = np.load(os.path.join(tempfile.gettempdir(), 'A3_masks.npy'), mmap_mode='r')
out = np.zeros((NF, 2, 3), np.float32)
WX, WY = 8, 4
for s in range(0, NF, 1000):
    for ch in (0, 1):
        c = np.asarray(mm[s:s + 1000, ch], np.float32)
        c[:, 21:, 83:] = 0; c[:, :17, :53] = 0; c[:, 46:, :] = 0
        I = np.zeros((c.shape[0], 56, 121), np.float32); I[:, 1:, 1:] = c.cumsum(1).cumsum(2)
        w = I[:, WY:, WX:] - I[:, :-WY, WX:] - I[:, WY:, :-WX] + I[:, :-WY, :-WX]
        flat = w.reshape(len(w), -1); i = flat.argmax(1)
        out[s:s + len(w), ch, 0] = flat[np.arange(len(w)), i] * 4
        yy, xx = np.unravel_index(i, w.shape[1:])
        out[s:s + len(w), ch, 1] = (xx + WX / 2) * 16; out[s:s + len(w), ch, 2] = (yy + WY / 2) * 16
np.save(DATA + '/A3_popscan.npy', out)
for ch, nm in ((0, 'magenta'), (1, 'deepblue')):
    v = out[:, ch, 0]
    print(nm, 'pct', np.percentile(v, [50, 75, 90, 95, 98, 99, 99.5]).round(0))
    h, e = np.histogram(v, bins=[0, 100, 200, 400, 600, 800, 1000, 1500, 2000, 3000, 5000, 9000]); print('   hist', list(zip(e[:-1].astype(int), h)))
