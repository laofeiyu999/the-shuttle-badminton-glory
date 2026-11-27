# -*- coding: utf-8 -*-
"""全帧角色追踪（输出原始像素量，后处理见 B2_track_post.py）。
用法: python B2_track.py f0 f1 out.csv
背景: data/B2_bgseg.npy（每 1000 帧一段的中值背景，ROI y∈[540,1300)）
每帧每方(L=左半场, R=右半场)：身体团块（差分、去掉加亮型特效与影子）的面积/质心/包围盒，白鞋质心与底边，脚下青色圈中心；
全帧：场地线可见率 line_frac（镜头切换时下降）、与上一帧的平均差 mad（重复帧/顿帧检测）、强加亮像素数与质心（闪光检测）。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
from scipy import ndimage as ndi
Y0, Y1 = 540, 1300
CH = Y1 - Y0
NETX = 959
bgseg = np.load(os.path.join(DATA, "B2_bgseg.npy"))
med_full = np.load(os.path.join(DATA, "B2_bg_median.npy"))
linemask = (med_full.min(2) > 190) & ((med_full.max(2).astype(int) - med_full.min(2)) < 50)
linemask[:760] = False; linemask[1210:] = False
_ly, _lx = np.nonzero(linemask); _sel = np.arange(0, len(_ly), 7); LY, LX = _ly[_sel] - Y0, _lx[_sel]
excl = np.zeros((CH, W), bool)
excl[1010 - Y0:, :290] = True       # 左下角前景裁判
excl[1120 - Y0:, 860:1060] = True   # 网柱下主裁
excl[990 - Y0:, 1680:] = True       # 右下角前景观众
excl[:, 938:982] = True             # 网柱
excl[:770 - Y0 - 110, :] = False
ST = np.ones((3, 3), bool)
_cache = {}
def getbg(f):
    k = min(f // 1000, len(bgseg) - 1)
    if k not in _cache:
        _cache.clear()
        b = bgseg[k].astype(np.int16)
        _cache[k] = (b, (b * 0.60).astype(np.int16), (b * 0.96).astype(np.int16))
    return _cache[k]

def masks(a16, f):
    bg, lo, hi = getbg(f)
    d3 = a16 - bg
    diff = np.abs(d3).sum(2)
    fg = diff > 70
    additive = (d3.min(2) > -12)
    shadow = ((a16 >= lo) & (a16 <= hi)).all(2)
    body = fg & (~additive) & (~shadow) & (~excl)
    return bg, d3, diff, fg, additive, shadow, body

def analyze(a, f, prev):
    a16 = a.astype(np.int16)
    bg, d3, diff, fg, additive, shadow, body = masks(a16, f)
    mn = a16.min(2); mx = a16.max(2)
    r = {"line_frac": float((mn[LY, LX] > 150).mean())}
    # 强加亮（闪光）
    fl = (d3.sum(2) > 300) & (mn > 170)
    fl[:, :] &= True
    nfl = int(fl.sum()); r["fl_n"] = nfl
    if nfl > 30:
        fy, fx = np.nonzero(fl)
        r["fl_x"] = float(fx.mean()); r["fl_y"] = float(fy.mean() + Y0)
        r["fl_x0"] = float(np.percentile(fx, 2)); r["fl_x1"] = float(np.percentile(fx, 98))
        r["fl_y0"] = float(np.percentile(fy, 2) + Y0); r["fl_y1"] = float(np.percentile(fy, 98) + Y0)
    # 身体团块（1/4 分辨率连通域）
    b4 = body[: CH // 4 * 4, : W // 4 * 4].reshape(CH // 4, 4, W // 4, 4).sum((1, 3)) >= 5
    b4 = ndi.binary_dilation(b4, ST, iterations=2)
    lab, n = ndi.label(b4)
    if n == 0:
        return r
    sl = ndi.find_objects(lab)
    cnt = ndi.sum(body[: CH // 4 * 4, : W // 4 * 4].reshape(CH // 4, 4, W // 4, 4).sum((1, 3)), lab, np.arange(1, n + 1))
    for side, p in ((0, "L"), (1, "R")):
        best = None; bscore = 0
        for i in range(n):
            if cnt[i] < 900: continue
            ys, xs = sl[i]
            cxm = 2.0 * (xs.start + xs.stop)
            if (side == 0) != (cxm < NETX): continue
            bot = ys.stop * 4 + Y0
            if bot < 775: continue
            if (ys.stop - ys.start) * 4 > 420 or (xs.stop - xs.start) * 4 > 520: continue
            s = cnt[i]
            if prev[side] is not None:
                dd = np.hypot(cxm - prev[side][0], bot - prev[side][1])
                s = s / (1.0 + (dd / 80.0) ** 2)
            if s > bscore: bscore = s; best = i
        if best is None: continue
        ys, xs = sl[best]
        y0, y1, x0, x1 = ys.start * 4, ys.stop * 4, xs.start * 4, xs.stop * 4
        m = body[y0:y1, x0:x1] & np.repeat(np.repeat(lab[ys, xs] == best + 1, 4, 0), 4, 1)
        yy, xx = np.nonzero(m)
        if len(yy) < 500: continue
        r[p + "_n"] = len(yy); r[p + "_cx"] = float(xx.mean() + x0); r[p + "_cy"] = float(yy.mean() + y0 + Y0)
        top = np.percentile(yy, 0.5) + y0; bot = np.percentile(yy, 99.5) + y0
        r[p + "_top"] = float(top + Y0); r[p + "_bot"] = float(bot + Y0)
        r[p + "_x0"] = float(np.percentile(xx, 0.5) + x0); r[p + "_x1"] = float(np.percentile(xx, 99.5) + x0)
        # 躯干带（高度 25%~60%）质心
        hb = (yy + y0 > top + 0.25 * (bot - top)) & (yy + y0 < top + 0.60 * (bot - top))
        if hb.sum() > 50:
            r[p + "_tx"] = float(xx[hb].mean() + x0); r[p + "_ty"] = float(yy[hb].mean() + y0 + Y0)
        # 白鞋：团块下部附近的近白像素（非背景白线）
        wy0 = int(max(top + 0.55 * (bot - top), 0)); wy1 = int(min(bot + 40, CH)); wx0 = int(max(x0 - 40, 0)); wx1 = int(min(x1 + 40, W))
        sm = (mn[wy0:wy1, wx0:wx1] > 175) & ((mx[wy0:wy1, wx0:wx1] - mn[wy0:wy1, wx0:wx1]) < 55) & (diff[wy0:wy1, wx0:wx1] > 90) & (~excl[wy0:wy1, wx0:wx1])
        sm = ndi.binary_opening(sm, ST)
        sy, sx = np.nonzero(sm)
        r[p + "_sn"] = len(sy)
        if len(sy) > 12:
            r[p + "_sx"] = float(sx.mean() + wx0); r[p + "_sy"] = float(sy.mean() + wy0 + Y0)
            r[p + "_sbot"] = float(np.percentile(sy, 97) + wy0 + Y0)
            r[p + "_sx0"] = float(np.percentile(sx, 2) + wx0); r[p + "_sx1"] = float(np.percentile(sx, 98) + wx0)
            # 最低那只鞋（底部 12 px 带）的 x
            lowm = sy > np.percentile(sy, 97) - 12
            r[p + "_slowx"] = float(sx[lowm].mean() + wx0)
        # 青色脚下圈
        ry0 = int(max(bot - 70, 0)); ry1 = int(min(bot + 90, CH)); rx0 = int(max(x0 - 110, 0)); rx1 = int(min(x1 + 110, W))
        w_ = a16[ry0:ry1, rx0:rx1]
        cyn = (w_[..., 1] > 160) & (w_[..., 2] > 205) & (w_[..., 0] < 140) & (d3[ry0:ry1, rx0:rx1, 1] > 45)
        cy_, cx_ = np.nonzero(cyn)
        r[p + "_rn"] = len(cy_)
        if len(cy_) > 60:
            r[p + "_rx0"] = float(np.percentile(cx_, 2) + rx0); r[p + "_rx1"] = float(np.percentile(cx_, 98) + rx0)
            r[p + "_ry0"] = float(np.percentile(cy_, 2) + ry0 + Y0); r[p + "_ry1"] = float(np.percentile(cy_, 98) + ry0 + Y0)
            r[p + "_rcx"] = float(cx_.mean() + rx0); r[p + "_rcy"] = float(cy_.mean() + ry0 + Y0)
        # 影子：团块周围的影子像素质心（取最大连通域）
        hy0 = int(max(bot - 60, 0)); hy1 = int(min(bot + 130, CH)); hx0 = int(max(x0 - 160, 0)); hx1 = int(min(x1 + 160, W))
        sh = shadow[hy0:hy1, hx0:hx1] & fg[hy0:hy1, hx0:hx1] & (~excl[hy0:hy1, hx0:hx1])
        sh = ndi.binary_opening(sh, ST, iterations=2)
        ls, ns = ndi.label(sh)
        if ns > 0:
            ar = ndi.sum(sh, ls, np.arange(1, ns + 1)); k = int(np.argmax(ar))
            if ar[k] > 150:
                hy, hx = np.nonzero(ls == k + 1)
                r[p + "_shn"] = int(ar[k]); r[p + "_shx"] = float(hx.mean() + hx0); r[p + "_shy"] = float(hy.mean() + hy0 + Y0)
    return r

COLS = ["frame", "t", "line_frac", "mad", "fl_n", "fl_x", "fl_y", "fl_x0", "fl_x1", "fl_y0", "fl_y1"]
for p in "LR":
    COLS += [p + s for s in ["_n", "_cx", "_cy", "_top", "_bot", "_x0", "_x1", "_tx", "_ty", "_sn", "_sx", "_sy", "_sbot", "_sx0", "_sx1", "_slowx",
                             "_rn", "_rx0", "_rx1", "_ry0", "_ry1", "_rcx", "_rcy", "_shn", "_shx", "_shy"]]
def fmt(v):
    return ("%.2f" % v) if isinstance(v, float) else str(v)
if __name__ == "__main__":
    f0, f1, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    prev = [None, None]; last = None
    with open(out, "w") as fo:
        fo.write(",".join(COLS) + "\n")
        for f, a in stream(f0, f1 - f0, "crop=%d:%d:0:%d" % (W, CH, Y0), W, CH):
            r = analyze(a, f, prev)
            sub = a[::4, ::4].astype(np.int16)
            if last is not None: r["mad"] = float(np.abs(sub - last).mean())
            last = sub
            for si, p in enumerate("LR"):
                if p + "_cx" in r: prev[si] = (r[p + "_cx"], r[p + "_bot"])
            r["frame"] = f; r["t"] = f / FPS
            fo.write(",".join(fmt(r[c]) if c in r else "" for c in COLS) + "\n")
    print("done", f0, f1)
