# 回合联系表：每格 = 连续 k 帧逐像素取最大值（lighten 叠加），保证每一帧都进入画面
# 用法: python tools/C_rally.py PREFIX f0 f1 [--k 4] [--crop x,y,w,h] [--cols 4] [--rows 5] [--cell 400]
import sys, argparse, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames
ap = argparse.ArgumentParser()
ap.add_argument('prefix'); ap.add_argument('f0', type=int); ap.add_argument('f1', type=int)
ap.add_argument('--k', type=int, default=4); ap.add_argument('--crop', default='100,150,1180,780')
ap.add_argument('--cols', type=int, default=4); ap.add_argument('--rows', type=int, default=5)
ap.add_argument('--cell', type=int, default=400)
a = ap.parse_args()
pts = load_pts(); crop = tuple(int(v) for v in a.crop.split(','))
per = a.cols * a.rows * a.k
ch = int(round(a.cell * crop[3] / crop[2]))
for s in range(a.f0, a.f1 + 1, per):
    e = min(s + per - 1, a.f1, len(pts) - 1)
    arr, _ = read_frames(s, e, pts, crop)
    im = Image.new('RGB', (a.cols * a.cell, a.rows * ch)); d = ImageDraw.Draw(im)
    for c in range(0, len(arr), a.k):
        m = arr[c:c + a.k].max(axis=0)
        i = c // a.k; x, y = (i % a.cols) * a.cell, (i // a.cols) * ch
        im.paste(Image.fromarray(m).resize((a.cell, ch), Image.LANCZOS), (x, y))
        f = s + c
        d.rectangle([x, y, x + 150, y + 12], fill=(0, 0, 0))
        d.text((x + 2, y), f'{f}-{min(f + a.k - 1, e)} {pts[f]:.3f}', fill=(255, 255, 0))
    out = f'{a.prefix}_{s:04d}.jpg'; im.save(out, quality=90); print(out, im.size)
