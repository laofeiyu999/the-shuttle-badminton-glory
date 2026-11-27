# 第一遍全帧扫描（并行分段）：每帧提取候选团块，供离线追踪用
#  white: 白色小团（球本体候选）  sat: 高饱和亮色团（拖尾/落点圈/脚下圈）  big: 前景大团（人物）
#  dark: 变暗团（影子）  flash: 极亮像素统计（击球闪光）  hud: 能量条行带、比分区缩略
# 用法: python B_05_pass1.py <seg_index> <n_segs>   或不带参数=调度全部
import numpy as np, sys, os, subprocess, time, pickle
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from scipy import ndimage as ndi
YMAX = 1264
def blobs(mask, f, amin, amax, topn, extra=None):
    lab, n = ndi.label(mask)
    if n == 0: return np.zeros((0, 10), np.float32), lab
    idx = np.arange(1, n + 1)
    area = np.bincount(lab.ravel())[1:]
    keep = np.nonzero((area >= amin) & (area <= amax))[0]
    if len(keep) > topn: keep = keep[np.argsort(-area[keep])[:topn]]
    sl = ndi.find_objects(lab)
    out = []
    for k in keep:
        s = sl[k]; m = lab[s] == k + 1
        yy, xx = np.nonzero(m)
        col = f[s][m].mean(0)
        out.append([xx.mean() + s[1].start, yy.mean() + s[0].start, area[k], s[1].start, s[1].stop, s[0].start, s[0].stop, col[0], col[1], col[2]])
    return np.array(out, np.float32).reshape(-1, 10), lab
def run(seg, nseg):
    bg = np.load(CACHE + '/bg_all.npy')[:YMAX]
    bgc = [np.ascontiguousarray(bg[..., c]) for c in range(3)]
    bgsum = bgc[0].astype(np.int16) + bgc[1] + bgc[2]
    a = seg * NF // nseg; b = (seg + 1) * NF // nseg
    R = dict(fgm=[], white=[], sat=[], big=[], dark=[], flash=[], hudA=[], hudB=[], score=[], frame=[])
    t0 = time.time()
    for i, f in frames(a, b - a):
        g = f[:YMAX]
        gc = [np.ascontiguousarray(g[..., c]) for c in range(3)]
        dc = [np.maximum(gc[c], bgc[c]) - np.minimum(gc[c], bgc[c]) for c in range(3)]
        d = np.maximum(np.maximum(dc[0], dc[1]), dc[2])
        mn = np.minimum(np.minimum(gc[0], gc[1]), gc[2]); mx = np.maximum(np.maximum(gc[0], gc[1]), gc[2])
        wm = (mn > 165) & (d > 30)
        sm = (mx > 185) & ((mx - mn) > 90) & (d > 45)
        wb, _ = blobs(wm, g, 12, 2500, 60)
        sb, _ = blobs(sm, g, 25, 60000, 60)
        # 每个白团附近的饱和像素统计（拖尾）：外扩 14 px
        ex = np.zeros((len(wb), 6), np.float32)
        for k, w in enumerate(wb):
            x0, x1, y0, y1 = int(w[3]) - 14, int(w[4]) + 14, int(w[5]) - 14, int(w[6]) + 14
            x0, y0 = max(x0, 0), max(y0, 0)
            m = sm[y0:y1, x0:x1]
            c = m.sum()
            if c:
                yy, xx = np.nonzero(m); col = g[y0:y1, x0:x1][m].mean(0)
                ex[k] = [c, xx.mean() + x0, yy.mean() + y0, col[0], col[1], col[2]]
        wb = np.hstack([wb, ex])
        fg = (d > 40)[: YMAX // 4 * 4].reshape(YMAX // 4, 4, W // 4, 4).any(axis=(1, 3))
        fg[:150] = False
        bb, _ = blobs(fg, g[::4, ::4], 150, 10 ** 7, 6)
        # 影子（全分辨率）：整体变暗的团块。球影是扁椭圆，位于球的正下方地面
        gsum = gc[0].astype(np.int16) + gc[1] + gc[2]
        dkm = (bgsum - gsum) > 45
        dkm[:770] = False
        lab, n = ndi.label(dkm)
        db = np.zeros((0, 9), np.float32)
        if n:
            area = np.bincount(lab.ravel())[1:]
            keep = np.nonzero((area >= 40) & (area <= 6000))[0]
            if len(keep) > 40: keep = keep[np.argsort(-area[keep])[:40]]
            sl = ndi.find_objects(lab); rows = []
            for k in keep:
                sk = sl[k]; m = lab[sk] == k + 1
                yy, xx = np.nonzero(m)
                rt = gsum[sk][m].sum() / max(1.0, float(bgsum[sk][m].sum()))
                rows.append([xx.mean() + sk[1].start, yy.mean() + sk[0].start, area[k], sk[1].start, sk[1].stop, sk[0].start, sk[0].stop, rt, xx.std() / max(yy.std(), 0.3)])
            db = np.array(rows, np.float32).reshape(-1, 9)
        fm = (mn > 240) & (d > 50)
        c = fm.sum()
        if c > 0:
            yy, xx = np.nonzero(fm); fl = [c, xx.mean(), yy.mean(), xx.std(), yy.std()]
        else: fl = [0, 0, 0, 0, 0]
        R['frame'].append(i); R['fgm'].append(np.packbits(fg)); R['white'].append(wb); R['sat'].append(sb); R['big'].append(bb); R['dark'].append(db); R['flash'].append(fl)
        R['hudA'].append(f[250:266].mean(0).astype(np.uint8)); R['hudB'].append(f[200:246].max(0))
        R['score'].append(f[196:284:2, 800:1120:2].mean(2).astype(np.uint8))
        if (i - a) % 300 == 0: print(seg, i, round(time.time() - t0, 1), flush=True)
    pickle.dump(R, open(CACHE + f'/p1_{seg:02d}.pkl', 'wb'))
    print('seg', seg, 'done', len(R['frame']), 'frames', round(time.time() - t0, 1), flush=True)
if __name__ == '__main__':
    if len(sys.argv) == 3:
        run(int(sys.argv[1]), int(sys.argv[2]))
    else:
        NS = 10
        ps = [subprocess.Popen([sys.executable, __file__, str(s), str(NS)]) for s in range(NS)]
        for p in ps: p.wait()
        print('all done')
