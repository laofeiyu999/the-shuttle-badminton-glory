import pickle, glob, numpy as np, sys
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
def load():
    R = None
    for f in sorted(glob.glob(CACHE + '/p1_*.pkl')):
        d = pickle.load(open(f, 'rb'))
        if R is None: R = {k: list(v) for k, v in d.items()}
        else:
            for k, v in d.items(): R[k].extend(v)
    o = np.argsort(R['frame'])
    for k in R: R[k] = [R[k][i] for i in o]
    return R
