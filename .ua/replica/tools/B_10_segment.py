# 切拍初版：球链按 tracklet 的像素 x 速度符号分组，符号翻转处为击球；用闪光起跳帧精修击球帧
import sys, numpy as np, pickle, json
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
ball = np.load(CACHE + '/ball0.npy'); fl = np.load(CACHE + '/flash.npy')
c = fl[:, 0]
# 闪光起跳：1–2 帧内极亮像素数明显上升
on = []
for k in range(2, NF - 1):
    base = np.median(c[max(0, k - 6):k])
    if c[k] - base > 500 and c[k] > 1.8 * base + 200 and c[k - 1] - base < 0.5 * (c[k] - base):
        if on and k - on[-1][0] < 5: continue
        # 闪光自身质心
        n1 = c[k]; n0 = min(base, n1 - 1)
        pk = k + int(np.argmax(c[k:k + 3]))
        px = (fl[pk, 0] * fl[pk, 1] - base * fl[k - 1, 1]) / max(fl[pk, 0] - base, 1)
        py = (fl[pk, 0] * fl[pk, 2] - base * fl[k - 1, 2]) / max(fl[pk, 0] - base, 1)
        on.append((k, float(c[pk] - base), float(px), float(py)))
print('flash onsets', len(on))
ids = ball[:, 9]
segs = []
for i in np.unique(ids[np.isfinite(ids)]):
    f = np.nonzero(ids == i)[0]
    x = ball[f, 0]; y = ball[f, 1]
    vx = np.polyfit(f, x, 1)[0] if len(f) >= 3 else 0
    segs.append(dict(f0=int(f[0]), f1=int(f[-1]), n=len(f), vx=float(vx), x0=float(x[0]), x1=float(x[-1]), y0=float(y[0]), y1=float(y[-1]), dx=float(x[-1] - x[0])))
segs.sort(key=lambda s: s['f0'])
json.dump(dict(on=on, segs=segs), open(CACHE + '/seg0.json', 'w'))
for s in segs[:40]: print(s)
