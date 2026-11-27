# -*- coding: utf-8 -*-
"""A2_kf.py：关键帧半自动标定。
  python A2_kf.py label f [f...]      -> 未门控脊点 Hough，编号叠加图 A2_L_<f>.jpg + data/A2_lines/<f>.npy
  solve(f, assign, p0, free_dim=...)  -> 用“模型线名 -> 图像直线编号”对应，最小化投影模型点到图像直线的距离。
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy.optimize import least_squares
from A_common import *
from A2_cam import project, segments, DIM_STD, HALF_L, hud_ok
from A2_hough import ridge_points
from A2_h import fast_hough
LD = os.path.join(DATA, 'A2_lines'); os.makedirs(LD, exist_ok=True)


def label(f, show=True, quiet=False):
    rgb = get_frame(f)
    xs, ys, _ = ridge_points(rgb, thr=30)
    L = fast_hough(xs, ys, nmax=40, min_votes=45, min_cov=90)
    hz = sorted([l for l in L if abs(l['theta'] - 90) < 20], key=lambda l: (l['rho'] - 961 * l['n'][0]) / l['n'][1])
    ob = sorted([l for l in L if abs(l['theta'] - 90) >= 20], key=lambda l: (l['rho'] - 880 * l['n'][1]) / l['n'][0])
    L = hz + ob
    arr = np.array([[l['n'][0], l['n'][1], l['rho'], l['p0'][0], l['p0'][1], l['p1'][0], l['p1'][1], l['npts']] for l in L])
    np.save(os.path.join(LD, '%05d.npy' % f), arr)
    if not quiet: print('== f%d t=%.2f' % (f, f / 60.))
    im = Image.fromarray((rgb * 0.55).astype(np.uint8)); d = ImageDraw.Draw(im); ft = font(22)
    cols = [(255, 60, 60), (255, 255, 0), (0, 255, 0), (255, 0, 255), (0, 255, 255), (255, 160, 0)]
    for i, l in enumerate(L):
        c = cols[i % 6]; d.line([tuple(l['p0']), tuple(l['p1'])], fill=c, width=2)
        k = 0.2 + 0.6 * ((i * 7) % 10) / 10.0; m = l['p0'] * (1 - k) + l['p1'] * k
        d.rectangle([m[0] - 2, m[1] - 12, m[0] + 26, m[1] + 12], fill=(0, 0, 0)); d.text((m[0], m[1] - 12), str(i), fill=c, font=ft)
        n, r = l['n'], l['rho']
        if quiet: continue
        if i < len(hz):
            print('%2d H y@961 %6.1f slope %7.4f n %4d x[%5.0f..%5.0f]' % (i, (r - 961 * n[0]) / n[1], -n[0] / n[1], l['npts'], min(l['p0'][0], l['p1'][0]), max(l['p0'][0], l['p1'][0])))
        else:
            print('%2d O dx/dy %7.4f x@y880 %7.1f n %4d y[%4.0f..%4.0f]' % (i, -n[1] / n[0], (r - 880 * n[1]) / n[0], l['npts'], min(l['p0'][1], l['p1'][1]), max(l['p0'][1], l['p1'][1])))
    if show:
        im = im.resize((1600, int(H * 1600 / W)), Image.LANCZOS); out = os.path.join(FR, 'A2_L_%05d.jpg' % f); im.save(out, quality=80); print(out)
    return arr


DKEYS = ['half_wd', 'half_ws', 'z_short', 'z_long', 'net_h']


def solve(f, assign, p0, free_dim=(), dim=None, roll=False, verbose=True, lines=None):
    """assign: {model_name: idx}；返回 p, dim, per-line rms(px), total rms。"""
    L = np.load(os.path.join(LD, '%05d.npy' % f)) if lines is None else lines
    dim0 = dict(dim or DIM_STD)
    names = list(assign.keys())
    def unpack(q):
        p = q[:6]; d = dict(dim0)
        for k, nm in enumerate(free_dim): d[nm] = q[6 + k]
        return p, d
    def res(q, split=False):
        p, d = unpack(q); segs = segments(d)
        out = []
        for nm in names:
            n0, n1, rho, x0, y0, x1, y1, _ = L[assign[nm]]
            a, b = np.array(segs[nm][0], float), np.array(segs[nm][1], float)
            t = np.linspace(0, 1, 41)[:, None]
            uv, dep = project(p, a + (b - a) * t)
            dist = uv[:, 0] * n0 + uv[:, 1] * n1 - rho
            # 只用落在检测线段范围（沿线方向）内的点；不足 3 点时用全部屏内点
            s = uv[:, 0] * (-n1) + uv[:, 1] * n0
            s0, s1 = sorted([x0 * (-n1) + y0 * n0, x1 * (-n1) + y1 * n0])
            w = (np.isfinite(dist) & (s >= s0 - 5) & (s <= s1 + 5)).astype(float)
            if w.sum() < 3: w = (np.isfinite(dist) & (uv[:, 0] > -200) & (uv[:, 0] < W + 200) & (uv[:, 1] > -200) & (uv[:, 1] < H + 200)).astype(float)
            dist = np.where(np.isfinite(dist), dist, 50.0) * w / np.sqrt(max(w.sum(), 1))
            out.append(dist)
        return out if split else np.concatenate(out)
    q0 = np.array(list(p0) + [dim0[k] for k in free_dim], float)
    r = least_squares(res, q0, x_scale=np.array([1, 1, 1, 3, 3, 5.0] + [0.3] * len(free_dim)), loss='linear', max_nfev=400)
    p, d = unpack(r.x)
    per = {nm: float(np.sqrt(np.sum(v ** 2))) for nm, v in zip(names, res(r.x, True))}
    tot = float(np.sqrt(np.mean([v ** 2 for v in per.values()])))
    if verbose:
        print('f%d p= x %.3f y %.3f z %.3f pitch %.2f yaw %.2f fov %.2f | rms %.2f px | ' % (f, *p, tot) + ' '.join('%s=%.3f' % (k, d[k]) for k in free_dim))
        print('   ' + ' '.join('%s:%.1f' % kv for kv in per.items()))
    return p, d, per, tot


if __name__ == '__main__':
    if sys.argv[1] == 'label':
        for a in sys.argv[2:]: label(int(a))
