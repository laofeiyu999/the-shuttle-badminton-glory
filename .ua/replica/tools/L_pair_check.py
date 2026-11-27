# -*- coding: utf-8 -*-
"""按击球闪光对齐，重新把主视角按键配到侧视角左方的拍上，与 B_shots.csv 现有的 key_A 比较。
python tools/L_pair_check.py → data/L_pair_check.md"""
import io, csv
import numpy as np
P = [(float(r['t_s']), r['key'], r['energy_before']) for r in csv.DictReader(io.open('data/A_hits.csv', encoding='utf-8-sig'))]
S = [r for r in csv.DictReader(io.open('data/B_shots.csv', encoding='utf-8-sig')) if r['side'] == 'L']
pt = np.array([p[0] for p in P])
same = diff = newly = lost = none = 0; rows = []; ediff = 0
for r in S:
    ts = float(r['t_s']); tm = ts - 0.015 if ts < 142.5 else ts - 0.30      # 侧视角击球时刻换到主视角
    d = pt - (tm - 0.25)                                                   # 按键应在击球闪光前约 0.25 s
    i = int(np.abs(d).argmin()); new = P[i][1] if abs(d[i]) <= 0.12 else ''
    old = r['key_A']
    if old and new:
        if old == new:
            same += 1
            try:
                if abs(float(r['energyA_before']) - float(P[i][2])) > 1: ediff += 1
            except Exception: pass
        else: diff += 1; rows.append((r['shot'], '%.2f' % ts, r['type'], old, new, '%+.2f' % d[i]))
    elif new and not old: newly += 1; rows.append((r['shot'], '%.2f' % ts, r['type'], '（无）', new, '%+.2f' % d[i]))
    elif old and not new: lost += 1; rows.append((r['shot'], '%.2f' % ts, r['type'], old, '（无）', '%+.2f' % d[i]))
    else: none += 1
L = ['# 侧视角拍表的按键配对复核（击球闪光对齐）', '', '由 `.ua/replica/tools/L_pair_check.py` 生成。规则：把侧视角左方每一拍的击球时刻换到主视角时间（142.5 s 前减 0.015 s，之后减 0.30 s），在它之前 0.25 s 的前后 0.12 s 内找主视角按键。', '',
     '左方 %d 拍：新旧配对相同 %d 拍（其中按键前能量不同的 %d 拍），按键不同 %d 拍，原先没配上现在配上 %d 拍，原先配上现在配不上 %d 拍，两边都没配上 %d 拍。' % (len(S), same, ediff, diff, newly, lost, none), '']
if rows:
    L += ['| 拍 | 侧视角时刻 s | 球种 | 原配对 | 新配对 | 按键偏离预期 s |', '| --- | --- | --- | --- | --- | --- |'] + ['| ' + ' | '.join(x) + ' |' for x in rows]
io.open('data/L_pair_check.md', 'w', encoding='utf-8').write(chr(10).join(L)); print('ok')
