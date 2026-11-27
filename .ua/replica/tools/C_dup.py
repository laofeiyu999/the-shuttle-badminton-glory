# 重复帧统计：录屏 62 fps 里有多少帧与前一帧相同（判断游戏实际渲染帧率）
import sys, subprocess, numpy as np
sys.path.insert(0, 'tools')
from C_sheet import load_pts, SRC
pts = load_pts(); w, h = 362, 268
p = subprocess.Popen(['ffmpeg', '-v', 'fatal', '-i', SRC, '-an', '-fps_mode', 'passthrough', '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
prev = None; d = []
while True:
    b = p.stdout.read(w * h)
    if len(b) < w * h: break
    a = np.frombuffer(b, np.uint8).astype(np.int16)
    if prev is not None: d.append(np.abs(a - prev).mean())
    prev = a
d = np.array(d); np.save('data/C_framediff.npy', d)
print('frames', len(d) + 1, 'diff percentiles', np.percentile(d, [5, 25, 50, 75, 95]).round(3))
for lo, hi, nm in [(860, 1700, 'rally1'), (2090, 2840, 'rally2'), (0, 264, 'rally0')]:
    s = d[lo:hi]; dup = (s < 0.25).mean()
    uniq = (s >= 0.25).sum(); dur = pts[hi] - pts[lo]
    print(nm, f'dup ratio {dup:.3f}, unique frames {uniq} in {dur:.2f}s = {uniq/dur:.1f} fps')
