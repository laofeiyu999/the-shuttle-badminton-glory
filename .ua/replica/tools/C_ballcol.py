# 沿路标跟球，逐帧输出球心颜色（窗口内最亮团块的中心 5x5 均值）、饱和度、亮团面积，用于判断闪白
# 用法: python tools/C_ballcol.py f:x,y f:x,y ...
import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames
pts = load_pts(); wp = []
for s in sys.argv[1:]:
    f, xy = s.split(':'); x, y = xy.split(','); wp.append((int(f), float(x), float(y)))
fs = [w[0] for w in wp]
frames, _ = read_frames(fs[0], fs[-1], pts, None)
prev = None
for f in range(fs[0], fs[-1] + 1):
    im = frames[f - fs[0]].astype(int)
    if prev is not None and np.abs(im - prev).mean() < 0.25: prev = im; continue   # 跳过重复帧
    prev = im
    x = np.interp(f, fs, [w[1] for w in wp]); y = np.interp(f, fs, [w[2] for w in wp])
    R = 26; x0, y0 = int(x - R), int(y - R); win = im[y0:y0 + 2 * R, x0:x0 + 2 * R]
    r, g, b = win[..., 0], win[..., 1], win[..., 2]
    score = np.minimum(r, g) - 0.0 * b          # 黄和白都高
    sm = ndi.uniform_filter(score.astype(float), 5)
    k = np.unravel_index(np.argmax(sm), sm.shape)
    c = win[max(k[0] - 2, 0):k[0] + 3, max(k[1] - 2, 0):k[1] + 3].reshape(-1, 3).mean(0)
    blob = (np.minimum(r, g) > 0.75 * sm[k]); lab, n = ndi.label(blob); area = int((lab == lab[k]).sum()) if lab[k] else 0
    sat = (c.max() - c.min()) / max(c.max(), 1)
    tag = 'WHITE' if sat < 0.22 else ('yellow' if c[2] < 0.6 * c[1] else 'pale')
    print(f, f'{pts[f]:.3f}', f'pos=({x0 + k[1]},{y0 + k[0]})', 'rgb=(%d,%d,%d)' % tuple(c), f'sat={sat:.2f}', f'area={area}', tag)
