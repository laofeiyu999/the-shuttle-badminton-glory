# -*- coding: utf-8 -*-
"""飞羽 NORMAL 族弹道前向模型 (由回放逐帧球位置拟合复原, 非原生代码照抄)。
用法:
  python D_fy_curve.py table   -> 写 .ua/replica/data/D_energy_tier_compare.csv (同条件三档能量对比)
  python D_fy_curve.py sample  -> 写 .ua/replica/data/D_curve_samples.json (若干典型球的逐帧点)
单位: 输入 cm, 内部 m / s。逻辑帧 25 帧/s。
"""
import json, math, sys, csv
import numpy as np
K, G, GAP = 0.24, 5.0, 0.016        # curveconstant.txt 1000 组: airFriction, gravity, timeGap
NET_PASS_CM = 157.0                 # 回放实测过网阈值 (netHeight 150 + netFixH 8 附近)
CFG = {c['shapeId']: c for c in json.load(open('References/fyqc/fyqc-client/text/curveshape.txt', encoding='utf-8'))['shapeData']}

def sim(v0, th, ymin, dt=GAP/8):
    vx = v0*math.cos(th); vy = v0*math.sin(th); x = y = 0.0
    xs=[0.0]; ys=[0.0]; vs=[v0]
    while y > ymin and len(xs) < 60000:
        v = math.hypot(vx, vy); ax = -K*v*vx; ay = -K*v*vy - G
        vxm = vx + ax*dt*0.5; vym = vy + ay*dt*0.5; vm = math.hypot(vxm, vym)
        vx += -K*vm*vxm*dt; vy += (-K*vm*vym - G)*dt; x += vxm*dt; y += vym*dt
        xs.append(x); ys.append(y); vs.append(math.hypot(vx, vy))
    # 末点裁到 ymin
    if len(xs) > 1 and ys[-1] < ymin:
        f = (ys[-2]-ymin)/(ys[-2]-ys[-1]); xs[-1] = xs[-2]+(xs[-1]-xs[-2])*f; ys[-1] = ymin
    return np.arange(len(xs))*dt, np.array(xs), np.array(ys), np.array(vs)

def solve_v(th, y0, dist):
    lo, hi = 0.3, 400.0
    if sim(hi, th, -y0, GAP)[1][-1] < dist: return None
    for _ in range(40):
        m = 0.5*(lo+hi)
        if sim(m, th, -y0, GAP/2)[1][-1] < dist: lo = m
        else: hi = m
    return hi

def build(curve_id, y0_cm, dist_cm, net_frac=None, speed_mul=1.0):
    """返回 dict: 出球角, v0, 实际时间 rt[], 水平距离 s[], 高度 y[] (m, 绝对), 及摘要。
    net_frac: 网平面在水平路径上的位置比例 (0..1); None 表示不跨网。"""
    c = CFG[curve_id]; y0 = y0_cm/100.0; dist = dist_cm/100.0
    ang = c['angle']
    while True:
        th = math.radians(ang); v0 = solve_v(th, y0, dist)
        if v0 is not None:
            ts, xs, ys, vs = sim(v0, th, -y0)
            if net_frac is None or not c['crossNetFix']: break
            hnet = y0 + float(np.interp(net_frac*dist, xs, ys))
            if hnet*100 >= NET_PASS_CM: break
        ang += 5
        if ang > 80: break
    tmin = ts[int(np.argmin(vs))]
    first, lerp, last = c['firstHalfSegmentTime'], c['speedLerpFactor'], c['lastHalfSegmentTime']
    t0s = (1-lerp/100.0)*tmin
    seg = np.where(ts < t0s, first, np.where(ts >= tmin, last, first+(last-first)*(ts-t0s)/max(tmin-t0s, 1e-9)))
    dt = ts[1]-ts[0]
    rt = np.concatenate([[0], np.cumsum(seg[:-1]/1000.0/GAP*dt)])/speed_mul
    Y = ys + y0
    # 实际速度
    ds = np.hypot(np.diff(xs), np.diff(ys)); rv = ds/np.diff(rt)
    return dict(angle=ang, v0_model=v0, T=float(rt[-1]), apex=float(Y.max())*100, t_apex=float(rt[int(np.argmax(Y))]),
                v_first=float(rv[0]), v_end=float(rv[-1]), v_avg=float(ds.sum()/rt[-1]), rt=rt, s=xs, y=Y,
                net_h=(None if net_frac is None else (y0+float(np.interp(net_frac*dist, xs, ys)))*100),
                t_net=(None if net_frac is None else float(np.interp(net_frac*dist, xs, rt))))

