# -*- coding: utf-8 -*-
"""PARABOLA_DOWN 族 (4xxx) 回放轨迹分析: 形状 y(s) 是否抛物线, 系数 a, 速度是否恒定。"""
import json, math, sys, collections
import numpy as np
T = json.load(open('.ua/replica/data/D_tmp/traj.json'))
P = {c['shapeId']: c for c in json.load(open('References/fyqc/fyqc-client/text/paraboladowncurve.txt', encoding='utf-8'))['shapeData']} if True else {}
agg = collections.defaultdict(list)
show = int(sys.argv[1]) if len(sys.argv) > 1 else 0
for t in T:
    if t['curve'] < 4000 or t['curve'] >= 5000: continue
    s0 = np.array(t['start']); d = np.array(t['drop']); pts = np.array(t['pts'])
    if len(pts) < 4 or t['startFrame'] is None: continue
    if t['landed']: pts = pts[:-1]
    fr = pts[:,0] - t['startFrame']
    s = np.hypot(pts[:,1]-s0[0], pts[:,3]-s0[2]); y = pts[:,2]
    dist = math.hypot(d[0]-s0[0], d[2]-s0[2])
    # 二次拟合 y = y0 + b s - a s^2 (过起点)
    A = np.stack([s, -s*s], 1); coef, *_ = np.linalg.lstsq(A, y - s0[1], rcond=None)
    res = (A@coef + s0[1] - y)
    # 3D 速度
    p3 = pts[:,1:4]; dv = np.linalg.norm(np.diff(p3, axis=0), axis=1)/np.diff(pts[:,0])*25/100
    hs = np.diff(s)/np.diff(pts[:,0])*25/100
    # 起点到第一帧
    v0 = math.dist(p3[0], s0)/100/((fr[0])*0.04+0.07) if fr[0] > 0 else 0
    mul = (t['mul'] or 10000)/10000
    agg[t['curve']].append((s0[1], dist, coef[0], coef[1]*1e4, np.abs(res).max(), np.median(dv), dv[0], dv[-1], np.median(hs), mul, len(pts), t['energyPre'] if t['energyPre'] is not None else -1,
                            (pts[-1,0]-t['startFrame']) , t['landed']))
    if show and t['curve'] == show:
        print('rep', t['rep'], 'hit', t['hitFrame'], 'y0 %.0f dist %.0f mul %.2f landed %s' % (s0[1], dist, mul, t['landed']))
        print('  fr', fr.astype(int).tolist()); print('  s ', np.round(s).astype(int).tolist()); print('  y ', np.round(y).astype(int).tolist()); print('  v3d m/s', np.round(dv,1).tolist())
for c in sorted(agg):
    L = np.array(agg[c], dtype=float); cf = P.get(c, {})
    print('%d %s n=%d cfg minA %s maxA %s vel %s dropFix %s drop %s' % (c, cf.get('name'), len(L), cf.get('parabolaMinA'), cf.get('parabolaMaxA'), cf.get('velocity'), cf.get('dropPosFix'), cf.get('dropId')))
    print('   y0 med %.0f [%.0f,%.0f] dist med %.0f [%.0f,%.0f] | b(slope0) med %.3f | a*1e4 med %.3f [%.3f,%.3f] | parab resid max med %.1f cm | v3d med %.1f m/s first %.1f last %.1f | horiz v %.1f | v/mul %.1f'
          % (np.median(L[:,0]), L[:,0].min(), L[:,0].max(), np.median(L[:,1]), L[:,1].min(), L[:,1].max(), np.median(L[:,2]), np.median(L[:,3]), L[:,3].min(), L[:,3].max(),
             np.median(L[:,4]), np.median(L[:,5]), np.median(L[:,6]), np.median(L[:,7]), np.median(L[:,8]), np.median(L[:,5]/L[:,9])))
