import sys; sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *; from B_plot import Plot; import numpy as np
from PIL import Image
def plot(a, b, name, src='ball0.npy', marks=None):
    import json
    if marks is None: marks = [(o[0], '') for o in json.load(open(CACHE + '/flash_on.json'))]
    ball = np.load(CACHE + '/' + src); fl = np.load(CACHE + '/flash.npy')
    Wd = 2000
    P1 = Plot(Wd, 380, (a, b), (0, 1920)); P2 = Plot(Wd, 380, (a, b), (-1264, 0)); P3 = Plot(Wd, 90, (a, b), (0, 5))
    st = 20 if b - a <= 1000 else (50 if b - a <= 2500 else 100)
    P1.grid(range(a, b, st), range(0, 1920, 240)); P2.grid(range(a, b, st), range(-1200, 0, 100)); P3.grid(range(a, b, st), [], lab=False)
    k = np.arange(a, min(b, NF))
    still = np.load(CACHE + '/still.npy'); col = np.where(still[k], 2, np.where(ball[k, 12] > 0, 0, 1))
    for kk, cc in zip(k, col):
        if np.isfinite(ball[kk, 0]):
            c = [(220, 0, 0), (0, 0, 220), (150, 150, 150)][cc]
            P1.pts([kk], [ball[kk, 0]], c); P2.pts([kk], [-ball[kk, 1]], c)
    P3.line(k, np.log10(fl[k, 0] + 1), (200, 0, 150))
    if marks is not None:
        for m, lab in marks:
            if a <= m < b:
                P1.line([m, m], [0, 1920], (0, 150, 0)); P1.text(m, 1900, lab, (0, 110, 0))
    im = Image.new('RGB', (Wd, 858), (0, 0, 0)); im.paste(P1.im, (0, 0)); im.paste(P2.im, (0, 384)); im.paste(P3.im, (0, 768)); im.save(FR + '/' + name, quality=88)
if __name__ == '__main__':
    a, b = int(sys.argv[1]), int(sys.argv[2]); plot(a, b, f'ball_{a}.jpg', *(sys.argv[3:4]))
