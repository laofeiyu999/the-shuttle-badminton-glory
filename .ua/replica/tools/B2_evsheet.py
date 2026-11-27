# -*- coding: utf-8 -*-
"""闪光事件总览：每个事件取 f_start+1 帧，裁 y 540-1240 全宽，缩到 560x204，6 列。"""
import sys, os, csv
sys.path.insert(0, os.path.dirname(__file__))
from B2_common import *
ev = list(csv.DictReader(open(os.path.join(DATA, 'B2_flash_events.csv'))))
fs = [int(e['f_start']) + 1 for e in ev]
fr = []
for f in fs:
    fr += grab(f, 1, crop=(0, 540, 1920, 700), scale=(560, 204))
per = 60
for i in range(0, len(fr), per):
    sheet(fr[i:i + per], 5, os.path.join(FR, 'sheets', 'ev_%02d.jpg' % (i // per)), fsz=13, quality=85)
print(len(fr))
