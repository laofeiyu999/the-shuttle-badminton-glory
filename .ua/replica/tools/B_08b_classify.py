# 球候选分类器：用高置信轨迹段上的白团做正样本，同帧其他白团做负样本，kNN 估计每个候选的“像球”概率
import sys, numpy as np, pickle
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from scipy.spatial import cKDTree
C = pickle.load(open(CACHE + '/cands.pkl', 'rb'))
TR = pickle.load(open(CACHE + '/tracklets.pkl', 'rb'))
def feat(w):
    sat = w[:, 10] > 20
    off = np.hypot(w[:, 0] - w[:, 11], w[:, 1] - w[:, 12]) * sat
    return np.column_stack([np.log(w[:, 2]), w[:, 4] - w[:, 3], w[:, 6] - w[:, 5], w[:, 7], w[:, 8], w[:, 9], np.log1p(w[:, 10]), off,
                            w[:, 13] * sat, w[:, 14] * sat, w[:, 15] * sat, np.log1p(w[:, 16]), np.log1p(w[:, 19])])
pos = {}
if len(sys.argv) > 1 and sys.argv[1] == 'boot':
    # 自举：用上一轮动态规划选出的球链（连续 ≥8 帧、非静止）做正样本
    ball = np.load(CACHE + '/ball0.npy'); still = np.load(CACHE + '/still.npy')
    ok = np.isfinite(ball[:, 0]) & ~still
    k = 0
    while k < NF:
        if ok[k]:
            e = k
            while e + 1 < NF and ok[e + 1] and np.hypot(*(ball[e + 1, :2] - ball[e, :2])) < 120: e += 1
            if e - k + 1 >= 8:
                for q in range(k, e + 1): pos.setdefault(q, []).append(ball[q, :2])
            k = e + 1
        else: k += 1
else:
    for t in TR:
        if t['iso'] >= 0.9 and t['trail'] > 0.6 and t['tcons'] > 0.8 and len(t['f']) >= 15 and t['rough'] < 3 and t['spd'] > 3 and 100 <= t['area'] <= 700:
            for k, c in zip(t['f'], t['c']): pos.setdefault(int(k), []).append(c[:2])
print('positive frames', len(pos))
Xp, Xn = [], []
for k, pl in pos.items():
    w = C[k]; w = w[(w[:, 2] >= 40) & (w[:, 2] <= 1300)]
    if not len(w): continue
    d = np.min([np.hypot(w[:, 0] - p[0], w[:, 1] - p[1]) for p in pl], axis=0)
    F = feat(w); Xp.append(F[d < 2]); Xn.append(F[d > 40])
Xp = np.vstack(Xp); Xn = np.vstack(Xn)
# 额外负样本：全片随机帧里不在任何 tracklet 上的静止白团
print('pos', len(Xp), 'neg', len(Xn))
rng = np.random.default_rng(0)
Xn = Xn[rng.choice(len(Xn), min(len(Xn), 12 * len(Xp)), replace=False)]
X = np.vstack([Xp, Xn]); y = np.r_[np.ones(len(Xp)), np.zeros(len(Xn))]
mu, sd = X.mean(0), X.std(0) + 1e-6
wt = np.array([1.5, 1, 1, 1, 1, 1, 1.5, 1, 1, 1, 1, 0.7, 0.7])
Z = (X - mu) / sd * wt
# 留出检验
idx = rng.permutation(len(Z)); h = len(Z) // 5; te, tr = idx[:h], idx[h:]
tree = cKDTree(Z[tr]); _, nn = tree.query(Z[te], k=9); p = y[tr][nn].mean(1)
for th in (0.2, 0.35, 0.5):
    print(f'th={th} recall={(p[y[te] == 1] >= th).mean():.3f} falsepos={(p[y[te] == 0] >= th).mean():.4f}')
tree = cKDTree(Z)
P = []
for k in range(NF):
    w = C[k]
    if not len(w): P.append(np.zeros(0, np.float32)); continue
    _, nn = tree.query((feat(np.maximum(w, 0) if False else w) - mu) / sd * wt, k=9)
    pp = y[nn].mean(1); pp[(w[:, 2] < 40) | (w[:, 2] > 1300)] = 0
    P.append(pp.astype(np.float32))
pickle.dump(P, open(CACHE + '/cand_p.pkl', 'wb'))
n = np.array([(p >= 0.35).sum() for p in P]); print('cands p>=0.35 per frame: hist', np.bincount(n)[:8])
