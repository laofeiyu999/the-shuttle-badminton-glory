# 球链 v4：对分类器筛出的候选做全片动态规划（每帧至多选一个候选），
# 得分 = Σ(p − 0.25 − 静态惩罚) − λ·位移 − μ·缺帧数；可随时断开重起。输出 ball0.npy
import sys, numpy as np, pickle
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
C = pickle.load(open(CACHE + '/cands.pkl', 'rb')); P = pickle.load(open(CACHE + '/cand_p.pkl', 'rb'))
BAD = [(3055, 3143), (7111, 7147), (7165, 7191), (7992, 8081), (8854, 8918)]
def isbad(k): return any(a <= k <= b for a, b in BAD)
TH, G, LAM, MU, VMAX = 0.2, 10, 0.004, 0.12, 200.0
N = []
for k in range(NF):
    w = C[k]; p = P[k]
    if not len(w) or isbad(k): N.append((np.zeros((0, 20)), np.zeros(0), np.zeros(0))); continue
    m = p >= TH
    w = w[m]; p = p[m]
    gain = p - 0.25 - 0.35 * (w[:, 19] > 150) - 0.3 * (w[:, 1] < 290)
    N.append((w, p, gain))
score = [np.zeros(len(n[0])) for n in N]; back = [np.full((len(n[0]), 2), -1) for n in N]
bestpre = np.zeros(NF + 1); bestarg = np.full((NF + 1, 2), -1)   # 到第 k 帧之前（不含）任意终点的最好得分
for k in range(NF):
    w, p, gain = N[k]
    for j in range(len(w)):
        # 断开重起：接在 k-G-1 之前的最好终点后面
        kk = max(0, k - G)
        b = bestpre[kk] - 0.5; arg = tuple(bestarg[kk]) if bestpre[kk] > 0 else (-1, -1)
        if b < 0: b = 0; arg = (-1, -1)
        for g in range(1, G + 1):
            q = k - g
            if q < 0: break
            wq = N[q][0]
            if not len(wq): continue
            d = np.hypot(wq[:, 0] - w[j, 0], wq[:, 1] - w[j, 1])
            ar = w[j, 2] / np.maximum(wq[:, 2], 1)
            s = score[q] - LAM * d - MU * (g - 1) - 0.3 * (np.abs(np.log(ar)) > 1.0)
            s[d > VMAX * g + 30] = -1e9
            i = int(np.argmax(s))
            if s[i] > b: b = s[i]; arg = (q, i)
        score[k][j] = b + gain[j]; back[k][j] = arg
    bestpre[k + 1] = bestpre[k]; bestarg[k + 1] = bestarg[k]
    if len(w) and score[k].max() > bestpre[k]:
        bestpre[k + 1] = score[k].max(); bestarg[k + 1] = (k, int(np.argmax(score[k])))
# 回溯
ball = np.full((NF, 14), np.nan)
k, j = bestarg[NF]
n = 0
while k >= 0:
    c = N[k][0][j]
    ball[k] = [c[0], c[1], c[2], c[10], c[11], c[12], c[13], c[14], c[15], 0, c[16], c[3], 1.0, N[k][1][j]]; n += 1
    k, j = back[k][j]
still = np.zeros(NF, bool)
for k in range(NF):
    if not np.isfinite(ball[k, 0]): continue
    a = ball[max(0, k - 4):k + 5, :2]; a = a[np.isfinite(a[:, 0])]
    if len(a) >= 5 and np.ptp(a[:, 0]) < 2.5 and np.ptp(a[:, 1]) < 2.5: still[k] = True
np.save(CACHE + '/ball0.npy', ball); np.save(CACHE + '/still.npy', still)
print('frames with ball', n, 'still', still.sum(), '/', NF)
