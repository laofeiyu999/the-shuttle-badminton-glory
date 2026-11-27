"""C_overview.py  全片概览联系表：每 STEP 帧取 1 帧（默认 8 帧≈7.75 fps），每张 5x4=20 格，每格 512 px。
同时可生成全帧率联系表（--full，6x5=30 帧/张，480 px/格，约 108 张）。
输出到 frames/C_tb/ov_XXXX.jpg（XXXX=起始帧号）或 frames/C_tb/full/ff_XXXX.jpg。
"""
import sys, os, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from C_sheet import load_pts, sheet, SRC, W, H, ROOT

full = '--full' in sys.argv
step = 1 if full else 8
cols, rows, cell = (6, 5, 480) if full else (5, 4, 512)
outdir = os.path.join(ROOT, 'frames', 'C_tb', 'full' if full else '')
os.makedirs(outdir, exist_ok=True)
pts = load_pts()
sw = 964  # 解码端先缩到 964 宽，节省管道流量
sh = int(round(H * sw / W)) // 2 * 2
cmd = ['ffmpeg', '-v', 'fatal', '-i', SRC, '-an', '-fps_mode', 'passthrough', '-vf', f'scale={sw}:{sh}',
       '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 8)
fs = sw * sh * 3
buf = []; idx = []; n = 0; per = cols * rows
while True:
    raw = p.stdout.read(fs)
    if len(raw) < fs:
        break
    if n % step == 0:
        buf.append(np.frombuffer(raw, np.uint8).reshape(sh, sw, 3)); idx.append(n)
        if len(buf) == per:
            sheet(np.stack(buf), idx, pts, os.path.join(outdir, ('ff_%04d.jpg' if full else 'ov_%04d.jpg') % idx[0]), cell, cols, q=85)
            buf = []; idx = []
    n += 1
if buf:
    sheet(np.stack(buf), idx, pts, os.path.join(outdir, ('ff_%04d.jpg' if full else 'ov_%04d.jpg') % idx[0]), cell, cols, q=85)
print('frames decoded', n)
