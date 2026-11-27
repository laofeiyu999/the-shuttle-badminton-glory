# -*- coding: utf-8 -*-
"""B2_ruler.py 身高标尺图：python B2_ruler.py 输出名 缩放 L:帧 R:帧 ...
在指定帧上以追踪到的脚下地面点为基准，画出高度 0/0.25/.../2.75 m 的水平刻度(沿竖直方向投影)，
并在脚下深度画一条 1 m 长的横向比例尺。每个样本裁 420×520 px 放大。"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
cal = np.load(os.path.join(DATA, 'B2_calib.npz')); Hc = cal['H']; P = cal['P']
d = np.load(os.path.join(DATA, 'B2_post.npz'))


def proj3(X, Y, Z):
    p = P @ np.array([X, Y, Z, 1.0]); return p[0] / p[2], p[1] / p[2]


def ruler(name, sc, items, dx=0.0, dz=0.0, hw=210, up=420, dn=100):
    out = []
    for it in items:
        s, f = it.split(':')[:2]; f = int(f)
        ex = it.split(':')[2:]
        x = d[s + '_x'][f]; z = d[s + '_z'][f]
        if len(ex) == 2: x = float(ex[0]); z = float(ex[1])
        u0, v0 = proj3(x, 0, z)
        cx0 = int(np.clip(u0 - hw, 0, W - 2 * hw)); cy0 = int(np.clip(v0 - up, 0, H - (up + dn)))
        a = grab(f, 1, crop=(cx0, cy0, 2 * hw, up + dn), scale=None)[0][1]
        im = Image.fromarray(a).resize((int(2 * hw * sc), int((up + dn) * sc)), Image.LANCZOS); dr = ImageDraw.Draw(im)
        for k in range(0, 12):
            Y = k * 0.25; u, v = proj3(x, Y, z); u = (u - cx0) * sc; v = (v - cy0) * sc
            L = 60 if k % 2 == 0 else 30
            dr.line([u - L, v, u + L, v], fill=(255, 255, 0) if k % 4 else (255, 60, 60), width=1)
            if k % 2 == 0: dr.text((u + L + 3, v - 6), '%.1f' % Y, fill=(255, 255, 0))
        # 横向 1 m 比例尺(沿 X，脚下深度)
        ua, va = proj3(x - 0.5, 0, z); ub, vb = proj3(x + 0.5, 0, z)
        dr.line([(ua - cx0) * sc, (va - cy0) * sc + 12, (ub - cx0) * sc, (vb - cy0) * sc + 12], fill=(0, 255, 0), width=2)
        dr.text((4, 4), '%s f%d x%.2f z%.2f' % (s, f, x, z), fill=(255, 255, 255))
        out.append((f, np.asarray(im)))
    p = os.path.join(FR, name + '.jpg'); sheet(out, min(len(out), 6), p, fsz=14, quality=90); return p


if __name__ == '__main__':
    print(ruler(sys.argv[1], float(sys.argv[2]), sys.argv[3:]))
