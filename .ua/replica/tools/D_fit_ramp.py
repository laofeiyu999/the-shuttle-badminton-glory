# -*- coding: utf-8 -*-
"""找时间扭曲斜坡的起止点用什么量参数化: 点序号 n, n/N, 水平距离比 s/S, 速度比 v/v0, 高度。"""
import json, math, sys
import numpy as np
K, G, GAP = 0.24, 5.0, 0.016
R = json.load(open('.ua/replica/data/D_tmp/fit_normal.json'))
cfg = {c['shapeId']: c for c in json.load(open('References/fyqc/fyqc-client/text/curveshape.txt', encoding='utf-8'))['shapeData']}
def sim(v0, th, ymin, dt=0.001):
    vx = v0*math.cos(th); vy = v0*math.sin(th); x = y = 0.0
    xs=[0.0]; ys=[0.0]; vs=[v0]
    while y > ymin - 0.3 and len(xs) < 9000:
        v = math.hypot(vx, vy); ax = -K*v*vx; ay = -K*v*vy - G
        vxm = vx + ax*dt*0.5; vym = vy + ay*dt*0.5; vm = math.hypot(vxm, vym)
        vx += -K*vm*vxm*dt; vy += (-K*vm*vym - G)*dt; x += vxm*dt; y += vym*dt
        xs.append(x); ys.append(y); vs.append(math.hypot(vx, vy))
    return np.arange(len(xs))*dt, np.array(xs), np.array(ys), np.array(vs)
ids = [int(a) for a in sys.argv[1:]]
print('curve first lerp last | th  v0   N  | rampStart: n  n/N  s/S  tau | rampEnd: n n/N s/S tau | len_n len_tau | apex_n')
for r in R:
    if r['curve'] not in ids or r['rms'] > 1.0 or not r['tauT']: continue
    c = cfg[r['curve']]; f1 = c['firstHalfSegmentTime']; f2 = c['lastHalfSegmentTime']
    if abs(f2-f1) < 2: continue
    tau = np.array(r['tau']); fr = np.array(r['fr'], float); mul = (r['mul'] or 10000)/10000.0
    seg = GAP*np.diff(fr)*0.04/np.diff(tau)*mul*1000
    tm = (tau[:-1]+tau[1:])*0.5
    ok = seg < 60
    if ok.sum() < 8: continue
    seg = seg[ok]; tm = tm[ok]
    # 斜坡起止: 线性外推 seg 在 (f1+10%, f2-10%) 区间的点
    lo = f1 + 0.12*(f2-f1); hi = f2 - 0.12*(f2-f1)
    m = (seg > lo) & (seg < hi)
    if m.sum() < 3 or seg[0] > lo or seg[-1] < hi: continue
    A = np.polyfit(seg[m], tm[m], 2)
    t_s = np.polyval(A, f1); t_e = np.polyval(A, f2)
    ts, xs, ys, vs = sim(r['v0'], math.radians(r['th']), -r['y0'])
    N = r['tauT']/GAP; S = r['sT']
    def at(t): return np.interp(t, ts, xs)/S
    apex_n = ts[int(np.argmax(ys))]/GAP
    tmin = ts[int(np.argmin(vs))]; ds = np.diff(xs)/0.001
    def tv(vc):
        i = np.where(vs <= vc)[0]
        return ts[i[0]] if len(i) else -1
    def th(vc):
        i = np.where(ds <= vc)[0]
        return ts[i[0]] if len(i) else -1
    extra = ' tminV=%.2f vmin=%.2f t(v<5)=%.2f t(vh<4)=%.2f t(vh<3)=%.2f v@e=%.2f vh@e=%.2f' % (tmin, vs.min(), tv(5.0), th(4.0), th(3.0), np.interp(t_e, ts, vs), np.interp(t_e, ts[1:], ds))
    print('%d %2d %2d %2d | %2.0f %5.1f %3.0f | %5.1f %.2f %.2f %.2f | %5.1f %.2f %.2f %.2f | %5.1f %.2f | %5.1f | E=%s' % (
        r['curve'], f1, c['speedLerpFactor'], f2, r['th'], r['v0'], N, t_s/GAP, t_s/r['tauT'], at(t_s), t_s,
        t_e/GAP, t_e/r['tauT'], at(t_e), t_e, (t_e-t_s)/GAP, t_e-t_s, apex_n, r['E']) + extra)
