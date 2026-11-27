# 球与拖尾自动测量：在给定帧段里按颜色找拖尾像素，输出每帧 bbox / 主轴长度 / 宽度 / 沿轴颜色
# 用法: python tools/C_track.py f0 f1 --kind red|yg|white [--roi x,y,w,h] [--strip OUT.png]
import sys, argparse, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames
ap = argparse.ArgumentParser()
ap.add_argument('f0', type=int); ap.add_argument('f1', type=int)
ap.add_argument('--kind', default='red'); ap.add_argument('--roi', default='0,60,1446,760')
ap.add_argument('--strip', default=''); ap.add_argument('--min', type=int, default=12)
ap.add_argument('--step', type=int, default=1)
a = ap.parse_args()
pts = load_pts(); roi = tuple(int(v) for v in a.roi.split(','))
arr, _ = read_frames(a.f0, a.f1, pts, roi)
def mask(im, kind):
    r, g, b = [im[..., i].astype(int) for i in range(3)]
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
    if kind == 'red':   # 橙红：R 高，G 中，B 低
        return (r > 150) & (g > 25) & (g < r * 0.80) & (b < g * 0.75 + 12) & (b < 110) & (r - b > 100)
    if kind == 'yg':    # 黄绿：G>=R*0.9，B 低
        return (g > 150) & (r > 110) & (b < 120) & (g >= r * 0.92) & (g - b > 80)
    if kind == 'white':
        return (mn > 215)
tiles = []
for i in range(0, len(arr), a.step):
    im = arr[i]; m = mask(im, a.kind)
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    if n == 0: print(a.f0 + i, 'none'); continue
    sizes = ndi.sum(m, lab, range(1, n + 1))
    out = []
    for k in np.argsort(sizes)[::-1][:4]:
        if sizes[k] < a.min: continue
        ys, xs = np.where(lab == k + 1)
        c = np.stack([xs, ys], 1).astype(float); mu = c.mean(0)
        w, v = np.linalg.eigh(np.cov((c - mu).T) + 1e-6 * np.eye(2))
        ax = v[:, 1]; t = (c - mu) @ ax; s = (c - mu) @ v[:, 0]
        L = t.max() - t.min(); W = 2 * 2.0 * np.sqrt(w[0])  # 约 4 sigma
        col = im[ys, xs].mean(0).astype(int)
        out.append(f'n={int(sizes[k])} c=({mu[0]+roi[0]:.0f},{mu[1]+roi[1]:.0f}) L={L:.0f} W4s={W:.1f} ang={np.degrees(np.arctan2(ax[1], ax[0])):.0f} rgb={tuple(col)}')
    print(a.f0 + i, f'{pts[a.f0 + i]:.3f}', ' | '.join(out))
