# 抽查：随机 20 帧把追踪点画回原帧（裁剪 320x240）
import sys, numpy as np
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from PIL import Image, ImageDraw
ball = np.load(CACHE + '/ball0.npy'); still = np.load(CACHE + '/still.npy')
ok = np.nonzero(np.isfinite(ball[:, 0]) & ~still)[0]
rng = np.random.default_rng(7); pick = np.sort(rng.choice(ok, 20, replace=False))
sheet = Image.new('RGB', (5 * 320, 4 * 240))
for i, k in enumerate(pick):
    im = Image.fromarray(grab(int(k))); x, y = ball[k, :2]
    x0 = int(min(max(x - 160, 0), W - 320)); y0 = int(min(max(y - 120, 0), H - 240))
    c = im.crop((x0, y0, x0 + 320, y0 + 240)); d = ImageDraw.Draw(c)
    d.ellipse((x - x0 - 14, y - y0 - 14, x - x0 + 14, y - y0 + 14), outline=(255, 0, 0), width=2); d.text((4, 4), str(int(k)), fill=(255, 255, 0))
    sheet.paste(c, (i % 5 * 320, i // 5 * 240))
sheet.save(FR + '/check20.jpg', quality=85); print(pick.tolist())
