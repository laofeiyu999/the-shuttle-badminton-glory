# 拖尾取色/量宽：对指定帧，用前后帧的时间中值做背景，取“增亮”像素里最大的细长连通块，沿主轴分 10 段输出芯部 RGB、宽度(半高宽)、总长
# 用法: python tools/C_trailcol.py NAME FRAME x,y,w,h kind   kind=red|yg|any ; 输出 frames/C_tb/tc_NAME.png (ROI 放大 3 倍)
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames
pts = load_pts()
name, f, roi, kind = sys.argv[1], int(sys.argv[2]), tuple(int(v) for v in sys.argv[3].split(',')), sys.argv[4]
offs = [-36, -30, -24, 24, 30, 36]
lo, hi = max(0, f + offs[0]), min(len(pts) - 1, f + offs[-1])
fr, f0 = read_frames(lo, hi, pts, roi)
im = fr[f - f0].astype(float)
bg = np.median(np.stack([fr[min(max(f + o, lo), hi) - f0] for o in offs]).astype(float), 0)
ex = (im - bg).max(2)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
m = ex > 28
if kind == 'red': m &= (r > g + 25) & (r > b + 50)
if kind == 'yg': m &= (g > b + 40) & (g > r - 40)
m = ndi.binary_closing(m, iterations=2)
lab, n = ndi.label(m)
if n == 0: print('no trail'); sys.exit()
sizes = ndi.sum(m, lab, range(1, n + 1)); k = int(np.argmax(sizes)) + 1
ys, xs = np.nonzero(lab == k)
P = np.stack([xs, ys], 1).astype(float); c = P.mean(0); u, s, vt = np.linalg.svd(P - c, full_matrices=False)
ax = vt[0]; nrm = np.array([-ax[1], ax[0]]); t = (P - c) @ ax; w = (P - c) @ nrm
L = t.max() - t.min()
print(name, 'frame', f, f'pts={pts[f]:.3f}', 'pixels', len(xs), f'length={L:.0f}px', f'axis=({ax[0]:.2f},{ax[1]:.2f})', 'roi', roi)
exv = ex[ys, xs]
for i in range(10):
    a0 = t.min() + L * i / 10; sel = (t >= a0) & (t < a0 + L / 10)
    if sel.sum() < 2: print(i, '-'); continue
    e = exv[sel]; top = e >= np.percentile(e, 70)
    core = im[ys[sel][top], xs[sel][top]].mean(0); allc = im[ys[sel], xs[sel]].mean(0)
    # 宽度: 该段内垂直方向 excess>半峰 的跨度
    half = e >= 0.5 * e.max(); width = w[sel][half].max() - w[sel][half].min() + 1
    print(i, f't={a0 - t.min():.0f}px', 'core=(%d,%d,%d)' % tuple(core), 'mean=(%d,%d,%d)' % tuple(allc), f'peakExcess={e.max():.0f}', f'fwhm={width:.1f}px', f'fullw={w[sel].max() - w[sel].min() + 1:.1f}px')
Image.fromarray(fr[f - f0]).resize((roi[2] * 3, roi[3] * 3), Image.LANCZOS).save(f'frames/C_tb/tc_{name}.png')
