# -*- coding: utf-8 -*-
"""A3: 由 A3_masks.npy 检出横幅(红=对方得分 / 蓝=我方得分? / 橙=准备·开始·第二局)与 HUD(三键)可见区间。"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
mm = np.load(os.path.join(tempfile.gettempdir(), 'A3_masks.npy'), mmap_mode='r')
d = np.load(DATA + '/A3_btnscan.npy'); lum = d[:, :, :3].mean(2); vis = ((lum - d[:, :, 6]) > 40).sum(1) >= 2
def runs(m, gap=3, minlen=4):
    idx = np.flatnonzero(m); out = []
    if len(idx) == 0: return out
    s = p = idx[0]
    for i in idx[1:]:
        if i - p > gap:
            if p - s + 1 >= minlen: out.append((int(s), int(p)))
            s = i
        p = i
    if p - s + 1 >= minlen: out.append((int(s), int(p)))
    return out
def bbox(ch, f):
    c = np.asarray(mm[f, ch], np.int32); c[:6] = 0 if ch == 4 else c[:6]
    ys, xs = np.nonzero(c > 20)
    if len(xs) < 4: return None
    return (xs.min() * 16, (xs.max() + 1) * 16, ys.min() * 16, (ys.max() + 1) * 16, int(c.sum() * 4))
# 红横幅：排除左上红条 (y<270,x<850 → 格 y<17,x<53)
red = np.asarray(mm[:, 4], np.int32).copy(); red[:, :17, :53] = 0
rs = red.reshape(NF, -1).sum(1) * 4
org = np.asarray(mm[:, 5], np.int32).copy(); org[:, 44:, :] = 0   # 排除能量条
os_ = org.reshape(NF, -1).sum(1) * 4
print('red px pct', np.percentile(rs, [50, 90, 95, 99]), ' orange px pct', np.percentile(os_, [50, 90, 95, 99]))
print('RED runs (>6000 px):')
for s, e in runs(rs > 6000):
    f = (s + e) // 2; c = red[f]; ys, xs = np.nonzero(c > 20)
    print('  f%d-%d (%.2f-%.2f s, %d fr) peak %d px bbox x%d-%d y%d-%d' % (s, e, s / 60, e / 60, e - s + 1, rs[s:e + 1].max(), xs.min() * 16, xs.max() * 16 + 16, ys.min() * 16, ys.max() * 16 + 16))
print('ORANGE runs (>4000 px):')
for s, e in runs(os_ > 4000):
    f = s + int(np.argmax(os_[s:e + 1])); c = org[f]; ys, xs = np.nonzero(c > 20)
    print('  f%d-%d (%.2f-%.2f s, %d fr) peak %d px @f%d bbox x%d-%d y%d-%d' % (s, e, s / 60, e / 60, e - s + 1, os_[f], f, xs.min() * 16, xs.max() * 16 + 16, ys.min() * 16, ys.max() * 16 + 16))
print('HUD visible runs:')
print(' '.join('%d-%d' % r for r in runs(vis, gap=5, minlen=10)))
np.save(DATA + '/A3_hudvis.npy', vis)
