# -*- coding: utf-8 -*-
"""A2_kf2.py：用部分对应求解后，打印各模型线在屏幕上的预测位置，辅助确认其余对应与球场尺寸。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A2_kf import *
def predict(p, d):
    segs = segments(d)
    for nm, (a, b) in segs.items():
        a = np.array(a, float); b = np.array(b, float)
        uv, dep = project(p, np.array([a, b, (a + b) / 2]))
        if nm.startswith(('base', 'long', 'short', 'net')):
            # y at x=961
            t = np.linspace(0, 1, 201)[:, None]; q, _ = project(p, a + (b - a) * t)
            k = np.nanargmin(np.abs(q[:, 0] - 961)); print('   %-11s y@961 %7.1f  ends x %.0f..%.0f' % (nm, q[k, 1], uv[0, 0], uv[1, 0]))
        else:
            t = np.linspace(0, 1, 801)[:, None]; q, dd = project(p, a + (b - a) * t)
            ok = np.isfinite(q[:, 1]); k = np.nanargmin(np.abs(q[:, 1] - 880) + np.where(ok, 0, 1e9))
            k2 = min(k + 40, 800) if k < 760 else k - 40
            print('   %-11s x@y880 %7.1f dx/dy %.4f' % (nm, q[k, 0] + (880 - q[k, 1]) * (q[k2, 0] - q[k, 0]) / (q[k2, 1] - q[k, 1]), (q[k2, 0] - q[k, 0]) / (q[k2, 1] - q[k, 1])))
if __name__ == '__main__':
    f = 840
    a = dict(short_near=17, short_far=14, net_top=12, sideD_L=31, sideS_L=32, centre_near=37, sideS_R=38, sideD_R=39)
    p, d, per, tot = solve(f, a, [0, 7, 16, 25, 0, 35])
    predict(p, d)
    p, d, per, tot = solve(f, a, [0, 7, 16, 25, 0, 35], free_dim=('z_short', 'half_ws', 'net_h'))
    predict(p, d)
