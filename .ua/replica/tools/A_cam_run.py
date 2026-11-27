# -*- coding: utf-8 -*-
"""全片相机标定（每 STEP 帧一次，多进程）。输出 data/A_camera_raw.csv。
python A_cam_run.py [step=2] [nproc=16]
每段：顺序跟踪（上一帧结果作初值，refine2）；跟踪失败时每 REINIT 帧做一次 Hough 初始化；
再做一遍反向跟踪补洞。合格标准 ok = hit>=0.6 且 back_hit>=0.5 且 nvis>=250。
"""
import sys, os, numpy as np, time
from multiprocessing import Pool
from PIL import Image
import A_cam as C
from A_common import iter_frames, NF, FPS, DATA

STEP = int(sys.argv[1]) if len(sys.argv) > 1 else 2
NPROC = int(sys.argv[2]) if len(sys.argv) > 2 else 16
REINIT = 6      # 以 STEP 帧为单位


def good(q):
    return q['hit'] >= 0.6 and q['back_hit'] >= 0.5 and q['nvis'] >= 250


def work(args):
    f0, f1 = args
    n = (f1 - f0 + STEP - 1) // STEP
    masks = []; fr = []
    for f, a in iter_frames(f0, n * STEP, 1, None, (C.WS, C.HS)):
        if (f - f0) % STEP:
            continue
        m, reg = C.line_mask(a)
        masks.append(np.packbits(m)); fr.append(f)
    n = len(fr)
    P = np.full((n, 6), np.nan); Q = np.zeros((n, 5)); OK = np.zeros(n, bool); SRC = np.zeros(n, int)

    def prep(i):
        m = np.unpackbits(masks[i])[:C.HS * C.WS].reshape(C.HS, C.WS).astype(bool)
        return m, C.dist_map(m), C.mask_points(m)

    def setres(i, p, q, src):
        P[i] = p; Q[i] = (q['fwd'], q['hit'], q['back'], q['back_hit'], q['nvis']); OK[i] = good(q); SRC[i] = src

    def better(i, q):
        return (not np.isfinite(P[i, 0])) or (q['fwd'] + q['back'] < Q[i, 0] + Q[i, 2] - 1e-6)

    prev = None; since = REINIT
    for i in range(n):
        m, dm, mp = prep(i)
        if len(mp) < 150:
            prev = None; since += 1
            continue
        done = False
        if prev is not None:
            p = C.refine2(prev, dm, mp, max_nfev=30, stages=(1e-2, 3e-3))
            q = C.fit_quality(p, dm, mp)
            setres(i, p, q, 1)
            done = OK[i]
        if not done:
            since += 1
            if since >= REINIT:
                since = 0
                r = C.hough_init(m, dm, mp)
                if r is not None:
                    p = r[0]; q = C.fit_quality(p, dm, mp)
                    if better(i, q):
                        setres(i, p, q, 2)
        prev = P[i].copy() if OK[i] else None
    # 反向补洞
    prev = None
    for i in range(n - 1, -1, -1):
        if OK[i]:
            prev = P[i].copy(); continue
        if prev is None:
            continue
        m, dm, mp = prep(i)
        if len(mp) < 150:
            prev = None; continue
        p = C.refine2(prev, dm, mp, max_nfev=30, stages=(1e-2, 3e-3))
        q = C.fit_quality(p, dm, mp)
        if better(i, q):
            setres(i, p, q, 3)
        prev = P[i].copy() if OK[i] else None
    # 正向再补一遍（Hough 成功点之后的洞）
    prev = None
    for i in range(n):
        if OK[i]:
            prev = P[i].copy(); continue
        if prev is None:
            continue
        m, dm, mp = prep(i)
        if len(mp) < 150:
            prev = None; continue
        p = C.refine2(prev, dm, mp, max_nfev=30, stages=(1e-2, 3e-3))
        q = C.fit_quality(p, dm, mp)
        if better(i, q):
            setres(i, p, q, 4)
        prev = P[i].copy() if OK[i] else None
    return np.array(fr), P, Q, OK, SRC


if __name__ == '__main__':
    t0 = time.time()
    F0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    F1 = int(sys.argv[4]) if len(sys.argv) > 4 else NF
    tag = sys.argv[5] if len(sys.argv) > 5 else 'raw'
    nseg = max(1, min(NPROC * 3, (F1 - F0) // 120))
    edges = np.linspace(F0, F1, nseg + 1).astype(int)
    edges = (edges // STEP) * STEP
    edges[-1] = F1
    jobs = [(int(edges[i]), int(edges[i + 1])) for i in range(nseg)]
    with Pool(NPROC) as pool:
        res = pool.map(work, jobs, chunksize=1)
    fr = np.concatenate([r[0] for r in res]); P = np.vstack([r[1] for r in res]); Q = np.vstack([r[2] for r in res])
    OK = np.concatenate([r[3] for r in res]); SRC = np.concatenate([r[4] for r in res])
    import csv
    with open(os.path.join(DATA, 'A_camera_%s.csv' % tag), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['frame', 't_s', 'cam_x_m', 'cam_y_m', 'cam_z_m', 'pitch_deg', 'yaw_deg', 'vfov_deg', 'fwd_px', 'hit', 'back', 'back_hit', 'nvis', 'ok', 'src'])
        for i in range(len(fr)):
            w.writerow([int(fr[i]), '%.4f' % (fr[i] / FPS)] + ['%.4f' % v for v in P[i]] + ['%.3f' % Q[i, 0], '%.3f' % Q[i, 1], '%.3f' % Q[i, 2], '%.3f' % Q[i, 3], int(Q[i, 4]), int(OK[i]), int(SRC[i])])
    print('frames', len(fr), 'ok', int(OK.sum()), 'time %.0fs' % (time.time() - t0))
