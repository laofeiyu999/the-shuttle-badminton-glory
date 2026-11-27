# -*- coding: utf-8 -*-
"""B2_move.py 移动统计：回合内速度分位数、持续最高速、起步/急停用时、折返最低速、击球前后速度剖面。
输入 data/B2_post.npz, data/B2_hits_auto.csv；输出 data/B2_move_stats.txt, data/B2_hit_speed_profile.csv, data/B2_bursts.csv"""
import sys, os, csv
import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import minimum_filter1d, uniform_filter1d
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
d = np.load(os.path.join(DATA, 'B2_post.npz')); N = len(d['fr'])
# 回合区间(秒)：发球触球 → 死球，手工由联系表和闪光事件定出；去掉星标演出切镜头段
RALLY = [(2.6, 29.9), (36.5, 46.8), (53.3, 60.9), (71.8, 85.3), (92.5, 110.3), (116.3, 138.8), (146.1, 159.9), (168.7, 176.3), (182.8, 210.3), (217.6, 229.9)]
inr = np.zeros(N, bool)
for a, b in RALLY: inr[int(a * FPS):int(b * FPS)] = True
BAN = {9, 53, 1702, 1750, 2535, 2582, 3449, 3497, 4482, 4529, 5714, 5762, 7156, 7186, 7211, 7246, 8286, 8324, 9010, 9058, 10732, 10780, 6990}
hits = [r for r in csv.DictReader(open(os.path.join(DATA, 'B2_hits_auto.csv'))) if int(r['frame']) not in BAN and int(r['dur']) <= 12 and inr[int(r['frame'])]]
out = []
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); out.append(s)
P('回合内帧数', inr.sum(), '(%.1f s)' % (inr.sum() / FPS), ' 击球闪光事件', len(hits))
bursts = []
for s in 'LR':
    x = d[s + '_x'].copy(); z = d[s + '_z'].copy(); sp = d[s + '_sp'].copy(); vx = d[s + '_vx'].copy(); vz = d[s + '_vz'].copy()
    ok = inr & ~np.isnan(sp)
    # 去掉插值/离群造成的尖峰：速度 > 9 m/s 的帧及其前后 4 帧不计
    spike = np.zeros(N, bool); idx = np.where(np.nan_to_num(sp) > 9)[0]
    for i in idx: spike[max(0, i - 4):i + 5] = True
    ok &= ~spike
    P('==', '左方' if s == 'L' else '右方', '有效帧', ok.sum())
    P(' 位置范围 x(沿球场长轴, 网=0) 1%%/50%%/99%%: %s  z(横向, 远边线为正): %s' % (np.percentile(x[ok], [1, 50, 99]).round(2), np.percentile(z[ok], [1, 50, 99]).round(2)))
    P(' 速度分位 50/75/90/95/99: %s m/s' % np.percentile(sp[ok], [50, 75, 90, 95, 99]).round(2))
    P(' |vx|(前后向) 90/95/99: %s   |vz|(横向) 90/95/99: %s' % (np.percentile(abs(vx[ok]), [90, 95, 99]).round(2), np.percentile(abs(vz[ok]), [90, 95, 99]).round(2)))
    # 持续最高速：连续 8 帧(0.16 s)内速度的最小值的最大值
    for nm, v in [('合速度', sp), ('|vx|', abs(vx)), ('|vz|', abs(vz))]:
        vv = np.where(ok, v, 0); sus = minimum_filter1d(vv, 8)
        top = np.sort(sus)[::-1]
        P('  持续 0.16 s 以上的最高 %s: max %.2f, 第 99.9 百分位 %.2f, 第 99.5 百分位 %.2f m/s (帧 %d)' % (nm, top[0], np.percentile(sus[ok], 99.9), np.percentile(sus[ok], 99.5), int(np.argmax(sus))))
    mv = ok & (sp > 1.0)
    h, e = np.histogram(sp[mv], np.arange(1, 8.01, 0.25)); k = np.argsort(h)[::-1][:3]
    P(' 移动中(>1 m/s)占回合帧比例 %.2f；速度众数区间 %s m/s；移动帧中位速度 %.2f' % (mv.sum() / ok.sum(), [(round(e[i], 2), round(e[i + 1], 2)) for i in k], np.median(sp[mv])))
    P(' 静止(<0.3 m/s)占比 %.2f' % ((ok & (sp < 0.3)).sum() / ok.sum()))
    # 移动段：速度 > 1 m/s 的连续段，要求峰值 > 3 m/s
    i = 0; segs = []
    while i < N:
        if ok[i] and sp[i] > 0.8:
            j = i
            while j < N and ok[j] and sp[j] > 0.8: j += 1
            if j - i >= 8 and sp[i:j].max() > 3.0: segs.append((i, j))
            i = j
        else: i += 1
    acc = []; dec = []; pk = []; dist = []; dur = []
    for a, b in segs:
        seg = sp[a:b]; p = seg.max(); ip = int(np.argmax(seg))
        # 起步：从 0.8 m/s 到达 0.9*峰值的用时；仅当段前 3 帧速度 < 1 才算从静止起步
        pre = sp[max(0, a - 3):a]; post = sp[b:b + 3]
        t90 = int(np.argmax(seg >= 0.9 * p)); tdec = (b - a) - 1 - int(len(seg) - 1 - np.argmax(seg[::-1] >= 0.9 * p))
        last90 = len(seg) - 1 - int(np.argmax(seg[::-1] >= 0.9 * p))
        dd = float(np.hypot(x[b - 1] - x[a], z[b - 1] - z[a]))
        st = len(pre) > 0 and np.nanmax(pre) < 1.0; en = len(post) > 0 and np.nanmax(post) < 1.0
        if st: acc.append(t90 / FPS)
        if en: dec.append((len(seg) - 1 - last90) / FPS)
        pk.append(p); dist.append(dd); dur.append((b - a) / FPS)
        bursts.append([s, a, '%.2f' % (a / FPS), b - a, '%.2f' % p, '%.2f' % dd, '%.2f' % (t90 / FPS) if st else '', '%.2f' % ((len(seg) - 1 - last90) / FPS) if en else '',
                       '%.2f' % (x[b - 1] - x[a]), '%.2f' % (z[b - 1] - z[a])])
    P(' 移动段数 %d；峰值速度中位 %.2f (25%%-75%%: %s)；段位移中位 %.2f m；段时长中位 %.2f s' % (len(segs), np.median(pk), np.percentile(pk, [25, 75]).round(2), np.median(dist), np.median(dur)))
    P(' 起步(0.8 m/s → 90%% 峰值)用时: 中位 %.2f s, 25%%-75%% %s, n=%d' % (np.median(acc), np.percentile(acc, [25, 75]).round(2), len(acc)))
    P(' 急停(最后一次 90%% 峰值 → 0.8 m/s)用时: 中位 %.2f s, 25%%-75%% %s, n=%d' % (np.median(dec), np.percentile(dec, [25, 75]).round(2), len(dec)))
    # 平均加速度：起步段前 0.1 s 的速度增量
    # 折返：速度方向夹角 > 120°(前后 6 帧平均速度向量)，且前后速度都 > 2 m/s 的时刻，记录其间最低速
    vxs = uniform_filter1d(np.nan_to_num(vx), 5); vzs = uniform_filter1d(np.nan_to_num(vz), 5)
    turns = []
    i = 10
    while i < N - 10:
        if ok[i - 8:i + 9].all():
            a1 = np.array([vxs[i - 7], vzs[i - 7]]); a2 = np.array([vxs[i + 7], vzs[i + 7]])
            n1 = np.hypot(*a1); n2 = np.hypot(*a2)
            if n1 > 2.0 and n2 > 2.0 and (a1 @ a2) / (n1 * n2) < -0.5:
                lo = sp[i - 7:i + 8].min(); turns.append((i, n1, n2, lo)); i += 15; continue
        i += 1
    if turns:
        T = np.array(turns)
        P(' 折返(0.28 s 内方向反转 >120°, 前后速度都 >2 m/s) %d 次：折返中最低速中位 %.2f m/s (25%%-75%% %s)，前速度中位 %.2f，后速度中位 %.2f' % (len(T), np.median(T[:, 3]), np.percentile(T[:, 3], [25, 75]).round(2), np.median(T[:, 1]), np.median(T[:, 2])))
        P('  折返帧: %s' % [int(v) for v in T[:, 0]][:40])
    # 击球前后速度剖面
    hs = [int(r['frame']) for r in hits if r['side'] == s]
    offs = np.arange(-40, 61)
    M = np.array([[sp[f + o] if 0 <= f + o < N and ok[f + o] else np.nan for o in offs] for f in hs])
    med = np.nanmedian(M, 0); q25 = np.nanpercentile(M, 25, 0); q75 = np.nanpercentile(M, 75, 0)
    P(' 击球数 %d；击球前后速度中位数(m/s): -0.6s %.2f, -0.4s %.2f, -0.2s %.2f, -0.1s %.2f, 0 %.2f, +0.1s %.2f, +0.2s %.2f, +0.3s %.2f, +0.4s %.2f, +0.6s %.2f, +0.8s %.2f, +1.0s %.2f' % (
        len(hs), med[10], med[20], med[30], med[35], med[40], med[45], med[50], med[55], med[60], med[70], med[80], med[90]))
    # 每次击球：击球帧速度；击球后首次速度 > 1.5 m/s 的延迟；击球前最后一次速度 > 1.5 的时间
    resume = []; stopb = []; v0 = []
    for f in hs:
        if not ok[f]: continue
        v0.append(sp[f])
        r = np.nan
        for o in range(0, 75):
            if f + o < N and ok[f + o] and sp[f + o] > 1.5 and (o == 0 or sp[f + o - 1] <= 1.5 or o > 0): 
                r = o / FPS; break
        # 要求先降到 <1 再回升才算“恢复”
        lowi = None
        for o in range(0, 40):
            if f + o < N and ok[f + o] and sp[f + o] < 1.0: lowi = o; break
        if lowi is not None:
            for o in range(lowi, 100):
                if f + o < N and ok[f + o] and sp[f + o] > 1.5: resume.append(o / FPS); break
        for o in range(0, 60):
            if f - o >= 0 and ok[f - o] and sp[f - o] > 1.5: stopb.append(o / FPS); break
    v0 = np.array(v0)
    P(' 击球帧速度: 中位 %.2f m/s；<0.5 m/s 的比例 %.2f；<1.0 的比例 %.2f；>2.5 的比例 %.2f' % (np.median(v0), (v0 < 0.5).mean(), (v0 < 1.0).mean(), (v0 > 2.5).mean()))
    P(' 击球前最后一次速度 >1.5 m/s 距击球: 中位 %.2f s (25%%-75%% %s, n=%d)' % (np.median(stopb), np.percentile(stopb, [25, 75]).round(2), len(stopb)))
    P(' 击球后(先降到 <1 m/s)再次 >1.5 m/s 的延迟: 中位 %.2f s (25%%-75%% %s, 10%% %.2f, n=%d)' % (np.median(resume), np.percentile(resume, [25, 75]).round(2), np.percentile(resume, 10), len(resume)))
    with open(os.path.join(DATA, 'B2_hit_speed_profile_%s.csv' % s), 'w', newline='') as fo:
        w = csv.writer(fo); w.writerow(['offset_frames', 'offset_s', 'median_speed', 'q25', 'q75', 'n'])
        for i, o in enumerate(offs): w.writerow([o, '%.2f' % (o / FPS), '%.3f' % med[i], '%.3f' % q25[i], '%.3f' % q75[i], int((~np.isnan(M[:, i])).sum())])
    # 回中：击球后 1.0 s 的位移方向；“家”取回合内位置中位数
    hx, hz = np.median(x[ok]), np.median(z[ok])
    P(' 回合内位置中位数(“家”位) x=%.2f z=%.2f' % (hx, hz))
    dh0 = []; dh1 = []; mvd = []
    for f in hs:
        g = f + 45
        if g < N and ok[f] and ok[g]:
            dh0.append(np.hypot(x[f] - hx, z[f] - hz)); dh1.append(np.hypot(x[g] - hx, z[g] - hz)); mvd.append(np.hypot(x[g] - x[f], z[g] - z[f]))
    dh0 = np.array(dh0); dh1 = np.array(dh1); mvd = np.array(mvd)
    far = dh0 > 1.5
    P(' 击球时距家位 >1.5 m 的 %d 次中：0.9 s 后距家位变小的比例 %.2f，中位变化 %.2f m；击球后 0.9 s 内位移中位 %.2f m；位移 <0.3 m(原地不动)的比例 %.2f' % (
        far.sum(), (dh1[far] < dh0[far] - 0.2).mean(), np.median(dh1[far] - dh0[far]), np.median(mvd[far]), (mvd[far] < 0.3).mean()))
with open(os.path.join(DATA, 'B2_bursts.csv'), 'w', newline='') as fo:
    w = csv.writer(fo); w.writerow(['side', 'f_start', 't_start', 'n_frames', 'peak_speed', 'net_disp_m', 't_accel_to90', 't_decel_from90', 'dx', 'dz']); w.writerows(bursts)
open(os.path.join(DATA, 'B2_move_stats.txt'), 'w', encoding='utf-8').write('\n'.join(out))
