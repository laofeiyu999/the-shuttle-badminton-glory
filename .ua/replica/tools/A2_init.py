# -*- coding: utf-8 -*-
"""A2_init.py：无先验的相机初值（利用滚转 0、偏航约 -0.4 度几乎恒定的结构）。
纵向球场线交于消失点 (vx≈949, vy)：对 vy 做一维投票；斜率 dx/dy = (X-cx)·k；横线 1/(y-vy) 对 Z 线性。
枚举 (两条斜线->两个 X)、(两条横线->两个 Z) 指派，脊点覆盖率预筛，取前若干个做线对应最小二乘，按拟合后质量选优。"""
import sys, os, itertools
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from A_common import W, H
import A2_trk as T

XS = np.array([-3.05, -2.56, 0.0, 2.56, 3.05])
ZS = [-6.70, -5.95, -2.15, 2.15, 5.95, 6.70]
VX = 972.0


def init_vp(L, dm, topk=10):
    n0, n1, rho, npts = L[:, 0], L[:, 1], L[:, 2], L[:, 7]
    isH = (np.abs(n1) > 0.94) & (np.abs(n0 / np.where(np.abs(n1) > 1e-6, n1, 1e-6)) < 0.03)
    O = np.nonzero(np.abs(n0) > 0.35)[0]; Hh = np.nonzero(isH)[0]
    if len(O) < 2 or len(Hh) < 2: return []
    # 每条斜线在 x=VX 处的 y；消失点 vy = 这些 y 的聚集处
    yv = (rho[O] - VX * n0[O]) / np.where(np.abs(n1[O]) > 1e-3, n1[O], 1e-3)
    tolv = 6 + 14 * np.abs(n0[O] / np.where(np.abs(n1[O]) > 1e-3, n1[O], 1e-3)) * 0  # 像素
    grid = np.arange(-1200, 330, 3.0)
    # x 方向 12 px 的不确定度换算成 y 容差：dy = 12 / |dx/dy|
    sl_all = -n1[O] / n0[O]
    tol = np.clip(14 / np.maximum(np.abs(sl_all), 0.02), 8, 200)
    votes = np.array([(np.abs(yv - g) < tol).sum() + 0.001 * (np.abs(yv - g) < 0.3 * tol).sum() for g in grid])
    out = []
    peaks = []
    v2 = votes.copy()
    for _ in range(4):
        k = int(v2.argmax())
        if v2[k] < 3: break
        peaks.append(grid[k]); v2[np.abs(grid - grid[k]) < 60] = 0
    for vy0 in peaks:
        S = O[np.abs(yv - vy0) < tol]
        A = np.stack([n0[S], n1[S]], 1); v = np.linalg.lstsq(A, rho[S], rcond=None)[0]
        vx, vy = v
        if abs(vx - VX) > 40: vx = VX; vy = vy0
        sl = np.sort(-n1[S] / n0[S])
        cands = []
        for (i, j) in itertools.combinations(range(len(sl)), 2):
            if sl[j] - sl[i] < 0.02: continue
            for (a, b) in itertools.combinations(range(5), 2):
                k = (sl[j] - sl[i]) / (XS[b] - XS[a]); c = sl[i] - k * XS[a]
                pred = k * XS + c
                dd = np.abs(sl[None, :] - pred[:, None]); jj = dd.argmin(1)
                hit = dd[np.arange(5), jj] < 0.010 + 0.012 * np.abs(pred)
                m = len(set(jj[hit].tolist()))
                cands.append((m, k, c))
        cands.sort(key=lambda t: -t[0])
        seen = []
        hs = sorted(Hh, key=lambda h: -npts[h])[:14]
        yh = np.sort(np.array([(rho[h] - 961 * n0[h]) / n1[h] for h in hs])); yh = yh[yh > vy + 25]
        if len(yh) < 2: continue
        inv = 1.0 / (yh - vy)
        for m, k, c in cands[:80]:
            if m < 3: break
            if any(abs(k - k2) < 0.004 and abs(c - c2) < 0.01 for k2, c2 in seen): continue
            seen.append((k, c))
            if len(seen) > 6: break
            cx = -c / k
            for (i, j) in itertools.combinations(range(len(yh)), 2):
                if yh[j] - yh[i] < 12: continue
                for (a, b) in itertools.combinations(range(6), 2):
                    beta = (inv[i] - inv[j]) / (ZS[b] - ZS[a])
                    st = beta * (H / 2 - vy) / k
                    if not (0.03 < st < 0.85): continue
                    th = np.arcsin(st); F = (H / 2 - vy) / np.tan(th); cy = np.cos(th) / k
                    fov = 2 * np.degrees(np.arctan(H / 2 / F))
                    if not (12 < fov < 70 and 1.0 < cy < 15): continue
                    cz = ZS[a] + (inv[i] * F * cy / np.cos(th) - cy * np.sin(th)) / np.cos(th)
                    if not (4 < cz < 35): continue
                    yaw = -np.degrees(np.arctan((vx - W / 2) * np.cos(th) / F))
                    p = np.array([cx, cy, cz, np.degrees(th), yaw, fov])
                    inl, nvis = T.verify(p, dm, tol=4.0)
                    if nvis >= 60: out.append((nvis * (2 * inl - 1), p))
    out.sort(key=lambda t: -t[0])
    res = []
    for s, p in out:
        if all(np.abs((p - q) / np.array([.4, .4, 1, 1.5, 2, 2.5])).max() > 1 for q in res): res.append(p)
        if len(res) >= topk: break
    return res


def solve_init(L, dm):
    best = None
    for p0 in init_vp(L, dm):
        p, q = T.fit(p0, L, dm, thrs=(12, 6, 3.5))
        v = (q['ok'], round(q['inl'] * min(q['nvis'], 400)) + 20 * q['n'])
        if best is None or v > best[0]: best = (v, p, q)
        if q['ok'] and q['n'] >= 7 and q['inl'] > 0.9: break
    return (best[1], best[2]) if best else (None, T.BADQ)

if __name__ == '__main__':
    import time
    from A_common import get_frame
    for a in sys.argv[1:]:
        f = int(a); rgb = get_frame(f); L, dm = T.detect(rgb); t0 = time.time()
        p, q = solve_init(L, dm)
        if p is None: print('f%d no init' % f); continue
        print('f%d %.2fs p %s n %d (%d/%d) rms %.2f inl %.2f nvis %d sf %.2f ok %s' % (f, time.time() - t0, np.round(p, 2), q['n'], q['nH'], q['nO'], q['rms'], q['inl'], q['nvis'], q['sig'][5], q['ok']))
