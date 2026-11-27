# 用全帧缩略图(60x45)检测镜头切换/移动：与全片中位数背景缩略图的差异 + 相邻帧差
import numpy as np, sys
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
small = np.load(CACHE + '/small.npy').astype(np.int16)
bg = np.load(CACHE + '/bg_all.npy')
bgs = bg.reshape(45, 32, 60, 32, 3).mean(axis=(1, 3)).astype(np.int16)
# 只看场地外围的静态区域（看台、地板边缘），避开人物活动区与前景
d_bg = np.abs(small - bgs).mean(axis=3)            # (N,45,60)
whole = d_bg.mean(axis=(1, 2))
top = d_bg[:, 6:14, :].mean(axis=(1, 2))           # 看台带
d_adj = np.abs(np.diff(small, axis=0)).mean(axis=(1, 2, 3))
np.save(CACHE + '/cut_whole.npy', whole)
print('whole pct', np.percentile(whole, [5, 25, 50, 75, 90, 95, 99, 99.9]))
print('top pct', np.percentile(top, [5, 25, 50, 75, 90, 95, 99, 99.9]))
print('adj pct', np.percentile(d_adj, [50, 90, 99, 99.9]))
thr = np.percentile(whole, 50) * 2.5 + 3
bad = whole > thr
print('thr', thr, 'bad frames', bad.sum())
# 连续段
segs = []
i = 0
while i < len(bad):
    if bad[i]:
        j = i
        while j + 1 < len(bad) and bad[j + 1]:
            j += 1
        segs.append((i, j)); i = j + 1
    else:
        i += 1
for a, b in segs:
    print(f'bad seg {a}-{b}  t={a/FPS:.2f}-{b/FPS:.2f}s  len={b-a+1}  max={whole[a:b+1].max():.1f}')
big = np.where(d_adj > np.percentile(d_adj, 99.9))[0]
print('big adjacent diffs at frames', big.tolist())
