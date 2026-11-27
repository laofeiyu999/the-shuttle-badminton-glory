# -*- coding: utf-8 -*-
"""A2_grid.py f [x y w h] [outw]: 抽一帧，可裁剪，叠加原始像素坐标网格，存 frames/A_main/A2_g_<f>[_crop].jpg"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A_common import *
def grid(f, crop=None, outw=1600, name=None, step=None):
    a = get_frame(f)
    x0, y0, w, h = crop if crop else (0, 0, W, H)
    im = Image.fromarray(a[y0:y0+h, x0:x0+w])
    s = outw / w
    im = im.resize((outw, int(round(h*s))), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    if step is None:
        step = 100 if w > 1000 else (50 if w > 500 else (20 if w > 200 else 10))
    ft = font(13)
    for gx in range((x0//step+1)*step, x0+w, step):
        X = (gx-x0)*s
        d.line([X, 0, X, im.size[1]], fill=(255, 255, 0) if gx % (step*5) == 0 else (0, 255, 255), width=1)
        d.text((X+2, 2), str(gx), fill=(255, 255, 0), font=ft)
        d.text((X+2, im.size[1]-16), str(gx), fill=(255, 255, 0), font=ft)
    for gy in range((y0//step+1)*step, y0+h, step):
        Y = (gy-y0)*s
        d.line([0, Y, im.size[0], Y], fill=(255, 255, 0) if gy % (step*5) == 0 else (0, 255, 255), width=1)
        d.text((2, Y+1), str(gy), fill=(255, 255, 0), font=ft)
        d.text((im.size[0]-34, Y+1), str(gy), fill=(255, 255, 0), font=ft)
    out = os.path.join(FR, name or ('A2_g_%05d%s.jpg' % (f, '_c%d_%d' % (x0, y0) if crop else '')))
    im.save(out, quality=85)
    return out
if __name__ == '__main__':
    f = int(sys.argv[1])
    crop = tuple(int(v) for v in sys.argv[2:6]) if len(sys.argv) >= 6 else None
    outw = int(sys.argv[6]) if len(sys.argv) > 6 else 1600
    print(grid(f, crop, outw))
