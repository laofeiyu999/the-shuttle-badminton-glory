# -*- coding: utf-8 -*-
"""场地线拟合 → 单应 H（地面米 → 像素）→ 相机分解（焦距、位姿）→ 保存 B2_calib.npz
场地坐标：X 沿球场长轴（网=0，左半场为负，右半场为正），Z 沿宽（远边线 +3.05，近边线 -3.05），Y 向上。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
med = np.load(os.path.join(DATA, "B2_bg_median.npy")).astype(np.float32)
white = (med.min(axis=2) > 185) & ((med.max(axis=2) - med.min(axis=2)) < 60)
ys, xs = np.nonzero(white)
pts = np.stack([xs, ys], 1).astype(np.float64)
# 线的初值（像素两点）与场地方程
L = 6.70; LS = 5.94; SS = 1.98; WD = 3.05; WS = 2.59
lines = {
 # name: (p0, p1, ('z', val) or ('x', val), 有效范围过滤)
 "far_dbl":  ((300, 797), (1620, 797), ('z', +WD)),
 "far_sgl":  ((300, 813), (1620, 813), ('z', +WS)),
 "ctr_L":    ((100, 935), (660, 935), ('z', 0.0)),
 "ctr_R":    ((1260, 935), (1820, 935), ('z', 0.0)),
 "near_sgl": ((250, 1141), (900, 1141), ('z', -WS)),
 "near_sglR":((1000, 1141), (1900, 1141), ('z', -WS)),
 "near_dbl": ((250, 1197), (900, 1197), ('z', -WD)),
 "near_dblR":((1020, 1197), (1900, 1197), ('z', -WD)),
 "base_L":   ((280, 800), (10, 988), ('x', -L)),
 "long_L":   ((350, 800), (10, 1067), ('x', -LS)),
 "short_L":  ((738, 800), (557, 1190), ('x', -SS)),
 "short_R":  ((1182, 800), (1363, 1190), ('x', +SS)),
 "long_R":   ((1565, 800), (1910, 1067), ('x', +LS)),
 "base_R":   ((1638, 800), (1910, 988), ('x', +L)),
}
def fit(p0, p1, tol=6, it=4):
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    for k in range(it):
        d = p1 - p0; ln = np.linalg.norm(d); d /= ln; n = np.array([-d[1], d[0]])
        r = pts - p0
        t = r @ d; dist = r @ n
        m = (np.abs(dist) < (tol if k == 0 else 3.5)) & (t > 0.0) & (t < ln)
        P = pts[m]
        c = P.mean(0); u, s, vt = np.linalg.svd(P - c, full_matrices=False)
        d2 = vt[0]
        if d2 @ d < 0: d2 = -d2
        tt = (P - c) @ d2
        # 保持端点范围
        t0 = (p0 - c) @ d2; t1 = (p1 - c) @ d2
        p0 = c + d2 * t0; p1 = c + d2 * t1
    n = np.array([-d2[1], d2[0]])
    res = np.abs((P - c) @ n)
    # 齐次线 a x + b y + c = 0
    l = np.array([n[0], n[1], -n @ c])
    return l, len(P), res.mean(), s[1] / np.sqrt(len(P))
fits = {}
for k, (p0, p1, eq) in lines.items():
    l, n, r, w = fit(p0, p1)
    fits[k] = (l, eq)
    print("%-10s n=%5d  meanres=%.2f px  halfwidth_rms=%.2f  line=%s" % (k, n, r, w, np.round(l, 5)))
# 合并同一方程的线（近边线左右段先分别保留，看是否共线）
def inter(l1, l2):
    p = np.cross(l1, l2); return p[:2] / p[2]
zl = {k: v for k, v in fits.items() if v[1][0] == 'z'}
xl = {k: v for k, v in fits.items() if v[1][0] == 'x'}
src = []; dst = []; names = []
for kz, (lz, ez) in zl.items():
    for kx, (lx, ex) in xl.items():
        # 中线只在发球线到底线之间；左段配左侧竖线
        if kz.startswith("ctr_L") and ex[1] > 0: continue
        if kz.startswith("ctr_R") and ex[1] < 0: continue
        if kz in ("near_sgl", "near_dbl") and ex[1] > 0: continue
        if kz in ("near_sglR", "near_dblR") and ex[1] < 0: continue
        p = inter(lz, lx)
        src.append([ex[1], ez[1]]); dst.append(p); names.append(kz + "×" + kx)
src = np.array(src); dst = np.array(dst)
def homog(src, dst):
    A = []
    for (X, Z), (u, v) in zip(src, dst):
        A.append([X, Z, 1, 0, 0, 0, -u * X, -u * Z, -u])
        A.append([0, 0, 0, X, Z, 1, -v * X, -v * Z, -v])
    A = np.array(A)
    # 归一化
    _, _, vt = np.linalg.svd(A)
    Hm = vt[-1].reshape(3, 3)
    return Hm / Hm[2, 2]
def proj(Hm, s):
    p = (Hm @ np.c_[s, np.ones(len(s))].T).T
    return p[:, :2] / p[:, 2:3]
Hm = homog(src, dst)
err = proj(Hm, src) - dst
print("points", len(src), "reproj rms %.2f px  max %.2f" % (np.sqrt((err ** 2).sum(1).mean()), np.abs(err).max()))
for n_, s_, d_, e_ in zip(names, src, dst, err):
    print("  %-22s court(%.2f,%.2f) px(%.1f,%.1f) err(%.1f,%.1f)" % (n_, s_[0], s_[1], d_[0], d_[1], e_[0], e_[1]))
# 备选尺寸测试：前发球线 1.9、单打宽 5.2
for SS2, WS2 in [(1.98, 2.59), (1.90, 2.59), (1.98, 2.60), (1.90, 2.60), (2.0, 2.6)]:
    s2 = src.copy()
    s2[np.isclose(np.abs(src[:, 0]), SS), 0] = np.sign(src[np.isclose(np.abs(src[:, 0]), SS), 0]) * SS2
    s2[np.isclose(np.abs(src[:, 1]), WS), 1] = np.sign(src[np.isclose(np.abs(src[:, 1]), WS), 1]) * WS2
    H2 = homog(s2, dst); e2 = proj(H2, s2) - dst
    print("alt short=%.2f sgl_half=%.2f  rms %.2f px" % (SS2, WS2, np.sqrt((e2 ** 2).sum(1).mean())))
np.savez(os.path.join(DATA, "B2_calib_H.npz"), H=Hm, src=src, dst=dst)
