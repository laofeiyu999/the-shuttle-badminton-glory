import sys, time, numpy as np
from PIL import Image
from A_common import get_frame, FR
import A_cam as C
fs=[int(a) for a in sys.argv[1:]]
for f in fs:
    full=get_frame(f)
    half=np.asarray(Image.fromarray(full).resize((C.WS,C.HS),Image.BOX))
    m,blue=C.line_mask(half)
    dm=C.dist_map(m); mp=C.mask_points(m)
    t=time.time()
    r=C.hough_init(m,dm,mp,verbose=True)
    if r is None: print(f,'init failed'); continue
    p,s=r
    q=C.fit_quality(p,dm,mp)
    print(f,'p=',np.round(p,3),'cost %.3f'%s,q,'%.1fs'%(time.time()-t))
    net=[((-3.05,1.55,0),(3.05,1.55,0),(255,255,0)),((-3.05,0,0),(-3.05,1.55,0),(255,255,0)),((3.05,0,0),(3.05,1.55,0),(255,255,0))]
    im=C.draw_overlay(full,p,extra=net)
    im.save(FR+'/camtest_f%05d.jpg'%f,quality=90)
