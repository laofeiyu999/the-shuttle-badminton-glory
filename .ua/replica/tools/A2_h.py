# -*- coding: utf-8 -*-
"""A2_h.py：全自动单帧相机标定。
流程：颜色门控白线脊点 -> 快速 Hough -> 两族直线(横/纵)两两配对到球场模型线 -> 批量单应假设打分
 -> 单应分解得 (位置, 俯角, 偏航, FOV) 初值 -> 截断倒角距离最小二乘精修（地面线 + 网顶线）。
用法：python A2_h.py f [f...]  打印解并存叠加图 A2_ov_<f>.jpg
"""
import sys, os, itertools
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy import ndimage as ndi
from A2_cam import W, H, hud_ok, get_frame, project, overlay, FR, bilin, HALF_L, DIM
from A2_auto import gated_mask, dmap, Auto

NTH = 360
TH = np.radians(np.arange(NTH) * 0.5)
CT, ST = np.cos(TH), np.sin(TH)
RMAX = int(np.hypot(W, H)) + 2
NR = 2 * RMAX + 1


def fast_hough(xs, ys, nmax=30, min_votes=40, tol=1.8, min_cov=70):
    n = len(xs)
    if n < 50: return []
    rho = np.rint(xs[:, None] * CT[None] + ys[:, None] * ST[None]).astype(np.int64) + RMAX
    key = rho + (np.arange(NTH) * NR)[None]
    acc = np.bincount(key.ravel(), minlength=NTH * NR).reshape(NTH, NR).astype(np.int32)
    alive = np.ones(n, bool); out = []
    for _ in range(nmax):
        a2 = acc[:, :-2] + acc[:, 1:-1] + acc[:, 2:]
        k = int(a2.argmax()); t, r = divmod(k, NR - 2)
        if a2[t, r] < min_votes: break
        th = TH[t]; rr = r + 1 - RMAX
        nv = np.array([np.cos(th), np.sin(th)])
        d = xs * nv[0] + ys * nv[1] - rr
        inl = alive & (np.abs(d) < 3.5)
        for it in range(3):
            if inl.sum() < 12: break
            X = np.stack([xs[inl], ys[inl]], 1); c = X.mean(0)
            vt = np.linalg.svd(X - c, full_matrices=False)[2]
            nv = vt[1]
            if nv[1] < 0 or (abs(nv[1]) < 1e-9 and nv[0] < 0): nv = -nv
            rr = float(c @ nv)
            d = xs * nv[0] + ys * nv[1] - rr
            inl = alive & (np.abs(d) < tol)
        kill = alive & (np.abs(d) < 3.5)
        if inl.sum() >= 12:
            dv = np.array([-nv[1], nv[0]]); s = xs[inl] * dv[0] + ys[inl] * dv[1]
            cov = len(np.unique(np.floor(s / 4))) * 4
            if cov >= min_cov:
                out.append(dict(n=nv.copy(), rho=rr, npts=int(inl.sum()), cov=float(cov), p0=nv * rr + dv * s.min(), p1=nv * rr + dv * s.max(), theta=float(np.degrees(np.arctan2(nv[1], nv[0])) % 180)))
        if kill.sum() == 0:
            acc[max(0, t - 2):t + 3, max(0, r - 3):r + 6] = 0; continue
        acc -= np.bincount(key[kill].ravel(), minlength=NTH * NR).reshape(NTH, NR).astype(np.int32)
        alive &= ~kill
    return out


def model_lines(dim=None):
    d = dim or DIM
    zs = [-HALF_L, -d['z_long'], -d['z_short'], d['z_short'], d['z_long'], HALF_L]
    xs = [-d['half_wd'], -d['half_ws'], 0.0, d['half_ws'], d['half_wd']]
    return xs, zs


def model_pts(dim=None, step=0.3):
    d = dim or DIM
    xs, zs = model_lines(d)
    P = []
    for x in xs:
        if x == 0:
            z = np.concatenate([np.arange(-HALF_L, -d['z_short'] + 1e-6, step), np.arange(d['z_short'], HALF_L + 1e-6, step)])
        else:
            z = np.arange(-HALF_L, HALF_L + 1e-6, step)
        P.append(np.stack([np.full_like(z, x), z], 1))
    for z in zs:
        x = np.arange(-d['half_wd'], d['half_wd'] + 1e-6, step)
        P.append(np.stack([x, np.full_like(x, z)], 1))
    return np.vstack(P)


