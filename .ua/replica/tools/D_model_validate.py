# -*- coding: utf-8 -*-
"""NORMAL 族前向模型验证 (回放逐帧球位置 vs 模型)。
模型 [回放拟合]:
  1) 弹道 = 二次阻力抛体 a = -k|v|v - g*ey, k=0.24 1/m, g=5 m/s^2, 模型步长 timeGap=0.016 s;
  2) 出球角 = 5 度量化 (由轨迹形状拟合得到, 这里取拟合值四舍五入到 5 度), v0 由 "落点距离" 反解;
  3) 时间重映射: 第 n 个模型步的真实耗时 seg(n)/speedMul,
       seg = first (ms)            当 tau < (1-lerp/100)*tMin
           = 线性过渡 first->last   当 (1-lerp/100)*tMin <= tau < tMin
           = last (ms)             当 tau >= tMin
     tMin = 模型弹道上速率最小的时刻 (未出现则取落地时刻)。
  4) 位置帧 f 对应曲线时间 (f - StartFrame)*0.04 + t0。
输出每条曲线 ID 的位置误差统计与 t0 分布。
"""
import json, math, sys, collections
import numpy as np
K, G, GAP = 0.24, 5.0, 0.016
R = json.load(open('.ua/replica/data/D_tmp/fit_normal.json'))
T = {(t['rep'], t['hitFrame']): t for t in json.load(open('.ua/replica/data/D_tmp/traj.json'))}
cfg = {c['shapeId']: c for c in json.load(open('References/fyqc/fyqc-client/text/curveshape.txt', encoding='utf-8'))['shapeData']}
def sim(v0, th, ymin, dt=GAP/16):
    vx = v0*math.cos(th); vy = v0*math.sin(th); x = y = 0.0
    xs=[0.0]; ys=[0.0]; vs=[v0]
    while y > ymin and len(xs) < 80000:
        v = math.hypot(vx, vy); ax = -K*v*vx; ay = -K*v*vy - G
        vxm = vx + ax*dt*0.5; vym = vy + ay*dt*0.5; vm = math.hypot(vxm, vym)
        vx += -K*vm*vxm*dt; vy += (-K*vm*vym - G)*dt; x += vxm*dt; y += vym*dt
        xs.append(x); ys.append(y); vs.append(math.hypot(vx, vy))
    return np.arange(len(xs))*dt, np.array(xs), np.array(ys), np.array(vs)
def solve_v(th, y0, dist):
    lo, hi = 0.3, 300.0
    def rng(v):
        ts, xs, ys, vs = sim(v, th, -y0, GAP/4); return xs[-1]
    if rng(hi) < dist: return None
    for _ in range(36):
        m = 0.5*(lo+hi)
        if rng(m) < dist: lo = m
        else: hi = m
    return hi
def real_time(ts, vs, first, lerp, last, mul):
    tmin = ts[int(np.argmin(vs))]
    ts0 = (1 - lerp/100.0)*tmin
    seg = np.where(ts < ts0, first, np.where(ts >= tmin, last, first + (last-first)*(ts-ts0)/max(tmin-ts0, 1e-9)))
    dt = ts[1]-ts[0]
    rt = np.concatenate([[0], np.cumsum(seg[:-1]/1000.0/GAP*dt)])/mul
    return rt, tmin
stats = collections.defaultdict(list); rows = []
for r in R:
    if r['rms'] > 1.5 or r['curve'] not in cfg: continue
    c = cfg[r['curve']]; tr = T[(r['rep'], r['hit'])]
    th = math.radians(round(r['th']/5.0)*5)
    v0 = solve_v(th, r['y0'], r['dist'])
    if v0 is None: continue
    ts, xs, ys, vs = sim(v0, th, -r['y0'])
    mul = (r['mul'] or 10000)/10000.0
    rt, tmin = real_time(ts, vs, c['firstHalfSegmentTime'], c['speedLerpFactor'], c['lastHalfSegmentTime'], mul)
    s0 = np.array(tr['start']); P = np.array(tr['pts'])
    if tr['landed']: P = P[:-1]
    P = P[:60]
    fr = P[:,0] - r['sf']; s = np.hypot(P[:,1]-s0[0], P[:,3]-s0[2])/100.0; y = (P[:,2]-s0[1])/100.0
    best = None
    for t0 in np.arange(0.0, 0.161, 0.005):
        t = fr*0.04 + t0
        sp = np.interp(t, rt, xs); yp = np.interp(t, rt, ys)
        e = np.hypot(sp-s, yp-y)
        if best is None or e.mean() < best[0]: best = (e.mean(), e.max(), t0)
    stats[r['curve']].append(best + (rt[-1], (r['y0']+ys.max())*100, v0, round(r['th']/5.0)*5, r['dist'], r['y0']))
    rows.append((r['curve'], r['E'], round(r['th']/5.0)*5, v0, rt[-1], best[2], best[0]*100))
print('curve n | mean pos err cm (median, worst) | max err cm (median) | t0 median s | T_total median s [min,max] | apex abs median cm')
allerr = []
for c in sorted(stats):
    L = np.array(stats[c]); allerr += list(L[:,0]*100)
    print('%d %2d | %.1f %.1f | %.1f | %.3f | %.2f [%.2f,%.2f] | %.0f' % (c, len(L), np.median(L[:,0])*100, L[:,0].max()*100, np.median(L[:,1])*100,
          np.median(L[:,2]), np.median(L[:,3]), L[:,3].min(), L[:,3].max(), np.median(L[:,4])))
print('ALL n=%d mean-err median %.2f cm, 90%% %.2f cm' % (len(allerr), np.median(allerr), np.percentile(allerr, 90)))
