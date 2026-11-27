# -*- coding: utf-8 -*-
"""B2_trail.py 拖尾寿命与宽度量测：python B2_trail.py 名称 起始帧 帧数 x y w h [阈值]
方法：裁剪窗内取 [起始帧-40, 起始帧+帧数+40] 每 4 帧采样的逐像素中值作背景；
逐帧算加亮量 d = max_c(帧 - 背景)，d > 阈值 记为拖尾像素。
对每个曾被点亮的像素统计 首次点亮帧 / 连续点亮帧数(=该处拖尾可见寿命)。
宽度：对每帧拖尾像素做主轴拟合(PCA)，取垂直主轴方向的 2×标准差×sqrt(3) 近似带宽，另给逐列竖直厚度中位数。
输出一行汇总并追加到 data/B2_trail_meas.csv。"""
import sys, os, csv
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *


def run(name, f0, n, x, y, w, h, thr=38):
    bgf = [a.astype(np.int16) for _, a in grab(max(0, f0 - 40), (n + 80) // 4, crop=(x, y, w, h), scale=None, step=4)]
    bg = np.median(np.stack(bgf), 0)
    fr = grab(f0, n, crop=(x, y, w, h), scale=None)
    on = np.zeros((n, h, w), bool); cols = []
    for i, (f, a) in enumerate(fr):
        d = (a.astype(np.int16) - bg).max(2)
        on[i] = d > thr
    first = np.where(on.any(0), on.argmax(0), -1)
    # 连续点亮帧数：从首次点亮起数到第一次熄灭
    life = np.zeros((h, w), int)
    alive = on.any(0)
    idx = np.arange(n)[:, None, None]
    after = (idx >= first[None]) & alive[None]
    off = after & ~on
    firstoff = np.where(off.any(0), off.argmax(0), n)
    life = np.where(alive, firstoff - first, 0)
    # 只统计首次点亮在窗口前 60% 且熄灭在窗口内的像素(寿命完整)
    full = alive & (first < int(n * 0.6)) & (firstoff < n) & (first > 0)
    lv = life[full]
    widths = []; thick = []; color = []; lens = []
    for i, (f, a) in enumerate(fr):
        ys, xs = np.where(on[i])
        if len(xs) < 60: continue
        pts = np.stack([xs, ys], 1).astype(float); c = pts.mean(0); u, s, vt = np.linalg.svd(pts - c, full_matrices=False)
        proj_perp = (pts - c) @ vt[1]; proj_par = (pts - c) @ vt[0]
        widths.append(np.percentile(proj_perp, 90) - np.percentile(proj_perp, 10)); lens.append(np.percentile(proj_par, 99) - np.percentile(proj_par, 1))
        cc = np.bincount(xs); thick.append(np.median(cc[cc > 0]))
        color.append(a[on[i]].mean(0))
    res = dict(name=name, f0=f0, n=n, pixels_full=int(full.sum()),
               life_p25='%.1f' % np.percentile(lv, 25) if len(lv) else '', life_med='%.1f' % np.median(lv) if len(lv) else '', life_p75='%.1f' % np.percentile(lv, 75) if len(lv) else '', life_p95='%.1f' % np.percentile(lv, 95) if len(lv) else '',
               width_p10_90_px='%.1f' % np.median(widths) if widths else '', col_thick_px='%.1f' % np.median(thick) if thick else '', max_len_px='%.0f' % np.max(lens) if lens else '',
               mean_rgb=str(np.mean(color, 0).round(0).tolist()) if color else '')
    print(res)
    p = os.path.join(DATA, 'B2_trail_meas.csv'); new = not os.path.exists(p)
    with open(p, 'a', newline='') as fo:
        wr = csv.DictWriter(fo, list(res.keys()))
        if new: wr.writeheader()
        wr.writerow(res)
    return res


if __name__ == '__main__':
    a = sys.argv
    run(a[1], int(a[2]), int(a[3]), *[int(v) for v in a[4:8]], thr=int(a[8]) if len(a) > 8 else 38)
