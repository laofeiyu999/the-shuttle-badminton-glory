# 全片均匀取样求时间中位数背景（去掉人和球），并统计每帧缩略图用于镜头切换检测
import numpy as np, sys, time
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from PIL import Image
t0 = time.time()
small = np.zeros((NF, 45, 60, 3), np.uint8)
samp = []
for i, f in frames(0):
    small[i] = f.reshape(45, 32, 60, 32, 3).mean(axis=(1, 3)).astype(np.uint8)
    if i % 60 == 30:
        samp.append(f.copy())
    if i % 2000 == 0:
        print(i, time.time()-t0, flush=True)
print('frames read', i+1)
np.save(CACHE + '/small.npy', small[:i+1])
samp = np.array(samp)
print(samp.shape)
bg = np.median(samp, axis=0).astype(np.uint8)
np.save(CACHE + '/bg_all.npy', bg)
Image.fromarray(bg).save(FR + '/bg_all.png')
print('done', time.time()-t0)
