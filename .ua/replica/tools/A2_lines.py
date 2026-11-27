# -*- coding: utf-8 -*-
"""A2_lines.py f [f2 ...]：颜色门控脊点 + Hough，打印直线表（斜线给出 dx/dy 与在 y=0/880 的 x；横线给出 y@x=961）。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A2_auto import gated_mask
from A2_hough import hough_lines
from A2_cam import get_frame
import numpy as np
def detect(f, rgb=None, **kw):
    rgb = get_frame(f) if rgb is None else rgb
    mk, _ = gated_mask(rgb)
    ys, xs = np.nonzero(mk)
    return hough_lines(xs.astype(np.float32), ys.astype(np.float32), **kw), mk
if __name__ == '__main__':
    for a in sys.argv[1:]:
        f = int(a); L, mk = detect(f)
        print('== f%d t=%.2f pts %d lines %d' % (f, f / 60., mk.sum(), len(L)))
        hz = sorted([l for l in L if abs(l['theta'] - 90) < 20], key=lambda l: l['rho'])
        ob = sorted([l for l in L if abs(l['theta'] - 90) >= 20], key=lambda l: (l['rho'] - 880 * l['n'][1]) / l['n'][0])
        for l in hz:
            n, r = l['n'], l['rho']
            print(' H th %6.2f y@961 %6.1f n %4d cov %4.0f x[%5.0f..%5.0f]' % (l['theta'], (r - 961 * n[0]) / n[1], l['npts'], l['cov'], min(l['p0'][0], l['p1'][0]), max(l['p0'][0], l['p1'][0])))
        for l in ob:
            n, r = l['n'], l['rho']
            print(' O th %6.2f dx/dy %7.4f x@y0 %7.1f x@y880 %7.1f n %4d cov %4.0f y[%4.0f..%4.0f]' % (l['theta'], -n[1] / n[0], r / n[0], (r - 880 * n[1]) / n[0], l['npts'], l['cov'], min(l['p0'][1], l['p1'][1]), max(l['p0'][1], l['p1'][1])))
