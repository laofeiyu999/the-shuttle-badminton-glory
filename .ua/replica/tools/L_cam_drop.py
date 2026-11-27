# -*- coding: utf-8 -*-
"""检验：主视角相机“领先”本方人物约 0.3 s，是不是因为相机还跟着落点。
特征：d = 本方人物距网；inc = 来球飞行期间（落点 − 人物位置），落点取本方下一次击球时的人物位置或球的落地点；
      out = 本方出球飞行期间（落点 − 人物位置），落点在对方半场（负值）。三者过同一个一阶低通后回归相机距网。
在 .ua/replica 下运行：python tools/L_cam_drop.py → data/L_cam_drop.md
"""
import io, csv, runpy
import numpy as np
g = runpy.run_path('tools/L_cam_dyn.py')
C = g['C']; sel = g['sel']; N = g['N']; DT = g['DT']; own_d = g['own_d']; opp_d = g['opp_d']; lp = g['lp']; reg = g['reg']; num = g['num']
tm = C['t'][sel]; cz = C['cz'][sel]
base = np.where(tm < 142.5, tm + g['SYNC'][0], tm + g['SYNC'][1])
S = list(csv.DictReader(io.open('data/B_shots.csv', encoding='utf-8-sig')))
inc = np.zeros(N); out_ = np.zeros(N); flying = np.zeros(N)
used = 0
for r in S:
    try: f0 = int(float(r['hit_frame'])); f1 = int(float(r['end_frame']))
    except Exception: continue
    if not (0 <= f0 < f1 < N) or f1 - f0 > 200: continue
    hit_by_opp = '对方' in r['end_kind']
    if r['side'] == 'R':   # 对手打过来
        drop = own_d[f1] if hit_by_opp else -num(r['end_x'])
        if np.isnan(drop) or drop < 0 or drop > 7.5: continue
        inc[f0:f1] = drop - own_d[f0:f1]; flying[f0:f1] = 1; used += 1
    else:                  # 本方打过去
        drop = opp_d[f1] if hit_by_opp else num(r['end_x'])
        if np.isnan(drop) or drop < 0 or drop > 7.5: continue
        out_[f0:f1] = -drop - own_d[f0:f1]; flying[f0:f1] = 2; used += 1
inc = np.nan_to_num(inc); out_ = np.nan_to_num(out_)
L = ['# 主视角相机是否跟落点', '', '由 `.ua/replica/tools/L_cam_drop.py` 生成。用到 %d 拍；回合内相机样本 %d 个。' % (used, sel.sum()), '',
     '回归式：相机距网 = c0 + c1 × d + c2 × 来球项 + c3 × 出球项，三项过同一个一阶低通（时间常数 tau）。偏移 = 在击球闪光对齐值之外再加的时间差，正值表示拿更晚的人物位置去配相机。', '']
L += ['## 1 只用人物位置', '', '| 偏移 s | tau 0 | tau 0.1 | tau 0.2 | tau 0.3 | tau 0.5 |', '| --- | --- | --- | --- | --- | --- |']
TA = (0, 0.1, 0.2, 0.3, 0.5); OFF = np.arange(-0.3, 0.41, 0.1)
for off in OFF:
    ii = np.clip(np.round((base + off) / DT).astype(int), 0, N - 1)
    L.append('| %+.1f | ' % off + ' | '.join('%.3f' % reg(cz, [lp(own_d, t)[ii]])[1] for t in TA) + ' |')
L += ['', '## 2 人物位置 + 落点', '', '| 偏移 s | tau 0 | tau 0.1 | tau 0.2 | tau 0.3 | tau 0.5 |', '| --- | --- | --- | --- | --- | --- |']
best = None
for off in OFF:
    ii = np.clip(np.round((base + off) / DT).astype(int), 0, N - 1); row = []
    for t in TA:
        co, r2, sd, n = reg(cz, [lp(own_d, t)[ii], lp(inc, t)[ii], lp(out_, t)[ii]]); row.append('%.3f' % r2)
        if best is None or r2 > best[0]: best = (r2, off, t, co, sd)
    L.append('| %+.1f | ' % off + ' | '.join(row) + ' |')
L += ['', '最好的一格：偏移 %+.1f s、tau %.1f s，R² %.3f，残差 %.2f m；相机距网 = %.2f + %.3f × d + %.3f × 来球项 + %.3f × 出球项。' % (best[1], best[2], best[0], best[4], best[3][0], best[3][1], best[3][2], best[3][3]), '']
L += ['## 3 偏移固定为 0 时各 tau 的系数', '', '| tau s | c0 | c1（人物） | c2（来球落点） | c3（出球落点） | R² | 残差 m |', '| --- | --- | --- | --- | --- | --- | --- |']
ii = np.clip(np.round(base / DT).astype(int), 0, N - 1)
for t in (0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5):
    co, r2, sd, n = reg(cz, [lp(own_d, t)[ii], lp(inc, t)[ii], lp(out_, t)[ii]])
    L.append('| %.2f | %.2f | %.3f | %.3f | %.3f | %.3f | %.2f |' % (t, co[0], co[1], co[2], co[3], r2, sd))
fl = flying[ii]
L += ['', '样本构成：来球飞行中 %d 个，出球飞行中 %d 个，其余 %d 个。' % ((fl == 1).sum(), (fl == 2).sum(), (fl == 0).sum())]
io.open('data/L_cam_drop.md', 'w', encoding='utf-8').write(chr(10).join(L))
print('ok', used)
