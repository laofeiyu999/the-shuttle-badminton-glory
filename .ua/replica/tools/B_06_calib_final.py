# 标定定稿：固定半场长 6.70、双打后发球线 5.94、双打半宽 3.05；前发球线 F、单打半宽 S 自由。保存 calib.json
import numpy as np, sys, json
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from B_04_calib import world, rot, project, J
from scipy.optimize import least_squares
pts = J['pts']
px = np.array([t['px'] for t in pts]); w = np.array([1.0 if t['inframe'] else 0.3 for t in pts])
def res(q, fixf=None):
    p = np.array(q[:7], float)
    if fixf: p[0] = fixf
    mp = world((6.70, 5.94, q[7], 3.05, q[8]))
    Xw = np.array([[mp[t['X']], mp[t['Y']], 0.0] for t in pts])
    return ((project(p, Xw) - px) * w[:, None]).ravel()
out = {}
for name, fixf in (('free', None), ('vfov60', 720 / np.tan(np.radians(30)))):
    r = least_squares(res, [1500, 0, -12, 4.5, 0, 0.3, 0, 1.98, 2.59], x_scale=[100, 1, 1, 1, .01, .01, .01, .1, .1], kwargs=dict(fixf=fixf))
    p = r.x[:7].copy()
    if fixf: p[0] = fixf
    e = r.fun.reshape(-1, 2) / w[:, None]
    inf = np.array([t['inframe'] for t in pts])
    # 参数不确定度（按残差的协方差）
    JT = r.jac; dof = max(1, len(r.fun) - len(r.x)); s2 = (r.fun ** 2).sum() / dof
    try: cov = np.linalg.inv(JT.T @ JT) * s2; sd = np.sqrt(np.diag(cov))
    except Exception: sd = np.full(9, np.nan)
    print(name, 'f=%.1f C=(%.3f,%.3f,%.3f) yaw=%.3f pitch=%.3f roll=%.3f F=%.3f S=%.3f' % (p[0], p[1], p[2], p[3], *np.degrees(p[4:7]), r.x[7], r.x[8]))
    print('   rms_in=%.2f rms_all=%.2f max=%.2f n=%d (in %d)' % (np.sqrt((e[inf] ** 2).sum(1).mean()), np.sqrt((e ** 2).sum(1).mean()), np.abs(e).max(), len(pts), inf.sum()))
    print('   sd:', np.round(sd, 4))
    out[name] = dict(p=p.tolist(), F=float(r.x[7]), S=float(r.x[8]), rms_in=float(np.sqrt((e[inf] ** 2).sum(1).mean())), sd=sd.tolist())
json.dump(out, open(CACHE + '/calib.json', 'w'), indent=1)
