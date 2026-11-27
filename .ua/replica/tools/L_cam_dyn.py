# -*- coding: utf-8 -*-
"""主视角相机的跟随动态：相机距网 cz、横向 cx、视场角 fov 对 本方人物、对手、球 的响应。
方法：目标量过一阶低通（时间常数 tau）后对相机量做线性回归，扫 tau 找拟合最好的值。
一阶低通是线性的，所以 LP(c0 + c1*a + c2*b) = c0 + c1*LP(a) + c2*LP(b)，每个 tau 只要解一次最小二乘。
在 .ua/replica 目录下运行：python tools/L_cam_dyn.py  → data/L_cam_dyn.md
坐标：主视角世界系 z 指向本方（本方底线 z=+6.70），侧视角 x 沿球场长轴、本方（左方）为负，所以 z_main = -x_side。
时间：t_side = t_main + 0.015（150 s 前）或 + 0.30（之后），来自击球闪光对齐（tools/L_sync_events.py）。
音频互相关给的是 -0.22 / +0.05，两者差 0.24 s：录屏的声音和画面不同步，看画面的分析要用闪光对齐。
"""
import io, csv
import numpy as np

DT = 0.02
def num(x):
    try: return float(x)
    except Exception: return np.nan

P = list(csv.DictReader(io.open('data/B2_player_track.csv', encoding='utf-8-sig')))
own_d = np.array([-num(r['L_x']) for r in P]); opp_d = np.array([num(r['R_x']) for r in P])
own_lat = np.array([num(r['L_z']) for r in P])
B = list(csv.DictReader(io.open('data/B_ball_track.csv', encoding='utf-8-sig')))
ball_z = np.array([-num(r['X_m']) for r in B]); ball_h = np.array([num(r['Z_m']) for r in B])
N = min(len(P), len(B)); own_d, opp_d, own_lat, ball_z, ball_h = own_d[:N], opp_d[:N], own_lat[:N], ball_z[:N], ball_h[:N]
C = np.genfromtxt('data/A2_cam_track.csv', delimiter=',', names=True)
H = list(csv.DictReader(io.open('data/A_hits.csv', encoding='utf-8-sig')))
ral = {}
for r in H: ral.setdefault(r['rally'], []).append(float(r['t_s']))
RALLY = [(min(v) + 0.3, max(v) + 0.8) for v in ral.values()]


def fill(x, maxgap):
    """线性补 NaN，缺口超过 maxgap 帧的保持 NaN。"""
    x = x.copy(); n = len(x); i = 0
    idx = np.where(~np.isnan(x))[0]
    if len(idx) == 0: return x
    y = np.interp(np.arange(n), idx, x[idx])
    gap = np.zeros(n, bool); isn = np.isnan(x); i = 0
    while i < n:
        if isn[i]:
            j = i
            while j < n and isn[j]: j += 1
            if j - i > maxgap: gap[i:j] = True
            i = j
        else: i += 1
    y[gap] = np.nan
    return y


def lp(x, tau):
    """一阶低通；NaN 处保持上一值并标记无效。"""
    if tau <= 0: return x.copy()
    a = 1 - np.exp(-DT / tau); y = np.empty_like(x); cur = np.nan
    for i, v in enumerate(x):
        if np.isnan(v): y[i] = np.nan; continue
        cur = v if np.isnan(cur) else cur + a * (v - cur); y[i] = cur
    return y


own_d = fill(own_d, 25); opp_d = fill(opp_d, 25); own_lat = fill(own_lat, 25)
ball_zf = fill(ball_z, 20); ball_hf = fill(ball_h, 20)
# 球不在追踪里的时候，用本方人物位置顶替（相机此时只跟人），高度按 1 m
ball_z2 = np.where(np.isnan(ball_zf), own_d, ball_zf); ball_h2 = np.where(np.isnan(ball_hf), 1.0, ball_hf)

ok = C['ok'] == 1
inr = np.zeros(len(C), bool)
for a, b in RALLY: inr |= (C['t'] >= a) & (C['t'] <= b)
sel = ok & inr
tm = C['t'][sel]
SYNC = (0.015, 0.30)
ts = np.where(tm < 142.5, tm + SYNC[0], tm + SYNC[1])
ii = np.clip(np.round(ts / DT).astype(int), 0, N - 1)
cz = C['cz'][sel]; cx = C['cx'][sel]; cy = C['cy'][sel]; fov = C['fov'][sel]; pitch = C['pitch'][sel]
out = ['# 主视角相机的跟随动态', '', '由 `.ua/replica/tools/L_cam_dyn.py` 生成。回合内样本 %d 个（每 0.1 s 一个，相机解算成功的）。' % sel.sum(), '']


