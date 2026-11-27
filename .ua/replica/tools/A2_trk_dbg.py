import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from A2_trk import *
from A_common import get_frame
for a in sys.argv[1:]:
    f = int(a); rgb = get_frame(f); t0 = time.time(); L, dm = detect(rgb); t1 = time.time()
    p, q = fit_bank(L, dm, [np.array(b) for b in BANK]); t2 = time.time()
    print('f%d lines %d det %.2fs fit %.2fs p %s n %d (%d/%d) rms %.2f ok %s' % (f, len(L), t1 - t0, t2 - t1, np.round(p, 2), q['n'], q['nH'], q['nO'], q['rms'], q['ok']), 'inl %.2f nvis %d sig_fov %.2f' % (q['inl'], q['nvis'], q['sig'][5]))
    print('   ', q.get('a'))
