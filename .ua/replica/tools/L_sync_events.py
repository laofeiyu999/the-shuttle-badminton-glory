# -*- coding: utf-8 -*-
"""用击球闪光核对主视角与侧视角的时间对齐（音频互相关给的是 t_side = t_main − 0.22 / + 0.05，这里用画面事件复核）。
主视角：每次本方按键后 0.1–0.6 s 内近白像素（A3_masks 通道 2，屏蔽 HUD）的突增帧 = 本方击球闪光。
侧视角：B_shots.csv 左方击球时刻、B2_flash_events.csv 闪光起始时刻。
在 .ua/replica 下运行：python tools/L_sync_events.py → data/L_sync_events.md（需要 %TEMP%/A3_masks.npy，没有就先跑 tools/A3_maskscan.py）
"""
import io, csv, os, tempfile
import numpy as np
mm = np.load(os.path.join(tempfile.gettempdir(), 'A3_masks.npy'), mmap_mode='r')
P = [(int(r['frame']), float(r['t_s']), r['key']) for r in csv.DictReader(io.open('data/A3_press.csv', encoding='utf-8-sig'))]
def series(f0, f1, ch=2):
    c = np.asarray(mm[f0:f1, ch], np.float32).copy()
    c[:, 21:, 83:] = 0; c[:, :17, :53] = 0; c[:, 46:, :] = 0; c[:, :8, 90:] = 0
    return c.sum((1, 2))
flash = []   # (按键帧, 闪光帧)
for f, t, k in P:
    a = series(f - 10, f + 40)
    base = np.median(a[:10]); d = a[10 + 6:10 + 37] - base
    i = np.argmax(d)
    if d[i] > 600:
        # 起始帧：往回找第一帧超过峰值 30% 的
        j = i
        while j > 0 and d[j - 1] > 0.3 * d[i]: j -= 1
        flash.append((f, f + 6 + j, k, float(d[i])))
fm = np.array([x[1] for x in flash]) / 60.0; pm = np.array([x[0] for x in flash]) / 60.0
S = [r for r in csv.DictReader(io.open('data/B_shots.csv', encoding='utf-8-sig')) if r['side'] == 'L']
hs = np.array([float(r['t_s']) for r in S])
FE = list(csv.DictReader(io.open('data/B2_flash_events.csv', encoding='utf-8-sig')))
fs = np.array([float(r['t_start']) for r in FE])
def match(a, b, lo=-1.0, hi=1.0, tol=0.08):
    res = []
    for nm, m in (('142.5 s 前', a < 142.5), ('142.5 s 后', a >= 142.5)):
        best = None
        for o in np.arange(lo, hi, 0.01):
            n = (np.abs((a[m] + o)[:, None] - b[None, :]).min(1) < tol).sum()
            if best is None or n > best[1]: best = (o, n)
        o = best[0]; dd = b[None, :] - a[m][:, None]; j = np.abs(dd - o).argmin(1); v = dd[np.arange(m.sum()), j]; v = v[np.abs(v - o) < 0.15]
        res.append((nm, int(m.sum()), len(v), float(np.median(v)), float(np.percentile(v, 10)), float(np.percentile(v, 90))))
    return res
L = ['# 用击球闪光核对两段视频的时间对齐', '', '由 `.ua/replica/tools/L_sync_events.py` 生成。', '',
     '主视角 89 次本方按键里，按键后 0.1–0.6 s 内检出近白闪光突增的有 %d 次；按键到闪光起始的间隔中位 %.3f s（10%%–90%% 分位 %.3f–%.3f s）。' % (len(flash), np.median(fm - pm), np.percentile(fm - pm, 10), np.percentile(fm - pm, 90)), '',
     '下表的差值 = 侧视角时刻 − 主视角时刻（同一事件），也就是 t_side = t_main + 差值。', '',
     '| 主视角事件 | 侧视角事件 | 时段 | 主视角事件数 | 配上 | 差值中位 s | 10% 分位 | 90% 分位 |', '| --- | --- | --- | --- | --- | --- | --- | --- |']
for an, a in (('击球闪光起始', fm), ('按键', np.array([x[1] for x in P]))):
    for bn, b in (('左方击球时刻（B_shots）', hs), ('闪光起始（B2_flash_events，双方都有）', fs)):
        for r in match(a, b):
            L.append('| %s | %s | %s | %d | %d | %+.3f | %+.3f | %+.3f |' % (an, bn, r[0], r[1], r[2], r[3], r[4], r[5]))
io.open('data/L_sync_events.md', 'w', encoding='utf-8').write(chr(10).join(L))
np.save('data/L_main_flash.npy', np.array([(x[0], x[1]) for x in flash]))
print('ok', len(flash))