def reg(y, feats):
    A = np.column_stack([np.ones(len(y))] + feats); m = ~np.isnan(A).any(axis=1) & ~np.isnan(y)
    co, *_ = np.linalg.lstsq(A[m], y[m], rcond=None); res = y[m] - A[m] @ co
    return co, 1 - res.var() / y[m].var(), res.std(), m.sum()


TAUS = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5]
# ---- 1 相机距网 ----
out += ['## 1 相机距网', '', '### 1.1 只跟本方人物：cz = c0 + c1 × LP(d, tau)', '', '| tau s | c0 | c1 | R² | 残差 m |', '| --- | --- | --- | --- | --- |']
best = None
for tau in TAUS:
    co, r2, sd, n = reg(cz, [lp(own_d, tau)[ii]])
    out.append('| %.2f | %.2f | %.3f | %.3f | %.2f |' % (tau, co[0], co[1], r2, sd))
    if best is None or r2 > best[1]: best = (tau, r2)
out += ['', '只跟人物时拟合最好的 tau = %.2f s（R² %.3f）。' % best, '']
out += ['### 1.2 人物 + 球：cz = c0 + c1 × LP(d, tau) + c2 × LP(球的纵向位置, tau)', '', '球的纵向位置以网为 0、本方一侧为正；球不在追踪里时用人物位置顶替。', '',
        '| tau s | c0 | c1（人物） | c2（球） | R² | 残差 m |', '| --- | --- | --- | --- | --- | --- |']
best2 = None
for tau in TAUS:
    co, r2, sd, n = reg(cz, [lp(own_d, tau)[ii], lp(ball_z2, tau)[ii]])
    out.append('| %.2f | %.2f | %.3f | %.3f | %.3f | %.2f |' % (tau, co[0], co[1], co[2], r2, sd))
    if best2 is None or r2 > best2[1]: best2 = (tau, r2, co)
out += ['', '拟合最好的 tau = %.2f s（R² %.3f）。' % best2[:2], '']
out += ['### 1.3 人物 + 球 + 对手', '', '| tau s | c0 | c1（人物） | c2（球） | c3（对手距网） | R² | 残差 m |', '| --- | --- | --- | --- | --- | --- | --- |']
for tau in [0.1, 0.2, 0.3, 0.5]:
    co, r2, sd, n = reg(cz, [lp(own_d, tau)[ii], lp(ball_z2, tau)[ii], lp(opp_d, tau)[ii]])
    out.append('| %.2f | %.2f | %.3f | %.3f | %.3f | %.3f | %.2f |' % (tau, co[0], co[1], co[2], co[3], r2, sd))
out += ['', '### 1.4 人物和球用不同的时间常数', '', '| 人物 tau | 球 tau | c1 | c2 | R² |', '| --- | --- | --- | --- | --- |']
grid = []
for t1 in [0, 0.1, 0.2, 0.3, 0.5]:
    for t2 in [0.1, 0.2, 0.3, 0.5, 0.8, 1.2]:
        co, r2, sd, n = reg(cz, [lp(own_d, t1)[ii], lp(ball_z2, t2)[ii]]); grid.append((r2, t1, t2, co))
for r2, t1, t2, co in sorted(grid, key=lambda g: -g[0])[:6]:
    out.append('| %.2f | %.2f | %.3f | %.3f | %.3f |' % (t1, t2, co[1], co[2], r2))
# ---- 2 高度与俯角 ----
co, r2, sd, n = reg(cy, [cz]); out += ['', '## 2 高度和俯角跟着距网走', '', '- 相机高度 cy = %.3f × cz + %.2f（R² %.2f，残差 %.2f m）。' % (co[1], co[0], r2, sd)]
co, r2, sd, n = reg(pitch, [cz, fov]); out.append('- 俯角 = %.2f + %.3f × cz %+.3f × vFOV（R² %.2f，残差 %.2f°）。' % (co[0], co[1], co[2], r2, sd))
# ---- 3 横向 ----
out += ['', '## 3 相机横向', '', '| tau s | 系数 | R² | 残差 m |', '| --- | --- | --- | --- |']
for tau in [0, 0.1, 0.2, 0.3, 0.5, 0.8]:
    co, r2, sd, n = reg(cx, [lp(own_lat, tau)[ii]]); out.append('| %.2f | %.3f | %.3f | %.2f |' % (tau, co[1], r2, sd))
