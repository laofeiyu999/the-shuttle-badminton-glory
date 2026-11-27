import numpy as np, sys
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from scipy import ndimage as ndi
from PIL import Image
bg = np.load(CACHE + '/bg_all.npy').astype(np.int16)
for k in [int(a) for a in sys.argv[1:]]:
    f = grab(k).astype(np.int16)
    d = np.abs(f - bg).max(axis=2)
    mn = f.min(axis=2); mx = f.max(axis=2)
    print('frame', k, 'diff>40 px', (d > 40).sum())
    for name, m in [('white', (mn > 170) & (d > 35)), ('cyan', (f[..., 0] < 120) & (f[..., 1] > 190) & (f[..., 2] > 190) & (d > 35)), ('sat', (mx > 200) & (mx - mn > 110) & (d > 50))]:
        lab, n = ndi.label(m)
        if n == 0: print(' ', name, 'none'); continue
        idx = np.arange(1, n + 1)
        area = ndi.sum(m, lab, idx); com = ndi.center_of_mass(m, lab, idx); sl = ndi.find_objects(lab)
        order = np.argsort(-area)[:14]
        print(' ', name, n, 'blobs')
        for o in order:
            if area[o] < 12: continue
            s = sl[o]; col = f[lab == o + 1].mean(0)
            print(f'    area={int(area[o]):5d} c=({com[o][1]:.0f},{com[o][0]:.0f}) bbox x{s[1].start}-{s[1].stop} y{s[0].start}-{s[0].stop} rgb=({col[0]:.0f},{col[1]:.0f},{col[2]:.0f})')
