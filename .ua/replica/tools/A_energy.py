# -*- coding: utf-8 -*-
"""能量条读数：全帧追踪条上的小球拍游标（手柄为粉红色细斜线），输出 data/A_energy.csv。
先跑 A_dump_bar.py 生成条带缓存。条带原点 (730,760)，尺寸 460x80。
游标手柄在条带 y=62..74，斜率约 -8px/13行；0% 时手柄 x≈31，100% 时 x≈409（条带坐标, y=70 处）。
"""
import numpy as np, os, tempfile, csv
NF = 14029; FPS = 60.0
X0, Y0 = 730, 760
mm = np.memmap(os.path.join(tempfile.gettempdir(), 'A_bar_strip.u8'), np.uint8, 'r', shape=(NF, 80, 460, 3))
rows = np.arange(62, 75)
shift = np.round(-(rows - 70) * 8 / 13.0).astype(int)   # 把斜线对齐到 y=70 处的 x
XL, XR = 31.5, 409.5   # 0% / 100% 的手柄 x（y=70），由 f60 与 f5010 标定，后面用数据再校
out = np.zeros((NF, 8), np.float32)
CH = 500
for s in range(0, NF, CH):
    a = mm[s:s + CH].astype(np.int16)
    sub = a[:, rows]                       # (n,13,460,3)
    R, G, B = sub[..., 0], sub[..., 1], sub[..., 2]
    p = R - G
    # 局部背景：左右各 10 px 处的较小值
    pl = np.roll(p, 10, axis=2); pr = np.roll(p, -10, axis=2)
    bg = np.maximum(pl, pr)
    m = ((p - bg) > 45) & (G < 165) & (R > 95) & (B > 110)
    # 去斜
    al = np.zeros(m.shape, bool)
    for i, sh in enumerate(shift):
        al[:, i] = np.roll(m[:, i], -sh, axis=1)
    cnt = al.sum(1).astype(np.int16)        # (n,460)
    # 手柄宽约 4px：3px 窗口求和
    c3 = cnt + np.roll(cnt, 1, 1) + np.roll(cnt, -1, 1)
    c3[:, :12] = 0; c3[:, 440:] = 0
    x = c3.argmax(1); v = c3.max(1)
    # 亚像素：加权质心
    xs = np.arange(460)
    for k in range(len(x)):
        lo, hi = max(0, x[k] - 4), min(460, x[k] + 5)
        w = cnt[k, lo:hi].astype(float)
        cx = (w * xs[lo:hi]).sum() / w.sum() if w.sum() > 0 else np.nan
        out[s + k, 0] = cx
        out[s + k, 1] = v[k]
    # 条身颜色采样（y=48..58，x 位于 25/50/70/92% 处）
    for j, fx in enumerate((0.25, 0.50, 0.92)):
        xc = int(44 + fx * 378)
        c = a[:, 49:57, xc - 3:xc + 4].reshape(len(a), -1, 3).mean(1)
        # 压成一个状态码用的三个量：R, G, B 平均
        out[s:s + len(a), 2 + j * 2] = c[:, 0]
        out[s:s + len(a), 3 + j * 2] = c[:, 2]
np.save(os.path.join(tempfile.gettempdir(), 'A_energy_raw.npy'), out)
x = out[:, 0]; v = out[:, 1]
print('valid(v>=18):', (v >= 18).sum(), 'of', NF)
h, e = np.histogram(x[v >= 18], bins=np.arange(20, 430, 10))
print(list(zip(e[:-1].astype(int), h)))
print('min/max x', np.nanmin(x[v >= 18]), np.nanmax(x[v >= 18]))
