# -*- coding: utf-8 -*-
"""从已解码的回放 jsonl 中抽出每一条球路的逐帧球位置。
输出 .ua/replica/data/D_tmp/traj.json : list of
 {rep, hitFrame(msg27帧), startFrame(msg63), curve, mul, key, serve, owner, action, energyPre,
  start[x,y,z], drop[x,y,z], pts[[frame,x,y,z],...], landed(bool), nextHitFrame}
用法: python D_replay_traj.py
"""
import json, base64, struct, os, glob
BALL = 268435457
def v3(s):
    if not s: return [0.0,0.0,0.0]
    return list(struct.unpack("<3f", base64.b64decode(s)[:12]))
out = []
for path in sorted(glob.glob('.ua/replica/data/D_tmp/r?.jsonl')):
    rep = os.path.basename(path)[:2]
    recs = [json.loads(l) for l in open(path, encoding='utf-8')][1:]
    ballpos = {}
    hits = []      # msg27
    curves = {}    # startpos key -> msg63
    energy = None; elog = []
    lastact = {}
    for r in recs:
        d = r.get('d') or {}
        if not isinstance(d, dict): continue
        if r['id'] == 6 and r['pid'] == BALL:
            p = d.get('Pos', {})
            ballpos[r['f']] = (p.get('X',0.0), p.get('Y',0.0), p.get('Z',0.0))
        elif r['id'] == 57 and d.get('CounterType') == 'COUNTER_TYPE_CONTINUOUS':
            elog.append((r['f'], d.get('Value', 0)))
        elif r['id'] == 88:
            lastact[r['pid']] = (r['f'], d.get('ActionID'), d.get('AverageSpeedMul'), d.get('HitFrame'))
        elif r['id'] == 27:
            hits.append(dict(f=r['f'], owner=r['pid'], key=d.get('HitKey'), start=v3(d.get('StartPos')),
                             drop=v3(d.get('DropPos')), curve=d.get('CurveShapeId'), tips=v3(d.get('TipsPos')),
                             pre=lastact.get(r['pid'])))
        elif r['id'] == 63:
            curves[(d.get('StartFrame'), d.get('OwnerID'))] = d
    def e_before(f):
        v = None
        for ff, vv in elog:
            if ff < f: v = vv
            else: break
        return v
    frames = sorted(ballpos)
    for i, h in enumerate(hits):
        nxt = hits[i+1]['f'] if i+1 < len(hits) else None
        pts = []; landed = False
        f = h['f'] + 1
        end = nxt if nxt is not None else h['f'] + 200
        while f <= end and f in ballpos:
            x, y, z = ballpos[f]
            if y > 5000: break
            pts.append([f, round(x,2), round(y,2), round(z,2)])
            if y <= 0.001:
                landed = True; break
            f += 1
        c63 = None
        for (sf, ow), d in curves.items():
            if ow == h['owner'] and sf is not None and 0 <= h['f'] - sf <= 3:
                c63 = d
        out.append(dict(rep=rep, hitFrame=h['f'], startFrame=(c63 or {}).get('StartFrame'), curve=h['curve'],
                        mul=(c63 or {}).get('AverageSpeedMul'), key=h['key'], serve=bool((c63 or {}).get('IsServe')),
                        owner=h['owner'], action=(h['pre'] or [None,None])[1], preFrame=(h['pre'] or [None])[0],
                        energyPre=e_before(h['f']), start=[round(v,2) for v in h['start']],
                        drop=[round(v,2) for v in h['drop']], pts=pts, landed=landed, nextHitFrame=nxt))
json.dump(out, open('.ua/replica/data/D_tmp/traj.json', 'w'))
print(len(out), 'trajectories;', sum(1 for t in out if t['landed']), 'landed')
