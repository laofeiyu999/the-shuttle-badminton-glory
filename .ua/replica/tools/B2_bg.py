# -*- coding: utf-8 -*-
"""中值背景（每 100 帧取 1 帧，共约 118 帧）+ 相机稳定性检查（场地线位置随时间）"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
fr = []
idx = []
for f, a in stream(0, None, None, W, H, step=100):
    fr.append(a.copy()); idx.append(f)
fr = np.stack(fr)
print(fr.shape)
med = np.median(fr, axis=0).astype(np.uint8)
Image.fromarray(med).save(os.path.join(FR, "bg_median.png"))
np.save(os.path.join(DATA, "B2_bg_median.npy"), med)
# 稳定性：每帧与中值在几处线段小窗的差
g = fr.astype(np.float32).mean(axis=3)
mg = med.astype(np.float32).mean(axis=2)
# 取几处场地线的列剖面：x=400 处远边线附近 y 780-830; x=300 处近边线 y 1170-1220; y=1000 行 x 600-720（左前发球线）
def peak(prof):
    p = prof - prof.min(); 
    return (p * np.arange(len(p))).sum() / max(p.sum(), 1e-6)
for i in range(0, len(idx), 6):
    a = g[i]
    y1 = 780 + peak(a[780:830, 395:405].mean(axis=1))
    y2 = 1170 + peak(a[1170:1225, 295:305].mean(axis=1))
    x1 = 600 + peak(a[995:1005, 600:720].mean(axis=0))
    x2 = 1200 + peak(a[995:1005, 1200:1320].mean(axis=0))
    print(idx[i], "far_y %.2f near_y %.2f Lssl_x %.2f Rssl_x %.2f" % (y1, y2, x1, x2), "meandiff %.2f" % np.abs(a - mg)[700:1250].mean())