def homog_batch(src, dst):
    """src,dst: (N,4,2) -> H (N,3,3) with H[2,2]=1"""
    N = len(src)
    A = np.zeros((N, 8, 8)); b = np.zeros((N, 8))
    X, Y = src[..., 0], src[..., 1]; u, v = dst[..., 0], dst[..., 1]
    for i in range(4):
        A[:, 2 * i, 0] = X[:, i]; A[:, 2 * i, 1] = Y[:, i]; A[:, 2 * i, 2] = 1
        A[:, 2 * i, 6] = -u[:, i] * X[:, i]; A[:, 2 * i, 7] = -u[:, i] * Y[:, i]; b[:, 2 * i] = u[:, i]
        A[:, 2 * i + 1, 3] = X[:, i]; A[:, 2 * i + 1, 4] = Y[:, i]; A[:, 2 * i + 1, 5] = 1
        A[:, 2 * i + 1, 6] = -v[:, i] * X[:, i]; A[:, 2 * i + 1, 7] = -v[:, i] * Y[:, i]; b[:, 2 * i + 1] = v[:, i]
    det = np.linalg.det(A); ok = np.abs(det) > 1e-9
    h = np.zeros((N, 8)); h[ok] = np.linalg.solve(A[ok], b[ok][..., None])[..., 0]
    Hm = np.concatenate([h, np.ones((N, 1))], 1).reshape(N, 3, 3)
    return Hm, ok


def decompose(Hm):
    """地面单应 (X,Z,1)->像素 分解为 p=(cx,cy,cz,pitch,yaw,fov)。失败返回 None。"""
    T = np.array([[1, 0, -W / 2], [0, 1, -H / 2], [0, 0, 1.0]])
    G = T @ Hm
    h1, h2, h3 = G[:, 0], G[:, 1], G[:, 2]
    fs = []
    den = h1[2] * h2[2]
    if abs(den) > 1e-12:
        f2 = -(h1[0] * h2[0] + h1[1] * h2[1]) / den
        if f2 > 0: fs.append(np.sqrt(f2))
    den = h1[2] ** 2 - h2[2] ** 2
    if abs(den) > 1e-12:
        f2 = -((h1[0] ** 2 + h1[1] ** 2) - (h2[0] ** 2 + h2[1] ** 2)) / den
        if f2 > 0: fs.append(np.sqrt(f2))
    if not fs: return None
    best = None
    for f in fs:
        Ki = np.diag([1 / f, 1 / f, 1.0])
        a, b, c = Ki @ h1, Ki @ h2, Ki @ h3
        lam = (np.linalg.norm(a) + np.linalg.norm(b)) / 2
        for sgn in (1, -1):
            r1, r2, t = sgn * a / lam, sgn * b / lam, sgn * c / lam
            r1 = r1 / np.linalg.norm(r1); r2 = r2 - r1 * (r1 @ r2); r2 = r2 / np.linalg.norm(r2)
            r3 = np.cross(r1, r2)
            R = np.stack([r1, r3, r2], 1)
            C = -R.T @ t          # (X, -Y, Z)
            cam = np.array([C[0], -C[1], C[2]])
            fw = np.array([R[2, 0], -R[2, 1], R[2, 2]])
            if cam[1] <= 0.2 or t[2] <= 0: continue
            pitch = np.degrees(np.arcsin(np.clip(-fw[1], -1, 1))); yaw = np.degrees(np.arctan2(fw[0], -fw[2]))
            fov = 2 * np.degrees(np.arctan((H / 2) / f))
            p = np.array([cam[0], cam[1], cam[2], pitch, yaw, fov])
            if best is None: best = p
    return best


