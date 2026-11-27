# -*- coding: utf-8 -*-
"""全片 0.5 s 间隔联系表：每张 5x5=25 格，每格 384x288"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
step = 25
cw, ch = 384, 288
frames = []
k = 0
for f, a in stream(0, None, "scale=%d:%d" % (cw, ch), cw, ch, step=step):
    frames.append((f, a.copy()))
    if len(frames) == 25:
        sheet(frames, 5, os.path.join(FR, "sheets", "ov_%02d.jpg" % k), fsz=18); k += 1; frames = []
if frames:
    sheet(frames, 5, os.path.join(FR, "sheets", "ov_%02d.jpg" % k), fsz=18)
print("sheets", k + 1)
