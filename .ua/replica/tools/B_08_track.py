# 球追踪 v3。要点：录屏 50 fps 但游戏渲染节奏不均匀（同一球相邻帧位移会出现 0 倍、1 倍、2 倍），
# 所以连接门限按“沿运动方向 0–2.6 倍步长 + 垂直方向小误差”设计，而不是等速预测。
# 种子：孤立白团，或带高饱和拖尾的白团（拖尾方向给出运动方向）。
import sys, numpy as np, pickle
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
C = pickle.load(open(CACHE + '/cands.pkl', 'rb'))
BAD = [(3055, 3143), (7111, 7147), (7165, 7191), (7992, 8081), (8854, 8918)]
def isbad(k): return any(a <= k <= b for a, b in BAD)
CA = []
for k in range(NF):
    w = C[k]
    if not len(w) or isbad(k): CA.append(np.zeros((0, 21), np.float32)); continue
    m = (w[:, 2] >= 40) & (w[:, 2] <= 1300) & (w[:, 19] < 300)
    m &= ~((w[:, 1] < 290) & (w[:, 19] > 60))
    w = w[m]
    thin = w[:, 16] / (np.maximum(w[:, 17], w[:, 18]) / 4 + 1e-6)
    iso = ((w[:, 16] < 900) & (w[:, 17] < 120)) | ((thin < 10) & (w[:, 10] > 60))
    CA.append(np.column_stack([w, iso]).astype(np.float32))
def tdir(c):
    if c[10] < 40: return None
    d = c[:2] - c[11:13]; n = np.hypot(*d)
    return d / n if n > 3 else None
class T:
    def __init__(s, k, c): s.f = [k]; s.c = [c]; s.miss = 0
    def vel(s):
        # 稳健速度：最近至多 5 步的位移总和 / 帧数
        if len(s.f) < 2: return None
        n = min(5, len(s.f) - 1)
        return (s.c[-1][:2] - s.c[-1 - n][:2]) / (s.f[-1] - s.f[-1 - n])
    def match(s, k, w, used):
        if not len(w): return -1
        p = s.c[-1][:2]; dt = k - s.f[-1]; v = s.vel()
        dv = w[:, :2] - p; d = np.hypot(*dv.T); iso = w[:, 20] > 0; tr = w[:, 10] > 60
        ar = w[:, 2] / max(s.c[-1][2], 1.0); okar = (ar > 0.25) & (ar < 4)
        if v is not None and np.hypot(*v) > 1.5:
            sp = np.hypot(*v); u = v / sp
            al = dv @ u; pe = np.abs(dv @ np.array([-u[1], u[0]]))
            lo = -4 - 0.2 * sp; hi = (2.6 * dt + 0.6) * sp + 8
            pg = np.where(iso | tr, 7 + 0.10 * np.abs(al) + 1.5 * s.miss, 5 + 0.05 * np.abs(al))
            ok = (al > lo) & (al < hi) & (pe < pg) & okar
            ok &= iso | tr | ((al > 0.4 * sp * dt) & (al < 1.8 * sp * dt + 4))
            cost = pe + 0.25 * np.abs(al - sp * dt)
        elif v is not None:
            ok = (d < 12 + 4 * dt) & okar & iso; cost = d
        else:
            u = tdir(s.c[-1])
            ok = (d < 40.0 * dt) & iso & okar
            if u is not None:
                cs = (dv @ u) / (d + 1e-6)
                ok |= (cs > 0.9) & (d < 330.0 * dt) & (iso | tr) & okar
            cost = d
        cost = np.where(ok & ~used, cost, 1e9)
        j = int(np.argmin(cost))
        return j if cost[j] < 1e8 else -1
act, done = [], []
for k in range(NF):
    w = CA[k]; used = np.zeros(len(w), bool)
    for t in sorted(act, key=lambda t: -len(t.f)):
        j = t.match(k, w, used)
        if j >= 0: t.f.append(k); t.c.append(w[j]); t.miss = 0; used[j] = True
        else: t.miss += 1
    keep = []
    for t in act:
        (done if t.miss > (4 if len(t.f) >= 3 else 1) else keep).append(t)
    act = keep
    if len(w):
        for j in np.nonzero(~used & ((w[:, 20] > 0) | (w[:, 10] > 60)))[0]: act.append(T(k, w[j]))
done += act
out = []
for t in done:
    f = np.array(t.f); c = np.array(t.c)
    if len(f) < 3: continue
    st = np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1]))
    path = float(st.sum())
    if path < 20: continue
    # 平滑度：对 x(t)、y(t) 做二次拟合的残差（消除节奏抖动后看是否像一条弹道）
    if len(f) >= 6:
        rx = c[:, 0] - np.polyval(np.polyfit(f, c[:, 0], 2), f); ry = c[:, 1] - np.polyval(np.polyfit(f, c[:, 1], 2), f)
        # 垂直于运动方向的残差
        vv = np.gradient(c[:, :2], f, axis=0); n = np.hypot(*vv.T) + 1e-6
        perp = (rx * -vv[:, 1] + ry * vv[:, 0]) / n
        rough = float(np.sqrt(np.mean(perp ** 2)))
    else: rough = 0.0
    v = np.gradient(c[:, :2], f, axis=0); u = c[:, :2] - c[:, 11:13]
    cs = (v * u).sum(1) / (np.hypot(*v.T) * np.hypot(*u.T) + 1e-6); mt = c[:, 10] > 40
    tcons = float(np.median(cs[mt])) if mt.sum() >= 2 else 0.0
    out.append(dict(f=f, c=c, path=path, trail=float(mt.mean()), area=float(np.median(c[:, 2])), rough=rough, tcons=tcons,
                    iso=float(c[:, 20].mean()), spd=float(path / (f[-1] - f[0]))))
print('tracklets', len(done), 'kept', len(out))
pickle.dump(out, open(CACHE + '/tracklets.pkl', 'wb'))
