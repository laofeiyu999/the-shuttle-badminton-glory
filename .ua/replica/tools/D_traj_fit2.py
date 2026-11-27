# -*- coding: utf-8 -*-
"""回放逐帧球位置 -> NORMAL 族弹道参数与时间扭曲律。
模型: a = -k|v|v + (0,-g), k=0.24 1/m, g=5 m/s^2 (text/curveconstant.txt 1000 组)。
对每条轨迹: 只用形状 y(s) 拟合 (v0, theta) -> 每帧模型时间 tau -> seg = timeGap*dt/dtau*mul。
输出: .ua/replica/data/D_tmp/fit_normal.json
用法: python D_traj_fit2.py [curveId ...]
"""
import json, math, sys
import numpy as np
from scipy.optimize import least_squares
K, G, GAP = 0.24, 5.0, 0.016
T = json.load(open('.ua/replica/data/D_tmp/traj.json'))
want = set(int(a) for a in sys.argv[1:])
def sim(v0, th, ymin, dt=0.002, tmax=8.0):
    vx = v0*math.cos(th); vy = v0*math.sin(th); x = y = 0.0
    xs=[0.0]; ys=[0.0]; t=0.0
    while t < tmax and y > ymin - 0.5:
        v = math.hypot(vx, vy)
        ax = -K*v*vx; ay = -K*v*vy - G
        # 中点法
        vxm = vx + ax*dt*0.5; vym = vy + ay*dt*0.5
        vm = math.hypot(vxm, vym)
        vx += -K*vm*vxm*dt; vy += (-K*vm*vym - G)*dt
        x += vxm*dt; y += vym*dt; t += dt
        xs.append(x); ys.append(y)
    return np.arange(len(xs))*dt, np.array(xs), np.array(ys)
res_all = []
import collections as _c
NPER = 24
_g = _c.defaultdict(list)
for tr in T:
    if tr['curve'] < 2000 and len(tr['pts']) >= 9: _g[tr['curve']].append(tr)
SEL = []
for c, L in _g.items():
    L.sort(key=lambda t: (-(1 if t['landed'] else 0), -len(t['pts'])))
    SEL += L[:NPER]
for tr in SEL:
    c = tr['curve']
    if c >= 2000 or (want and c not in want): continue
    if len(tr['pts']) < 9: continue
    s0 = np.array(tr['start']); P = np.array(tr['pts'])
    if tr['landed']: P = P[:-1]
    fr = P[:,0]; s = np.hypot(P[:,1]-s0[0], P[:,3]-s0[2])/100.0; y = (P[:,2]-s0[1])/100.0
    if np.any(np.diff(s) <= 0): continue
    y0 = s0[1]/100.0
    def res(p):
        ts, xs, ys = sim(p[0], p[1], -y0)
        if xs[-1] < s[-1]: return np.full(len(s), 3.0) + (s[-1]-xs[-1])
        return np.interp(s, xs, ys) - y
    best = None
    for v0g in (20, 60):
        for thg in (0.1, 0.7):
            r = least_squares(res, [v0g, thg], bounds=([2, -1.0], [200, 1.5]), x_scale=[10, 0.2])
            if best is None or r.cost < best.cost: best = r
    v0, th = best.x
    rms = math.sqrt(np.mean(best.fun**2))*100
    ts, xs, ys = sim(v0, th, -y0)
    tau = np.interp(s, xs, ts)
    # 落地模型时间
    idx = np.where(ys <= -y0)[0]
    tauT = ts[idx[0]] if len(idx) else None
    sT = xs[idx[0]] if len(idx) else None
    dist = math.hypot(tr['drop'][0]-s0[0], tr['drop'][2]-s0[2])/100.0
    apex = float(ys.max())
    sf = tr['startFrame'] if tr['startFrame'] else tr['hitFrame']-1
    res_all.append(dict(rep=tr['rep'], hit=tr['hitFrame'], sf=sf, curve=c, mul=tr['mul'], E=tr['energyPre'], y0=y0,
                        dist=dist, v0=float(v0), th=math.degrees(th), rms=rms, tauT=tauT, sT=sT, apex=apex,
                        landed=tr['landed'], fr=[int(f-sf) for f in fr], tau=[round(float(v),4) for v in tau],
                        serve=tr['serve'], action=tr['action'], startz=s0[2], dropz=tr['drop'][2]))
json.dump(res_all, open('.ua/replica/data/D_tmp/fit_normal.json', 'w'))
import collections
by = collections.defaultdict(list)
for r in res_all:
    if r['rms'] < 1.5: by[r['curve']].append(r)
print('curve n  theta(deg) med[min,max]   v0 med[min,max] m/s   apex-rise med cm   y0 med cm  dist med m  tauT med s')
for c in sorted(by):
    L = by[c]; th = [r['th'] for r in L]; v = [r['v0'] for r in L]
    print('%d %3d  %5.1f [%5.1f,%5.1f]   %5.1f [%5.1f,%5.1f]   %5.0f   %4.0f  %5.2f  %s  bad=%d' % (c, len(L), np.median(th), min(th), max(th),
          np.median(v), min(v), max(v), np.median([r['apex'] for r in L])*100, np.median([r['y0'] for r in L])*100,
          np.median([r['dist'] for r in L]), '%.2f' % np.median([r['tauT'] for r in L if r['tauT']]),
          sum(1 for r in res_all if r['curve']==c and r['rms']>=1.5)))
