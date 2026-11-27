# -*- coding: utf-8 -*-
"""A3: 全片逐帧颜色掩膜扫描（半分辨率 960x440，再按 8x8 块计数 → 120x55 格，每格 0..64）。
输出 %TEMP%/A3_masks.u8  memmap 形状 (NF, 6, 55, 120) uint8，通道：
0 品红笔刷(“完美”底色)  R>130,G<115,B>150,R-G>90
1 深蓝笔刷(“糟糕”底色)  R<35,70<=G<=125,B>185
2 近白(击球闪光/白闪)    min(R,G,B)>235
3 粉白辉光(完美击球光晕)  R>235,B>235,110<G<215
4 红(“对方得分”横幅)     R>200,G<80,B<95
5 橙(“准备/开始/第二局”横幅) R>230,115<G<195,B<70
另存 data/A3_framediff.npy：相邻帧平均绝对差(半分辨率灰度)。"""
import sys, os, time, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
SW, SH = 960, 440
mm = np.lib.format.open_memmap(os.path.join(tempfile.gettempdir(), 'A3_masks.npy'), 'w+', np.uint8, (NF, 6, 55, 120))
fd = np.zeros(NF, np.float32); prev = None; t0 = time.time()
for f, a in iter_frames(0, None, 1, (0, 0, 1920, 880), (SW, SH)):
    if f >= NF: break
    R = a[..., 0].astype(np.int16); G = a[..., 1].astype(np.int16); B = a[..., 2].astype(np.int16)
    ms = [(R > 130) & (G < 115) & (B > 150) & (R - G > 90),
          (R < 35) & (G >= 70) & (G <= 125) & (B > 185),
          (np.minimum(np.minimum(R, G), B) > 235),
          (R > 235) & (B > 235) & (G > 110) & (G < 215),
          (R > 200) & (G < 80) & (B < 95),
          (R > 230) & (G > 115) & (G < 195) & (B < 70)]
    for i, m in enumerate(ms):
        mm[f, i] = m.reshape(55, 8, 120, 8).sum((1, 3))
    g = (R + G + B)
    if prev is not None: fd[f] = np.abs(g - prev).mean() / 3
    prev = g
mm.flush(); np.save(DATA + '/A3_framediff.npy', fd)
print('done', f + 1, 'sec %.0f' % (time.time() - t0))
