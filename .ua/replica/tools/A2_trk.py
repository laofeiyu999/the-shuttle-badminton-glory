# -*- coding: utf-8 -*-
"""A2_trk.py：全片相机跟踪（Hough 直线 + 与上一帧位姿自动关联 + 线对应最小二乘）。
  python A2_trk.py f0 f1 step out.csv [cx cy cz pitch yaw fov]
无初值或跟丢时，用位姿库（BANK + 已成功位姿）逐个尝试。输出列：
  f,t,cx,cy,cz,pitch,yaw,fov,nmatch,nH,nO,rms,ok
"""
import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy.optimize import least_squares
from A_common import SRC, W, H, FPS, DATA
from A2_cam import project, segments, HALF_L, hud_ok
from scipy import ndimage as ndi
from A2_hough import ridge_points
from A2_h import fast_hough

DIM_GAME = dict(half_wd=3.05, half_ws=2.56, z_short=2.15, z_long=5.95, net_h=1.53)
SEGS = segments(DIM_GAME)
NAMES = list(SEGS.keys())
HFAM = [n for n in NAMES if n.startswith(('base', 'long', 'short', 'net'))]
T41 = np.linspace(0, 1, 41)[:, None]
SEGP = {n: np.array(SEGS[n][0], float) + (np.array(SEGS[n][1], float) - np.array(SEGS[n][0], float)) * T41 for n in NAMES}
BANK = [[1.0, 4.5, 11.7, 21.3, -0.5, 30.5], [-1.15, 5.08, 12.75, 17.7, -0.4, 38.8]]


