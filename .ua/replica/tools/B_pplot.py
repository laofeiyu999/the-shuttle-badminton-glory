import sys; sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *; from B_plot import Plot; import pickle, numpy as np, json
from PIL import Image
def plot(a, b, name, th=0.3):
    C = pickle.load(open(CACHE + '/cands.pkl', 'rb')); P = pickle.load(open(CACHE + '/cand_p.pkl', 'rb'))
    on = json.load(open(CACHE + '/flash_on.json'))
    Wd = 2000
    P1 = Plot(Wd, 400, (a, b), (0, 1920)); P2 = Plot(Wd, 400, (a, b), (-1264, 0))
    st = 20 if b - a <= 1000 else 50
    P1.grid(range(a, b, st), range(0, 1920, 240)); P2.grid(range(a, b, st), range(-1200, 0, 100))
    for o in on:
        if a <= o[0] < b: P1.line([o[0]] * 2, [0, 1920], (0, 150, 0)); P2.line([o[0]] * 2, [-1264, 0], (0, 150, 0))
    for k in range(a, min(b, NF)):
        w = C[k]; p = P[k]
        for j in np.nonzero(p >= th)[0]:
            c = (220, 0, 0) if p[j] >= 0.6 else (0, 0, 220)
            P1.pts([k], [w[j, 0]], c); P2.pts([k], [-w[j, 1]], c)
    im = Image.new('RGB', (Wd, 804), (0, 0, 0)); im.paste(P1.im, (0, 0)); im.paste(P2.im, (0, 404)); im.save(FR + '/' + name, quality=88)
if __name__ == '__main__':
    a, b = int(sys.argv[1]), int(sys.argv[2]); plot(a, b, f'p_{a}.jpg')
