# 球影关联：对每个有球的帧，在“球正下方的竖直线在画面中的像”附近找暗斑候选；再估计光照方向
import sys, numpy as np, pickle
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_load import *
from B_geom import *
R = load()
ball = np.load(CACHE + '/ball0.npy')
dark = R['dark']
pickle.dump(dark, open(CACHE + '/dark.pkl', 'wb'))
VP = np.array([CX, CY + FOC / np.tan(P[5])])     # 竖直方向消失点（roll≈0）
print('vertical VP', VP.round(0))
rows = []
for k in range(NF):
    if not np.isfinite(ball[k, 0]): continue
    d = dark[k]
    if not len(d): continue
    u, v = ball[k, :2]
    m = (d[:, 2] >= 120) & (d[:, 2] <= 1100) & (d[:, 7] > 0.68) & (d[:, 7] < 0.92) & (d[:, 8] > 1.25) & (d[:, 1] > v + 4) & (d[:, 1] < 1215) & (d[:, 1] > 785)
    d = d[m]
    if not len(d): continue
    # 预计 x：沿球→VP 的直线
    xe = u + (d[:, 1] - v) * (VP[0] - u) / (VP[1] - v)
    dx = d[:, 0] - xe
    for j in np.nonzero(np.abs(dx) < 60)[0]:
        rows.append([k, u, v, d[j, 0], d[j, 1], d[j, 2], d[j, 7], d[j, 8], dx[j]])
S = np.array(rows); np.save(CACHE + '/shadow_cand.npy', S)
print('cand rows', len(S), 'frames', len(np.unique(S[:, 0])), 'of', np.isfinite(ball[:, 0]).sum())
print('dx pct', np.percentile(S[:, 8], [5, 25, 50, 75, 95]).round(1))
h, e = np.histogram(S[:, 8], bins=np.arange(-60, 61, 5)); print(dict(zip(e[:-1].astype(int), h)))
