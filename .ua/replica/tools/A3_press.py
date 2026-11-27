# -*- coding: utf-8 -*-
"""A3: 由 A3_btnscan.npy 检出按键事件。
按下表现(目视核对 f237 近球、f959 远球)：键盘面整体变暗约 10%(盘内平均亮度 195→175)，持续约 20 帧，
同时出现录屏触点灰圆(系统“显示触摸”)。检测：4 帧内亮度骤降 ≥7 且随后 12 帧内最低值 ≤ 基线−9；HUD 需可见。
持续帧数 dim = 亮度低于(基线−6)的帧数(HUD 消失则截断)。输出 data/A3_press.csv。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
d = np.load(DATA + '/A3_btnscan.npy')
names = ['高吊', '近球', '远球']
lum = d[:, :, :3].mean(2); bg = d[:, :, 6]
vis = (lum - bg) > 40
ev = []
for k in range(3):
    L = lum[:, k]; f = 12
    while f < NF - 14:
        if vis[f - 2:f + 5, k].all() and L[f + 4] - L[f] <= -7:
            base = np.median(L[f - 8:f + 1])
            # 起始帧：第一帧低于 base-2
            s = f
            while s < f + 5 and L[s] > base - 2: s += 1
            seg = L[s:s + 14]
            if seg.min() <= base - 9:
                g = s
                while g < NF - 1 and g - s < 90 and vis[g, k] and L[g] < base - 6: g += 1
                hud_lost = not vis[min(g, NF - 1), k]
                ev.append((s, k, g - s, base - seg.min(), base, int(hud_lost), abs(bg[s + 6, k] - bg[s - 2, k])))
                f = max(g, s + 20); continue
        f += 1
ev.sort()
with open(DATA + '/A3_press.csv', 'w', encoding='utf-8') as fo:
    fo.write('frame,t_s,key,dim_frames,depth,base_lum,hud_lost_during,bg_shift\n')
    for e in ev: fo.write('%d,%.3f,%s,%d,%.1f,%.1f,%d,%.1f\n' % (e[0], e[0] / 60, names[e[1]], e[2], e[3], e[4], e[5], e[6]))
print('events', len(ev), [sum(1 for e in ev if e[1] == k) for k in range(3)])
for i in range(0, len(ev), 4):
    print(' | '.join('%5d %s d%2d h%2d b%2d%s' % (e[0], 'GJY'[e[1]], e[2], e[3], e[6], '*' if e[5] else ' ') for e in ev[i:i + 4]))