def hypotheses(L, dm, dim=None, top=12, maxl=9):
    hz = [l for l in L if abs(l['theta'] - 90) < 25]
    ob = [l for l in L if abs(l['theta'] - 90) >= 25]
    hz = sorted(sorted(hz, key=lambda l: -l['npts'])[:maxl], key=lambda l: (l['rho'] - 961 * l['n'][0]) / l['n'][1])
    ob = sorted(sorted(ob, key=lambda l: -l['npts'])[:maxl], key=lambda l: (l['rho'] - 880 * l['n'][1]) / l['n'][0])
    if len(hz) < 2 or len(ob) < 2: return []
    mx, mz = model_lines(dim)
    def inter(l1, l2):
        A = np.array([l1['n'], l2['n']]); return np.linalg.solve(A, np.array([l1['rho'], l2['rho']]))
    src, dst = [], []
    hp = list(itertools.combinations(range(len(hz)), 2)); op = list(itertools.combinations(range(len(ob)), 2))
    zp = list(itertools.combinations(range(len(mz)), 2)); xp = list(itertools.combinations(range(len(mx)), 2))
    for (a, b) in hp:
        for (c, d) in op:
            try:
                q = [inter(ob[c], hz[a]), inter(ob[d], hz[a]), inter(ob[c], hz[b]), inter(ob[d], hz[b])]
            except Exception:
                continue
            for (z1, z2) in zp:
                for (x1, x2) in xp:
                    src.append([(mx[x1], mz[z1]), (mx[x2], mz[z1]), (mx[x1], mz[z2]), (mx[x2], mz[z2])]); dst.append(q)
    src = np.array(src); dst = np.array(dst)
    Hm, ok = homog_batch(src, dst)
    M = model_pts(dim, 0.4)
    Mh = np.concatenate([M, np.ones((len(M), 1))], 1)
    scores = np.full(len(Hm), -1e9)
    B = 20000
    for i in range(0, len(Hm), B):
        q = np.einsum('nij,mj->nmi', Hm[i:i + B], Mh)
        w = q[..., 2]
        good = w > 1e-6
        x = np.where(good, q[..., 0] / np.where(good, w, 1), -1); y = np.where(good, q[..., 1] / np.where(good, w, 1), -1)
        vis = good & (x >= 2) & (x < W - 2) & (y >= 2) & (y < H - 2)
        vis &= hud_ok(np.where(vis, x, 0), np.where(vis, y, 0))
        xi = np.clip(np.rint(x), 0, W - 1).astype(int); yi = np.clip(np.rint(y), 0, H - 1).astype(int)
        dd = dm[yi, xi]
        inl = vis & (dd < 3.5)
        scores[i:i + B] = inl.sum(1) - 0.8 * (vis & ~inl).sum(1) - 0.0 * (~vis).sum(1)
    scores[~ok] = -1e9
    order = np.argsort(-scores)[:top]
    return [(float(scores[k]), Hm[k]) for k in order]


_A = None
def solve_frame(rgb, dim=None, verbose=False, prior=None):
    global _A
    if _A is None or dim is not None: _A = Auto(dim, step=0.12)
    A = _A
    mk, _ = gated_mask(rgb)
    dm = dmap(mk)
    if prior is not None:
        p = A.refine(prior, dm, taus=(10, 5)); sc = A.score(p, dm)
        if sc['inl'] > 0.85 and sc['ngood'] >= max(4, sc['nlines'] - 2) and sc['nvis'] > 150:
            return p, sc, mk
    ys, xs = np.nonzero(mk)
    L = fast_hough(xs.astype(np.float32), ys.astype(np.float32))
    hyp = hypotheses(L, dm, dim)
    best = None; seen = []
    for s, Hm in hyp:
        p0 = decompose(Hm)
        if p0 is None or not (8 < p0[5] < 80 and 0.5 < p0[1] < 20 and -5 < p0[3] < 70): continue
        if any(np.allclose(p0, q, atol=0.05) for q in seen): continue
        seen.append(p0)
        p = A.refine(p0, dm, taus=(10, 5)); sc = A.score(p, dm)
        val = sc['inl'] * min(sc['nvis'], 600) + 30 * sc['ngood']
        if verbose: print('  hyp s %.0f p0 %s -> inl %.2f good %d/%d nvis %d' % (s, np.round(p0, 1), sc['inl'], sc['ngood'], sc['nlines'], sc['nvis']))
        if best is None or val > best[0]: best = (val, p, sc)
        if sc['inl'] > 0.9 and sc['ngood'] >= sc['nlines'] - 1 and sc['nvis'] > 300: break
        if len(seen) >= 6: break
    if best is None: return None, None, mk
    return best[1], best[2], mk


if __name__ == '__main__':
    import time
    for a in sys.argv[1:]:
        f = int(a); t0 = time.time(); rgb = get_frame(f)
        p, sc, mk = solve_frame(rgb, verbose=True)
        if p is None: print('f%d FAIL' % f); continue
        print('f%d t=%.2f (%.1fs) p= %.2f %.2f %.2f pitch %.2f yaw %.2f fov %.2f | nvis %d inl %.3f rms %.2f good %d/%d' % (f, f / 60., time.time() - t0, *p, sc['nvis'], sc['inl'], sc['rms'], sc['ngood'], sc['nlines']))
        print('   ' + ' '.join('%s:%d/%.2f' % (k, v[0], v[1]) for k, v in sc['per'].items()))
        o = rgb.copy(); o[mk] = (255, 255, 0)
        overlay(o, p, _A.F, os.path.join(FR, 'A2_ov_%05d.jpg' % f))
