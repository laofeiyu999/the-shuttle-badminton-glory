# -*- coding: utf-8 -*-
"""B2 公共工具：ffmpeg 管道读帧、拼图。视频 fy_side.mp4 1920x1440 50fps 11719 帧"""
import subprocess, numpy as np, os
from PIL import Image, ImageDraw, ImageFont
ROOT = r"D:\GameDev\the-shuttle-badminton-glory"
VID = os.path.join(ROOT, ".ua", "replica", "src", "fy_side.mp4")
FR = os.path.join(ROOT, ".ua", "replica", "frames", "B2_fx")
DATA = os.path.join(ROOT, ".ua", "replica", "data")
FPS = 50.0
W, H = 1920, 1440
NF = 11719

def stream(start_f=0, n=None, vf=None, w=W, h=H, step=1):
    """逐帧 yield (帧号, HxWx3 uint8)。vf 为 ffmpeg 滤镜串（需自行保证输出 w×h）。step>1 用 select 取每 step 帧。"""
    cmd = ["ffmpeg", "-v", "error"]
    if start_f > 0:
        cmd += ["-ss", "%.4f" % (start_f / FPS)]
    cmd += ["-i", VID]
    filt = []
    if step > 1:
        filt.append(r"select='not(mod(n\,%d))'" % step)
    if vf:
        filt.append(vf)
    if filt:
        cmd += ["-vf", ",".join(filt)]
    cmd += ["-fps_mode", "passthrough"]
    if n is not None:
        cmd += ["-frames:v", str(n)]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=w * h * 3 * 4)
    i = 0
    sz = w * h * 3
    while True:
        buf = p.stdout.read(sz)
        if len(buf) < sz:
            break
        yield start_f + i * step, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        i += 1
    p.stdout.close(); p.wait()

def grab(f0, n=1, crop=None, scale=None, step=1):
    """取 n 帧（从帧 f0 起，每 step 帧一张）。crop=(x,y,w,h)，scale=(w,h)。返回 list[(f, arr)]"""
    filt = []; w, h = W, H
    if crop:
        x, y, cw, ch = crop
        filt.append("crop=%d:%d:%d:%d" % (cw, ch, x, y)); w, h = cw, ch
    if scale:
        filt.append("scale=%d:%d:flags=lanczos" % scale); w, h = scale
    out = []
    if step == 1:
        for f, a in stream(f0, n, ",".join(filt) if filt else None, w, h):
            out.append((f, a.copy()))
    else:
        # 从 f0 起 select 每 step 帧
        cmd = ["ffmpeg", "-v", "error", "-ss", "%.4f" % (f0 / FPS), "-i", VID,
               "-vf", ",".join([r"select='not(mod(n\,%d))'" % step] + filt), "-fps_mode", "passthrough",
               "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        raw = subprocess.run(cmd, stdout=subprocess.PIPE).stdout
        sz = w * h * 3
        for i in range(len(raw) // sz):
            out.append((f0 + i * step, np.frombuffer(raw[i*sz:(i+1)*sz], np.uint8).reshape(h, w, 3).copy()))
    return out

def font(sz=16):
    for p in [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def sheet(frames, cols, path, label=True, fsz=16, quality=88, labels=None):
    """frames: list[(f, arr)] 拼成联系表。标签=帧号+时间"""
    h, w = frames[0][1].shape[:2]
    rows = (len(frames) + cols - 1) // cols
    im = Image.new("RGB", (cols * w, rows * h))
    d = ImageDraw.Draw(im); ft = font(fsz)
    for i, (f, a) in enumerate(frames):
        x, y = (i % cols) * w, (i // cols) * h
        im.paste(Image.fromarray(a), (x, y))
        if label:
            t = labels[i] if labels else "f%d %.2fs" % (f, f / FPS)
            d.rectangle([x, y, x + ft.getlength(t) + 6, y + fsz + 4], fill=(0, 0, 0))
            d.text((x + 3, y + 1), t, fill=(255, 255, 0), font=ft)
    im.save(path, quality=quality)
    return path