# ---- 4 视场角 ----
out += ['', '## 4 视场角对球高', '', '目标量 = max(0, 球高 − h0)，过一阶低通后回归 vFOV。', '', '| h0 m | tau s | 基准 vFOV | 每米增加 | R² | 残差 ° |', '| --- | --- | --- | --- | --- | --- |']
g = []
for h0 in [2.0, 2.5, 3.0, 3.5, 4.0]:
    for tau in [0.1, 0.2, 0.3, 0.5, 0.8]:
        co, r2, sd, n = reg(fov, [lp(np.maximum(0, ball_h2 - h0), tau)[ii]]); g.append((r2, h0, tau, co, sd))
for r2, h0, tau, co, sd in sorted(g, key=lambda x: -x[0])[:8]:
    out.append('| %.1f | %.2f | %.1f | %.2f | %.3f | %.2f |' % (h0, tau, co[0], co[1], r2, sd))
hv = ball_h2[ii]
out += ['', '按球高分档的 vFOV 中位（不滤波，直接看）：', '', '| 球高 m | 样本 | vFOV 中位 | 10%–90% |', '| --- | --- | --- | --- |']
for a, b in [(0, 1.5), (1.5, 2.5), (2.5, 3.5), (3.5, 4.5), (4.5, 9)]:
    m = (hv >= a) & (hv < b)
    if m.sum() > 3: out.append('| %.1f–%.1f | %d | %.1f | %.1f–%.1f |' % (a, b, m.sum(), np.median(fov[m]), np.percentile(fov[m], 10), np.percentile(fov[m], 90)))
out.append('')
out.append('球的追踪覆盖：回合内样本里球有三维坐标的占 %.0f%%；球高超过 3.5 m 的样本 %d 个（球常常飞出侧视角画面上沿，球高是低估）。' % (100 * (~np.isnan(ball_zf[ii])).mean(), (hv > 3.5).sum()))
# ---- 5 时间偏移扫描 ----
out += ['', '## 5 时间偏移扫描', '', '在闪光对齐之外再加一个偏移（正值 = 拿更晚的人物位置去配相机，即相机领先人物），看相机距网对人物位置的 R²。', '',
        '| 偏移 s | tau 0 | tau 0.1 | tau 0.2 | tau 0.3 | tau 0.5 |', '| --- | --- | --- | --- | --- | --- |']
for off in np.arange(-0.3, 0.41, 0.05):
    jj = np.clip(np.round((ts + off) / DT).astype(int), 0, N - 1)
    out.append('| %+.2f | ' % off + ' | '.join('%.3f' % reg(cz, [lp(own_d, t)[jj]])[1] for t in (0, 0.1, 0.2, 0.3, 0.5)) + ' |')
out += ['', '横向（cx 对本方横向位置）：', '', '| 偏移 s | tau 0 | tau 0.1 | tau 0.2 | tau 0.3 | tau 0.5 |', '| --- | --- | --- | --- | --- | --- |']
for off in np.arange(-0.3, 0.41, 0.05):
    jj = np.clip(np.round((ts + off) / DT).astype(int), 0, N - 1)
    out.append('| %+.2f | ' % off + ' | '.join('%.3f' % reg(cx, [lp(own_lat, t)[jj]])[1] for t in (0, 0.1, 0.2, 0.3, 0.5)) + ' |')
out += ['', '分段各自最好的偏移（tau 0）：', '']
for nm, m in (('142.5 s 前', tm < 142.5), ('142.5 s 后', tm >= 142.5)):
    bb = None
    for off in np.arange(-0.3, 0.41, 0.01):
        jj = np.clip(np.round((ts + off) / DT).astype(int), 0, N - 1)
        co, r2, sd, n = reg(cz[m], [own_d[jj][m]])
        if bb is None or r2 > bb[0]: bb = (r2, off, co, sd, n)
    out.append('- %s（%d 个样本）：偏移 %+.2f s，cz = %.2f + %.3f × d，R² %.3f，残差 %.2f m。' % (nm, bb[4], bb[1], bb[2][0], bb[2][1], bb[0], bb[3]))
io.open('data/L_cam_dyn.md', 'w', encoding='utf-8').write(chr(10).join(out))
print('ok', sel.sum())
