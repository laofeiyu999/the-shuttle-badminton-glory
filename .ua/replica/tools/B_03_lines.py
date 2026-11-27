# 在中位数背景图上拟合球场白线（亚像素），求交点，输出 B_cache/lines.json 与叠加图
import numpy as np, sys, json
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from PIL import Image, ImageDraw
bg = np.load(CACHE + '/bg_all.npy').astype(np.float32)
mn = bg.min(axis=2); mx = bg.max(axis=2)
white = (mn > 150) & (mx - mn < 70)
print('white px', white.sum())
ys, xs = np.nonzero(white)
S = 1.2
init = {  # 1600 宽图上的近似端点
 'farD': ((260,663),(1340,663)), 'farS': ((320,679),(1280,679)),
 'nearS': ((40,950),(1560,950)), 'nearD': ((40,998),(1560,998)),
 'cenL': ((100,778),(550,778)), 'cenR': ((1050,778),(1500,778)),
 'fsL': ((612,675),(470,985)), 'fsR': ((985,675),(1130,985)),
 'baseL': ((235,668),(10,822)), 'baseR': ((1365,668),(1590,822)),
 'bsL': ((298,668),(10,878)), 'bsR': ((1302,668),(1590,878)),
}
lines = {}
for k, (a, b) in init.items():
    a = np.array(a, float) * S; b = np.array(b, float) * S
    d = (b - a) / np.linalg.norm(b - a); n = np.array([-d[1], d[0]]); c = a @ n
    L = np.linalg.norm(b - a)
    for it, tol in enumerate([12, 8, 5, 4, 3.5, 3.5]):
        t = (xs - a[0]) * d[0] + (ys - a[1]) * d[1]
        dist = xs * n[0] + ys * n[1] - c
        m = (np.abs(dist) < tol) & (t > 0.03 * L) & (t < 0.97 * L)
        P = np.stack([xs[m], ys[m]], 1).astype(float)
        mu = P.mean(0)
        u, s, vt = np.linalg.svd(P - mu, full_matrices=False)
        d = vt[0]; n = np.array([-d[1], d[0]]); c = mu @ n
        if d @ (b - a) < 0: d = -d
    res = (P @ n - c)
    lines[k] = dict(n=n.tolist(), c=float(c), npx=int(m.sum()), rms=float(res.std()))
    print(k, 'npx', m.sum(), 'rms', round(res.std(), 2), 'n', n.round(4), 'c', round(c, 2))
def inter(k1, k2):
    A = np.array([lines[k1]['n'], lines[k2]['n']]); c = np.array([lines[k1]['c'], lines[k2]['c']])
    return np.linalg.solve(A, c)
# 世界坐标参数化：X 沿场长（网=0，右为正），Y 横向（场中=0，远端为正），Z 向上
pairs = []
for xn, lx in [('baseL','-B'),('bsL','-D'),('fsL','-F'),('fsR','+F'),('bsR','+D'),('baseR','+B')]:
    for yn, ly in [('farD','+W'),('farS','+S'),('nearS','-S'),('nearD','-W')]:
        pairs.append((xn, yn, lx, ly))
for xn, lx in [('baseL','-B'),('bsL','-D'),('fsL','-F')]:
    pairs.append((xn, 'cenL', lx, '0'))
for xn, lx in [('baseR','+B'),('bsR','+D'),('fsR','+F')]:
    pairs.append((xn, 'cenR', lx, '0'))
pts = []
for xn, yn, lx, ly in pairs:
    p = inter(xn, yn)
    pts.append(dict(name=xn + 'x' + yn, px=p.tolist(), X=lx, Y=ly, inframe=bool(-50 < p[0] < W + 50 and 0 < p[1] < H)))
json.dump(dict(lines=lines, pts=pts), open(CACHE + '/lines.json', 'w'), indent=1)
im = Image.fromarray(bg.astype(np.uint8)); dr = ImageDraw.Draw(im)
for k, l in lines.items():
    n = np.array(l['n']); c = l['c']; d = np.array([n[1], -n[0]]); p0 = n * c
    dr.line([tuple(p0 - 3000 * d), tuple(p0 + 3000 * d)], fill=(255, 0, 0), width=1)
for p in pts:
    x, y = p['px']; dr.ellipse([x-6, y-6, x+6, y+6], outline=(255, 255, 0), width=2)
im.crop((0, 700, 1920, 1300)).save(FR + '/calib_lines.jpg', quality=90)
for p in pts: print(p['name'], np.round(p['px'], 1), p['X'], p['Y'], p['inframe'])
