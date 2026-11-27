# -*- coding: utf-8 -*-
"""B2_hittable.py 逐次击球表：把闪光事件(已归属击球方)与追踪数据合并，给出每次击球的
触球高度(闪光中心相对脚点)、击球前停步时刻、击球后恢复移动时刻、是否腾空、到对方下一拍的间隔，并按高度粗分类。
输出 data/B2_hit_table.csv 和按类别的统计 data/B2_hit_class_stats.txt"""
import sys, os, csv
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
d = np.load(os.path.join(DATA, 'B2_post.npz')); N = len(d['fr'])
rel = {s: np.load(os.path.join(DATA, 'B2_jumprel_%s.npy' % s)) for s in 'LR'}
BAN = {9, 53, 1702, 1750, 2535, 2582, 3449, 3497, 4482, 4529, 5714, 5762, 7156, 7186, 7211, 7246, 8286, 8324, 9010, 9058, 10732, 10780, 6990,
       1355, 1415, 3026, 7883, 7968, 9469, 10313, 11464}   # 后 8 个是落点圈亮起，不是击球
rows = [r for r in csv.DictReader(open(os.path.join(DATA, 'B2_hits_auto.csv'))) if int(r['frame']) not in BAN]
out = []
for i, r in enumerate(rows):
    f = int(r['frame']); s = r['side']; sp = d[s + '_sp']; x = d[s + '_x']; z = d[s + '_z']
    fh = float(r['flash_h'])
    # 击球前：向前找最近一次速度 > 1.5 的帧（停步提前量）
    pre = ''
    for o in range(0, 60):
        if f - o >= 0 and not np.isnan(sp[f - o]) and sp[f - o] > 1.5: pre = o; break
    # 击球后：先找速度最低点(0..20 帧内)，再找其后首次 > 1.5 的帧
    post = ''; lo = ''
    w = sp[f:f + 21]
    if np.isfinite(w).any():
        k = int(np.nanargmin(w)); lo = float(w[k])
        for o in range(k, 110):
            if f + o < N and not np.isnan(sp[f + o]) and sp[f + o] > 1.5: post = o; break
    jr = rel[s][max(0, f - 12):f + 13]; jmax = float(np.nanmax(jr)) if np.isfinite(jr).any() else np.nan
    nxt = ''
    for j in range(i + 1, len(rows)):
        if rows[j]['side'] != s: nxt = int(rows[j]['frame']) - f; break
    cls = 'overhead' if fh >= 1.7 else ('mid' if fh >= 0.75 else 'low')
    if abs(x[f]) < 2.2 and not np.isnan(x[f]): cls += '_front'
    elif abs(x[f]) > 4.2: cls += '_back'
    else: cls += '_midcourt'
    out.append([f, '%.2f' % (f / FPS), s, '%.2f' % x[f], '%.2f' % z[f], '%.2f' % fh, r['dur'], r['peak'], '%.2f' % sp[f], pre, '%.2f' % lo if lo != '' else '', post, '%.2f' % jmax, nxt, cls])
with open(os.path.join(DATA, 'B2_hit_table.csv'), 'w', newline='') as fo:
    w = csv.writer(fo); w.writerow(['frame', 't', 'side', 'x', 'z', 'flash_h_m', 'flash_dur_frames', 'flash_peak_px', 'speed_at_hit', 'frames_since_moving_before', 'min_speed_after', 'frames_to_move_after', 'foot_rel_h_max', 'frames_to_opponent_hit', 'class'])
    w.writerows(out)
txt = []
import collections
g = collections.defaultdict(list)
for o in out: g[o[-1].split('_')[0]].append(o); g[o[-1]].append(o)
for k in sorted(g):
    v = g[k]; post = [o[11] for o in v if o[11] != '']; sp0 = [float(o[8]) for o in v if o[8] != 'nan']; lo = [float(o[10]) for o in v if o[10] != '']
    nx = [o[13] for o in v if o[13] != '' and o[13] < 200]
    line = '%-18s n=%3d  击球帧速度中位 %.2f  击球后最低速中位 %.2f  恢复移动(>1.5 m/s)中位 %s 帧 (25-75%%: %s)  到对方击球中位 %s 帧' % (
        k, len(v), np.median(sp0) if sp0 else np.nan, np.median(lo) if lo else np.nan, np.median(post) if post else '', np.percentile(post, [25, 75]).tolist() if post else '', np.median(nx) if nx else '')
    print(line); txt.append(line)
open(os.path.join(DATA, 'B2_hit_class_stats.txt'), 'w', encoding='utf-8').write('\n'.join(txt))
