# 触球闪光逐帧测量：以触球前第 6 帧为参考，统计每帧“增亮像素”的面积、外接框、平均颜色
# 用法: python tools/C_flash.py name:frame[:x,y] ...   （x,y 可选：闪光大致中心，显示坐标；不给则自动找）
import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames
pts = load_pts()
R = 170  # 半窗
for spec in sys.argv[1:]:
    p = spec.split(':'); name, f = p[0], int(p[1])
    arr, _ = read_frames(f - 6, f + 34, pts, (0, 0, 1446, 1072))
    a = arr.astype(np.int16); ref = a[0]
    def inc(i):
        d = (a[i] - ref).max(axis=-1); br = a[i].max(axis=-1)
        return (d > 70) & (br > 185)
    if len(p) > 2:
        cx, cy = [int(v) for v in p[2].split(',')]
    else:
        best = None
        for i in range(6, 20):
            m = inc(i); m[:60] = False; m[880:] = False; m[:, 1230:] = False
            m = ndi.binary_opening(m, np.ones((3, 3)))
            lab, n = ndi.label(m)
            if n == 0: continue
            sz = ndi.sum(m, lab, range(1, n + 1)); k = int(np.argmax(sz))
            if best is None or sz[k] > best[0]:
                c = ndi.center_of_mass(m, lab, k + 1); best = (sz[k], int(c[1]), int(c[0]))
        cx, cy = best[1], best[2]
    x0, y0 = max(cx - R, 0), max(cy - R, 0)
    print(f'## {name} ref frame {f-6}, center=({cx},{cy})')
    for i in range(2, len(a)):
        m = inc(i)[y0:cy + R, x0:cx + R]
        n = int(m.sum())
        if n < 15: print(f'  {f-6+i} {pts[f-6+i]:.3f} area=0'); continue
        ys, xs = np.where(m)
        col = a[i][y0:cy + R, x0:cx + R][m].mean(0).astype(int)
        # 核心：近白像素
        core = (a[i][y0:cy + R, x0:cx + R].min(axis=-1) > 225) & m
        print(f'  {f-6+i} {pts[f-6+i]:.3f} area={n} bbox={xs.max()-xs.min()+1}x{ys.max()-ys.min()+1} rgb={tuple(int(v) for v in col)} white={int(core.sum())}')
