# -*- coding: utf-8 -*-
"""跟随裁剪拼条：python B2_follow.py L|R 起始帧 帧数 步长 半宽px 上px 下px 缩放 列数 输出名 [mark]
以追踪到的脚下位置为锚点裁剪(锚点按首帧到末帧线性插值平滑，丢失时取最近有效值)，mark=1 时画出脚下点(红十字)和速度文字。"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
_d = None; _H = None


def _load():
    global _d, _H
    if _d is None:
        _d = np.load(os.path.join(DATA, 'B2_post.npz')); _H = np.load(os.path.join(DATA, 'B2_calib.npz'))['H']
    return _d, _H


def proj(x, z):
    d, Hc = _load(); p = Hc @ np.array([x, z, 1.0]); return p[0] / p[2], p[1] / p[2]


def follow(side, f0, n, step, hw, up, dn, sc, cols, name, mark=False, fixed=False, q=88):
    d, Hc = _load(); xs = d[side + '_x']; zs = d[side + '_z']; sp = d[side + '_sp']
    fs = list(range(f0, f0 + n * step, step)); uv = []
    for f in fs:
        g = f
        k = 0
        while (np.isnan(xs[g]) or np.isnan(zs[g])) and k < 200:
            k += 1
            for c in (f - k, f + k):
                if 0 <= c < len(xs) and not np.isnan(xs[c]) and not np.isnan(zs[c]): g = c; break
        uv.append(proj(xs[g], zs[g]) if not np.isnan(xs[g]) else (960, 900))
    uv = np.array(uv)
    if fixed: uv[:] = np.median(uv, 0)
    else:
        from scipy.ndimage import uniform_filter1d
        if len(uv) >= 5: uv = uniform_filter1d(uv, 5, axis=0, mode='nearest')
    x0 = max(0, int(uv[:, 0].min() - hw)); x1 = min(W, int(uv[:, 0].max() + hw))
    y0 = max(0, int(uv[:, 1].min() - up)); y1 = min(H, int(uv[:, 1].max() + dn))
    full = grab(f0, n, crop=(x0, y0, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2), scale=None, step=step)
    out = []
    w, h = 2 * hw, up + dn
    for (f, a), (u, v) in zip(full, uv):
        cx = int(np.clip(u - x0 - hw, 0, max(0, a.shape[1] - w))); cy = int(np.clip(v - y0 - up, 0, max(0, a.shape[0] - h)))
        im = Image.fromarray(a[cy:cy + h, cx:cx + w])
        if mark:
            dr = ImageDraw.Draw(im)
            if not np.isnan(xs[f]):
                pu, pv = proj(xs[f], zs[f]); pu -= x0 + cx; pv -= y0 + cy
                dr.line([pu - 8, pv, pu + 8, pv], fill=(255, 0, 0), width=2); dr.line([pu, pv - 8, pu, pv + 8], fill=(255, 0, 0), width=2)
                dr.text((4, h - 14), 'x%.2f z%.2f v%.1f' % (xs[f], zs[f], sp[f]), fill=(255, 255, 0))
        if sc != 1: im = im.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
        out.append((f, np.asarray(im)))
    p = os.path.join(FR, name + '.jpg'); sheet(out, cols, p, fsz=14, quality=q); return p


if __name__ == '__main__':
    a = sys.argv
    print(follow(a[1], int(a[2]), int(a[3]), int(a[4]), int(a[5]), int(a[6]), int(a[7]), float(a[8]), int(a[9]), a[10], mark=len(a) > 11 and a[11] == '1'))
