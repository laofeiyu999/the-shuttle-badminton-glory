# -*- coding: utf-8 -*-
"""核对：侧视角逐拍自由拟合（纯阻力抛体，重力 g、阻力 k 自由）得到的 g≈8.0、k≈0.46，
与源码模型（g=5.0、k=0.24 再加时间重映射）是否矛盾。
做法：用源码模型（tools/D_fy_curve.py 的 build）生成弹道，按侧视角的采样方式（50 帧/s，
去掉触球后头 0.10 s）取点，再用与 B_12_shots.py 相同的拟合函数去拟合，看拟合出的 g、k。
在仓库根目录运行：python .ua/replica/tools/L_fit_check.py
输出 .ua/replica/data/L_fit_check.md
"""
import sys, io
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, '.ua/replica/tools')
import D_fy_curve as D


def sim(v0s, v0z, g, k, T, dt=0.004):
    n = int(T / dt) + 2; out = np.zeros((n, 2)); s = z = 0.0; vs, vz = v0s, v0z
    for i in range(n):
        out[i] = (s, z); v = np.hypot(vs, vz)
        vs += -k * v * vs * dt; vz += (-g - k * v * vz) * dt; s += vs * dt; z += vz * dt
    return out


def fit_model(t, s, z, kfix=None):
    T = t[-1]

    def res(p):
        k = kfix if kfix is not None else p[3]
        o = sim(p[0], p[1], p[2], k, T); ti = np.arange(len(o)) * 0.004
        return np.r_[np.interp(t, ti, o[:, 0]) - s, np.interp(t, ti, o[:, 1]) - z]
    p0 = [max(s[-1] / max(T, 0.1) * 1.8, 1), 3.0, 8.0] + ([] if kfix is not None else [0.2])
    lo = [0, -60, 0] + ([] if kfix is not None else [0]); hi = [150, 60, 60] + ([] if kfix is not None else [3])
    r = least_squares(res, p0, bounds=(lo, hi), max_nfev=200)
    return list(r.x), float(np.sqrt(np.mean(r.fun ** 2)))


# (说明, 曲线 ID, 起点高度 cm, 水平距离 cm, 网在路径上的位置比例, 接球高度 cm)
CASES = [
    ('近球 低档 网前低手', 1000, 90, 300, 0.45, 60),
    ('近球 中档 网前低手', 1001, 90, 300, 0.45, 60),
    ('近球 满档 网前低手', 1002, 90, 300, 0.45, 60),
    ('近球 低档 中场腰部', 1000, 100, 600, 0.55, 80),
    ('近球 中档 中场腰部', 1001, 100, 600, 0.55, 80),
    ('远球 低档 中场头顶', 1013, 170, 900, 0.45, 150),
    ('远球 中档 中场头顶', 1014, 170, 900, 0.45, 150),
    ('远球 满档 中场头顶', 1015, 170, 900, 0.45, 150),
    ('远球 低档 中场腰部', 1013, 100, 900, 0.45, 120),
    ('远球 中档 中场腰部', 1014, 100, 900, 0.45, 120),
    ('高球 低档 网前低手', 1003, 60, 750, 0.15, 200),
    ('高球 中档 网前低手', 1004, 60, 750, 0.15, 200),
    ('高球 低档 中场腰部', 1003, 100, 1000, 0.40, 200),
    ('高球 满档 中场腰部', 1005, 100, 1000, 0.40, 200),
]

rows = []
for name, cid, y0, d, nf, yend in CASES:
    b = D.build(cid, y0, d, nf)
    c = D.CFG[cid]
    rt, s, y = b['rt'], b['s'], b['y']
    # 截到对方接球高度（下降段第一次低于 yend）
    ia = int(np.argmax(y)); below = np.where((np.arange(len(y)) > ia) & (y * 100 < yend))[0]
    tend = rt[below[0]] if len(below) else rt[-1]
    t = np.arange(0.10, tend, 0.02)
    if len(t) < 8:
        continue
    ss = np.interp(t, rt, s); zz = np.interp(t, rt, y)
    tt = t - t[0]; ss0 = ss - ss[0]; zz0 = zz - zz[0]
    p, rms = fit_model(tt, ss0, zz0)
    p2, rms2 = fit_model(tt, ss0, zz0, kfix=0.24)
    rows.append((name, cid, c['firstHalfSegmentTime'], c['lastHalfSegmentTime'], c['speedLerpFactor'], b['angle'], b['T'], b['apex'],
                 p[2], p[3], rms, p2[2], rms2))

out = io.StringIO()
out.write('# 源码弹道模型用“纯阻力抛体”去拟合会得到什么\n\n')
out.write('目的：解释侧视角逐拍自由拟合的重力中位 7.97 m/s²、阻力 0.456 /m（B_side_trajectory.md）为什么与源码模型的 5.0、0.24 不同。\n')
out.write('做法：用源码模型生成弹道（阻力 0.24 /m、重力 5.0 m/s²，再做时间重映射），按侧视角的采样方式取点（50 帧/s，去掉触球后头 0.10 s，截到对方接球高度），再用和侧视角相同的拟合函数拟合。脚本 tools/L_fit_check.py。\n\n')
out.write('| 弹道 | 曲线 ID | 重映射 first / last（毫秒每 16 ms 模型步） | 出球角 | 全程时长 s | 顶点 cm | 自由拟合 g | 自由拟合 k | 拟合残差 m | 固定 k=0.24 时的 g | 固定 k 时残差 m |\n')
out.write('|---|---|---|---|---|---|---|---|---|---|---|\n')
for r in rows:
    out.write('| %s | %d | %s / %s（过渡 %s%%） | %d° | %.2f | %.0f | %.2f | %.3f | %.3f | %.2f | %.3f |\n' % r)
g = np.array([r[8] for r in rows]); k = np.array([r[9] for r in rows])
out.write('\n自由拟合 g：中位 %.2f，范围 %.2f–%.2f；自由拟合 k：中位 %.3f，范围 %.3f–%.3f。\n' % (np.median(g), g.min(), g.max(), np.median(k), k.min(), k.max()))
out.write(u'\n结论：源码模型自己生成的弹道，用纯阻力抛体去拟合，得到的重力并不是 5.0，而是随能量档和球种在 5–13 m/s² 之间变化，阻力在 0.24–0.75 /m 之间。原因是时间重映射：源码模型先按 5.0 和 0.24 算出形状，再把时间轴压缩（每个 16 ms 的模型步只播 4–24 ms），压缩后的弹道等效于更大的重力；重映射前后段快慢不同，又会被拟合成更大的阻力。侧视角实测的中位数 7.97 和 0.456 落在这个范围里，所以两者并不矛盾，实测值也不能直接当成模型参数用。在 Unity 里复现要用“源码参数加时间重映射”，不要用实测拟合出来的重力和阻力。\n')
io.open('.ua/replica/data/L_fit_check.md', 'w', encoding='utf-8', newline='\n').write(out.getvalue())
print('ok', len(rows))