def frames(f0, f1, step):
    vf = ("select='not(mod(n" + chr(92) + ",%d))'" % step) if step > 1 else 'null'
    cmd = ['ffmpeg', '-v', 'quiet', '-ss', '%.6f' % (f0 / FPS + 0.0005), '-i', SRC, '-frames:v', str((f1 - f0) // step + 1), '-vf', vf, '-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10 ** 8)
    sz = W * H * 3; i = 0
    while True:
        buf = p.stdout.read(sz)
        if len(buf) < sz: break
        yield f0 + i * step, np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        i += 1
    p.stdout.close(); p.kill()


def detect(rgb):
    """返回 (直线数组 Nx8, 脊点距离图)。"""
    xs, ys, _ = ridge_points(rgb, thr=30)
    mk = np.zeros((H, W), bool); mk[ys.astype(int), xs.astype(int)] = True
    dm = np.minimum(ndi.distance_transform_edt(~mk), 20).astype(np.float32)
    L = fast_hough(xs, ys, nmax=40, min_votes=45, min_cov=90)
    if not L: return np.zeros((0, 8)), dm
    return np.array([[l['n'][0], l['n'][1], l['rho'], l['p0'][0], l['p0'][1], l['p1'][0], l['p1'][1], l['npts']] for l in L]), dm


VP = np.vstack([SEGP[n][::2] for n in NAMES if n != 'net_top'])
def verify(p, dm, tol=2.5):
    """模型地面线采样点（非 HUD、屏内）落在白线脊点 tol 像素内的比例。"""
    uv, dep = project(p, VP)
    x, y = uv[:, 0], uv[:, 1]
    vis = np.isfinite(x) & np.isfinite(y) & (dep > 0.1)
    xx = np.where(vis, x, 0); yy = np.where(vis, y, 0)
    vis &= hud_ok(xx, yy)
    if vis.sum() < 20: return 0.0, int(vis.sum())
    d = dm[np.clip(np.rint(yy[vis]), 0, H - 1).astype(int), np.clip(np.rint(xx[vis]), 0, W - 1).astype(int)]
    return float((d < tol).mean()), int(vis.sum())


def line_dists(p, L, margin=30):
    """每条模型线对每条检测线的 (rms 距离, 有效点数, 角度差)。"""
    out = {}
    for nm in NAMES:
        uv, dep = project(p, SEGP[nm])
        ok = np.isfinite(uv[:, 0]) & (dep > 0.1)
        if ok.sum() < 5: continue
        u = uv[ok]
        dirv = u[-1] - u[0]; nrm = np.linalg.norm(dirv)
        if nrm < 20: continue
        dirv /= nrm
        res = []
        for j in range(len(L)):
            n0, n1, rho, x0, y0, x1, y1, npts = L[j]
            cosang = abs(dirv[0] * (-n1) + dirv[1] * n0)
            if cosang < 0.985: continue      # > 10 度
            s = u[:, 0] * (-n1) + u[:, 1] * n0
            s0, s1 = sorted([x0 * (-n1) + y0 * n0, x1 * (-n1) + y1 * n0])
            w = (s >= s0 - margin) & (s <= s1 + margin)
            if w.sum() < 3: continue
            # 重叠长度占检测线长度的比例
            scr = (u[:, 0] > 0) & (u[:, 0] < W) & (u[:, 1] > 0) & (u[:, 1] < H)
            if scr.sum() < 3: continue
            mlen = s[scr].max() - s[scr].min()
            ovl = min(s1, s[scr].max()) - max(s0, s[scr].min())
            if ovl < 0.5 * min(max(s1 - s0, 1), max(mlen, 1)) or ovl < 40: continue
            d = u[w, 0] * n0 + u[w, 1] * n1 - rho
            res.append((float(np.sqrt(np.mean(d ** 2))), j, float(np.degrees(np.arccos(min(cosang, 1))))))
        if res: out[nm] = sorted(res)
    return out


def associate(p, L, thr):
    cand = line_dists(p, L)
    pairs = sorted([(r[0], nm, r[1]) for nm, rs in cand.items() for r in rs if r[0] < thr])
    used_m, used_l, a = set(), set(), {}
    for d, nm, j in pairs:
        if nm in used_m or j in used_l: continue
        a[nm] = j; used_m.add(nm); used_l.add(j)
    return a


def solve_assign(p0, L, a):
    names = list(a.keys())
    def res(q):
        out = []
        for nm in names:
            n0, n1, rho, x0, y0, x1, y1, _ = L[a[nm]]
            uv, dep = project(q, SEGP[nm])
            dist = uv[:, 0] * n0 + uv[:, 1] * n1 - rho
            s = uv[:, 0] * (-n1) + uv[:, 1] * n0
            s0, s1 = sorted([x0 * (-n1) + y0 * n0, x1 * (-n1) + y1 * n0])
            w = (np.isfinite(dist) & (s >= s0 - 5) & (s <= s1 + 5)).astype(float)
            if w.sum() < 3: w = np.isfinite(dist).astype(float)
            out.append(np.where(np.isfinite(dist), dist, 50.0) * w / np.sqrt(max(w.sum(), 1)))
        return np.concatenate(out)
    r = least_squares(res, np.array(p0, float), x_scale=[1, 1, 1, 3, 3, 5.0], loss='soft_l1', f_scale=2.0, max_nfev=80)
    rr = res(r.x).reshape(len(names), -1)
    per = np.sqrt((rr ** 2).sum(1))
    try:
        sig = 0.5 * np.sqrt(np.diag(np.linalg.inv(r.jac.T @ r.jac)))
    except Exception:
        sig = np.full(6, 99.0)
    return r.x, dict(zip(names, per)), sig


def fit(p0, L, dm, thrs=(16, 6, 3.5)):
    p = np.array(p0, float); a = {}; per = {}; sig = np.full(6, 99.0)
    bad = lambda a, nH, nO: dict(n=len(a), nH=nH, nO=nO, rms=99.0, ok=False, a=a, inl=0.0, nvis=0, sig=sig)
    for thr in thrs:
        a = associate(p, L, thr)
        nH = sum(1 for n in a if n in HFAM); nO = len(a) - nH
        if len(a) < 4 or nH < 2 or nO < 2: return p, bad(a, nH, nO)
        p, per, sig = solve_assign(p, L, a)
    a = {k: v for k, v in a.items() if per[k] < 3.0}
    nH = sum(1 for n in a if n in HFAM); nO = len(a) - nH
    if len(a) < 4 or nH < 2 or nO < 2: return p, bad(a, nH, nO)
    p, per, sig = solve_assign(p, L, a)
    rms = float(np.sqrt(np.mean(np.array(list(per.values())) ** 2)))
    sane = 0.8 < p[1] < 16 and 2 < p[2] < 40 and 6 < p[5] < 80 and -3 < p[3] < 70 and abs(p[4]) < 50
    inl, nvis = verify(p, dm)
    ok = bool(sane and rms < 1.6 and len(a) >= 5 and nH >= 2 and nO >= 3 and inl > 0.78 and nvis >= 60 and sig[5] < 2.5)
    return p, dict(n=len(a), nH=nH, nO=nO, rms=rms, ok=ok, a=a, inl=inl, nvis=nvis, sig=sig)


def fit_bank(L, dm, bank):
    best = None
    for b in bank:
        p, q = fit(b, L, dm, thrs=(30, 12, 5, 3.5))
        v = (q['ok'], round(q['inl'] * min(q['nvis'], 400)) + 20 * q['n'])
        if best is None or v > best[0]: best = (v, p, q)
        if q['ok'] and q['n'] >= 8 and q['inl'] > 0.9: break
    return best[1], best[2]


def row(f, p, q):
    pr = p if p is not None else np.full(6, np.nan)
    return [f, f / FPS] + list(pr) + [q['n'], q['nH'], q['nO'], q['rms'], q['inl'], q['nvis'], q['sig'][5], q['sig'][2], int(q['ok'])]

BADQ = dict(n=0, nH=0, nO=0, rms=99.0, ok=False, inl=0.0, nvis=0, sig=np.full(6, 99.0))
HDR = 'f,t,cx,cy,cz,pitch,yaw,fov,nmatch,nH,nO,rms,inl,nvis,sig_fov,sig_z,ok'

def qual(q):
    return (bool(q['ok']), round(q['inl'] * min(q['nvis'], 400)) + 20 * q['n'])


def run(f0, f1, step, out, p0=None, verbose=True):
    import A2_init as I
    rows = []; store = []; p = None if p0 is None else np.array(p0, float); t0 = time.time()
    for f, rgb in frames(f0, f1, step):
        L, dm = detect(rgb)
        q = BADQ; pn = p; src = 0
        if len(L) >= 4:
            if p is not None:
                pn, q = fit(p, L, dm); src = 1
            if (not q['ok']) or q['inl'] < 0.9 or q['n'] < 7:
                pi, qi = I.solve_init(L, dm)
                if pi is not None and qual(qi) > qual(q): pn, q = pi, qi; src = 2
        if q['ok']: p = pn
        rows.append(row(f, pn, q) + [src]); store.append((L, dm.astype(np.float16)))
        if verbose and (len(rows) % 25 == 1):
            pr = rows[-1][2:8]
            print('f%5d t%6.2f p %6.2f %5.2f %6.2f pit %5.2f yaw %6.2f fov %5.2f n %2d (%d/%d) rms %.2f inl %.2f %s  [%.0fs]' % (f, f / FPS, *pr, q['n'], q['nH'], q['nO'], q['rms'], q['inl'], 'ok' if q['ok'] else 'BAD', time.time() - t0), flush=True)
    # 反向补洞：从后一个成功帧的位姿向前回填
    nfix = 0
    for k in range(len(rows) - 2, -1, -1):
        if rows[k][-2] == 0 and rows[k + 1][-2] == 1:
            L, dm = store[k]
            if len(L) >= 4:
                pn, q = fit(np.array(rows[k + 1][2:8]), L, dm.astype(np.float32))
                if q['ok']: rows[k] = row(rows[k][0], pn, q) + [3]; nfix += 1
    np.savetxt(out, np.array(rows, float), delimiter=',', fmt='%.4f', header=HDR + ',src', comments='')
    a = np.array(rows, float); print('done %d frames, ok %.1f%% (backfill %d), %.0fs' % (len(a), 100 * a[:, -2].mean(), nfix, time.time() - t0))

if __name__ == '__main__':
    f0, f1, step, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    p0 = [float(v) for v in sys.argv[5:11]] if len(sys.argv) >= 11 else None
    run(f0, f1, step, out, p0)
