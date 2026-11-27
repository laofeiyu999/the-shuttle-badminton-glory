# -*- coding: utf-8 -*-
"""分段中值背景：每 1000 帧一段，每 20 帧取样，ROI y∈[540,1300)。输出 data/B2_bgseg.npy (nseg,760,1920,3) uint8"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
Y0, Y1 = 540, 1300
SEG = 1000
buf = {}
for f, a in stream(0, None, "crop=%d:%d:0:%d" % (W, Y1 - Y0, Y0), W, Y1 - Y0, step=20):
    buf.setdefault(f // SEG, []).append(a.copy())
ks = sorted(buf)
out = np.stack([np.median(np.stack(buf[k]), axis=0).astype(np.uint8) for k in ks])
np.save(os.path.join(DATA, "B2_bgseg.npy"), out)
print(out.shape, [len(buf[k]) for k in ks])
