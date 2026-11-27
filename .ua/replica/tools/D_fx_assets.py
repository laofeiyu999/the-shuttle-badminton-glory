# -*- coding: utf-8 -*-
"""清点 fyqc-client 下疑似战斗特效贴图 (按文件名前缀归类), 输出 .ua/replica/data/D_fx_texture_inventory.csv (文件名/尺寸/大小, 不拷贝图像)。"""
import os, re, csv, collections, sys
from PIL import Image
ROOT = 'References/fyqc/fyqc-client'
CATS = [('trail', r'^trail'), ('smoke', r'^smoke'), ('glow', r'^glow'), ('ring', r'^ring'), ('star', r'^star'), ('fire', r'^fire'), ('ray', r'^ray'), ('noise', r'^noise'),
        ('mask', r'^mask'), ('par', r'^par(_|\d)'), ('hit', r'^hit'), ('tech', r'^tech'), ('block', r'^block'), ('poly', r'^poly'), ('sword', r'^sword'), ('wenli', r'^wenli'),
        ('light', r'^(light|lightning|flare|lensflare|spark|shine|beam|line|wave|shock|dust|water|ice|wind|flash|circle|dot|point|crack|stone|leaf|flower|feather|bubble|arrow|lizi|guang|quan|yan|xing|tuowei|daoguang|shan)'),
        ('Efx', r'(?i)^(efx|fx_|vfx|eff)'), ('badminton', r'(?i)badminton|shuttle|yumao|^ball'), ('TW_DM', r'^(TW_|DM_)')]
rows = []; cnt = collections.Counter(); ex = collections.defaultdict(list); sizes = collections.defaultdict(collections.Counter)
seen = {}
for sub in ('textures/APK', 'textures/DEVICE'):
    for fn in sorted(os.listdir(os.path.join(ROOT, sub))):
        cat = None
        for c, pat in CATS:
            if re.search(pat, fn): cat = c; break
        if not cat: continue
        p = os.path.join(ROOT, sub, fn)
        try:
            with Image.open(p) as im: w, h = im.size; mode = im.mode
        except Exception as e:
            w = h = 0; mode = 'err'
        rows.append([cat, sub + '/' + fn, w, h, mode, os.path.getsize(p)])
        cnt[cat] += 1; sizes[cat]['%dx%d' % (w, h)] += 1
        if len(ex[cat]) < 14: ex[cat].append(fn)
w = csv.writer(open('.ua/replica/data/D_fx_texture_inventory.csv', 'w', newline='', encoding='utf-8-sig'))
w.writerow(['category', 'path_under_fyqc-client', 'width', 'height', 'mode', 'bytes']); w.writerows(rows)
for c in cnt:
    print(c, cnt[c], dict(sizes[c].most_common(6))); print('   ', ex[c])
