# 极简绘图：散点画到 PIL 图像（无 matplotlib 时用）
import numpy as np
from PIL import Image, ImageDraw
class Plot:
    def __init__(s, w, h, xr, yr, bgc=(255, 255, 255)):
        s.w, s.h, s.xr, s.yr = w, h, xr, yr
        s.im = Image.new('RGB', (w, h), bgc); s.d = ImageDraw.Draw(s.im)
    def xy(s, x, y):
        return (np.asarray(x, float) - s.xr[0]) / (s.xr[1] - s.xr[0]) * s.w, s.h - (np.asarray(y, float) - s.yr[0]) / (s.yr[1] - s.yr[0]) * s.h
    def pts(s, x, y, c=(0, 0, 0), r=1):
        X, Y = s.xy(x, y)
        for a, b in zip(np.atleast_1d(X), np.atleast_1d(Y)):
            s.d.rectangle([a - r, b - r, a + r, b + r], fill=c)
    def line(s, x, y, c=(0, 0, 0), wd=1):
        X, Y = s.xy(x, y); s.d.line(list(zip(X.tolist(), Y.tolist())), fill=c, width=wd)
    def grid(s, xs, ys, c=(210, 210, 210), lab=True):
        for x in xs:
            X, _ = s.xy(x, 0); s.d.line([(X, 0), (X, s.h)], fill=c)
            if lab: s.d.text((X + 2, s.h - 12), f'{x:g}', fill=(90, 90, 90))
        for y in ys:
            _, Y = s.xy(0, y); s.d.line([(0, Y), (s.w, Y)], fill=c)
            if lab: s.d.text((2, Y + 1), f'{y:g}', fill=(90, 90, 90))
    def text(s, x, y, t, c=(0, 0, 0)):
        X, Y = s.xy(x, y); s.d.text((float(X), float(Y)), t, fill=c)
    def save(s, p): s.im.save(p, quality=88)
