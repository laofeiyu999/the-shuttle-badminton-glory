# -*- coding: utf-8 -*-
"""对回放逐帧球位置做弹道拟合。
模型: 二次阻力 a = -k|v|v + (0,-g)，k=0.24 1/m，g=5 m/s^2（curveconstant 1000 组）。
步骤: 1) 只用形状 y(s) 拟合 (v0, theta)；2) 求每帧的模型时间 tau_i，看 tau 对真实时间 t 的关系（时间扭曲）。
用法: python D_traj_fit.py <curveId> [最多条数] [k] [g]
"""
import json, math, sys
import numpy as np
from scipy.optimize import least_squares
cid = int(sys.argv[1]); nmax = int(sys.argv[2]) if len(sys.argv) > 2 else 6
K = float(sys.argv[3]) if len(sys.argv) > 3 else 0.24
G = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
T = json.load(open('.ua/replica/data/D_tmp/traj.json'))
def sim(v0, th, k=K, g=G, dt=0.0005, tmax=6.0):
    vx = v0*math.cos(th); vy = v0*math.sin(th); x = y = 0.0
    xs=[0.0]; ys=[0.0]; ts=[0.0]; t=0.0
    while t < tmax and y > -4.0:
        v = math.hypot(vx, vy)
        ax = -k*v*vx; ay = -k*v*vy - g
        vx += ax*dt; vy += ay*dt; x += vx*dt; y += vy*dt; t += dt
        xs.append(x); ys.append(y); ts.append(t)
    return np.array(ts), np.array(xs), np.array(ys)
cnt = 0
for tr in T:
    if tr['curve'] != cid or len(tr['pts']) < 8: continue
    if not tr['landed'] and len(tr['pts']) < 12: continue
    s0 = np.array(tr['start']); P = np.array(tr['pts'])
    fr = P[:,0]; s = np.hypot(P[:,1]-s0[0], P[:,3]-s0[2])/100.0; y = (P[:,2]-s0[1])/100.0
    if tr['landed']: s = s[:-1]; y = y[:-1]; fr = fr[:-1]
    def res(p, full=False):
        v0, th = p
        ts, xs, ys = sim(abs(v0), th)
        if xs[-1] < s[-1]:
            return np.full(len(s), 5.0)
        yy = np.interp(s, xs, ys)
        return yy - y
    best = None
    for v0g in (15, 30, 60, 100):
        for thg in (0.0, 0.3, 0.8):
            try:
                r = least_squares(res, [v0g, thg], bounds=([3, -1.2], [400, 1.5]))
            except Exception as e:
                continue
            if best is None or r.cost < best.cost: best = r
    v0, th = best.x
    ts, xs, ys = sim(v0, th)
    tau = np.interp(s, xs, ts)
    rms = math.sqrt(np.mean(best.fun**2))*100
    t = (fr - (tr['startFrame'] if tr['startFrame'] else tr['hitFrame']))*0.04
    print('--- rep %s hit %d start %s curve %d mul %s E %s  y0=%.0fcm  dist=%.0fcm  n=%d landed=%s' % (
        tr['rep'], tr['hitFrame'], tr['startFrame'], cid, tr['mul'], tr['energyPre'], s0[1],
        math.hypot(tr['drop'][0]-s0[0], tr['drop'][2]-s0[2]), len(P), tr['landed']))
    print('   fit v0=%.1f m/s theta=%.1f deg  shape rms=%.1f cm  apex=+%.0fcm' % (v0, math.degrees(th), rms, max(0, y.max())*100))
    print('   t(s)   :', ' '.join('%.2f' % v for v in t))
    print('   tau(s) :', ' '.join('%.2f' % v for v in tau))
    d = np.diff(tau)/np.diff(t)
    print('   dtau/dt:', ' '.join('%.2f' % v for v in d))
    cnt += 1
    if cnt >= nmax: break
