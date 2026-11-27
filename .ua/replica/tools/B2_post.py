# -*- coding: utf-8 -*-
"""B2_post.py 追踪后处理：像素 → 场地坐标(米)，速度，身高，闪光事件。
输入 data/B2_track_raw.npy/.csv, data/B2_calib.npz
输出 data/B2_player_track.csv, data/B2_flash_events.csv, data/B2_speed_hist.csv, data/B2_post.npz
坐标：X 沿球场长轴(网=0, 左半场负)，Z 沿宽(远边线 +3.05, 近边线 -3.05)，Y 向上。"""
import numpy as np, csv, os, sys
from scipy.signal import medfilt, savgol_filter
from scipy.ndimage import uniform_filter1d
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
A = np.load(os.path.join(DATA, 'B2_track_raw.npy'))
keys = open(os.path.join(DATA, 'B2_track_raw.csv')).readline().strip().split(',')
C = {k: A[:, i] for i, k in enumerate(keys)}
cal = np.load(os.path.join(DATA, 'B2_calib.npz')); Hm = cal['H']; Hi = np.linalg.inv(Hm); P = cal['P']
N = len(A); fr = C['frame'].astype(int); t = fr / FPS
VV = 4847.0   # 竖直消失点 v (像素)，由 P 第二列算出


def gnd(u, v):
    p = Hi @ np.stack([u, v, np.ones_like(u)]); return p[0] / p[2], p[1] / p[2]


def height_at(X, Z, v):
    """地面点 (X,0,Z) 正上方、投影到图像行 v 的高度 Y(米)。"""
    a = P[1, 0] * X + P[1, 2] * Z + P[1, 3]; b = P[1, 1]
    c = P[2, 0] * X + P[2, 2] * Z + P[2, 3]; d = P[2, 1]
    return (v * c - a) / (b - v * d)


def nanmed(x, k):
    y = x.copy(); idx = np.where(~np.isnan(x))[0]
    if len(idx) < k: return y
    y[idx] = medfilt(x[idx], k); return y


def interp_nan(x, maxgap=25):
    y = x.copy(); idx = np.where(~np.isnan(x))[0]
    if len(idx) == 0: return y
    yi = np.interp(np.arange(len(x)), idx, x[idx])
    # 只补短缺口
    isn = np.isnan(x); out = y.copy(); i = 0
    while i < len(x):
        if isn[i]:
            j = i
            while j < len(x) and isn[j]: j += 1
            if j - i <= maxgap and i > 0 and j < len(x): out[i:j] = yi[i:j]
            i = j
        else: i += 1
    return out


valid_cam = C['line_frac'] > 0.9          # 观战机位帧（镜头切换/转场时为假）
res = {}
for s in 'LR':
    sn = C[s + '_sn']; vf = np.where(sn > 50, C[s + '_sbot'], C[s + '_bot'])
    tx, ty = C[s + '_tx'], C[s + '_ty']
    uf = 960 + (tx - 960) * (vf - VV) / (ty - VV)       # 躯干中心沿竖直消失线落到脚底行
    x1, z1 = gnd(uf, vf); z1 = z1 + 0.28                 # 鞋底最低点比身体中心偏近相机约 0.28 m（由右方青圈标定）
    air = np.zeros(N, bool); x, z = x1.copy(), z1.copy()
    if s == 'R':
        rx, rz = gnd(C['R_rcx'], C['R_rcy'])
        xa, _ = gnd(C['R_rx0'], C['R_rcy']); xb, _ = gnd(C['R_rx1'], C['R_rcy'])
        okr = (C['R_rn'] > 300) & ((xb - xa) < 1.35)
        x1 = x1 + 0.12
        x = np.where(okr, rx, x1); z = np.where(okr, rz, z1)
        air = okr & ((C['R_rcy'] - C['R_sbot']) > 22)   # 圈在地面，鞋底抬离 → 腾空
        res['R_ringok'] = okr
    else:
        shn = C['L_shn']; oks = shn > 150
        air = oks & ((C['L_shy'] - C['L_sbot']) > 18)
    x[~valid_cam] = np.nan; z[~valid_cam] = np.nan
    # 离群剔除：团块面积突变(并入闪光/跳到场外路人)、越界、相对 15 帧中值偏离 > 0.6 m
    nb = C[s + '_n']; nmed = nanmed(interp_nan(nb, 2000), 51)
    bad = (nb > 2.2 * nmed) | (nb < 0.4 * nmed) | (abs(x) > 7.6) | (abs(z) > 3.9) | np.isnan(nb)
    if s == 'L': bad |= x > -0.2
    else: bad |= x < 0.2
    x[bad] = np.nan; z[bad] = np.nan
    for _ in range(2):
        xm = nanmed(interp_nan(x, 2000), 15); zm = nanmed(interp_nan(z, 2000), 15)
        dev = np.hypot(x - xm, z - zm) > 0.6
        x[dev] = np.nan; z[dev] = np.nan
    res[s + '_bad'] = np.isnan(x)
    res[s + '_air0'] = air
    if s == 'L':   # 左方腾空帧：z 不可信（脚离地），置空后插值
        aa = air.copy()
        for k in range(1, 4): aa[k:] |= air[:-k]; aa[:-k] |= air[k:]
        z[aa] = np.nan; z = interp_nan(z, 40)
    x = nanmed(x, 5); z = nanmed(z, 5)
    xi = interp_nan(x, 15); zi = interp_nan(z, 15)
    xs = xi.copy(); zs = zi.copy(); good = ~np.isnan(xi) & ~np.isnan(zi)
    # 分段平滑(Savitzky-Golay 窗 11 帧=0.22 s, 2 阶)
    i = 0
    while i < N:
        if good[i]:
            j = i
            while j < N and good[j]: j += 1
            if j - i >= 13:
                xs[i:j] = savgol_filter(xi[i:j], 11, 2); zs[i:j] = savgol_filter(zi[i:j], 11, 2)
            i = j
        else: i += 1
    vx = np.gradient(xs) * FPS; vz = np.gradient(zs) * FPS
    res[s + '_x'], res[s + '_z'], res[s + '_vx'], res[s + '_vz'] = xs, zs, vx, vz
    res[s + '_sp'] = np.hypot(vx, vz)
    # 身高：地面点正上方到团块顶行
    res[s + '_h'] = height_at(xs, zs, C[s + '_top'])
    # 鞋底离地高度(腾空)：鞋底行在身体所在地面点上方的高度
    res[s + '_footh'] = height_at(xs, zs, np.where(sn > 50, C[s + '_sbot'], np.nan))
    res[s + '_bw'] = C[s + '_x1'] - C[s + '_x0']

