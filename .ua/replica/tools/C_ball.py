# 跟球放大条图：给定若干路标 (帧,x,y)（显示坐标），线性插值球位置，逐帧裁 SxS 放大 Z 倍拼条
# 用法: python tools/C_ball.py OUT.png S Z step f:x,y f:x,y ...
import sys, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames
pts = load_pts()
out, S, Z, step = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
wp = []
for s in sys.argv[5:]:
    f, xy = s.split(':'); x, y = xy.split(','); wp.append((int(f), float(x), float(y)))
fs = [w[0] for w in wp]
frames, _ = read_frames(fs[0], fs[-1], pts, None)
idx = list(range(fs[0], fs[-1] + 1, step))
cols = min(len(idx), 8); rows = (len(idx) + cols - 1) // cols
im = Image.new('RGB', (cols * S * Z, rows * (S * Z)))
d = ImageDraw.Draw(im)
for k, f in enumerate(idx):
    x = np.interp(f, fs, [w[1] for w in wp]); y = np.interp(f, fs, [w[2] for w in wp])
    x0 = int(np.clip(x - S / 2, 0, 1446 - S)); y0 = int(np.clip(y - S / 2, 0, 1072 - S))
    t = Image.fromarray(frames[f - fs[0]][y0:y0 + S, x0:x0 + S]).resize((S * Z, S * Z), Image.NEAREST if Z >= 4 else Image.BICUBIC)
    px, py = (k % cols) * S * Z, (k // cols) * S * Z
    im.paste(t, (px, py)); d.rectangle([px, py, px + 92, py + 11], fill=(0, 0, 0)); d.text((px + 2, py), f'{f} {pts[f]:.3f}', fill=(255, 255, 0))
im.save(out); print(out, im.size)
