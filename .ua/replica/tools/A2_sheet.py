# -*- coding: utf-8 -*-
"""A2_sheet.py name f1 f2 ... (最多 6 帧)：2 列 x 3 行联系表，每格 800 px 宽，叠加 100 px 原始坐标网格（标注原始像素值）。"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
name = sys.argv[1]; fs = [int(a) for a in sys.argv[2:]]
cw = 800; ch = int(round(cw * H / W)); s = cw / W
im = Image.new('RGB', (2 * cw, ((len(fs) + 1) // 2) * ch)); d = ImageDraw.Draw(im); ft = font(12); ft2 = font(16)
for k, f in enumerate(fs):
    a = get_frame(f); x0, y0 = (k % 2) * cw, (k // 2) * ch
    im.paste(Image.fromarray(a).resize((cw, ch), Image.LANCZOS), (x0, y0))
    for gx in range(100, W, 100):
        d.line([x0 + gx * s, y0, x0 + gx * s, y0 + ch], fill=(255, 255, 0) if gx % 500 == 0 else (0, 255, 255), width=1)
        d.text((x0 + gx * s + 2, y0 + ch - 14), str(gx), fill=(255, 255, 0), font=ft)
    for gy in range(50, H, 50):
        d.line([x0, y0 + gy * s, x0 + cw, y0 + gy * s], fill=(255, 255, 0) if gy % 250 == 0 else ((0, 255, 255) if gy % 100 == 0 else (0, 110, 110)), width=1)
        if gy % 100 == 0: d.text((x0 + 2, y0 + gy * s), str(gy), fill=(255, 255, 0), font=ft)
    lab = '%s f%d' % (tc(f), f); d.rectangle([x0 + 300, y0, x0 + 300 + ft2.getlength(lab) + 6, y0 + 20], fill=(0, 0, 0)); d.text((x0 + 303, y0 + 1), lab, fill=(255, 255, 0), font=ft2)
out = os.path.join(FR, 'A2_s_%s.jpg' % name); im.save(out, quality=84); print(out)
