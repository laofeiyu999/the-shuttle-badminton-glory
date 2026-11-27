# -*- coding: utf-8 -*-
"""B2_multi.py 多样本动作对照条：python B2_multi.py 输出名 pre post step hw up dn 缩放 列数 L:帧 R:帧 ...
每个样本以追踪脚点为锚(固定裁剪窗，取该段脚点范围)，从 触球帧-pre 到 触球帧+post，每 step 帧一格；触球帧格子加红框。"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
cal = np.load(os.path.join(DATA, 'B2_calib.npz')); Hc = cal['H']
d = np.load(os.path.join(DATA, 'B2_post.npz'))


def proj(x, z):
    p = Hc @ np.array([x, z, 1.0]); return p[0] / p[2], p[1] / p[2]


def multi(name, pre, post, step, hw, up, dn, sc, cols, items, q=86):
    out = []
    for it in items:
        s, hf = it.split(':'); hf = int(hf)
        fs = list(range(hf - pre, hf + post + 1, step))
        xs = d[s + '_x']; zs = d[s + '_z']; uv = []
        for f in fs:
            g = f; k = 0
            while (np.isnan(xs[g]) or np.isnan(zs[g])) and k < 200:
                k += 1
                for c in (f - k, f + k):
                    if 0 <= c < len(xs) and not np.isnan(xs[c]) and not np.isnan(zs[c]): g = c; break
            uv.append(proj(xs[g], zs[g]) if not np.isnan(xs[g]) else (960, 900))
        uv = np.array(uv)
        from scipy.ndimage import uniform_filter1d
        uv = uniform_filter1d(uv, 5, axis=0, mode='nearest')
        x0 = max(0, int(uv[:, 0].min() - hw)); x1 = min(W, int(uv[:, 0].max() + hw))
        y0 = max(0, int(uv[:, 1].min() - up)); y1 = min(H, int(uv[:, 1].max() + dn))
        full = grab(fs[0], len(fs), crop=(x0, y0, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2), scale=None, step=step)
        w, h = 2 * hw, up + dn
        for (f, a), (u, v) in zip(full, uv):
            cx = int(np.clip(u - x0 - hw, 0, max(0, a.shape[1] - w))); cy = int(np.clip(v - y0 - up, 0, max(0, a.shape[0] - h)))
            im = Image.fromarray(a[cy:cy + h, cx:cx + w])
            if im.size != (w, h):
                bg = Image.new('RGB', (w, h)); bg.paste(im, (0, 0)); im = bg
            im = im.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
            dr = ImageDraw.Draw(im)
            if f == hf: dr.rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], outline=(255, 0, 0), width=3)
            dr.text((3, im.size[1] - 13), '%s %+d' % (s, f - hf), fill=(255, 255, 0))
            out.append((f, np.asarray(im)))
        while len(out) % cols: out.append((0, np.zeros_like(out[-1][1])))
    p = os.path.join(FR, name + '.jpg'); sheet(out, cols, p, fsz=12, quality=q); return p


if __name__ == '__main__':
    a = sys.argv
    print(multi(a[1], int(a[2]), int(a[3]), int(a[4]), int(a[5]), int(a[6]), int(a[7]), float(a[8]), int(a[9]), a[10:]))
