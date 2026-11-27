# -*- coding: utf-8 -*-
"""A2_hough.py：白线脊点提取 + Hough 直线检测（numpy）。lines(rgb) -> list of dict(theta,rho,n,p0,p1)
直线表示：x*cos(t)+y*sin(t)=rho，t∈[0,180)。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy import ndimage as ndi
from A2_cam import W, H, hud_ok, get_frame

def ridge_points(rgb, thr=30, size=15):
    m = rgb.min(2).astype(np.int16)
    th = m - ndi.grey_opening(m, size=(size, size))
    th = ndi.uniform_filter(th.astype(np.float32), 3)
    mx = (th >= np.roll(th, 1, 1)) & (th > np.roll(th, -1, 1))
    my = (th >= np.roll(th, 1, 0)) & (th > np.roll(th, -1, 0))
    mk = (th > thr) & (mx | my)
    # 只保留背景为蓝场地/绿地附近的点：要求 15px 邻域开运算后的底色蓝或绿占优（排除看台/人物上的白）
    ys, xs = np.nonzero(mk)
    ok = hud_ok(xs, ys)
    return xs[ok].astype(np.float32), ys[ok].astype(np.float32), th

TH = np.radians(np.arange(0, 180, 0.25))
CT, ST = np.cos(TH), np.sin(TH)
RMAX = int(np.hypot(W, H)) + 2

def hough_lines(xs, ys, nmax=28, min_votes=45, tol=1.6, min_len=60):
    out = []
    xs = xs.copy(); ys = ys.copy()
    alive = np.ones(len(xs), bool)
    # 一次性累加，之后贪心取峰并剔除其内点再重算（减去贡献）
    rho = np.rint(xs[:, None] * CT[None] + ys[:, None] * ST[None]).astype(np.int32) + RMAX
    nr = 2 * RMAX + 1
    acc = np.zeros((len(TH), nr), np.int32)
    ti = np.arange(len(TH))[None].repeat(len(xs), 0)
    np.add.at(acc, (ti.ravel(), rho.ravel()), 1)
    for _ in range(nmax):
        a2 = acc[:, :-1] + acc[:, 1:]
        k = int(a2.argmax()); t, r = divmod(k, nr - 1)
        if a2[t, r] < min_votes: break
        th = TH[t]; rr = r + 0.5 - RMAX
        d = xs * np.cos(th) + ys * np.sin(th) - rr
        inl = alive & (np.abs(d) < 3.0)
        # 精修：TLS
        for it in range(3):
            if inl.sum() < 10: break
            X = np.stack([xs[inl], ys[inl]], 1); c = X.mean(0)
            u, s, vt = np.linalg.svd(X - c, full_matrices=False)
            n = vt[1]; 
            if n[1] < 0 or (abs(n[1]) < 1e-9 and n[0] < 0): n = -n
            th2 = np.arctan2(n[1], n[0]); rr2 = c @ n
            d = xs * n[0] + ys * n[1] - rr2
            inl = alive & (np.abs(d) < tol)
        if inl.sum() >= 10:
            dirv = np.array([-n[1], n[0]])
            s_ = xs[inl] * dirv[0] + ys[inl] * dirv[1]
            # 沿线覆盖长度（按 4px 桶计数）
            cov = len(np.unique(np.floor(s_ / 4))) * 4
            if cov >= min_len:
                lo, hi = s_.min(), s_.max()
                p0 = n * rr2 + dirv * lo; p1 = n * rr2 + dirv * hi
                out.append(dict(theta=float(np.degrees(th2)) % 180, n=n.copy(), rho=float(rr2), npts=int(inl.sum()), cov=float(cov), p0=p0, p1=p1))
        # 剔除（用宽一点的带）
        kill = alive & (np.abs(xs * np.cos(th) + ys * np.sin(th) - rr) < 3.5)
        if inl.sum() >= 10:
            kill |= alive & (np.abs(d) < 3.0)
        if kill.sum() == 0:
            acc[max(0, t - 2):t + 3, max(0, r - 3):r + 5] = 0
            continue
        np.subtract.at(acc, (ti[kill].ravel(), rho[kill].ravel()), 1)
        alive &= ~kill
    return out

if __name__ == '__main__':
    import time
    f = int(sys.argv[1]); t0 = time.time()
    rgb = get_frame(f); xs, ys, th = ridge_points(rgb)
    print('ridge pts', len(xs))
    L = hough_lines(xs, ys)
    print('time %.1fs' % (time.time() - t0))
    for l in sorted(L, key=lambda l: (l['theta'] > 45 and l['theta'] < 135, l['rho'])):
        print('th %6.2f rho %8.1f n %4d cov %5.0f  (%6.1f,%6.1f)-(%6.1f,%6.1f)' % (l['theta'], l['rho'], l['npts'], l['cov'], l['p0'][0], l['p0'][1], l['p1'][0], l['p1'][1]))
