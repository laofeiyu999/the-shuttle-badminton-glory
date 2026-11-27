# 单拍放大：自动找触球闪光中心，输出 (1) 闪光放大图 zf_<name>.jpg：触球前 2 到后 13 个游戏帧（每 2 录屏帧取 1），裁 420x420 原始像素 1:1
#          (2) 出球拖尾图 zt_<name>.jpg：触球后 0–0.9 s 每 2 录屏帧 1 格，裁 760x560 → 0.6 倍
# 用法: python tools/C_hit.py name:frame[:cx,cy] ...
import sys, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames, sheet
pts = load_pts()
for spec in sys.argv[1:]:
    p = spec.split(':'); name, f = p[0], int(p[1])
    if len(p) > 2: cx, cy = [int(v) for v in p[2].split(',')]
    else:
        arr, _ = read_frames(f - 4, f + 10, pts, (0, 0, 1446, 1072)); a = arr.astype(np.int16)
        best = (0, 700, 500)
        for i in range(4, len(a)):
            d = (a[i] - a[i - 4]).max(axis=-1); m = (d > 90) & (a[i].max(axis=-1) > 200)
            m[:70] = False; m[860:] = False; m[:, 1230:] = False
            dens = ndi.uniform_filter(m.astype(np.float32), 41)
            k = np.unravel_index(np.argmax(dens), dens.shape)
            if dens[k] > best[0]: best = (dens[k], int(k[1]), int(k[0]))
        cx, cy = best[1], best[2]
    x0 = int(min(max(cx - 210, 0), 1446 - 420)); y0 = int(min(max(cy - 210, 0), 1072 - 420))
    fr, f0 = read_frames(f - 4, f + 27, pts, (x0, y0, 420, 420))
    idx = list(range(0, len(fr), 2))
    sheet(fr[idx], [f0 + i for i in idx], pts, f'frames/C_tb/zf_{name}.jpg', 360, 4, 360 / 420)
    X0 = int(min(max(cx - 380, 0), 1446 - 760)); Y0 = int(min(max(cy - 420, 60), 1072 - 560))
    fr, f0 = read_frames(f, f + 59, pts, (X0, Y0, 760, 560))
    idx = list(range(0, len(fr), 3))
    sheet(fr[idx], [f0 + i for i in idx], pts, f'frames/C_tb/zt_{name}.jpg', 400, 4, 400 / 760)
    print(name, 'center', cx, cy, 'flash crop', (x0, y0), 'trail crop', (X0, Y0))
