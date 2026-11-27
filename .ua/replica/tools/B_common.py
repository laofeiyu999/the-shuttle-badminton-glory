# B_common.py  公共函数：ffmpeg 管道读帧
import subprocess, numpy as np, os
ROOT = r'D:/GameDev/the-shuttle-badminton-glory'
SRC = ROOT + '/.ua/replica/src/fy_side.mp4'
DATA = ROOT + '/.ua/replica/data'
CACHE = DATA + '/B_cache'
FR = ROOT + '/.ua/replica/frames/B_side'
W, H, FPS, NF = 1920, 1440, 50.0, 11719

def frames(start=0, count=None, scale=None, crop=None, src=SRC, fps=FPS, w=W, h=H):
    """逐帧生成 (帧号, rgb ndarray)。start 为帧号，精确定位（-ss 放在 -i 前，ffmpeg 会精确解码到该时间）。"""
    vf = []
    ow, oh = w, h
    if crop:
        cw, ch, cx, cy = crop
        vf.append(f'crop={cw}:{ch}:{cx}:{cy}'); ow, oh = cw, ch
    if scale:
        vf.append(f'scale={scale[0]}:{scale[1]}:flags=area'); ow, oh = scale
    cmd = ['ffmpeg', '-v', 'error']
    if start > 0:
        cmd += ['-ss', f'{(start)/fps - 0.5/fps:.5f}']
    cmd += ['-i', src]
    if count is not None:
        cmd += ['-frames:v', str(count)]
    if vf:
        cmd += ['-vf', ','.join(vf)]
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=ow*oh*3*4)
    n = ow*oh*3
    i = start
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield i, np.frombuffer(buf, np.uint8).reshape(oh, ow, 3)
        i += 1
    p.stdout.close(); p.wait()

def grab(idx, **kw):
    for i, f in frames(idx, 1, **kw):
        return f.copy()
