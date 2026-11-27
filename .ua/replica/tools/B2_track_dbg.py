# -*- coding: utf-8 -*-
"""追踪调试图：python B2_track_dbg.py 100,425,1000 → frames/B2_fx/dbg_track.jpg"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from B2_track import *
from PIL import ImageDraw
import time
fs = [int(x) for x in sys.argv[1].split(",")]
out = []
for f in fs:
    (ff, a), = grab(f, 1, crop=(0, Y0, W, CH))
    t0 = time.time(); r = analyze(a, f, [None, None]); dt = time.time() - t0
    a16 = a.astype(np.int16); bg, d3, diff, fg, additive, shadow, body = masks(a16, f)
    vis = (a * 0.35).astype(np.uint8); vis[body] = (255, 255, 255); vis[shadow & fg] = (90, 0, 160); vis[fg & additive] = (0, 120, 0)
    im = Image.fromarray(vis); d = ImageDraw.Draw(im)
    for p, col in (("L", (255, 255, 0)), ("R", (255, 128, 0))):
        if p + "_cx" not in r: continue
        d.rectangle([r[p + "_x0"], r[p + "_top"] - Y0, r[p + "_x1"], r[p + "_bot"] - Y0], outline=col, width=2)
        if p + "_sx" in r: d.ellipse([r[p + "_sx"] - 5, r[p + "_sy"] - Y0 - 5, r[p + "_sx"] + 5, r[p + "_sy"] - Y0 + 5], outline=(255, 0, 0), width=3)
        if p + "_shx" in r: d.ellipse([r[p + "_shx"] - 5, r[p + "_shy"] - Y0 - 5, r[p + "_shx"] + 5, r[p + "_shy"] - Y0 + 5], outline=(255, 0, 255), width=3)
        if p + "_rx0" in r: d.rectangle([r[p + "_rx0"], r[p + "_ry0"] - Y0, r[p + "_rx1"], r[p + "_ry1"] - Y0], outline=(0, 255, 255), width=2)
    print(f, "%.0f ms" % (dt * 1000), {k: (round(float(v), 1)) for k, v in r.items()})
    out.append((ff, np.asarray(im)[160:700:1]))
sheet(out, 1, os.path.join(FR, "dbg_track.jpg"), fsz=20)
