# -*- coding: utf-8 -*-
"""把能量条条带 (x730..1190, y760..840) 全帧存成 npy memmap（临时目录，供 A_energy.py 分析）。"""
import numpy as np, os, tempfile
from A_common import *
X0, Y0, CW, CH = 730, 760, 460, 80
out = os.path.join(tempfile.gettempdir(), 'A_bar_strip.u8')
mm = np.memmap(out, np.uint8, 'w+', shape=(NF, CH, CW, 3))
n = 0
for f, a in iter_frames(0, None, 1, (X0, Y0, CW, CH)):
    if f >= NF: break
    mm[f] = a; n += 1
mm.flush()
print('frames', n, out)
