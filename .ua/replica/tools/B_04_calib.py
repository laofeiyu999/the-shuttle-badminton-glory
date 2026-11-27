# 针孔相机标定：用球场线交点（地面 Z=0）拟合 f、相机位置、朝向；网柱顶作为高度自检/联合约束
import numpy as np, sys, json
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from scipy.optimize import least_squares
J = json.load(open(CACHE + '/lines.json'))
def world(dims):
    B, D, F, Wd, S = dims
    mp = {'-B': -B, '+B': B, '-D': -D, '+D': D, '-F': -F, '+F': F, '+W': Wd, '-W': -Wd, '+S': S, '-S': -S, '0': 0.0}
    return mp
def rot(a):
    # yaw(绕Z) pitch(俯) roll
    yaw, pitch, roll = a
    cy, sy = np.cos(yaw), np.sin(yaw); cp, sp = np.cos(pitch), np.sin(pitch); cr, sr = np.cos(roll), np.sin(roll)
    # 相机基：先定义朝向 forward（水平面内 yaw，从 -Y 看向 +Y 为 yaw=0），俯角 pitch 向下为正
    fwd = np.array([sy * cp, cy * cp, -sp])
    right = np.array([cy, -sy, 0.0])
    down = np.cross(fwd, right)
    R0 = np.stack([right, down, fwd])          # world->cam (x右 y下 z前)
    Rr = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Rr @ R0
def project(p, Xw, cx=960.0, cy=720.0):
    f = p[0]; C = p[1:4]; R = rot(p[4:7])
    if len(p) > 7: cx, cy = p[7], p[8]
    Xc = (Xw - C) @ R.T
    return np.stack([f * Xc[:, 0] / Xc[:, 2] + cx, f * Xc[:, 1] / Xc[:, 2] + cy], 1)
def run(dims, use_all=True, free_pp=False, verbose=False):
    mp = world(dims)
    pts = [q for q in J['pts'] if (use_all or q['inframe'])]
    Xw = np.array([[mp[q['X']], mp[q['Y']], 0.0] for q in pts]); px = np.array([q['px'] for q in pts])
    w = np.array([1.0 if q['inframe'] else 0.3 for q in pts])
    def res(p):
        return ((project(p, Xw) - px) * w[:, None]).ravel()
    p0 = [1500, 0, -12, 4.5, 0, 0.3, 0] + ([960, 720] if free_pp else [])
    r = least_squares(res, p0, x_scale=[100, 1, 1, 1, .01, .01, .01] + ([10, 10] if free_pp else []))
    e = (project(r.x, Xw) - px)
    inf = np.array([q['inframe'] for q in pts])
    rms_in = np.sqrt((e[inf] ** 2).sum(1).mean()); rms_all = np.sqrt((e ** 2).sum(1).mean())
    if verbose:
        for q, ee in zip(pts, e): print(f"  {q['name']:16s} {q['X']:>3s} {q['Y']:>3s} err=({ee[0]:+.2f},{ee[1]:+.2f}) {'in' if q['inframe'] else 'out'}")
    return r.x, rms_in, rms_all, e.max()
cands = {
 'std(6.70,5.94,1.98,3.05,2.59)': (6.70, 5.94, 1.98, 3.05, 2.59),
 'fy(6.70,5.94,1.90,3.05,2.60)': (6.70, 5.94, 1.90, 3.05, 2.60),
 'fy2(6.70,5.94,1.90,3.05,2.59)': (6.70, 5.94, 1.90, 3.05, 2.59),
 'std_F1.98_S2.60': (6.70, 5.94, 1.98, 3.05, 2.60),
}
for k, d in cands.items():
    for fp in (False, True):
        p, ri, ra, mx = run(d, free_pp=fp)
        print(f'{k:32s} freePP={fp} rms_in={ri:.2f}px rms_all={ra:.2f}px f={p[0]:.1f} C=({p[1]:.3f},{p[2]:.3f},{p[3]:.3f}) yaw={np.degrees(p[4]):.3f} pitch={np.degrees(p[5]):.3f} roll={np.degrees(p[6]):.3f}', p[7:] if fp else '')
# 让尺寸自由：固定 B=6.7, Wd=3.05，自由 D,F,S
pts = J['pts']
def res_free(q):
    p = q[:7]; D, F, S = q[7:10]
    mp = world((6.70, D, F, 3.05, S))
    Xw = np.array([[mp[t['X']], mp[t['Y']], 0.0] for t in pts]); px = np.array([t['px'] for t in pts])
    w = np.array([1.0 if t['inframe'] else 0.3 for t in pts])
    return ((project(p, Xw) - px) * w[:, None]).ravel()
r = least_squares(res_free, [1500, 0, -12, 4.5, 0, 0.3, 0, 5.94, 1.95, 2.6], x_scale=[100, 1, 1, 1, .01, .01, .01, .1, .1, .1])
print('free dims: D,F,S =', r.x[7:].round(3), 'f', r.x[0].round(1), 'C', r.x[1:4].round(3), 'rms', np.sqrt((r.fun ** 2).mean() * 2).round(2))
