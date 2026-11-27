# -*- coding: utf-8 -*-
"""A2_cam.py 相机标定库（重写版）。
世界系：原点=球网中心地面；x 向右（本方看向球网的右手）；y 向上；z 指向本方（本方底线 z=+6.70）。
相机参数 p=(cx,cy,cz,pitch(俯角,向下为正,度),yaw(向右转为正,度),vfov(度))，roll=0。
方法：白线掩膜(最小通道 top-hat) -> 距离变换 -> 模型采样点到掩膜的截断距离最小二乘。
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import least_squares
from A_common import W, H, get_frame, iter_frames, FR, DATA

HALF_L = 6.70
DIM_STD = dict(half_wd=3.05, half_ws=2.59, z_short=1.98, z_long=5.94, net_h=1.55)
DIM = dict(DIM_STD)


def segments(dim=None, lines=None):
    d = dim or DIM
    s = {}
    wd, ws, zs, zl = d['half_wd'], d['half_ws'], d['z_short'], d['z_long']
    s['sideD_L'] = ((-wd, 0, -HALF_L), (-wd, 0, HALF_L))
    s['sideD_R'] = ((wd, 0, -HALF_L), (wd, 0, HALF_L))
    s['sideS_L'] = ((-ws, 0, -HALF_L), (-ws, 0, HALF_L))
    s['sideS_R'] = ((ws, 0, -HALF_L), (ws, 0, HALF_L))
    s['base_far'] = ((-wd, 0, -HALF_L), (wd, 0, -HALF_L))
    s['base_near'] = ((-wd, 0, HALF_L), (wd, 0, HALF_L))
    s['long_far'] = ((-wd, 0, -zl), (wd, 0, -zl))
    s['long_near'] = ((-wd, 0, zl), (wd, 0, zl))
    s['short_far'] = ((-wd, 0, -zs), (wd, 0, -zs))
    s['short_near'] = ((-wd, 0, zs), (wd, 0, zs))
    s['centre_far'] = ((0, 0, -HALF_L), (0, 0, -zs))
    s['centre_near'] = ((0, 0, zs), (0, 0, HALF_L))
    s['net_top'] = ((-wd, d['net_h'], 0), (wd, d['net_h'], 0))
    if lines is not None:
        s = {k: v for k, v in s.items() if k in lines}
    return s


def sample(segs, step=0.10):
    pts, sid, names = [], [], list(segs.keys())
    for k, nm in enumerate(names):
        a, b = np.array(segs[nm][0], float), np.array(segs[nm][1], float)
        n = max(2, int(np.linalg.norm(b - a) / step) + 1)
        t = np.linspace(0, 1, n)[:, None]
        pts.append(a + (b - a) * t); sid.append(np.full(n, k))
    return np.vstack(pts), np.concatenate(sid), names


def basis(pitch, yaw):
    th, ps = np.radians(pitch), np.radians(yaw)
    f = np.array([np.sin(ps) * np.cos(th), -np.sin(th), -np.cos(ps) * np.cos(th)])
    r = np.array([np.cos(ps), 0.0, np.sin(ps)])
    u = np.cross(r, f)
    return r, u, f


def project(p, P):
    cx, cy, cz, pitch, yaw, fov = p[:6]
    r, u, f = basis(pitch, yaw)
    v = np.asarray(P, float) - np.array([cx, cy, cz])
    d = v @ f
    F = (H / 2) / np.tan(np.radians(fov) / 2)
    dd = np.where(d > 0.05, d, np.nan)
    return np.stack([W / 2 + F * (v @ r) / dd, H / 2 - F * (v @ u) / dd], 1), d


# HUD 遮罩矩形 (x0,y0,x1,y1)：左上双条、右上、右下三键、能量条
HUD = [(0, 0, 530, 262), (1540, 0, 1922, 170), (1330, 330, 1922, 880), (700, 780, 1200, 850)]


def hud_ok(x, y):
    ok = (x >= 2) & (x < W - 2) & (y >= 2) & (y < H - 2)
    for x0, y0, x1, y1 in HUD:
        ok &= ~((x >= x0) & (x < x1) & (y >= y0) & (y < y1))
    return ok


def line_mask(rgb, thr=38, size=17):
    m = rgb.min(2).astype(np.int16)
    th = m - ndi.grey_opening(m, size=(size, size))
    mk = th > thr
    # 去掉大团块（人物、HUD 实心）：连通域里面积/外接框细长的才保留——简单起见只按 top-hat
    return mk


def dist_map(mask, tau):
    dt = ndi.distance_transform_edt(~mask)
    return np.minimum(dt, tau).astype(np.float32)


def bilin(img, x, y):
    x0 = np.clip(np.floor(x).astype(int), 0, img.shape[1] - 2); y0 = np.clip(np.floor(y).astype(int), 0, img.shape[0] - 2)
    fx, fy = x - x0, y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


class Fitter:
    def __init__(self, dim=None, lines=None, step=0.10):
        self.segs = segments(dim, lines)
        self.P, self.sid, self.names = sample(self.segs, step)

    def resid(self, p, dm, tau):
        uv, d = project(p, self.P)
        x, y = uv[:, 0], uv[:, 1]
        vis = np.isfinite(x) & np.isfinite(y)
        xx = np.where(vis, x, 0); yy = np.where(vis, y, 0)
        vis &= hud_ok(xx, yy)
        r = np.where(vis, bilin(dm, np.clip(xx, 0, W - 1.001), np.clip(yy, 0, H - 1.001)), tau * 0.6)
        return r, vis

    def fit(self, p0, mask, taus=(14, 6, 3), free=(1, 1, 1, 1, 1, 1), bounds=None):
        p = np.array(p0, float)
        idx = [i for i in range(6) if free[i]]
        lo = np.array([-8, 0.8, 3, 0, -40, 8.0]); hi = np.array([8, 14, 30, 60, 40, 75.0])
        for tau in taus:
            dm = dist_map(mask, tau)
            def fun(q):
                pp = p.copy(); pp[idx] = q
                return self.resid(pp, dm, tau)[0]
            q0 = np.clip(p[idx], lo[idx] + 1e-6, hi[idx] - 1e-6)
            res = least_squares(fun, q0, bounds=(lo[idx], hi[idx]), diff_step=[2e-3] * len(idx), x_scale=np.array([1, 1, 1, 3, 3, 5.0])[idx], loss='soft_l1', f_scale=1.5, max_nfev=60)
            p[idx] = res.x
        return p, self.score(p, mask)

    def score(self, p, mask, tol=2.5):
        dm = dist_map(mask, 20)
        uv, d = project(p, self.P)
        x, y = uv[:, 0], uv[:, 1]
        vis = np.isfinite(x) & np.isfinite(y)
        xx = np.where(vis, x, 0); yy = np.where(vis, y, 0)
        vis &= hud_ok(xx, yy)
        r = bilin(dm, np.clip(xx, 0, W - 1.001), np.clip(yy, 0, H - 1.001))
        inl = vis & (r < tol)
        per = {}
        for k, nm in enumerate(self.names):
            s = self.sid == k
            nv = int((vis & s).sum())
            per[nm] = (nv, float((inl & s).sum()) / nv if nv else np.nan)
        nv = int(vis.sum())
        rms = float(np.sqrt(np.mean(r[inl] ** 2))) if inl.sum() else np.nan
        return dict(nvis=nv, inl=float(inl.sum()) / max(nv, 1), rms_inl=rms, med=float(np.median(r[vis])) if nv else np.nan, per=per)


def overlay(rgb, p, fitter, out, mask=None, crop=None, outw=1600):
    from PIL import Image, ImageDraw
    im = Image.fromarray(rgb.copy())
    d = ImageDraw.Draw(im)
    for nm, (a, b) in fitter.segs.items():
        t = np.linspace(0, 1, 60)[:, None]
        uv, dep = project(p, np.array(a) + (np.array(b) - np.array(a)) * t)
        pts = [(float(x), float(y)) for (x, y), dd in zip(uv, dep) if np.isfinite(x) and dd > 0.05 and -2000 < x < 4000 and -2000 < y < 3000]
        if len(pts) > 1:
            d.line(pts, fill=(255, 0, 0), width=1)
    if crop:
        x0, y0, w, h = crop; im = im.crop((x0, y0, x0 + w, y0 + h))
    im = im.resize((outw, int(im.size[1] * outw / im.size[0])), Image.LANCZOS)
    im.save(out, quality=85)
    return out
