# B_view.py 看图工具：python B_view.py out.jpg start count step x y w h scale cols [label]
# 从 start 帧起每 step 帧取一帧，共 count 帧，裁剪 (x,y,w,h)，放大 scale 倍，拼成 cols 列联系表，左上角标帧号
import numpy as np, sys
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from PIL import Image, ImageDraw
def sheet(out, start, count, step, x, y, w, h, scale, cols, overlay=None, quality=88):
    tiles = []
    need = set(range(start, start + count * step, step))
    for i, f in frames(start, (count - 1) * step + 1):
        if i in need:
            im = Image.fromarray(f[y:y+h, x:x+w])
            if overlay: overlay(i, im, x, y)
            if scale != 1:
                im = im.resize((int(w*scale), int(h*scale)), Image.LANCZOS if scale < 1 else Image.NEAREST)
            d = ImageDraw.Draw(im); d.rectangle([0, 0, 58, 12], fill=(0, 0, 0)); d.text((2, 0), f'{i} {i/FPS:.2f}', fill=(255, 255, 0))
            tiles.append(im)
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new('RGB', (tw * cols, th * rows))
    for k, t in enumerate(tiles):
        S.paste(t, ((k % cols) * tw, (k // cols) * th))
    S.save(out, quality=quality)
    print(out, S.size)
if __name__ == '__main__':
    a = sys.argv
    out = a[1] if ('/' in a[1] or ':' in a[1]) else FR + '/' + a[1]
    sheet(out, int(a[2]), int(a[3]), int(a[4]), int(a[5]), int(a[6]), int(a[7]), int(a[8]), float(a[9]), int(a[10]))
