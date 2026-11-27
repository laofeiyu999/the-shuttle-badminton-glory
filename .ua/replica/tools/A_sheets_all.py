# -*- coding: utf-8 -*-
"""全片 0.5 s 间隔联系表（单次顺序解码，快）。输出 frames/A_main/ov_XX.jpg
python A_sheets_all.py [step_frames=30] [cols=4] [rows=6] [cellw=480] [prefix=ov]
"""
import sys, os
from PIL import Image, ImageDraw
from A_common import *

step = int(sys.argv[1]) if len(sys.argv) > 1 else 30
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 4
rows = int(sys.argv[3]) if len(sys.argv) > 3 else 6
cellw = int(sys.argv[4]) if len(sys.argv) > 4 else 480
prefix = sys.argv[5] if len(sys.argv) > 5 else 'ov'
f0 = int(sys.argv[6]) if len(sys.argv) > 6 else 0
f1 = int(sys.argv[7]) if len(sys.argv) > 7 else NF
cellh = int(round(cellw * H / W))
per = cols * rows
ft = font(max(12, cellw // 24))
im = None
k = 0
si = 0
n = (f1 - f0 + step - 1) // step
for f, a in iter_frames(f0, None, step, None, (cellw, cellh)) if f0 == 0 else iter_frames(f0, None, step, None, (cellw, cellh)):
    if f >= f1:
        break
    if k % per == 0:
        im = Image.new('RGB', (cols * cellw, rows * cellh))
        d = ImageDraw.Draw(im)
    j = k % per
    x, y = (j % cols) * cellw, (j // cols) * cellh
    im.paste(Image.fromarray(a), (x, y))
    s = '%s f%d' % (tc(f), f)
    d.rectangle([x, y, x + ft.getlength(s) + 6, y + ft.size + 4], fill=(0, 0, 0))
    d.text((x + 3, y + 1), s, fill=(255, 255, 0), font=ft)
    k += 1
    if k % per == 0:
        im.save(os.path.join(FR, '%s_%02d.jpg' % (prefix, si)), quality=85)
        si += 1
if k % per:
    im.save(os.path.join(FR, '%s_%02d.jpg' % (prefix, si)), quality=85)
    si += 1
print('sheets', si, 'frames', k)
