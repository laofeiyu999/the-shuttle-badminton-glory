# 从 pass1 的白团里筛球候选：去掉静态闪烁点、HUD、属于大前景团（人物）的白块
import sys, numpy as np, pickle
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_load import *
from scipy import ndimage as ndi
R = load()
# 静态图：白团中心落点直方图（4 px 栅格）
Hs = np.zeros((H // 4 + 1, W // 4 + 1), np.int32)
for k in range(NF):
    w = R['white'][k]
    if len(w): np.add.at(Hs, ((w[:, 1] // 4).astype(int), (w[:, 0] // 4).astype(int)), 1)
Hs3 = ndi.uniform_filter(Hs.astype(np.float32), 3) * 9
out = []
st8 = np.ones((3, 3), bool)
for k in range(NF):
    w = R['white'][k]
    if not len(w): out.append(np.zeros((0, 20), np.float32)); continue
    fg = np.unpackbits(R['fgm'][k])[: 316 * 480].reshape(316, 480).astype(bool)
    lab, n = ndi.label(fg, structure=st8)
    area = np.concatenate([[0], np.bincount(lab.ravel())[1:]])
    yi = np.clip((w[:, 1] // 4).astype(int), 0, 315); xi = np.clip((w[:, 0] // 4).astype(int), 0, 479)
    # 取 3x3 邻域内最大的连通域
    ca = np.zeros(len(w)); ch = np.zeros(len(w)); cw = np.zeros(len(w))
    sl = ndi.find_objects(lab)
    for j in range(len(w)):
        ls = np.unique(lab[max(0, yi[j] - 1): yi[j] + 2, max(0, xi[j] - 1): xi[j] + 2]); ls = ls[ls > 0]
        if len(ls):
            l = ls[np.argmax(area[ls])]; ca[j] = area[l]; s = sl[l - 1]; ch[j] = (s[0].stop - s[0].start) * 4; cw[j] = (s[1].stop - s[1].start) * 4
    stc = Hs3[np.clip((w[:, 1] // 4).astype(int), 0, H // 4), np.clip((w[:, 0] // 4).astype(int), 0, W // 4)]
    o = np.column_stack([w, ca, ch, cw, stc]).astype(np.float32)
    out.append(o)
pickle.dump(out, open(CACHE + '/cands.pkl', 'wb'))
print('static cells >300:', (Hs3 > 300).sum())
