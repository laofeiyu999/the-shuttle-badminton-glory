# 特效取色：对 帧+ROI，用前后帧时间中值做背景，取增亮像素；输出 屏幕色(按增亮分位)、加色估计(im-bg)、增亮区外接尺寸
# 用法: python tools/C_fxcol.py name:frame:x,y,w,h[:thr] ...
import sys, numpy as np
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames
pts = load_pts()
for s in sys.argv[1:]:
    p = s.split(':'); name, f = p[0], int(p[1]); roi = tuple(int(v) for v in p[2].split(',')); thr = float(p[3]) if len(p) > 3 else 30
    offs = [-40, -34, -28, 28, 34, 40]; lo, hi = max(0, f + offs[0]), min(len(pts) - 1, f + offs[-1])
    fr, f0 = read_frames(lo, hi, pts, roi); im = fr[f - f0].astype(float)
    bg = np.median(np.stack([fr[min(max(f + o, lo), hi) - f0] for o in offs]).astype(float), 0)
    d = im - bg; ex = d.max(2); m = ex > thr
    if m.sum() < 5: print(name, 'no fx'); continue
    ys, xs = np.nonzero(m); e = ex[m]
    out = [name, f'f{f} {pts[f]:.3f}s', f'n={m.sum()}', f'bbox={xs.max()-xs.min()+1}x{ys.max()-ys.min()+1}px']
    for lab, q0, q1 in (('top10%', 90, 100), ('mid', 40, 70), ('low', 5, 30)):
        sel = (e >= np.percentile(e, q0)) & (e <= np.percentile(e, q1))
        c = im[m][sel].mean(0); a = np.clip(d[m][sel].mean(0), 0, 255)
        out.append(f'{lab}: screen=({c[0]:.0f},{c[1]:.0f},{c[2]:.0f}) add=({a[0]:.0f},{a[1]:.0f},{a[2]:.0f})')
    # 按加色分量的色相分箱(30 度)，列出占比 >6% 的色团：这样角色移动造成的杂色和特效本色能分开
    dd = np.clip(d[m], 0, 255); mx = dd.max(1); mn = dd.min(1); sat = (mx - mn) / np.maximum(mx, 1)
    r, g, b = dd[:, 0], dd[:, 1], dd[:, 2]; c = mx - mn + 1e-6
    hue = np.where(mx == r, ((g - b) / c) % 6, np.where(mx == g, (b - r) / c + 2, (r - g) / c + 4)) * 60
    binid = np.where(sat < 0.18, -1, (hue // 30).astype(int))
    for bi in sorted(set(binid.tolist())):
        sel = binid == bi
        if sel.mean() < 0.06: continue
        cs = im[m][sel].mean(0); ca = dd[sel].mean(0); top = sel & (e >= np.percentile(e[sel], 80)); ct = im[m][top].mean(0)
        out.append(f"{'neutral' if bi < 0 else str(bi*30)+'deg'} {sel.mean()*100:.0f}%: screen=({cs[0]:.0f},{cs[1]:.0f},{cs[2]:.0f}) bright=({ct[0]:.0f},{ct[1]:.0f},{ct[2]:.0f}) add=({ca[0]:.0f},{ca[1]:.0f},{ca[2]:.0f})")
    print((chr(10) + '   ').join(out))
