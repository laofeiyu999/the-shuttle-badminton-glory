# -*- coding: utf-8 -*-
"""任务 A 公共工具：ffmpeg 管道读帧、联系表。
用法见各 A_*.py。视频：.ua/replica/src/fy_main.mp4 (1922x880, 60 fps, 14029 帧)
"""
import subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SRC = os.path.join(ROOT, '.ua', 'replica', 'src', 'fy_main.mp4')
FR = os.path.join(ROOT, '.ua', 'replica', 'frames', 'A_main')
DATA = os.path.join(ROOT, '.ua', 'replica', 'data')
W, H, FPS, NF = 1922, 880, 60.0, 14029


def iter_frames(start_f=0, n=None, step=1, crop=None, scale=None, src=SRC):
    """逐帧产出 (frame_index, rgb ndarray)。crop=(x,y,w,h) 原始像素；scale=(w,h) 输出尺寸。
    start_f 用精确 seek（-ss 放在 -i 前，ffmpeg 对 h264 会解码到准确帧）。"""
    vf = []
    if step > 1:
        vf.append("select='not(mod(n\\,%d))'" % step)
    w, h = W, H
    if crop:
        x, y, w, h = crop
        vf.append('crop=%d:%d:%d:%d' % (w, h, x, y))
    if scale:
        w, h = scale
        vf.append('scale=%d:%d:flags=area' % (w, h))
    cmd = ['ffmpeg', '-v', 'error']
    if start_f > 0:
        cmd += ['-ss', '%.6f' % (start_f / FPS + 0.0005)]
    cmd += ['-i', src]
    if n is not None:
        cmd += ['-frames:v', str(n)]
    if vf:
        cmd += ['-vf', ','.join(vf)]
    cmd += ['-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 8)
    sz = w * h * 3
    i = 0
    while True:
        buf = p.stdout.read(sz)
        if len(buf) < sz:
            break
        yield start_f + i * step, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        i += 1
    p.stdout.close()
    p.wait()


def get_frame(f, crop=None, scale=None):
    for _, a in iter_frames(f, 1, 1, crop, scale):
        return a.copy()
    return None


def font(sz=18):
    for name in ('arial.ttf', 'msyh.ttc', 'consola.ttf'):
        try:
            return ImageFont.truetype(name, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def tc(f):
    t = f / FPS
    return '%02d:%05.2f' % (int(t // 60), t % 60)


def sheet(frames, cols, cellw, out, crop=None, label=True, zoom=None, q=88):
    """frames: 帧号列表。crop=(x,y,w,h)。输出 jpg。"""
    cw_src, ch_src = (crop[2], crop[3]) if crop else (W, H)
    cellh = int(round(cellw * ch_src / cw_src))
    rows = (len(frames) + cols - 1) // cols
    im = Image.new('RGB', (cols * cellw, rows * cellh))
    d = ImageDraw.Draw(im)
    ft = font(max(12, cellw // 26))
    for k, f in enumerate(frames):
        a = get_frame(f, crop, (cellw, cellh))
        if a is None:
            continue
        x, y = (k % cols) * cellw, (k // cols) * cellh
        im.paste(Image.fromarray(a), (x, y))
        if label:
            s = '%s f%d' % (tc(f), f)
            d.rectangle([x, y, x + ft.getlength(s) + 6, y + ft.size + 4], fill=(0, 0, 0))
            d.text((x + 3, y + 1), s, fill=(255, 255, 0), font=ft)
    im.save(out, quality=q)
    return out
