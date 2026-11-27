# -*- coding: utf-8 -*-
"""A2_kf_run.py [f]：关键帧人工对应表 + 求解。KF[f] = (assign, p0)。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from A2_kf import *
KF = {
 1200: (dict(base_far=13, net_top=15, short_far=26, short_near=31, sideD_L=33, sideS_L=35, centre_near=36, sideS_R=37, sideD_R=39), [1, 4, 9, 24, 0, 40]),
}
if __name__ == '__main__':
    fs = [int(a) for a in sys.argv[1:]] or sorted(KF)
    for f in fs:
        a, p0 = KF[f]
        solve(f, a, p0)
        solve(f, a, p0, free_dim=('z_short',))
        solve(f, a, p0, free_dim=('z_short', 'half_ws', 'net_h'))
