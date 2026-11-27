# -*- coding: utf-8 -*-
"""B2_jump.py 起跳检测。右方：鞋底行相对脚下青圈中心(圈留在地面)的高度；左方：鞋底行相对影子质心的高度。
输出 data/B2_jumps.csv（side,f_start,f_peak,f_end,air_frames,air_s,peak_h_m,x,z,dx,dz,nearest_hit_frame,hit_offset_frames）"""
import sys, os, csv
import numpy as np
from scipy.signal import medfilt
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
A = np.load(os.path.join(DATA, 'B2_track_raw.npy')); keys = open(os.path.join(DATA, 'B2_track_raw.csv')).readline().strip().split(',')
C = {k: A[:, i] for i, k in enumerate(keys)}
cal = np.load(os.path.join(DATA, 'B2_calib.npz')); Hc = cal['H']; P = cal['P']; Hi = np.linalg.inv(Hc)
d = np.load(os.path.join(DATA, 'B2_post.npz')); N = len(A)


def gnd(u, v):
    p = Hi @ np.stack([u, v, np.ones_like(u)]); return p[0] / p[2], p[1] / p[2]


def height_at(X, Z, v):
    a = P[1, 0] * X + P[1, 2] * Z + P[1, 3]; b = P[1, 1]
    c = P[2, 0] * X + P[2, 2] * Z + P[2, 3]; dd = P[2, 1]
    return (v * c - a) / (b - v * dd)


hits = [(int(r['frame']), r['side']) for r in csv.DictReader(open(os.path.join(DATA, 'B2_hits_auto.csv')))]
rows = []
for s in 'LR':
    sbot = np.where(C[s + '_sn'] > 50, C[s + '_sbot'], np.nan)
    if s == 'R':
        ok = (C['R_rn'] > 300)
        # 圈的内环中心：用圈包围盒上缘 + 固定半深不可靠(圈会变大)，用质心
        gx, gz = gnd(C['R_rcx'], C['R_rcy'])
    else:
        ok = (C['L_shn'] > 150)
        gx, gz = gnd(C['L_shx'], C['L_shy'])
    h = height_at(gx, gz, sbot); h[~ok] = np.nan
    # 基线：601 帧滑动中位数
    idx = np.where(~np.isnan(h))[0]; base = np.full(N, np.nan)
    hm = h[idx]; k = 301
    bm = np.array([np.median(hm[max(0, i - k):i + k]) for i in range(len(hm))]); base[idx] = bm
    rel = h - base
    print(s, '基线中位 %.3f  rel 分位 5/50/95/99/99.9: %s  有效帧 %d' % (np.nanmedian(base), np.nanpercentile(rel, [5, 50, 95, 99, 99.9]).round(3), len(idx)))
    np.save(os.path.join(DATA, 'B2_jumprel_%s.npy' % s), rel)
    up = np.nan_to_num(rel, nan=0) > 0.12
    i = 0
    while i < N:
        if up[i]:
            j = i
            while j < N and (up[j] or (j + 1 < N and up[j + 1]) or (j + 2 < N and up[j + 2])): j += 1
            seg = rel[i:j]; pk = np.nanmax(seg)
            if j - i >= 6 and pk > 0.22 and C['line_frac'][i] > 0.9:
                ip = i + int(np.nanargmax(seg))
                near = min([hf for hf, hs in hits if hs == s] or [0], key=lambda q: abs(q - ip))
                x0, z0 = d[s + '_x'][max(0, i - 2)], d[s + '_z'][max(0, i - 2)]; x1, z1 = d[s + '_x'][min(N - 1, j + 2)], d[s + '_z'][min(N - 1, j + 2)]
                rows.append([s, i, ip, j, j - i, '%.2f' % ((j - i) / FPS), '%.2f' % pk, '%.2f' % x0, '%.2f' % z0, '%.2f' % (x1 - x0), '%.2f' % (z1 - z0), near, near - i, '%.2f' % d[s + '_sp'][max(0, i - 3)]])
            i = j
        else: i += 1
with open(os.path.join(DATA, 'B2_jumps.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['side', 'f_start', 'f_peak', 'f_end', 'air_frames', 'air_s', 'peak_h_m', 'x', 'z', 'dx', 'dz', 'nearest_hit_frame', 'hit_minus_start_frames', 'speed_before']); w.writerows(rows)
for r in rows: print(r)
