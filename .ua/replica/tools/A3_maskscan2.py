# -*- coding: utf-8 -*-
"""A3: 第二遍全片掩膜（针对蓝色“糟糕”弹字）。半分辨率 960x440 → 8x8 块计数 (55x120)。
ch0 糟糕底刷(收紧) R<32, 60<=G<=130, B>205；ch1 糟糕字身青色 60<=R<=195, G>205, B>200, G-R>50。
输出 %TEMP%/A3_masks2.npy (NF,2,55,120) uint8。"""
import sys, os, time, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
mm = np.lib.format.open_memmap(os.path.join(tempfile.gettempdir(), 'A3_masks2.npy'), 'w+', np.uint8, (NF, 2, 55, 120))
t0 = time.time()
for f, a in iter_frames(0, None, 1, (0, 0, 1920, 880), (960, 440)):
    if f >= NF: break
    R = a[..., 0].astype(np.int16); G = a[..., 1].astype(np.int16); B = a[..., 2].astype(np.int16)
    mm[f, 0] = ((R < 32) & (G >= 60) & (G <= 130) & (B > 205)).reshape(55, 8, 120, 8).sum((1, 3))
    mm[f, 1] = ((R >= 60) & (R <= 195) & (G > 205) & (B > 200) & (G - R > 50)).reshape(55, 8, 120, 8).sum((1, 3))
mm.flush(); print('done', f + 1, 'sec %.0f' % (time.time() - t0))
