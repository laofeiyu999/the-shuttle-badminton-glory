# 几何工具：相机投影、像素→地面、给定地面点求高度
import numpy as np, json, sys
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
def rot(a):
    yaw, pitch, roll = a
    cy, sy = np.cos(yaw), np.sin(yaw); cp, sp = np.cos(pitch), np.sin(pitch); cr, sr = np.cos(roll), np.sin(roll)
    fwd = np.array([sy * cp, cy * cp, -sp]); right = np.array([cy, -sy, 0.0]); down = np.cross(fwd, right)
    R0 = np.stack([right, down, fwd]); Rr = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Rr @ R0
_c = json.load(open(CACHE + '/calib.json'))['free']
P = np.array(_c['p']); FOC = P[0]; CAM = P[1:4]; RM = rot(P[4:7]); CX, CY = 960.0, 720.0
def proj(X):
    X = np.atleast_2d(np.asarray(X, float)); Xc = (X - CAM) @ RM.T
    return np.stack([FOC * Xc[:, 0] / Xc[:, 2] + CX, FOC * Xc[:, 1] / Xc[:, 2] + CY], 1)
def ray(px):
    px = np.atleast_2d(np.asarray(px, float))
    d = np.stack([(px[:, 0] - CX) / FOC, (px[:, 1] - CY) / FOC, np.ones(len(px))], 1) @ RM
    return d
def ground(px, z=0.0):
    d = ray(px); t = (z - CAM[2]) / d[:, 2]
    return CAM + d * t[:, None]
def on_plane_x(px, X):
    # 像素射线与竖直平面 X=const 的交点
    d = ray(px); t = (X - CAM[0]) / d[:, 0]
    return CAM + d * t[:, None]
def on_plane_y(px, Y):
    d = ray(px); t = (Y - CAM[1]) / d[:, 1]
    return CAM + d * t[:, None]
def height_at(px, XY):
    # 已知地面投影 (X,Y)，求最贴近像素射线的高度 Z（最小二乘，主要由像素 y 决定）
    px = np.atleast_2d(np.asarray(px, float)); XY = np.atleast_2d(np.asarray(XY, float))
    d = ray(px)
    # 射线上到竖直线 (X,Y,·) 最近的点
    a = XY - CAM[:2]
    t = (a * d[:, :2]).sum(1) / (d[:, :2] ** 2).sum(1)
    return CAM[2] + t * d[:, 2]
