# -*- coding: utf-8 -*-
"""分析 D_traj_fit2 的结果: (a) 出球角的 5 度量化与过网抬角规则; (b) 时间扭曲律 seg(u)。"""
import json, math, sys, collections
import numpy as np
K, G, GAP = 0.24, 5.0, 0.016
R = json.load(open('.ua/replica/data/D_tmp/fit_normal.json'))
cfg = {}
d = json.load(open('References/fyqc/fyqc-client/text/curveshape.txt', encoding='utf-8'))
for c in d['shapeData']: cfg[c['shapeId']] = c
def sim(v0, th, ymin, dt=0.001):
    vx = v0*math.cos(th); vy = v0*math.sin(th); x = y = 0.0
    xs=[0.0]; ys=[0.0]
    while y > ymin - 0.3 and len(xs) < 9000:
        v = math.hypot(vx, vy); ax = -K*v*vx; ay = -K*v*vy - G
        vxm = vx + ax*dt*0.5; vym = vy + ay*dt*0.5; vm = math.hypot(vxm, vym)
        vx += -K*vm*vxm*dt; vy += (-K*vm*vym - G)*dt; x += vxm*dt; y += vym*dt
        xs.append(x); ys.append(y)
    return np.arange(len(xs))*dt, np.array(xs), np.array(ys)
def solve_v(th, y0, dist):
    lo, hi = 0.5, 400.0
    def rng(v):
        ts, xs, ys = sim(v, th, -y0)
        i = np.where(ys <= -y0)[0]
        return xs[i[0]] if len(i) else xs[-1]
    if rng(hi) < dist: return None
    for _ in range(40):
        m = 0.5*(lo+hi)
        if rng(m) < dist: lo = m
        else: hi = m
    return hi
mode = sys.argv[1] if len(sys.argv) > 1 else 'angle'
if mode == 'angle':
    print('curve cfgAngle fixAmp | selAngle y0 dist netfrac | yNet(sel) yNet(sel-5) | apexAbs')
    for r in R:
        if r['rms'] > 1.5 or r['curve'] not in cfg: continue
        c = cfg[r['curve']]; a0 = c['angle']; sel = round(r['th']/5.0)*5
        if sel == a0 and '-all' not in sys.argv: continue
        # 网位置在路径上的比例
        if r['startz']*r['dropz'] >= 0: frac = None
        else: frac = abs(r['startz'])/(abs(r['startz'])+abs(r['dropz']))
        out = []
        for a in (sel, sel-5):
            v = solve_v(math.radians(a), r['y0'], r['dist'])
            if v is None or frac is None: out.append(float('nan')); continue
            ts, xs, ys = sim(v, math.radians(a), -r['y0'])
            out.append((r['y0'] + float(np.interp(frac*r['dist'], xs, ys)))*100)
        print('%d %3d %3d | %3d  y0=%4.0f dist=%5.0f frac=%s | %6.1f %6.1f | apex=%4.0f' % (r['curve'], a0, c['fixAmplitude'], sel, r['y0']*100, r['dist']*100,
              ('%.2f' % frac) if frac is not None else 'same', out[0], out[1], (r['y0']+r['apex'])*100))
else:
    cid = int(sys.argv[2])
    c = cfg[cid]
    print('cfg first=%s lerp=%s last=%s angle=%s' % (c['firstHalfSegmentTime'], c['speedLerpFactor'], c['lastHalfSegmentTime'], c['angle']))
    n = 0
    for r in R:
        if r['curve'] != cid or r['rms'] > 1.5 or not r['tauT']: continue
        tau = np.array(r['tau']); fr = np.array(r['fr'], float)
        mul = (r['mul'] or 10000)/10000.0
        seg = GAP*np.diff(fr)*0.04/np.diff(tau)*mul      # 每个 0.016 模型段的真实时长 × mul
        u = (tau[:-1]+tau[1:])*0.5/r['tauT']
        N = r['tauT']/GAP
        print('E=%s mul=%.3f th=%.0f v0=%.1f N=%.0f tauT=%.2f frames=%d..%d landed=%s tau0=%.3f' % (r['E'], mul, r['th'], r['v0'], N, r['tauT'], fr[0], fr[-1], r['landed'], tau[0]))
        print('   u  :', ' '.join('%.2f' % v for v in u))
        print('   seg:', ' '.join('%.1f' % (v*1000) for v in seg))
        n += 1
        if n >= int(sys.argv[3]) if len(sys.argv) > 3 else n >= 4: break
