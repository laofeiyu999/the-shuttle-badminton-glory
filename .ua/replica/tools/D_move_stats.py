# -*- coding: utf-8 -*-
"""回放统计: (1) 击球动作期间角色位移 (跨步/救球/鱼跃), (2) 自由移动速度与起停, (3) 落点分布 (按曲线 dropId / 按键 / 出球方向)。"""
import json, base64, struct, os, glob, math, collections, csv
import numpy as np
BALL = 268435457
def v3(s): return list(struct.unpack("<3f", base64.b64decode(s)[:12])) if s else [0.0,0.0,0.0]
disp = collections.defaultdict(list); speeds = []; drops = []; accel = []
for path in sorted(glob.glob('.ua/replica/data/D_tmp/r?.jsonl')):
    recs = [json.loads(l) for l in open(path, encoding='utf-8')][1:]
    pos = collections.defaultdict(dict); hits = []
    for r in recs:
        d = r.get('d') or {}
        if not isinstance(d, dict): continue
        if r['id'] == 6 and r['pid'] != BALL and 'Pos' in d:
            pos[r['pid']][r['f']] = (d['Pos'].get('X', 0.0), d['Pos'].get('Z', 0.0))
        elif r['id'] == 3: hits.append((r['f'], r['pid'], d.get('ActionID')))
        elif r['id'] == 63:
            s = v3(d.get('StartPos')); dp = v3(d.get('DropPos'))
            drops.append((d.get('CurveID'), (d.get('HitKey') or '')[-2:].replace('_',''), (d.get('OutDir') or '')[-5:], bool(d.get('IsServe')), s, dp))
    for f, pid, act in hits:
        P = pos[pid]; fs = sorted(k for k in P if f-1 <= k <= f+40)
        if len(fs) < 5: continue
        p0 = P[fs[0]]; dd = [(k-f, math.hypot(P[k][0]-p0[0], P[k][1]-p0[1])) for k in fs]
        mx = max(x[1] for x in dd); tmx = next(x[0] for x in dd if x[1] >= 0.95*mx) if mx > 5 else 0
        disp[act].append((mx, tmx))
    for pid, P in pos.items():
        fs = sorted(P)
        for a, b in zip(fs, fs[1:]):
            if b-a == 1:
                speeds.append(math.hypot(P[b][0]-P[a][0], P[b][1]-P[a][1])*25)
def grp(a):
    if 2001 <= a <= 2008: return '内圈 2001-2008'
    if a == 2009: return '原地高位起跳 2009'
    if 3001 <= a <= 3008: return '跨步中低 3001-3008'
    if 4001 <= a <= 4008: return '跨步高位 4001-4008'
    if 5001 <= a <= 5008: return '救球低位 5001-5008'
    if 5011 <= a <= 5018: return '救球中高位 5011-5018'
    if 5021 <= a <= 5028: return '鱼跃 5021-5028'
    if a == 1076: return '星标扣球 1076'
    if a in (6000, 6001): return '发球'
    return None
G = collections.defaultdict(list)
for a, L in disp.items():
    g = grp(a or 0)
    if g: G[g] += L
print('动作期间角色位移 (HIT_RES 帧起 40 帧内最大位移 cm; 达到 95% 位移的帧数)')
for g in G:
    L = np.array(G[g]); print('  %s n=%d  位移 p10 %.0f med %.0f p90 %.0f max %.0f | 用时帧 med %.0f' % (g, len(L), *np.percentile(L[:,0], [10,50,90]), L[:,0].max(), np.median(L[:,1])))
sp = np.array(speeds); mv = sp[sp > 20]
print('逐帧移动速度 cm/s (>20): n=%d p50 %.0f p75 %.0f p90 %.0f p99 %.0f max %.0f' % (len(mv), *np.percentile(mv, [50,75,90,99]), mv.max()))
h = np.histogram(mv, bins=[20,100,200,300,330,360,390,420,450,500,560,620,800,2000,100000]); print('  hist', list(zip(h[1][:-1].astype(int), h[0])))
# 落点
cd = {c['id']: c for c in (lambda j: j if isinstance(j, list) else j.get('list') or list(j.values())[0])(json.load(open('References/fyqc/fyqc-client/text/curvedrop.txt', encoding='utf-8')))}
cs = {c['shapeId']: c['dropId'] for c in json.load(open('References/fyqc/fyqc-client/text/curveshape.txt', encoding='utf-8'))['shapeData']}
cs.update({c['shapeId']: c['dropId'] for c in json.load(open('References/fyqc/fyqc-client/text/paraboladowncurve.txt', encoding='utf-8'))['shapeData']})
print('curvedrop:'); [print('  ', json.dumps(c, ensure_ascii=False)) for c in cd.values()]
D = collections.defaultdict(list)
for cid, key, od, serve, s, dp in drops:
    side = 1 if s[2] > 0 else -1     # 击球方半场
    zrel = -side*dp[2]               # 落点在对方半场内距网距离 (正)
    xrel = dp[0]*side                # 统一朝向后的横向
    D[(cs.get(cid), key, od)].append((zrel, abs(dp[0]), xrel))
print('落点统计 (dropId, key, outDir) n | 距网 z cm min p10 med p90 max | |x| cm min med max')
for k in sorted(D, key=lambda x: (x[0] or 0, x[1], x[2])):
    L = np.array(D[k]); 
    if len(L) < 5: continue
    print('  ', k, len(L), '| %.0f %.0f %.0f %.0f %.0f | %.0f %.0f %.0f' % (L[:,0].min(), *np.percentile(L[:,0], [10,50,90]), L[:,0].max(), L[:,1].min(), np.median(L[:,1]), L[:,1].max()))
