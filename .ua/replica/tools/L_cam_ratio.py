# -*- coding: utf-8 -*-
"""把相机跟随式代回针孔模型，算各站位下的画面比例。python tools/L_cam_ratio.py → data/L_cam_ratio.md"""
import io, math
ASP = 1922 / 880.0
def proj(cy, cz, pitch, fov, y, z, x=0.0):
    p = math.radians(pitch); vy = y - cy; vz = z - cz
    depth = -vy * math.sin(p) - vz * math.cos(p); up = vy * math.cos(p) - vz * math.sin(p)
    t = math.tan(math.radians(fov / 2))
    return 0.5 - up / depth / (2 * t), x / depth / (2 * t * ASP)
SETS = [('原式（音频对齐）', lambda d: (4.45 + 0.32 * d, 11.2 + 0.87 * d, 19.9 + 0.47 * d)),
        ('新式（击球闪光对齐）', lambda d: (4.25 + 0.38 * d, 10.9 + d, 20.0 + 0.46 * d))]
L = ['# 相机跟随式对应的画面比例', '', '由 `.ua/replica/tools/L_cam_ratio.py` 生成。针孔模型，垂直视场角 30°，宽高比 2.184:1，人物身高 1.75 m，网顶 1.53 m，球网宽 6.1 m，底线距网 6.70 m。屏高百分比从顶边量起。', '']
for nm, fn in SETS:
    L += ['## ' + nm, '', '| d m | 相机距网 m | 高度 m | 俯角 ° | 人物头顶 | 人物脚底 | 人物身高占屏高 | 网带上沿 | 球网占屏宽 | 对方底线 | 本方底线 |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for d in (1.0, 2.0, 3.0, 4.0, 5.0, 6.2):
        cy, cz, pt = fn(d)
        top = proj(cy, cz, pt, 30, 1.75, d)[0]; foot = proj(cy, cz, pt, 30, 0, d)[0]; net = proj(cy, cz, pt, 30, 1.53, 0)
        netw = 2 * proj(cy, cz, pt, 30, 1.53, 0, 3.05)[1]; far = proj(cy, cz, pt, 30, 0, -6.7)[0]; near = proj(cy, cz, pt, 30, 0, 6.7)[0]
        L.append('| %.1f | %.2f | %.2f | %.1f | %.0f%% | %.0f%% | %.1f%% | %.1f%% | %.1f%% | %.0f%% | %s |' % (d, cz, cy, pt, top * 100, foot * 100, (foot - top) * 100, net[0] * 100, netw * 100, far * 100, ('%.0f%%' % (near * 100)) if near <= 1 else '画面外（%.0f%%）' % (near * 100)))
    L.append('')
io.open('data/L_cam_ratio.md', 'w', encoding='utf-8').write(chr(10).join(L)); print('ok')
