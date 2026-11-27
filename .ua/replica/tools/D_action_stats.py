# -*- coding: utf-8 -*-
"""每个击球动作 ID 的击球点统计: 击球高度 sy, 球相对击球者的水平距离/方向, 按键后到击球的帧数, 击球者按键时到球预判点的距离。
输出 .ua/replica/data/D_action_hit_stats.csv 及屏幕摘要。"""
import json, base64, struct, os, glob, math, collections, csv
import numpy as np
BALL = 268435457
def v3(s):
    return list(struct.unpack("<3f", base64.b64decode(s)[:12])) if s else [0.0,0.0,0.0]
names = {}
for a in json.load(open('References/fyqc/fyqc-client/text/hitaction.txt', encoding='utf-8')):
    names[a['id']] = (a['name'], a.get('actionType'), a.get('beforeActionLength'), a.get('castActionLength'))
rows = []
for path in sorted(glob.glob('.ua/replica/data/D_tmp/r?.jsonl')):
    rep = os.path.basename(path)[:2]
    recs = [json.loads(l) for l in open(path, encoding='utf-8')][1:]
    ppos = {}; lasthit = {}; poshist = collections.defaultdict(list)
    for r in recs:
        d = r.get('d') or {}
        if not isinstance(d, dict): continue
        if r['id'] == 6 and r['pid'] != BALL and 'Pos' in d:
            ppos[r['pid']] = (d['Pos'].get('X', 0.0), d['Pos'].get('Z', 0.0)); poshist[r['pid']].append((r['f'], ppos[r['pid']]))
        elif r['id'] == 3:
            lasthit[r['pid']] = (r['f'], d.get('ActionID'), d.get('HitType'), d.get('HitKey'), (d.get('Pos') or {}).get('X', 0.0), (d.get('Pos') or {}).get('Z', 0.0), d.get('MoveScale'), d.get('IsDirect'))
        elif r['id'] == 63:
            o = d.get('OwnerID'); 
            if o not in lasthit: continue
            hf, act, ht, hk, px, pz, ms, isd = lasthit[o]
            sf = d.get('StartFrame')
            if sf is None or sf - hf > 40 or sf < hf: continue
            s = v3(d.get('StartPos')); dp = v3(d.get('DropPos'))
            cur = ppos.get(o, (px, pz))
            side = 1 if pz > 0 else -1          # 击球者所在半场 (z 符号); 朝网方向 = -side
            # 以 "朝网" 为前: fwd = (ball - player) 在 -side*z 上的分量; right 用 x*side (面向网时右手侧) 仅作参考
            dx = s[0]-cur[0]; dz = s[2]-cur[1]
            fwd = -side*dz; lat = dx
            rows.append(dict(rep=rep, frame=sf, owner=o, action=act, hitType=ht, key=(hk or '')[-1:] if hk and not hk.endswith('GY') else 'GY', curve=d.get('CurveID'),
                             sy=round(s[1],1), ballX=round(s[0],1), ballZabs=round(abs(s[2]),1), dist=round(math.hypot(dx,dz),1), fwd=round(fwd,1), lat=round(lat,1),
                             pressToHit=sf-hf, pressDist=round(math.hypot(s[0]-px, s[2]-pz),1), plZabs=round(abs(cur[1]),1), dropZabs=round(abs(dp[2]),1), dropX=round(dp[0],1),
                             moveScale=ms, isDirect=isd, serve=bool(d.get('IsServe'))))
w = csv.DictWriter(open('.ua/replica/data/D_action_hit_stats.csv', 'w', newline='', encoding='utf-8-sig'), fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('rows', len(rows))
g = collections.defaultdict(list)
for r in rows: g[r['action']].append(r)
def q(a, p): return np.percentile(a, p)
print('action name type before cast | n | sy p5/med/p95 | dist(hit) p5/med/p95 | pressDist med p95 | pressToHit med [min,max] | fwd med lat med | keys | curves')
for a in sorted(g):
    L = g[a]; sy = [r['sy'] for r in L]; di = [r['dist'] for r in L]; pd = [r['pressDist'] for r in L]; ph = [r['pressToHit'] for r in L]
    keys = collections.Counter(r['key'] for r in L); cs = collections.Counter(r['curve'] for r in L)
    nm = names.get(a, ('?',0,0,0))
    print('%s %s t%s b%.2f c%.2f | %3d | %3.0f %3.0f %3.0f | %3.0f %3.0f %3.0f | %3.0f %3.0f | %d [%d,%d] | %4.0f %4.0f | %s | %s' % (a, nm[0], nm[1], nm[2] or 0, nm[3] or 0, len(L), q(sy,5), q(sy,50), q(sy,95), q(di,5), q(di,50), q(di,95),
          q(pd,50), q(pd,95), q(ph,50), min(ph), max(ph), np.median([r['fwd'] for r in L]), np.median([r['lat'] for r in L]), dict(keys), dict(cs.most_common(4))))
