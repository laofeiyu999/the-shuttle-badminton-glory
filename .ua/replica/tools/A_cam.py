# -*- coding: utf-8 -*-
"""任务 A 相机标定库：白线掩膜 + 球场线模型 + 针孔相机拟合（chamfer）。
坐标系（任务约定）：原点=球网中心地面；x 向右（从本方看向球网时的右手边）；y 向上；
z 指向本方底线后方（本方半场 z>0，对方半场 z<0）。右手系。
相机参数 p = (cx, cy, cz, pitch_deg(俯角, 向下为正), yaw_deg(向右转为正), vfov_deg)，roll=0。
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import least_squares

W, H = 1922, 880
S = 2                      # 掩膜降采样倍数
WS, HS = W // S, H // S
TAU = 7.0                  # chamfer 截断（降采样像素）

# ---------------- 球场线模型 ----------------
HALF_L = 6.70
HALF_WD = 3.05             # 双打边线
HALF_WS = 2.59             # 单打边线
Z_SHORT = 1.98             # 前发球线
Z_LONG = 6.70 - 0.76       # 双打后发球线


def court_segments(z_short=Z_SHORT, half_ws=HALF_WS, z_long=Z_LONG, half_wd=HALF_WD, half_l=HALF_L):
    s = []
    for x in (-half_wd, half_wd, -half_ws, half_ws):
        s.append(((x, 0, -half_l), (x, 0, half_l)))
    for z in (-half_l, half_l, -z_long, z_long, -z_short, z_short):
        s.append(((-half_wd, 0, z), (half_wd, 0, z)))
    s.append(((0, 0, z_short), (0, 0, half_l)))
    s.append(((0, 0, -half_l), (0, 0, -z_short)))
    return s


def sample_segments(segs, step=0.12):
    pts = []
    sid = []
    for k, (a, b) in enumerate(segs):
        a = np.array(a, float); b = np.array(b, float)
        n = max(2, int(np.linalg.norm(b - a) / step) + 1)
        t = np.linspace(0, 1, n)[:, None]
        pts.append(a + (b - a) * t)
        sid.append(np.full(n, k))
    return np.vstack(pts), np.concatenate(sid)


SEGS = court_segments()
PTS, SID = sample_segments(SEGS)


# ---------------- 投影 ----------------
def basis(pitch_deg, yaw_deg):
    th = np.radians(pitch_deg); ps = np.radians(yaw_deg)
    f = np.array([np.sin(ps) * np.cos(th), -np.sin(th), -np.cos(ps) * np.cos(th)])
    r = np.array([np.cos(ps), 0.0, np.sin(ps)])
    u = np.array([np.sin(th) * np.sin(ps), np.cos(th), -np.sin(th) * np.cos(ps)])
    return r, u, f


def project(p, P):
    """世界点 P (N,3) → 屏幕像素 (N,2)（全分辨率，原点左上），以及深度。"""
    cx, cy, cz, pitch, yaw, fov = p
    r, u, f = basis(pitch, yaw)
    v = P - np.array([cx, cy, cz])
    d = v @ f
    F = (H / 2) / np.tan(np.radians(fov) / 2)
    dd = np.where(d > 0.05, d, np.nan)
    xs = W / 2 + F * (v @ r) / dd
    ys = H / 2 - F * (v @ u) / dd
    return np.stack([xs, ys], 1), d


def unproject_ground(p, xy, y0=0.0):
    """屏幕像素 → 高度 y0 平面上的世界点。"""
    cx, cy, cz, pitch, yaw, fov = p
    r, u, f = basis(pitch, yaw)
    F = (H / 2) / np.tan(np.radians(fov) / 2)
    xy = np.atleast_2d(np.asarray(xy, float))
    dirs = f[None] + ((xy[:, 0] - W / 2) / F)[:, None] * r[None] - ((xy[:, 1] - H / 2) / F)[:, None] * u[None]
    t = (y0 - cy) / dirs[:, 1]
    return np.array([cx, cy, cz])[None] + dirs * t[:, None]


# ---------------- 掩膜 ----------------
# HUD 遮挡区（全分辨率像素）：三键、右上、左上两条分数带、能量条
HUD_BOXES = [(1350, 330, 1922, 880), (1540, 0, 1922, 160), (0, 30, 560, 100), (0, 165, 560, 255), (740, 770, 1190, 840)]


def court_region(blue):
    """最大的蓝色连通域（闭运算后）= 球场本体；用于排除远端大屏里的“球场画面”。"""
    b = ndi.binary_closing(blue, structure=np.ones((5, 5)), iterations=2)
    lab, n = ndi.label(b)
    if n == 0:
        return np.zeros_like(blue)
    sz = ndi.sum(b, lab, np.arange(1, n + 1))
    k = int(np.argmax(sz)) + 1
    reg = lab == k
    # 并入紧邻的大块（球网/人物把球场切开时）
    big = np.nonzero(sz >= 0.12 * sz[k - 1])[0] + 1
    regd = ndi.binary_dilation(reg, iterations=14)
    for j in big:
        if j != k and (regd & (lab == j)).any():
            reg |= lab == j
    return reg


def line_mask(rgb_half):
    """rgb_half: (HS,WS,3) uint8（已降采样）。返回 (白线掩膜, 球场蓝掩膜)。"""
    a = rgb_half.astype(np.int16)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    wv = np.minimum(R, G)
    blue = (B > 150) & (R < 125) & (B - R > 70) & (B - G > 40)
    op = ndi.grey_opening(wv, size=(9, 9))
    th = wv - op
    reg = court_region(blue)
    near = ndi.binary_dilation(reg, iterations=7)
    m = (th > 45) & (wv > 120) & (B > 140) & near
    for (x0, y0, x1, y1) in HUD_BOXES:
        m[y0 // S:y1 // S, x0 // S:x1 // S] = False
    return m, reg


def dist_map(mask):
    d = ndi.distance_transform_edt(~mask)
    return np.minimum(d, TAU).astype(np.float32)


def sample_bilinear(img, x, y):
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    x0c = np.clip(x0, 0, img.shape[1] - 2); y0c = np.clip(y0, 0, img.shape[0] - 2)
    a = img[y0c, x0c]; b = img[y0c, x0c + 1]; c = img[y0c + 1, x0c]; d = img[y0c + 1, x0c + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


HUDMASK = np.zeros((HS, WS), bool)
for (x0, y0, x1, y1) in HUD_BOXES:
    HUDMASK[y0 // S:y1 // S, x0 // S:x1 // S] = True


def residuals(p, dm, pts=None, valid_out=None):
    pts = PTS if pts is None else pts
    xy, d = project(p, pts)
    x = xy[:, 0] / S; y = xy[:, 1] / S
    ins = (d > 0.05) & (x >= 1) & (x < WS - 2) & (y >= 1) & (y < HS - 2)
    res = np.full(len(pts), TAU, np.float64)
    xi = np.where(ins, x, 1); yi = np.where(ins, y, 1)
    v = sample_bilinear(dm, xi, yi)
    hud = HUDMASK[np.clip(yi.astype(int), 0, HS - 1), np.clip(xi.astype(int), 0, WS - 1)]
    res[ins] = v[ins]
    res[ins & hud] = TAU * 0.5       # HUD 下：不奖不罚
    if valid_out is not None:
        valid_out.append(ins & ~hud)
    return res


def score(p, dm):
    vo = []
    r = residuals(p, dm, valid_out=vo)
    v = vo[0]
    nvis = int(v.sum())
    hit = float((r[v] < 1.5).mean()) if nvis else 0.0
    return float(r.mean()), nvis, hit


X_SCALE = np.array([0.5, 0.5, 0.5, 2.0, 2.0, 3.0])
LO = np.array([-9, 0.8, 0.5, -5, -60, 8.0])
HI = np.array([9, 16, 26, 80, 60, 75.0])


def refine(p0, dm, fix_fov=None, prior=None, prior_w=None):
    p0 = np.clip(np.array(p0, float), LO + 1e-6, HI - 1e-6)

    def fun(q):
        p = q.copy()
        if fix_fov is not None:
            p[5] = fix_fov
        r = residuals(p, dm)
        if prior is not None:
            r = np.concatenate([r, (p - prior) * prior_w])
        return r
    best = None
    for ds in (3e-3, 1e-3):
        sol = least_squares(fun, p0, x_scale=X_SCALE, diff_step=ds * X_SCALE / np.maximum(np.abs(p0), 1e-3),
                            loss='soft_l1', f_scale=1.5, bounds=(LO, HI), max_nfev=60)
        p0 = sol.x
    p = sol.x.copy()
    if fix_fov is not None:
        p[5] = fix_fov
    return p


def global_init(dm, n=40000, seed=0, top=12, fix_fov=None, rng_box=None):
    rng = np.random.default_rng(seed)
    lo = np.array([-5, 1.5, 3, 8, -30, 18.0]); hi = np.array([5, 10, 18, 60, 30, 60.0])
    if rng_box is not None:
        lo, hi = rng_box
    cand = lo + (hi - lo) * rng.random((n, 6))
    if fix_fov is not None:
        cand[:, 5] = fix_fov
    sub = PTS[::3]
    sc = np.array([residuals(c, dm, sub).mean() for c in cand])
    idx = np.argsort(sc)[:top]
    best = None
    for i in idx:
        p = refine(cand[i], dm, fix_fov)
        s, nv, hit = score(p, dm)
        if best is None or s < best[1]:
            best = (p, s, nv, hit)
    return best


def draw_overlay(rgb_full, p, color=(255, 0, 255), segs=None, extra=None):
    from PIL import Image, ImageDraw
    im = Image.fromarray(rgb_full).copy()
    d = ImageDraw.Draw(im)
    for a, b in (segs or SEGS):
        P, _ = sample_segments([(a, b)], 0.3)
        xy, dep = project(p, P)
        ok = dep > 0.05
        pl = [tuple(q) for q, o in zip(xy, ok) if o and -3000 < q[0] < 5000 and -3000 < q[1] < 4000]
        if len(pl) > 1:
            d.line(pl, fill=color, width=1)
    if extra:
        for (a, b, col) in extra:
            xy, dep = project(p, np.array([a, b], float))
            if (dep > 0.05).all():
                d.line([tuple(xy[0]), tuple(xy[1])], fill=col, width=1)
    return im


# ---------------- 双向代价（防止模型塌缩到局部） ----------------
XL_ALL = np.array([-HALF_WD, HALF_WD, -HALF_WS, HALF_WS])
ZL_ALL = np.array([-HALF_L, HALF_L, -Z_LONG, Z_LONG, -Z_SHORT, Z_SHORT])
TW = 0.35   # 世界距离截断 (m)


def world_line_dist(x, z):
    """地面点到最近球场线的距离 (m)。"""
    big = 9.0
    inz = np.abs(z) <= HALF_L + 0.05
    dx = np.abs(x[:, None] - XL_ALL[None]).min(1)
    dx = np.where(inz, dx, big)
    inc = (np.abs(z) >= Z_SHORT - 0.05) & inz
    dc = np.where(inc, np.abs(x), big)
    inx = np.abs(x) <= HALF_WD + 0.05
    dz = np.abs(z[:, None] - ZL_ALL[None]).min(1)
    dz = np.where(inx, dz, big)
    # 线端点外：到球场矩形的距离
    ox = np.maximum(np.abs(x) - HALF_WD, 0); oz = np.maximum(np.abs(z) - HALF_L, 0)
    dout = np.hypot(ox, oz)
    d = np.minimum(np.minimum(dx, dc), dz)
    d = np.where((ox > 0) | (oz > 0), np.maximum(dout, 0) + 0.0 * d, d)
    return d


def mask_points(mask, nmax=1500, seed=0):
    """从掩膜取样像素点（去掉小连通域），返回全分辨率像素坐标 (N,2)。"""
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        return np.zeros((0, 2))
    sz = ndi.sum(mask, lab, np.arange(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = sz >= 40
    m2 = keep[lab]
    ys, xs = np.nonzero(m2)
    if len(xs) > nmax:
        idx = np.random.default_rng(seed).choice(len(xs), nmax, replace=False)
        xs, ys = xs[idx], ys[idx]
    return np.stack([xs * S + S / 2.0, ys * S + S / 2.0], 1)


def res_back(p, mpts):
    """掩膜点 → 地面，到最近球场线的世界距离；同时允许解释为球网上沿白带（z=0, y≈1.54）。"""
    if len(mpts) == 0:
        return np.zeros(0)
    cx, cy, cz, pitch, yaw, fov = p
    r, u, f = basis(pitch, yaw)
    F = (H / 2) / np.tan(np.radians(fov) / 2)
    dirs = f[None] + ((mpts[:, 0] - W / 2) / F)[:, None] * r[None] - ((mpts[:, 1] - H / 2) / F)[:, None] * u[None]
    dy = np.where(dirs[:, 1] < -1e-6, dirs[:, 1], -1e-6)
    t = -cy / dy
    gx = cx + dirs[:, 0] * t; gz = cz + dirs[:, 2] * t
    d = world_line_dist(gx, gz)
    d = np.where(dirs[:, 1] < -1e-6, d, 9.0)
    dz = np.where(dirs[:, 2] < -1e-6, dirs[:, 2], -1e-6)
    tn = -cz / dz
    nx = cx + dirs[:, 0] * tn; ny = cy + dirs[:, 1] * tn
    dn = np.hypot(np.maximum(np.abs(nx) - 3.15, 0), ny - 1.54)
    dn = np.where(dirs[:, 2] < -1e-6, dn, 9.0)
    d = np.minimum(d, dn * 2.0)
    return np.minimum(d, TW) / TW * TAU


def res_both(p, dm, mpts, wb=1.0):
    a = residuals(p, dm)
    b = res_back(p, mpts) * wb
    return np.concatenate([a, b * np.sqrt(len(a) / max(len(b), 1))])


def cost_both(p, dm, mpts, pts=None):
    a = residuals(p, dm, pts)
    b = res_back(p, mpts)
    return a.mean() + (b.mean() if len(b) else TAU)


def refine2(p0, dm, mpts, fix_fov=None, prior=None, prior_w=None, max_nfev=50, stages=(2e-2, 5e-3)):
    p0 = np.clip(np.array(p0, float), LO + 1e-6, HI - 1e-6)

    def fun(q):
        p = q.copy()
        if fix_fov is not None:
            p[5] = fix_fov
        r = res_both(p, dm, mpts)
        if prior is not None:
            r = np.concatenate([r, (p - prior) * prior_w])
        return r
    sol = None
    for ds in stages:
        sol = least_squares(fun, p0, x_scale=X_SCALE, diff_step=ds * X_SCALE / np.maximum(np.abs(p0), 1e-2),
                            loss='soft_l1', f_scale=2.0, bounds=(LO, HI), max_nfev=max_nfev)
        p0 = sol.x
    p = sol.x.copy()
    if fix_fov is not None:
        p[5] = fix_fov
    return p


def global_init2(dm, mpts, n=20000, seed=0, top=10, box=None):
    rng = np.random.default_rng(seed)
    lo = np.array([-5, 1.5, 4, 8, -25, 18.0]); hi = np.array([5, 11, 20, 60, 25, 65.0])
    if box is not None:
        lo, hi = box
    cand = lo + (hi - lo) * rng.random((n, 6))
    sub = PTS[::4]; ms = mpts[::4]
    sc = np.array([cost_both(c, dm, ms, sub) for c in cand])
    idx = np.argsort(sc)[:top]
    best = None
    for i in idx:
        p = refine2(cand[i], dm, mpts)
        s = cost_both(p, dm, mpts)
        if best is None or s < best[1]:
            best = (p, s)
    return best


def fit_quality(p, dm, mpts):
    vo = []
    a = residuals(p, dm, valid_out=vo)
    v = vo[0]
    b = res_back(p, mpts)
    return dict(fwd=float(a[v].mean()) if v.any() else TAU, nvis=int(v.sum()),
                hit=float((a[v] < 1.5).mean()) if v.any() else 0.0,
                back=float(b.mean()) if len(b) else TAU, back_hit=float((b < TAU * 0.25).mean()) if len(b) else 0.0)


# ---------------- Hough 初始化（线对枚举 → 单应 → 相机） ----------------
def hough_lines(mask, nmax=10, min_votes=60):
    """返回直线列表 (nx, ny, rho, votes)，nx*x+ny*y=rho，坐标为降采样像素。"""
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        return []
    sz = ndi.sum(mask, lab, np.arange(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = sz >= 40
    ys, xs = np.nonzero(keep[lab])
    if len(xs) < 50:
        return []
    th = np.radians(np.arange(0, 180, 0.5))
    c, s = np.cos(th), np.sin(th)
    rho = xs[:, None] * c[None] + ys[:, None] * s[None]
    R = int(np.hypot(WS, HS)) + 2
    ri = np.round(rho).astype(int) + R
    acc = np.zeros((len(th), 2 * R + 1), np.int32)
    ti = np.broadcast_to(np.arange(len(th))[None], ri.shape)
    np.add.at(acc, (ti.ravel(), ri.ravel()), 1)
    accs = ndi.uniform_filter(acc.astype(np.float32), (3, 3), mode='wrap') * 9
    out = []
    a = accs.copy()
    for _ in range(nmax):
        k = a.argmax(); t0, r0 = np.unravel_index(k, a.shape)
        if a[t0, r0] < min_votes:
            break
        nx, ny, rr = c[t0], s[t0], r0 - R
        # 用邻近点最小二乘细化
        d = xs * nx + ys * ny - rr
        sel = np.abs(d) < 3
        if sel.sum() >= 30:
            px, py = xs[sel].astype(float), ys[sel].astype(float)
            mx, my = px.mean(), py.mean()
            u, sv, vt = np.linalg.svd(np.stack([px - mx, py - my], 1), full_matrices=False)
            nrm = vt[1]
            ext = sv[0] / np.sqrt(len(px))
            if nrm @ np.array([nx, ny]) < 0: nrm = -nrm
            out.append((nrm[0], nrm[1], nrm[0] * mx + nrm[1] * my, int(sel.sum()), ext))
        # 抑制
        for dt in range(-8, 9):
            tt = (t0 + dt) % len(th)
            rc = r0 if (0 <= t0 + dt < len(th)) else 2 * R - r0
            a[tt, max(0, rc - 14):rc + 15] = 0
    return out


def _isect(l1, l2):
    A = np.array([[l1[0], l1[1]], [l2[0], l2[1]]]); b = np.array([l1[2], l2[2]])
    if abs(np.linalg.det(A)) < 1e-6:
        return None
    return np.linalg.solve(A, b)


def _homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A))
    return vt[-1].reshape(3, 3)


GXZ = PTS[:, [0, 2]]
XVALS = [-HALF_WD, -HALF_WS, 0.0, HALF_WS, HALF_WD]
ZVALS = [-HALF_L, -Z_LONG, -Z_SHORT, Z_SHORT, Z_LONG, HALF_L]


def _score_H(Hm, dm, mpts_s):
    q = np.c_[GXZ[::3], np.ones(len(GXZ[::3]))] @ Hm.T
    w = q[:, 2]
    if (w > 0).mean() < 0.5:
        Hm = -Hm; w = -w; q = -q
    ok = w > 1e-9
    x = np.where(ok, q[:, 0] / np.where(ok, w, 1), -1); y = np.where(ok, q[:, 1] / np.where(ok, w, 1), -1)
    ins = ok & (x >= 1) & (x < WS - 2) & (y >= 1) & (y < HS - 2)
    if ins.sum() < 40:
        return 1e9
    res = np.full(len(x), TAU)
    v = sample_bilinear(dm, np.where(ins, x, 1), np.where(ins, y, 1))
    hud = HUDMASK[np.clip(y.astype(int), 0, HS - 1), np.clip(x.astype(int), 0, WS - 1)]
    res[ins] = v[ins]; res[ins & hud] = TAU * 0.5
    fwd = res.mean()
    # 反向：掩膜点回到地面
    try:
        Hi = np.linalg.inv(Hm)
    except Exception:
        return 1e9
    g = np.c_[mpts_s / S, np.ones(len(mpts_s))] @ Hi.T
    gw = g[:, 2]
    gx = g[:, 0] / np.where(np.abs(gw) > 1e-12, gw, 1e-12); gz = g[:, 1] / np.where(np.abs(gw) > 1e-12, gw, 1e-12)
    d = world_line_dist(gx, gz)
    back = (np.minimum(d, TW) / TW * TAU).mean()
    return fwd + back


def cam_from_H(Hm):
    """地面单应（世界(x,z)→降采样像素）解析分解为 6 参数相机。返回 (p, roll_err) 或 None。
    M = diag(F,F,1)·[R[:,x], R[:,z], -R·C]，相机坐标 (右, 上, 前)。"""
    T = np.array([[S, 0, -W / 2.0], [0, -S, H / 2.0], [0, 0, 1.0]])
    M = T @ Hm
    m1, m2, m3 = M[:, 0], M[:, 1], M[:, 2]
    den = m1[2] * m2[2]
    F2 = -(m1[0] * m2[0] + m1[1] * m2[1]) / den if abs(den) > 1e-12 else -1
    if not (F2 > 0):
        d2 = m1[2] ** 2 - m2[2] ** 2
        F2 = (m2[0] ** 2 + m2[1] ** 2 - m1[0] ** 2 - m1[1] ** 2) / d2 if abs(d2) > 1e-12 else -1
    if not (F2 > 0):
        return None
    F = np.sqrt(F2)
    Ki = np.diag([1 / F, 1 / F, 1.0])
    a = Ki @ m1; b = Ki @ m2; c = Ki @ m3
    lam = (np.linalg.norm(a) + np.linalg.norm(b)) / 2
    if lam < 1e-12:
        return None
    for sgn in (1, -1):
        rx = a / lam * sgn; rz = b / lam * sgn
        rx /= np.linalg.norm(rx); rz = rz - rx * (rx @ rz); rz /= np.linalg.norm(rz)
        ry = -np.cross(rz, rx)
        R = np.stack([rx, ry, rz], 1)          # 列 = 世界轴在相机坐标下
        Cw = -R.T @ (c / lam * sgn)
        if Cw[1] > 0:
            break
    fwd = R[2]; right = R[0]
    pitch = np.degrees(np.arcsin(np.clip(-fwd[1], -1, 1)))
    yaw = np.degrees(np.arctan2(fwd[0], -fwd[2]))
    fov = 2 * np.degrees(np.arctan((H / 2) / F))
    p = np.array([Cw[0], Cw[1], Cw[2], pitch, yaw, fov])
    return p, abs(right[1])


def plausible(p, roll):
    return (roll < 0.10 and 0.8 <= p[1] <= 16 and 1.0 <= p[2] <= 28 and abs(p[0]) <= 10
            and -5 <= p[3] <= 80 and abs(p[4]) <= 60 and 8 <= p[5] <= 75)


def _split_families(lines):
    """按方向角把直线分成两族（找角度环上最大的两个空隙）。"""
    ang = np.array([np.degrees(np.arctan2(l[1], l[0])) % 180 for l in lines])
    o = np.argsort(ang); a = ang[o]
    gaps = np.diff(np.r_[a, a[0] + 180])
    g = np.argsort(gaps)[::-1][:2]
    g.sort()
    A = [lines[o[k]] for k in range(g[0] + 1, g[1] + 1)]
    B = [lines[o[k]] for k in list(range(g[1] + 1, len(a))) + list(range(0, g[0] + 1))]
    return A, B


def _enum(lon, tra, dm, ms, maxl=5):
    lon = sorted(lon, key=lambda l: -l[3])[:maxl]
    tra = sorted(tra, key=lambda l: -l[3])[:maxl + 1]
    yref = HS * 0.8
    lon.sort(key=lambda l: (l[2] - l[1] * yref) / (l[0] if abs(l[0]) > 1e-6 else 1e-6))
    tra.sort(key=lambda l: (l[2] - l[0] * WS / 2) / (l[1] if abs(l[1]) > 1e-6 else 1e-6))
    cands = []
    for i in range(len(lon)):
        for j in range(i + 1, len(lon)):
            for a in range(len(tra)):
                for b in range(a + 1, len(tra)):
                    pts = [_isect(lon[i], tra[a]), _isect(lon[j], tra[a]), _isect(lon[i], tra[b]), _isect(lon[j], tra[b])]
                    if any(p is None for p in pts):
                        continue
                    for xi in range(5):
                        for xj in range(xi + 1, 5):
                            for za in range(6):
                                for zb in range(za + 1, 6):
                                    src = [(XVALS[xi], ZVALS[za]), (XVALS[xj], ZVALS[za]), (XVALS[xi], ZVALS[zb]), (XVALS[xj], ZVALS[zb])]
                                    Hm = _homography(src, pts)
                                    cands.append((_score_H(Hm, dm, ms), Hm))
    return cands


def hough_init(mask, dm, mpts, topk=3, verbose=False):
    lines = hough_lines(mask)
    if len(lines) < 4:
        return None
    A, B = _split_families(lines)
    if verbose:
        print('lines', len(lines), 'A', len(A), 'B', len(B))
    if len(A) < 2 or len(B) < 2:
        return None
    ms = mpts[::3]
    cands = _enum(A, B, dm, ms) + _enum(B, A, dm, ms)
    cands.sort(key=lambda c: c[0])
    best = None
    tried = 0
    for sc, Hm in cands[:400]:
        r = cam_from_H(Hm)
        if r is None or not plausible(*r):
            continue
        p = refine2(r[0], dm, mpts)
        c = cost_both(p, dm, mpts)
        if verbose:
            print('  cand sc %.2f roll %.3f cost %.2f' % (sc, r[1], c), np.round(r[0], 2), np.round(p, 2))
        if best is None or c < best[1]:
            best = (p, c)
        tried += 1
        if tried >= topk:
            break
    return best
