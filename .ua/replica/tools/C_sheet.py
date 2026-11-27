"""C_sheet.py  网球宝贝 tb1.mp4 抽帧联系表工具（任务 C）
用法:
  python C_sheet.py OUT.jpg --f0 900 --f1 960 [--step 1] [--crop x,y,w,h] [--cell 480] [--cols 6]
                    [--zoom 1.0] [--t0 秒 --t1 秒]
帧号以 ffprobe 解码顺序 0..3230 计，时间码用 data/C_tb1_pts.csv 的 pts。
crop 以显示方向(1446x1072)像素计。每格左上角标 帧号 / pts 秒。
"""
import argparse, subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'tb1.mp4')
PTS = os.path.join(ROOT, 'data', 'C_tb1_pts.csv')
W, H = 1446, 1072


def load_pts():
    return np.array([float(l.split(',')[0]) for l in open(PTS)])


def read_frames(f0, f1, pts=None, crop=None):
    """返回 [f0,f1] 闭区间的帧 (N,h,w,3) uint8，按解码顺序。"""
    if pts is None:
        pts = load_pts()
    f0 = max(0, f0); f1 = min(len(pts) - 1, f1)
    n = f1 - f0 + 1
    ss = max(0.0, pts[f0] - 0.0004) if f0 > 0 else 0.0
    vf = []
    w, h = W, H
    if crop:
        x, y, w, h = crop
        vf.append(f'crop={w}:{h}:{x}:{y}')
    cmd = ['ffmpeg', '-v', 'fatal', '-ss', f'{ss:.6f}', '-i', SRC, '-an', '-frames:v', str(n),
           '-fps_mode', 'passthrough']
    if vf:
        cmd += ['-vf', ','.join(vf)]
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    raw = subprocess.run(cmd, stdout=subprocess.PIPE).stdout
    arr = np.frombuffer(raw, np.uint8)
    got = arr.size // (w * h * 3)
    arr = arr[:got * w * h * 3].reshape(got, h, w, 3)
    return arr, f0


def font(sz):
    for p in ['C:/Windows/Fonts/consola.ttf', 'C:/Windows/Fonts/arial.ttf']:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def sheet(frames, idx, pts, out, cell=480, cols=6, zoom=None, label=True, q=88):
    n, h, w, _ = frames.shape
    if zoom:
        cw, ch = int(round(w * zoom)), int(round(h * zoom))
    else:
        cw = cell; ch = int(round(h * cell / w))
    rows = (n + cols - 1) // cols
    S = Image.new('RGB', (cols * cw, rows * ch), (0, 0, 0))
    fnt = font(max(11, cw // 22))
    for i in range(n):
        im = Image.fromarray(frames[i])
        im = im.resize((cw, ch), Image.LANCZOS if cw < w else Image.BICUBIC)
        if label:
            d = ImageDraw.Draw(im)
            txt = f'{idx[i]} {pts[idx[i]]:.3f}'
            d.rectangle([0, 0, fnt.getlength(txt) + 4, fnt.size + 3], fill=(0, 0, 0))
            d.text((2, 1), txt, fill=(255, 255, 0), font=fnt)
        S.paste(im, ((i % cols) * cw, (i // cols) * ch))
    S.save(out, quality=q)
    return S.size


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--f0', type=int); ap.add_argument('--f1', type=int)
    ap.add_argument('--t0', type=float); ap.add_argument('--t1', type=float)
    ap.add_argument('--step', type=int, default=1)
    ap.add_argument('--crop'); ap.add_argument('--cell', type=int, default=480)
    ap.add_argument('--cols', type=int, default=6); ap.add_argument('--zoom', type=float)
    a = ap.parse_args()
    pts = load_pts()
    if a.t0 is not None:
        a.f0 = int(np.searchsorted(pts, a.t0))
    if a.t1 is not None:
        a.f1 = int(np.searchsorted(pts, a.t1))
    crop = tuple(int(v) for v in a.crop.split(',')) if a.crop else None
    fr, f0 = read_frames(a.f0, a.f1, pts, crop)
    idx = np.arange(f0, f0 + len(fr))
    sel = np.arange(0, len(fr), a.step)
    sz = sheet(fr[sel], idx[sel], pts, a.out, a.cell, a.cols, a.zoom)
    print(a.out, 'frames', f0, f0 + len(fr) - 1, 'n', len(sel), 'size', sz)
