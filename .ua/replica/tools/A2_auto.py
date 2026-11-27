# -*- coding: utf-8 -*-
"""A2_auto.py：颜色门控脊点 + 消失点初始化 + 网格搜索 + 最小二乘。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import least_squares
from A2_cam import W, H, hud_ok, get_frame, project, segments, sample, Fitter, overlay, FR, bilin


def gated_mask(rgb, thr=28, size=15):
    """白线脊点掩膜：最小通道 top-hat + 局部底色为场地蓝或地胶绿。返回 bool 掩膜（已细化为脊）。"""
    a = rgb.astype(np.int16)
    m = a.min(2)
    th = (m - ndi.grey_opening(m, size=(size, size))).astype(np.float32)
    th = ndi.uniform_filter(th, 3)
    mx = (th >= np.roll(th, 1, 1)) & (th > np.roll(th, -1, 1))
    my = (th >= np.roll(th, 1, 0)) & (th > np.roll(th, -1, 0))
    bg = np.stack([ndi.grey_opening(a[..., c], size=(size, size)) for c in range(3)], -1)
    bg = ndi.uniform_filter(bg.astype(np.float32), (9, 9, 1))
    R, G, B = bg[..., 0], bg[..., 1], bg[..., 2]
    blue = (B > 150) & (B - R > 95) & (B - G > 55) & (R < 120)
    green = (G > 95) & (G - R > 70) & (G - B > 15) & (R < 80)
    mk = (th > thr) & (mx | my) & (blue | green)
    yy, xx = np.mgrid[0:H, 0:W]
    mk &= hud_ok(xx, yy)
    return mk, blue


def dmap(mk, tau=30):
    return np.minimum(ndi.distance_transform_edt(~mk), tau).astype(np.float32)


class Auto:
    def __init__(self, dim=None, step=0.12):
        self.F = Fitter(dim, None, step)
        self.P, self.sid, self.names = self.F.P, self.F.sid, self.F.names

    def cost(self, p, dm, tau):
        uv, d = project(p, self.P)
        x, y = uv[:, 0], uv[:, 1]
        vis = np.isfinite(x) & np.isfinite(y)
        xx = np.where(vis, x, 0); yy = np.where(vis, y, 0)
        vis &= hud_ok(xx, yy)
        r = np.where(vis, np.minimum(bilin(dm, np.clip(xx, 0, W - 1.001), np.clip(yy, 0, H - 1.001)), tau), tau * 0.5)
        return r, vis

    def refine(self, p0, dm, taus=(25, 10, 5), free=(1, 1, 1, 1, 1, 1)):
        p = np.array(p0, float)
        idx = [i for i in range(6) if free[i]]
        lo = np.array([-9, 0.6, 2, -5, -45, 6.0]); hi = np.array([9, 16, 32, 70, 45, 80.0])
        xs = np.array([1, 1, 1, 3, 3, 5.0])
        for tau in taus:
            def fun(q):
                pp = p.copy(); pp[idx] = q
                return self.cost(pp, dm, tau)[0]
            q0 = np.clip(p[idx], lo[idx] + 1e-6, hi[idx] - 1e-6)
            res = least_squares(fun, q0, bounds=(lo[idx], hi[idx]), diff_step=2e-3, x_scale=xs[idx], loss='soft_l1', f_scale=2.0, max_nfev=40)
            p[idx] = res.x
        return p

    def score(self, p, dm, tol=2.5):
        uv, d = project(p, self.P)
        x, y = uv[:, 0], uv[:, 1]
        vis = np.isfinite(x) & np.isfinite(y)
        xx = np.where(vis, x, 0); yy = np.where(vis, y, 0)
        vis &= hud_ok(xx, yy)
        r = bilin(dm, np.clip(xx, 0, W - 1.001), np.clip(yy, 0, H - 1.001))
        inl = vis & (r < tol)
        per = {}
        for k, nm in enumerate(self.names):
            s = self.sid == k; nv = int((vis & s).sum())
            per[nm] = (nv, float((inl & s).sum()) / nv if nv else np.nan)
        nv = int(vis.sum())
        return dict(nvis=nv, inl=float(inl.sum()) / max(nv, 1), rms=float(np.sqrt(np.mean(r[inl] ** 2))) if inl.sum() else np.nan,
                    mean=float(np.mean(r[vis])) if nv else np.nan, per=per, nlines=sum(1 for v in per.values() if v[0] >= 8), ngood=sum(1 for v in per.values() if v[0] >= 8 and v[1] > 0.7))

    def grid_init(self, dm, rng=None, n=6000, seed=0, around=None):
        """随机搜索初值：返回按 mean 截断距离排序的前若干个。"""
        r = np.random.default_rng(seed)
        best = []
        for i in range(n):
            if around is not None and i % 2 == 0:
                p = np.array(around) + r.normal(0, [0.6, 0.8, 1.5, 3, 2, 4])
            else:
                p = np.array([r.uniform(-4, 4), r.uniform(1.2, 9), r.uniform(7.5, 22), r.uniform(8, 42), r.uniform(-25, 25), r.uniform(18, 60)])
            c, vis = self.cost(p, dm, 25)
            if vis.sum() < 250: continue
            best.append((float(np.mean(c)), tuple(p)))
        best.sort(key=lambda t: t[0])
        return best[:8]

    def solve(self, rgb, p0=None, nsearch=6000, verbose=False):
        mk, _ = gated_mask(rgb)
        dm = dmap(mk)
        cands = []
        if p0 is not None:
            p = self.refine(p0, dm, taus=(12, 5)); cands.append((p, self.score(p, dm)))
            if cands[0][1]['inl'] > 0.86 and cands[0][1]['ngood'] >= cands[0][1]['nlines'] - 1:
                return cands[0][0], cands[0][1], mk
        for c, q in self.grid_init(dm, n=nsearch, around=p0):
            p = self.refine(q, dm); sc = self.score(p, dm)
            cands.append((p, sc))
            if verbose: print('  cand c0 %.2f -> inl %.3f good %d/%d' % (c, sc['inl'], sc['ngood'], sc['nlines']), np.round(p, 2))
            if sc['inl'] > 0.9 and sc['ngood'] >= sc['nlines'] - 1: break
        cands.sort(key=lambda t: -(t[1]['inl'] * min(t[1]['nvis'], 700)))
        return cands[0][0], cands[0][1], mk


if __name__ == '__main__':
    import time
    f = int(sys.argv[1]); p0 = [float(v) for v in sys.argv[2:8]] if len(sys.argv) >= 8 else None
    t0 = time.time(); rgb = get_frame(f); A = Auto()
    p, sc, mk = A.solve(rgb, p0, verbose=True)
    print('t %.1fs mask px %d' % (time.time() - t0, mk.sum()))
    print('fit p= %.3f %.3f %.3f pitch %.2f yaw %.2f fov %.2f' % tuple(p))
    print('nvis %d inl %.3f rms %.2f mean %.2f good %d/%d' % (sc['nvis'], sc['inl'], sc['rms'], sc['mean'], sc['ngood'], sc['nlines']))
    print(' '.join('%s:%d/%.2f' % (k, v[0], v[1]) for k, v in sc['per'].items()))
    from PIL import Image
    o = rgb.copy(); o[mk] = (255, 255, 0)
    print(overlay(o, p, A.F, os.path.join(FR, 'A2_ov_%05d.jpg' % f)))
