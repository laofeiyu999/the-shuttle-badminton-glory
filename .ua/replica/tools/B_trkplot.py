import sys; sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *; from B_plot import Plot; import pickle, numpy as np
from PIL import Image
TR = pickle.load(open(CACHE + '/tracklets.pkl', 'rb'))
def plot(a, b, name, extra=None):
    P1 = Plot(1800, 420, (a, b), (0, 1920)); P2 = Plot(1800, 420, (a, b), (-1264, 0))
    st = 20 if b - a <= 1000 else 50
    P1.grid(range(a, b, st), range(0, 1920, 240)); P2.grid(range(a, b, st), range(-1200, 0, 100))
    for t in TR:
        if t['f'][-1] < a or t['f'][0] > b: continue
        c = (220, 0, 0) if t['trail'] > 0.4 else ((0, 0, 220) if t['rough'] < 0.3 else (0, 170, 0))
        P1.pts(t['f'], t['c'][:, 0], c); P2.pts(t['f'], -t['c'][:, 1], c)
    if extra is not None: extra(P1, P2)
    im = Image.new('RGB', (1800, 844), (0, 0, 0)); im.paste(P1.im, (0, 0)); im.paste(P2.im, (0, 424)); im.save(FR + '/' + name, quality=88)
if __name__ == '__main__':
    a, b = int(sys.argv[1]), int(sys.argv[2]); plot(a, b, f'trk_{a}.jpg')