with open(os.path.join(DATA, 'B2_player_track.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['frame', 't', 'cam_ok', 'L_x', 'L_z', 'R_x', 'R_z', 'L_vx', 'L_vz', 'R_vx', 'R_vz', 'L_speed', 'R_speed',
                'L_top_h', 'R_top_h', 'L_foot_h', 'R_foot_h'])
    for i in range(N):
        def g(a): return '' if np.isnan(a[i]) else '%.3f' % a[i]
        w.writerow([fr[i], '%.2f' % t[i], int(valid_cam[i])] + [g(res[k]) for k in
                   ['L_x', 'L_z', 'R_x', 'R_z', 'L_vx', 'L_vz', 'R_vx', 'R_vz', 'L_sp', 'R_sp', 'L_h', 'R_h', 'L_footh', 'R_footh']])

# 闪光事件：强加亮像素数相对滚动中值的突增
fl = C['fl_n']; base = medfilt(fl, 51); ex = fl - base
ev = []; i = 1
while i < N - 1:
    if ex[i] > 2500 and valid_cam[i] and ex[i] >= ex[i - 1]:
        j = i
        while j < N - 1 and ex[j + 1] > 1200: j += 1
        k = i + int(np.argmax(ex[i:j + 1]))
        # 起始帧：突增第一帧
        s0 = i
        while s0 > 0 and ex[s0 - 1] > 1200: s0 -= 1
        ev.append((s0, k, j, ex[k], C['fl_x'][s0], C['fl_y'][s0], C['fl_x0'][k], C['fl_x1'][k], C['fl_y0'][k], C['fl_y1'][k]))
        i = j + 4
    else: i += 1
with open(os.path.join(DATA, 'B2_flash_events.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['f_start', 't_start', 'f_peak', 'f_end', 'dur_frames', 'peak_excess_px', 'cx', 'cy', 'x0', 'x1', 'y0', 'y1'])
    for e in ev: w.writerow([e[0], '%.2f' % (e[0] / FPS), e[1], e[2], e[2] - e[0] + 1, int(e[3])] + ['%.0f' % v for v in e[4:]])
print('flash events', len(ev))
np.savez(os.path.join(DATA, 'B2_post.npz'), fr=fr, valid=valid_cam, **res)

# 速度直方图
edges = np.arange(0, 8.01, 0.25)
with open(os.path.join(DATA, 'B2_speed_hist.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['speed_lo', 'speed_hi', 'L_frames', 'R_frames', 'L_absvx_frames', 'L_absvz_frames', 'R_absvx_frames', 'R_absvz_frames'])
    hs = [np.histogram(a[~np.isnan(a)], edges)[0] for a in [res['L_sp'], res['R_sp'], abs(res['L_vx']), abs(res['L_vz']), abs(res['R_vx']), abs(res['R_vz'])]]
    for i in range(len(edges) - 1): w.writerow(['%.2f' % edges[i], '%.2f' % edges[i + 1]] + [h[i] for h in hs])
for s in 'LR':
    sp = res[s + '_sp']; m = ~np.isnan(sp)
    print(s, 'valid', m.sum(), 'x range', np.nanpercentile(res[s + '_x'], [0.5, 50, 99.5]).round(2), 'z', np.nanpercentile(res[s + '_z'], [0.5, 50, 99.5]).round(2))
    print('  speed pct 50/75/90/95/99/99.5/max', np.nanpercentile(sp, [50, 75, 90, 95, 99, 99.5, 100]).round(2))
    print('  |vx| 90/95/99/99.5', np.nanpercentile(abs(res[s + '_vx']), [90, 95, 99, 99.5]).round(2), '|vz|', np.nanpercentile(abs(res[s + '_vz']), [90, 95, 99, 99.5]).round(2))
    still = m & (sp < 0.3) & ~res[s + '_air0']
    h = res[s + '_h'][still]; h = h[~np.isnan(h)]
    hh, ee = np.histogram(h, np.arange(0.8, 3.0, 0.02)); k = np.argmax(hh)
    print('  standing top-height mode %.2f m; pct 10/25/50/75/90' % ee[k], np.percentile(h, [10, 25, 50, 75, 90]).round(2), 'n', len(h))
    print('  air0 frames', res[s + '_air0'].sum(), ' body width px still median', np.nanmedian(res[s + '_bw'][still]))
