# -*- coding: utf-8 -*-
"""主视角相机对本方人物位置的回归与分片区中位数（时间按击球闪光对齐）。
在 .ua/replica 下运行：python tools/L_cam_zone.py → data/L_cam_zone.md
"""
import io, runpy
import numpy as np
g = runpy.run_path('tools/L_cam_dyn.py')
C = g['C']; sel = g['sel']; N = g['N']; DT = g['DT']; own_d = g['own_d']; own_lat = g['own_lat']; reg = g['reg']; ts = g['ts']
ii = np.clip(np.round(ts / DT).astype(int), 0, N - 1)
cz = C['cz'][sel]; cx = C['cx'][sel]; cy = C['cy'][sel]; fov = C['fov'][sel]; pitch = C['pitch'][sel]
d = own_d[ii]; lat = own_lat[ii]; nar = fov < 33
L = ['# 主视角相机对本方人物位置的回归（击球闪光对齐）', '', '由 `.ua/replica/tools/L_cam_zone.py` 生成。回合内样本 %d 个，其中视场角没有放宽（vFOV < 33°）的 %d 个。d = 本方人物到网的纵向距离。' % (sel.sum(), nar.sum()), '',
     '## 1 回归', '', '| 量 | 样本范围 | 回归式 | R² | 残差 |', '| --- | --- | --- | --- | --- |']
def row(nm, y, x, m, unit, xn='d'):
    co, r2, sd, n = reg(y[m], [x[m]]); L.append('| %s | %s | %.2f %s %.3f × %s | %.3f | %.2f %s |' % (nm, '全部' if m.all() else 'vFOV < 33°', co[0], '+' if co[1] >= 0 else '−', abs(co[1]), xn, r2, sd, unit))
al = np.ones(len(cz), bool)
row('相机距网 m', cz, d, al, 'm'); row('相机距网 m', cz, d, nar, 'm'); row('相机高度 m', cy, d, al, 'm'); row('相机高度 m', cy, d, nar, 'm')
row('俯角 °', pitch, d, al, '°'); row('俯角 °', pitch, d, nar, '°'); row('相机高度 m', cy, cz, al, 'm', '相机距网'); row('相机横向 m', cx, -lat, al, 'm', '人物横向')
L += ['', '相机在人物身后的水平距离（相机距网 − d）：中位 %.2f m，10%%–90%% 分位 %.2f–%.2f m。' % (np.nanmedian(cz - d), np.nanpercentile(cz - d, 10), np.nanpercentile(cz - d, 90)),
      '人物横向位置范围：10%%–90%% 分位 %.2f 到 %.2f m；相机横向 10%%–90%% 分位 %.2f 到 %.2f m。' % (np.nanpercentile(lat, 10), np.nanpercentile(lat, 90), np.percentile(cx, 10), np.percentile(cx, 90)), '',
      '## 2 分片区中位数', '', '| 片区 | d 范围 m | 样本 | d 中位 | 相机距网 m | 高度 m | 俯角 ° | vFOV ° | 身后距离 m |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
for nm, a, b in (('前场', 0, 1.9), ('前中场', 1.9, 2.8), ('中场', 2.8, 4.2), ('中后场', 4.2, 5.2), ('后场', 5.2, 7.5)):
    m = (d >= a) & (d < b) & nar
    if m.sum() > 5:
        L.append('| %s | %.1f–%.1f | %d | %.2f | %.2f | %.2f | %.1f | %.1f | %.2f |' % (nm, a, b, m.sum(), np.median(d[m]), np.median(cz[m]), np.median(cy[m]), np.median(pitch[m]), np.median(fov[m]), np.median(cz[m] - d[m])))
wide = fov >= 35
L += ['', '## 3 视场角放宽时', '', '样本 %d 个：vFOV 中位 %.1f°，俯角中位 %.1f°（常态 %.1f°），相机距网 − (常态回归值) 中位 %+.2f m，高度 − (常态回归值) 中位 %+.2f m。' % (
    wide.sum(), np.median(fov[wide]), np.median(pitch[wide]), np.median(pitch[nar]),
    np.nanmedian(cz[wide] - np.polyval(np.polyfit(d[nar & ~np.isnan(d)], cz[nar & ~np.isnan(d)], 1), d[wide])),
    np.nanmedian(cy[wide] - np.polyval(np.polyfit(d[nar & ~np.isnan(d)], cy[nar & ~np.isnan(d)], 1), d[wide])))]
io.open('data/L_cam_zone.md', 'w', encoding='utf-8').write(chr(10).join(L))
print('ok')
