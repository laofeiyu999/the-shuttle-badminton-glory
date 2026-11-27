# -*- coding: utf-8 -*-
"""PARABOLA_DOWN: 水平速度/过网高度/系数 a 的规律检验。"""
import json, math, collections
import numpy as np
T = json.load(open('.ua/replica/data/D_tmp/traj.json'))
P = {c['shapeId']: c for c in json.load(open('References/fyqc/fyqc-client/text/paraboladowncurve.txt', encoding='utf-8'))['shapeData']}
for t in T:
    c = t['curve']
    if c < 4000 or c >= 5000 or t['startFrame'] is None: continue
    s0 = np.array(t['start']); d = np.array(t['drop']); pts = np.array(t['pts'])
    if t['landed']: pts = pts[:-1]
    pts = pts[pts[:,0]-t['startFrame'] >= 3] if c == 4011 else pts[1:]
    if len(pts) < 4: continue
    s = np.hypot(pts[:,1]-s0[0], pts[:,3]-s0[2]); y = pts[:,2]
    D = math.hypot(d[0]-s0[0], d[2]-s0[2])
    A = np.stack([np.ones_like(s), s, -s*s], 1); co, *_ = np.linalg.lstsq(A, y, rcond=None)
    yA, b, a = co
    hs = np.polyfit(pts[:,0], s, 1)[0]*25   # cm/s
    # 落地点 (抛物线零点)
    Dz = (b + math.sqrt(b*b + 4*a*yA))/(2*a) if a > 1e-9 else -yA/b
    mul = (t['mul'] or 10000)/10000; vel = P[c]['velocity']*mul
    # 网: z=0 平面
    dz = d[2]-s0[2]; fn = -s0[2]/dz if dz else 0; sn = fn*D
    hn = yA + b*sn - a*sn*sn
    chord = math.hypot(D, s0[1]); 
    # 弧长
    ss = np.linspace(0, Dz, 400); yy = yA + b*ss - a*ss*ss; arc = np.hypot(np.diff(ss), np.diff(yy)).sum()
    print('%d y0 %3.0f fitY0 %3.0f D %4.0f Dzero %4.0f | a*1e6 %5.1f b %.3f | netS %4.0f netH %5.1f | hs %4.0f hs/vel %.3f  D/chord %.3f D/arc %.3f cos(b) %.3f | T=D/hs %.3f arc/vel %.3f chord/vel %.3f'
          % (c, s0[1], yA, D, Dz, a*1e6, b, sn, hn, hs, hs/vel, D/chord, Dz/arc, math.cos(math.atan(b)), Dz/hs, arc/vel, chord/vel))
