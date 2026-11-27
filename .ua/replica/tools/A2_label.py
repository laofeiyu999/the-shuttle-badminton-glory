# -*- coding: utf-8 -*-
"""A2_label.py f：Hough 直线编号叠加图 A2_L_<f>.jpg（宽 1600），并把直线存 data/A2_lines/<f>.npy（n0,n1,rho,x0,y0,x1,y1,npts）。
打印表：H 行 = 近水平线（按 y 排序），O 行 = 斜线（按 y=880 处 x 排序）。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A2_lines import detect
from A_common import *
import numpy as np
os.makedirs(os.path.join(DATA, 'A2_lines'), exist_ok=True)
def run(f, show=True):
    rgb = get_frame(f)
    L, mk = detect(f, rgb, nmax=34, min_votes=40)
    hz = sorted([l for l in L if abs(l['theta'] - 90) < 20], key=lambda l: (l['rho'] - 961 * l['n'][0]) / l['n'][1])
    ob = sorted([l for l in L if abs(l['theta'] - 90) >= 20], key=lambda l: (l['rho'] - 880 * l['n'][1]) / l['n'][0])
    L = hz + ob
    arr = np.array([[l['n'][0], l['n'][1], l['rho'], l['p0'][0], l['p0'][1], l['p1'][0], l['p1'][1], l['npts']] for l in L])
    np.save(os.path.join(DATA, 'A2_lines', '%05d.npy' % f), arr)
    im = Image.fromarray((rgb * 0.6).astype(np.uint8)); d = ImageDraw.Draw(im); ft = font(22)
    cols = [(255, 60, 60), (255, 255, 0), (0, 255, 0), (255, 0, 255), (0, 255, 255), (255, 160, 0)]
    print('== f%d t=%.2f' % (f, f / 60.))
    for i, l in enumerate(L):
        c = cols[i % 6]
        d.line([tuple(l['p0']), tuple(l['p1'])], fill=c, width=2)
        k = 0.25 + 0.5 * ((i * 7) % 10) / 10.0
        m = l['p0'] * (1 - k) + l['p1'] * k
        d.rectangle([m[0] - 2, m[1] - 12, m[0] + 26, m[1] + 12], fill=(0, 0, 0)); d.text((m[0], m[1] - 12), str(i), fill=c, font=ft)
        n, r = l['n'], l['rho']
        if i < len(hz):
            print('%2d H y@961 %6.1f slope %7.4f n %4d x[%5.0f..%5.0f]' % (i, (r - 961 * n[0]) / n[1], -n[0] / n[1], l['npts'], min(l['p0'][0], l['p1'][0]), max(l['p0'][0], l['p1'][0])))
        else:
            print('%2d O dx/dy %7.4f x@y880 %7.1f n %4d y[%4.0f..%4.0f]' % (i, -n[1] / n[0], (r - 880 * n[1]) / n[0], l['npts'], min(l['p0'][1], l['p1'][1]), max(l['p0'][1], l['p1'][1])))
    if show:
        im = im.resize((1600, int(H * 1600 / W)), Image.LANCZOS)
        out = os.path.join(FR, 'A2_L_%05d.jpg' % f); im.save(out, quality=82); print(out)
if __name__ == '__main__':
    for a in sys.argv[1:]: run(int(a))
