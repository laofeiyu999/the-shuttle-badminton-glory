# -*- coding: utf-8 -*-
"""标定第二步：把场地内部尺寸当自由参数拟合（底线 6.70 m 定尺度），看飞羽场地线的真实比例"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
from scipy.optimize import least_squares
d = np.load(os.path.join(DATA, "B2_calib_H.npz"))
src0, dst = d["src"], d["dst"]
def homog(src, dst):
    A = []
    for (X, Z), (u, v) in zip(src, dst):
        A.append([X, Z, 1, 0, 0, 0, -u * X, -u * Z, -u]); A.append([0, 0, 0, X, Z, 1, -v * X, -v * Z, -v])
    _, _, vt = np.linalg.svd(np.array(A)); Hm = vt[-1].reshape(3, 3); return Hm / Hm[2, 2]
def proj(Hm, s):
    p = (Hm @ np.c_[s, np.ones(len(s))].T).T; return p[:, :2] / p[:, 2:3]
def build(p):
    Ls, S, Wd, Ws = p
    s = src0.copy()
    ax = np.abs(src0[:, 0]); sg = np.sign(src0[:, 0])
    s[np.isclose(ax, 5.94), 0] = sg[np.isclose(ax, 5.94)] * Ls
    s[np.isclose(ax, 1.98), 0] = sg[np.isclose(ax, 1.98)] * S
    az = np.abs(src0[:, 1]); sz = np.sign(src0[:, 1])
    s[np.isclose(az, 3.05), 1] = sz[np.isclose(az, 3.05)] * Wd
    s[np.isclose(az, 2.59), 1] = sz[np.isclose(az, 2.59)] * Ws
    return s
def res(p):
    s = build(p); Hm = homog(s, dst); return (proj(Hm, s) - dst).ravel()
for name, free in [("all free", [0, 1, 2, 3]), ("only S free", [1]), ("S & widths", [1, 2, 3])]:
    p0 = np.array([5.94, 1.98, 3.05, 2.59])
    def f(q):
        p = p0.copy(); p[free] = q; return res(p)
    r = least_squares(f, p0[free])
    p = p0.copy(); p[free] = r.x
    e = res(p).reshape(-1, 2)
    print(name, "Ls=%.3f S=%.3f Wd=%.3f Ws=%.3f  rms=%.2f px max=%.2f" % (*p, np.sqrt((e ** 2).sum(1).mean()), np.abs(e).max()))
