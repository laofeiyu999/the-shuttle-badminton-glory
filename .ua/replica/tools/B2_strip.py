# -*- coding: utf-8 -*-
"""逐帧拼条：python B2_strip.py 起始帧 帧数 步长 x y w h 缩放 列数 输出名(不带扩展名, 存到 frames/B2_fx/)"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
def strip(f0, n, step, x, y, w, h, sc, cols, name, fsz=16, q=88):
    x = max(0, min(x, W - w)); y = max(0, min(y, H - h))
    fr = grab(f0, n, crop=(x, y, w, h), scale=(int(w * sc) // 2 * 2, int(h * sc) // 2 * 2), step=step)
    p = os.path.join(FR, name + ".jpg")
    sheet(fr, cols, p, fsz=fsz, quality=q)
    return p
if __name__ == "__main__":
    a = sys.argv
    print(strip(int(a[1]), int(a[2]), int(a[3]), int(a[4]), int(a[5]), int(a[6]), int(a[7]), float(a[8]), int(a[9]), a[10]))
