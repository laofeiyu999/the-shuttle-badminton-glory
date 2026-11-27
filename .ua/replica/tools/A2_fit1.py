# -*- coding: utf-8 -*-
"""A2_fit1.py f cx cy cz pitch yaw fov : 单帧拟合测试，打印分段内点率，存叠加图 A2_ov_<f>.jpg"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from A2_cam import *
f = int(sys.argv[1]); p0 = [float(v) for v in sys.argv[2:8]]
rgb = get_frame(f); mk = line_mask(rgb)
print('mask frac %.4f' % mk.mean())
F = Fitter()
print('init', F.score(p0, mk)['inl'])
p, sc = F.fit(p0, mk)
print('fit p= %.3f %.3f %.3f pitch %.2f yaw %.2f fov %.2f' % tuple(p))
print('nvis %d inl %.3f rms_inl %.2f med %.2f' % (sc['nvis'], sc['inl'], sc['rms_inl'], sc['med']))
for k, v in sc['per'].items(): print('  %-12s nvis %4d inl %.2f' % (k, v[0], v[1]))
print(overlay(rgb, p, F, os.path.join(FR, 'A2_ov_%05d.jpg' % f)))
