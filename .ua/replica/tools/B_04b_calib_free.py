# 自由尺寸标定：固定双打半宽 3.05 m 作为尺度，其余尺寸自由，检验美术球场比例
import numpy as np, sys, json
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from B_04_calib import world, rot, project, J
from scipy.optimize import least_squares
pts = J['pts']
px = np.array([t['px'] for t in pts]); w = np.array([1.0 if t['inframe'] else 0.3 for t in pts])
def mk(free):
    def res(q):
        p = q[:7]; d = dict(B=6.70, D=5.94, F=1.98, Wd=3.05, S=2.59)
        for k, v in zip(free, q[7:]): d[k] = v
        mp = world((d['B'], d['D'], d['F'], d['Wd'], d['S']))
        Xw = np.array([[mp[t['X']], mp[t['Y']], 0.0] for t in pts])
        return ((project(p, Xw) - px) * w[:, None]).ravel()
    return res
for free in (['F'], ['F', 'S'], ['D', 'F', 'S'], ['B', 'D', 'F', 'S'], ['B', 'F'], ['B', 'D', 'F']):
    d0 = dict(B=6.70, D=5.94, F=1.98, S=2.59)
    r = least_squares(mk(free), [1500, 0, -12, 4.5, 0, 0.3, 0] + [d0[k] for k in free], x_scale=[100, 1, 1, 1, .01, .01, .01] + [.1] * len(free))
    e = r.fun.reshape(-1, 2) / w[:, None]
    print(free, dict(zip(free, r.x[7:].round(3))), 'f=%.1f C=(%.3f,%.3f,%.3f) pitch=%.2f' % (r.x[0], r.x[1], r.x[2], r.x[3], np.degrees(r.x[5])), 'rms=%.2f max=%.2f' % (np.sqrt((e ** 2).sum(1).mean()), np.abs(e).max()))
