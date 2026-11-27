# 视频3（拍屏，30 fps 恒定帧率，720x1270 竖拍）联系表：只读 References，按时间抽帧，裁上半屏（屏幕区域），格子标时间码
# 用法: python tools/C_v3.py OUT.jpg t0 t1 [--crop x,y,w,h] [--cols 5] [--cell 384] [--step 1]
import sys, glob, subprocess, argparse, numpy as np
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('t0', type=float); ap.add_argument('t1', type=float)
ap.add_argument('--crop', default='0,0,720,640'); ap.add_argument('--cols', type=int, default=5); ap.add_argument('--cell', type=int, default=384); ap.add_argument('--step', type=int, default=1)
a = ap.parse_args()
src = glob.glob('../../References/游戏详细参考图与视频/网球宝贝/*参考视频3.mp4')[0]
x, y, w, h = [int(v) for v in a.crop.split(',')]
f0, f1 = round(a.t0 * 30), round(a.t1 * 30)
raw = subprocess.run(['ffmpeg', '-v', 'fatal', '-i', src, '-vf', 'select=between(n' + chr(92) + f',{f0}' + chr(92) + f',{f1}),crop={w}:{h}:{x}:{y}', '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)[::a.step]
ch = round(a.cell * h / w); rows = -(-len(fr) // a.cols)
S = Image.new('RGB', (a.cols * a.cell, rows * ch))
for i, f in enumerate(fr):
    im = Image.fromarray(f).resize((a.cell, ch), Image.LANCZOS); d = ImageDraw.Draw(im)
    n = f0 + i * a.step; d.rectangle((0, 0, 118, 14), fill=(0, 0, 0)); d.text((2, 1), f'{n} {n/30:.3f}s', fill=(255, 255, 0))
    S.paste(im, ((i % a.cols) * a.cell, (i // a.cols) * ch))
S.save(a.out, quality=90); print(a.out, len(fr), S.size)
