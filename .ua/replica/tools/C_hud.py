# HUD 读数：检测右侧“击球速度 xxkm/h”黄字出现的时段、底部蓄力槽“球速”出现时段，并各拼一张条图
import sys, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, 'tools')
from C_sheet import load_pts, read_frames
pts = load_pts()
N = len(pts)
def scan(crop, fn):
    vals = []; keep = {}
    for s in range(0, N, 400):
        arr, f0 = read_frames(s, min(s + 399, N - 1), pts, crop)
        for i in range(len(arr)):
            vals.append(fn(arr[i].astype(int)))
            keep[s + i] = arr[i] if (s + i) % 2 == 0 else None
    return np.array(vals), keep
def yellow(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return int(((r > 170) & (g > 150) & (b < 120)).sum())
def white(a):
    return int((a.min(axis=-1) > 170).sum())
def episodes(v, th, gap=4):
    on = np.where(v > th)[0]; ep = []
    for f in on:
        if ep and f - ep[-1][1] <= gap: ep[-1][1] = f
        else: ep.append([f, f])
    return ep
sp_crop = (1350, 648, 96, 36)
v, keep = scan(sp_crop, yellow)
ep = episodes(v, 25)
print('speed readout episodes (f0,f1,t0,t1,dur):')
tiles = []
for a, b in ep:
    if b - a < 3: continue
    print(a, b, round(pts[a], 3), round(pts[b], 3), round(pts[b] - pts[a], 3))
    m = (a + b) // 2; m -= m % 2
    tiles.append((a, keep[m] if keep.get(m) is not None else keep[m + 2]))
W, H = sp_crop[2] * 3, sp_crop[3] * 3
im = Image.new('RGB', (W * 5, (H + 14) * ((len(tiles) + 4) // 5)))
d = ImageDraw.Draw(im)
for k, (a, t) in enumerate(tiles):
    x, y = (k % 5) * W, (k // 5) * (H + 14)
    im.paste(Image.fromarray(t).resize((W, H), Image.LANCZOS), (x, y + 14))
    d.text((x + 2, y + 1), f'{a} {pts[a]:.3f}', fill=(255, 255, 0))
im.save('frames/C_tb/hud_speed_all.png')
g_crop = (700, 885, 130, 30)
v2, _ = scan(g_crop, white)
print('gauge text episodes:', [(a, b, round(pts[a], 3), round(pts[b], 3)) for a, b in episodes(v2, 60) if b - a > 3])