def frames(b, t0=0.07):
    """逻辑帧采样: 第 n 帧 (击球后第 n 帧) 的 (s_cm, y_cm)。"""
    out = []; n = 1
    while True:
        t = n*0.04 + t0
        if t >= b['T']: break
        out.append((n, round(float(np.interp(t, b['rt'], b['s']))*100, 1), round(float(np.interp(t, b['rt'], b['y']))*100, 1))); n += 1
    return out

SCEN = [  # (场景名, 起点高度cm, 水平距离cm, 网位置比例)
 ('网前低手 y0=50 → 对方前场 d=400', 50, 400, 0.35),
 ('中场腰部 y0=100 → 对方前场 d=600', 100, 600, 0.55),
 ('中场头顶 y0=170 → 对方前场 d=600', 170, 600, 0.55),
 ('中场腰部 y0=100 → 对方后场 d=1000', 100, 1000, 0.40),
 ('中场头顶 y0=170 → 对方后场 d=1000', 170, 1000, 0.40),
 ('后场头顶 y0=170 → 对方后场 d=1150', 170, 1150, 0.50),
 ('后场头顶 y0=170 → 对方前场 d=800', 170, 800, 0.72),
 ('网前低手 y0=50 → 对方后场 d=750', 50, 750, 0.13),
]
FAM = [('平近_内 P键内圈', (1000,1001,1002)), ('平近_中 P键中圈', (1006,1007,1008)), ('平近_外 P键外圈', (1009,1010,1011)),
       ('平远_内 D键内圈', (1013,1014,1015)), ('平远_中 D键中圈', (1016,1017,1018)), ('平远_外 D键外圈', (1019,1020,1021)),
       ('高位吊后 GY键', (1003,1004,1005))]
if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'table'
    if mode == 'table':
        w = csv.writer(open('.ua/replica/data/D_energy_tier_compare.csv', 'w', newline='', encoding='utf-8-sig'))
        w.writerow(['family','scenario','curveId','energyTier','angle_deg','T_total_s','frames25','apex_cm','t_apex_s','net_h_cm','t_net_s','v_first_mps','v_avg_mps','v_end_mps','T_ratio_vs_tier0'])
        for fam, ids in FAM:
            for sc, y0, d, nf in SCEN:
                if ('平近' in fam and d > 700) or ('平远' in fam and d < 700) or ('高位' in fam and d < 700): continue
                T0 = None
                for tier, cid in enumerate(ids):
                    b = build(cid, y0, d, nf)
                    if T0 is None: T0 = b['T']
                    w.writerow([fam, sc, cid, tier, b['angle'], round(b['T'],3), round(b['T']*25,1), round(b['apex']), round(b['t_apex'],3),
                                round(b['net_h']), round(b['t_net'],3), round(b['v_first'],1), round(b['v_avg'],1), round(b['v_end'],1), round(b['T']/T0,3)])
                    print(fam, '|', sc, '|', cid, 'tier', tier, 'ang', b['angle'], 'T %.2f' % b['T'], 'apex %.0f' % b['apex'], 'net %.0f@%.2fs' % (b['net_h'], b['t_net']),
                          'v %.1f/%.1f/%.1f' % (b['v_first'], b['v_avg'], b['v_end']), 'ratio %.2f' % (b['T']/T0))
    elif mode == 'sample':
        out = {}
        for cid, y0, d, nf in [(1000,100,600,0.55),(1001,100,600,0.55),(1002,100,600,0.55),(1013,170,1000,0.4),(1014,170,1000,0.4),(1015,170,1000,0.4),
                               (1003,100,1000,0.4),(1004,100,1000,0.4),(1005,100,1000,0.4),(1003,50,750,0.13),(1012,39,900,0.4),(1030,102,600,0.5)]:
            b = build(cid, y0, d, nf)
            out['%d_y%d_d%d' % (cid, y0, d)] = dict(curveId=cid, name=CFG[cid]['name'], y0_cm=y0, dist_cm=d, net_frac=nf, angle_deg=b['angle'], T_s=round(b['T'],3),
                                                 apex_cm=round(b['apex'],1), frames_n_s_y_cm=frames(b))
        json.dump(out, open('.ua/replica/data/D_curve_samples.json', 'w', encoding='utf-8'), ensure_ascii=False)
        print('ok', len(out))
