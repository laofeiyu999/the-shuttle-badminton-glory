# -*- coding: utf-8 -*-
"""A2_track.py f0 f1 step dir(+1/-1) cx cy cz pitch yaw fov [out.csv]
从给定初值出发逐帧跟踪相机（每 step 帧），输出 csv：f,t,cx,cy,cz,pitch,yaw,fov,nvis,inl,rms,ngood,nlines,ok
dir=-1 时从 f1 向 f0 反向跟踪（初值对应 f1）。"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from A2_auto import *
from A_common import iter_frames, DATA

def track(f0, f1, step, direction, p0, out=None, verbose=True, stop_bad=8):
    A = Auto(step=0.15)
    frames = list(range(f0, f1 + 1, step))
    rows = []
    if direction > 0:
        it = iter_frames(f0, None, step)
        seq = ((f, a) for f, a in it if f <= f1)
    else:
        # 反向：分块读入
        def rev():
            fs = frames[::-1]
            for k in range(0, len(fs), 20):
                blk = fs[k:k + 20]
                lo = blk[-1]
                buf = {}
                for f, a in iter_frames(lo, len(blk), step):
                    buf[f] = a.copy()
                for f in blk:
                    if f in buf: yield f, buf[f]
        seq = rev()
    p = np.array(p0, float); bad = 0; t0 = time.time()
    for f, rgb in seq:
        mk, _ = gated_mask(rgb)
        dm = dmap(mk)
        q = A.refine(p, dm, taus=(12, 5))
        sc = A.score(q, dm)
        ok = sc['inl'] > 0.75 and sc['nvis'] >= 150 and sc['ngood'] >= 4
        if not ok:
            # 局部随机搜索
            c = A.grid_init(dm, n=600, around=p, seed=f)
            best = (q, sc)
            for c0, qq in c[:3]:
                q2 = A.refine(qq, dm); s2 = A.score(q2, dm)
                if s2['inl'] * min(s2['nvis'], 600) > best[1]['inl'] * min(best[1]['nvis'], 600): best = (q2, s2)
            q, sc = best
            ok = sc['inl'] > 0.75 and sc['nvis'] >= 150 and sc['ngood'] >= 4
        rows.append([f, f / 60.0] + list(q) + [sc['nvis'], sc['inl'], sc['rms'], sc['ngood'], sc['nlines'], int(ok)])
        if ok: p = q; bad = 0
        else: bad += 1
        if verbose and (len(rows) % 10 == 1 or not ok):
            print('f%5d t%6.2f p %6.2f %5.2f %6.2f pit %5.2f yaw %6.2f fov %5.2f nvis %3d inl %.2f rms %.2f good %d/%d %s' % (f, f / 60., *q, sc['nvis'], sc['inl'], sc['rms'], sc['ngood'], sc['nlines'], 'ok' if ok else 'BAD'))
        if bad >= stop_bad: break
    if verbose: print('n %d time %.1fs' % (len(rows), time.time() - t0))
    if out:
        np.savetxt(out, np.array(rows), delimiter=',', fmt='%.4f', header='f,t,cx,cy,cz,pitch,yaw,fov,nvis,inl,rms,ngood,nlines,ok', comments='')
    return rows

if __name__ == '__main__':
    f0, f1, step, d = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    p0 = [float(v) for v in sys.argv[5:11]]
    out = sys.argv[11] if len(sys.argv) > 11 else None
    track(f0, f1, step, d, p0, out)
