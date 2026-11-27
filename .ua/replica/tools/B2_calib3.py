# -*- coding: utf-8 -*-
"""标定第三步：固定 L=6.70, Ls=5.94, Wd=3.05；S、Ws 自由 → 最终 H；分解相机 K[R|t]（主点取画面中心，方像素）"""
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
def build(S, Ws):
    s = src0.copy()
    ax = np.abs(src0[:, 0]); sg = np.sign(src0[:, 0]); m = np.isclose(ax, 1.98); s[m, 0] = sg[m] * S
    az = np.abs(src0[:, 1]); sz = np.sign(src0[:, 1]); m = np.isclose(az, 2.59); s[m, 1] = sz[m] * Ws
    return s
r = least_squares(lambda q: (proj(homog(build(*q), dst), build(*q)) - dst).ravel(), [1.98, 2.59])
S, Ws = r.x
src = build(S, Ws); Hm = homog(src, dst); e = proj(Hm, src) - dst
print("S=%.3f m  Ws=%.3f m  rms=%.2f px max=%.2f px" % (S, Ws, np.sqrt((e ** 2).sum(1).mean()), np.abs(e).max()))
# 不确定度：S 对 rms 的敏感度
for S2 in [2.05, 2.10, 2.155, 2.20, 2.25]:
    s2 = build(S2, Ws); e2 = proj(homog(s2, dst), s2) - dst; print("  S=%.3f rms=%.2f" % (S2, np.sqrt((e2 ** 2).sum(1).mean())))
for W2 in [2.50, 2.55, 2.59, 2.60, 2.65]:
    s2 = build(S, W2); e2 = proj(homog(s2, dst), s2) - dst; print("  Ws=%.3f rms=%.2f" % (W2, np.sqrt((e2 ** 2).sum(1).mean())))
# 相机分解
cx, cy = W / 2, H / 2
h1, h2, h3 = Hm[:, 0], Hm[:, 1], Hm[:, 2]
def w(f): return np.diag([1 / f ** 2, 1 / f ** 2, 1.0])
T = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1.0]])
g1, g2, g3 = T @ h1, T @ h2, T @ h3
# 约束1: g1·ω·g2 = 0 → (g1x g2x + g1y g2y)/f² + g1z g2z = 0
f_a = np.sqrt(-(g1[0] * g2[0] + g1[1] * g2[1]) / (g1[2] * g2[2])) if (g1[2] * g2[2]) != 0 and -(g1[0] * g2[0] + g1[1] * g2[1]) / (g1[2] * g2[2]) > 0 else float('nan')
# 约束2: |g1|ω = |g2|ω
num = (g1[0] ** 2 + g1[1] ** 2) - (g2[0] ** 2 + g2[1] ** 2); den = g2[2] ** 2 - g1[2] ** 2
f_b = np.sqrt(num / den) if num / den > 0 else float('nan')
print("f from orthogonality: %.1f px ; from equal-norm: %.1f px" % (f_a, f_b))
def decomp(f):
    K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1.0]]); Ki = np.linalg.inv(K)
    a, b, c = Ki @ h1, Ki @ h2, Ki @ h3
    lam = 2.0 / (np.linalg.norm(a) + np.linalg.norm(b))
    r1 = a * lam; r2 = b * lam; t = c * lam
    if t[2] < 0: r1, r2, t = -r1, -r2, -t
    # X=r1(场地长轴), Z=r2(场地宽轴,向远侧), Y(向上) 使得上方在图像中 v 更小
    r3 = np.cross(r1, r2)
    R = np.stack([r1, r3, r2], 1)   # 列顺序对应世界 (X, Y, Z)
    # 让 Y 朝上：世界点 (0,1,0) 投影应该 v 变小
    P = K @ np.c_[R, t]
    p0 = P @ np.array([0, 0, 0, 1.0]); p1 = P @ np.array([0, 1, 0, 1.0])
    if p1[1] / p1[2] > p0[1] / p0[2]:
        R[:, 1] *= -1; P = K @ np.c_[R, t]
    # 正交化
    U, _, Vt = np.linalg.svd(R); Ro = U @ Vt
    if np.linalg.det(Ro) < 0: pass
    C = -Ro.T @ t
    return K, Ro, t, K @ np.c_[Ro, t], C, np.linalg.norm(a) / np.linalg.norm(b)
for f in [f_a, f_b]:
    if not np.isfinite(f): continue
    K, R, t, P, C, ratio = decomp(f)
    g = src; pr = (P @ np.c_[g[:, 0], np.zeros(len(g)), g[:, 1], np.ones(len(g))].T).T; pr = pr[:, :2] / pr[:, 2:3]
    ee = pr - dst
    print("f=%.1f  cam pos (X,Y,Z)=(%.2f, %.2f, %.2f) m  |r1|/|r2|=%.4f  reproj rms %.2f px  det=%.3f" % (f, *C, ratio, np.sqrt((ee ** 2).sum(1).mean()), np.linalg.det(R)))
    fov_v = 2 * np.degrees(np.arctan(H / 2 / f)); fov_h = 2 * np.degrees(np.arctan(W / 2 / f))
    fwd = R[2]; print("   vfov %.1f° hfov %.1f°  forward(world XYZ)=%s  pitch down %.1f°" % (fov_v, fov_h, np.round(fwd, 3), np.degrees(np.arcsin(-fwd[1]))))
    # 网柱 1.55 m 的预测像素
    for (X, Z) in [(0, 3.05), (0, -3.05), (0, 0)]:
        for Y in [0, 1.524, 1.55]:
            q = P @ np.array([X, Y, Z, 1.0]); print("   (X=%.1f,Y=%.3f,Z=%.2f) → px (%.1f, %.1f)" % (X, Y, Z, q[0] / q[2], q[1] / q[2]))
    np.savez(os.path.join(DATA, "B2_calib.npz"), H=Hm, P=P, K=K, R=R, t=t, C=C, S=S, Ws=Ws)
