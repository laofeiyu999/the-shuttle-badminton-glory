# 切拍 + 三维重建 + 每拍指标 -> data/B_shots.csv、data/B_ball_track.csv、data/B_shot_samples.csv
import sys, numpy as np, json, csv, pickle
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from B_geom import *
from scipy.optimize import least_squares
from collections import Counter
ball = np.load(CACHE + '/ball0.npy'); still = np.load(CACHE + '/still.npy'); fl = np.load(CACHE + '/flash.npy')
on = json.load(open(CACHE + '/flash_on.json')); SH = np.load(CACHE + '/shadow_cand.npy')
BAD = [(3055, 3143), (7111, 7147), (7165, 7191), (7992, 8081), (8854, 8918)]
ok = np.isfinite(ball[:, 0]) & ~still
for a, b in BAD: ok[a:b + 1] = False
for k in range(NF):   # 横幅误检：y≈480 的水平线
    if ok[k] and abs(ball[k, 1] - 480) < 8:
        a = ball[max(0, k - 6):k + 7, 1]; a = a[np.isfinite(a)]
        if len(a) >= 6 and np.ptp(a) < 4: ok[k] = False
def rd(name):
    for enc in ('utf-8-sig', 'gbk'):
        try: return list(csv.DictReader(open(DATA + '/' + name, encoding=enc)))
        except Exception: pass
    return []
PT = rd('B2_player_track.csv'); JP = rd('B2_jumps.csv'); AH = rd('A_hits.csv'); AE = rd('A_energy.csv')
def fnum(v):
    try: return float(v)
    except Exception: return np.nan
ptk = np.array([[fnum(r[c]) for c in ('L_x', 'L_z', 'R_x', 'R_z')] for r in PT]) if PT else None
aen = np.array([fnum(r['fill_0_1']) for r in AE]) if AE else None
def t_main(ts): return ts + 0.22 if ts < 150 else ts - 0.05
# ---------- 击球检测 ----------
hits = []
for k, s, fx, fy in on:
    k = int(k)
    if s < 800: continue
    f = np.arange(k, min(NF, k + 16)); f = f[ok[f]]
    if len(f) < 5: continue
    f = f[:8]; vx = np.polyfit(f, ball[f, 0], 1)[0]
    if abs(vx) < 1.0 and np.ptp(ball[f, 1]) < 12: continue
    hits.append([k, s, 'L' if vx > 0 else 'R', vx])
h2 = []
for h in hits:
    if h2 and h[0] - h2[-1][0] < 12:
        if h[1] > h2[-1][1]: h2[-1] = h
    else: h2.append(h)
hits = h2
print('flash hits', len(hits))
def track_end(k0, lim):
    last = k0; k = k0 + 1
    while k < lim:
        if ok[k]: last = k
        elif k - last > 14: break
        k += 1
    return last
ins = []   # 无闪光的折返
for i, h in enumerate(hits):
    lim = hits[i + 1][0] if i + 1 < len(hits) else NF
    e = track_end(h[0], min(lim, h[0] + 220))
    f = np.arange(h[0] + 1, e + 1); f = f[ok[f]]
    if len(f) < 16: continue
    x = ball[f, 0]; sg = 1 if h[2] == 'L' else -1
    j = int(np.argmax(sg * x))
    if 6 <= j < len(f) - 8 and sg * (x[j] - x[-1]) > 150:
        ins.append([int(f[j]), 0.0, 'R' if h[2] == 'L' else 'L', 0.0])
print('inserted reversal hits', len(ins), [i[0] for i in ins])
hits = sorted(hits + ins, key=lambda h: h[0])
shots = []
for i, h in enumerate(hits):
    nxt = hits[i + 1][0] if i + 1 < len(hits) else NF
    e = track_end(h[0], min(nxt, h[0] + 220))
    cont = (i + 1 < len(hits)) and (nxt - e <= 14) and hits[i + 1][2] != h[2]
    shots.append(dict(hit=h[0], side=h[2], flash=h[1], end=(nxt if cont else e), returned=cont))
# 剔除无有效轨迹的假击球（横幅、特写等），回合按击球间隔 > 2.8 s 切分
def ntrk(s):
    f = np.arange(s['hit'], s['end'] + 1); f = f[ok[f]]
    return len(f), (np.hypot(np.ptp(ball[f, 0]), np.ptp(ball[f, 1])) if len(f) else 0)
shots = [s for s in shots if ntrk(s)[0] >= 8 and ntrk(s)[1] > 60]
for i, s in enumerate(shots):
    if i + 1 < len(shots):
        nx = shots[i + 1]
        s['returned'] = (nx['hit'] - s['hit'] <= 140) and nx['side'] != s['side']
        if s['returned'] and nx['hit'] - s['end'] <= 14: s['end'] = nx['hit']
    else: s['returned'] = False
r = 0
for i, s in enumerate(shots):
    if i == 0 or shots[i]['hit'] - shots[i - 1]['hit'] > 140: r += 1; n = 0
    n += 1; s['rally'] = r; s['idx'] = n
# ---------- 三维重建 ----------
def plane_fit(s):
    m = (SH[:, 0] > s['hit']) & (SH[:, 0] < s['end']) & (np.abs(SH[:, 8]) < 30)
    q = SH[m]
    if len(q) >= 6:
        g = ground(q[:, 3:5]); X, Y = g[:, 0], g[:, 1]
        keep = np.abs(Y) < 3.6; A = [0.0, 0.0]; res = Y * 0
        for _ in range(3):
            if keep.sum() < 5: break
            A = np.polyfit(X[keep], Y[keep], 1); res = Y - np.polyval(A, X)
            keep = (np.abs(res) < 0.25) & (np.abs(Y) < 3.6)
        if keep.sum() >= 5 and np.ptp(X[keep]) > 1.5 and abs(A[0]) < 0.6:
            return float(A[1]), float(A[0]), int(keep.sum()), float(np.std(res[keep]))
        if keep.sum() >= 4: return float(np.median(Y[keep])), 0.0, int(keep.sum()), float(np.std(Y[keep]))
    return None
def sim(v0s, v0z, g, k, T, dt=0.004):
    n = int(T / dt) + 2; out = np.zeros((n, 2)); s = z = 0.0; vs, vz = v0s, v0z
    for i in range(n):
        out[i] = (s, z); v = np.hypot(vs, vz)
        vs += -k * v * vs * dt; vz += (-g - k * v * vz) * dt; s += vs * dt; z += vz * dt
    return out
def fit_model(t, s, z, kfix=None):
    T = t[-1]
    def res(p):
        k = kfix if kfix is not None else p[3]
        o = sim(p[0], p[1], p[2], k, T); ti = np.arange(len(o)) * 0.004
        return np.r_[np.interp(t, ti, o[:, 0]) - s, np.interp(t, ti, o[:, 1]) - z]
    p0 = [max(s[-1] / max(T, 0.1) * 1.8, 1), 3.0, 8.0] + ([] if kfix is not None else [0.2])
    lo = [0, -60, 0] + ([] if kfix is not None else [0]); hi = [150, 60, 60] + ([] if kfix is not None else [3])
    try:
        r = least_squares(res, p0, bounds=(lo, hi), max_nfev=50)
        return list(r.x), float(np.sqrt(np.mean(r.fun ** 2)))
    except Exception: return None, np.nan
samples = []; track3 = np.full((NF, 4), np.nan)
for si, s in enumerate(shots):
    f = np.arange(s['hit'], s['end'] + 1); f = f[ok[f]]
    s['n'] = len(f); s['cover'] = len(f) / max(s['end'] - s['hit'], 1)
    pf = plane_fit(s)
    if pf is None: s['plane'] = 'none'; a, b, npl, sdp = 0.0, 0.0, 0, np.nan
    else: a, b, npl, sdp = pf; s['plane'] = 'shadow'
    s['a'], s['b'], s['npl'], s['sdp'] = a, b, npl, sdp
for si, s in enumerate(shots):   # 无影子的拍借用相邻拍的平面
    if s['plane'] == 'none':
        cand = [shots[j] for j in (si - 1, si + 1) if 0 <= j < len(shots) and shots[j]['rally'] == s['rally'] and shots[j]['plane'] == 'shadow']
        if cand: s['a'], s['b'] = float(np.mean([c['a'] for c in cand])), float(np.mean([c['b'] for c in cand])); s['plane'] = 'neighbor'
def clean(f):
    # 去掉首尾与后续轨迹不连续的点（击球瞬间误选到人物/闪光上的候选）
    for rev in (False, True):
        for _ in range(3):
            if len(f) < 9: break
            g = f[::-1] if rev else f
            q = g[1:7]; px = np.polyfit(q, ball[q, 0], 2); py = np.polyfit(q, ball[q, 1], 2)
            e = np.hypot(np.polyval(px, g[0]) - ball[g[0], 0], np.polyval(py, g[0]) - ball[g[0], 1])
            step = np.median(np.hypot(np.diff(ball[q, 0]), np.diff(ball[q, 1])))
            if e > max(25, 1.5 * step * abs(g[1] - g[0]) + 10): f = f[:-1] if rev else f[1:]
            else: break
    return f
for si, s in enumerate(shots):
    f = np.arange(s['hit'], s['end'] + (0 if s['returned'] else 1)); f = clean(f[ok[f]])
    if len(f) < 4: s['valid'] = False; continue
    s['valid'] = True
    a, b = s['a'], s['b']
    d = ray(ball[f, :2]); t = (a + b * CAM[0] - CAM[1]) / (d[:, 1] - b * d[:, 0]); Xw = CAM + d * t[:, None]
    X, Y, Z = Xw[:, 0], Xw[:, 1], Xw[:, 2]
    sg = 1 if s['side'] == 'L' else -1
    S = (X - X[0]) * np.sqrt(1 + b * b) * sg
    tt = (f - s['hit']) / FPS
    track3[f] = np.c_[X, Y, Z, np.full(len(f), si + 1)]
    for q in range(len(f)): samples.append([si + 1, int(f[q]), round(tt[q], 3), round(S[q], 3), round(Z[q], 3), round(X[q], 3), round(Y[q], 3)])
    if f[0] - s['hit'] <= 2 or len(f) < 5: hx, hy, hz = X[0], Y[0], Z[0]
    else:
        m = slice(0, 4); hx = np.polyval(np.polyfit(tt[m], X[m], 1), 0); hz = np.polyval(np.polyfit(tt[m], Z[m], 1), 0); hy = a + b * hx
    s.update(hx=float(hx), hy=float(hy), hz=float(hz), late=int(f[0] - s['hit']))
    def vel(i0, i1):
        dt = tt[i1] - tt[i0]
        if dt <= 0: return np.nan, np.nan
        ds = S[i1] - S[i0]; dz = Z[i1] - Z[i0]
        return float(np.hypot(ds, dz) / dt), float(np.degrees(np.arctan2(dz, ds)))
    i1 = int(np.searchsorted(f, f[0] + 5)); i1 = min(max(i1, 2), len(f) - 1)
    s['v0'], s['ang0'] = vel(0, i1)
    i0 = int(np.searchsorted(f, f[-1] - 5)); i0 = max(min(i0, len(f) - 3), 0)
    s['v1'], s['ang1'] = vel(i0, len(f) - 1)
    s['T'] = (s['end'] - s['hit']) / FPS
    s['ex'], s['ey'], s['ez'] = float(X[-1]), float(Y[-1]), float(Z[-1])
    s['dist'] = float(abs(X[-1] - hx) * np.sqrt(1 + b * b)); s['vh'] = s['dist'] / max(s['T'], 1e-3)
    ia = int(np.argmax(Z)); s['apex'] = float(Z[ia]); s['apex_prog'] = float(abs(X[ia] - hx) / max(abs(X[-1] - hx), 1e-3)); s['apex_t'] = float(tt[ia])
    gap = np.diff(f); gi = np.nonzero(gap > 3)[0]
    s['trunc'] = bool(any(min(ball[f[g], 1], ball[f[g + 1], 1]) < 70 for g in gi)) or bool(ball[f, 1].min() < 8)
    s['net_h'] = s['net_t'] = np.nan
    cr = np.nonzero((X[:-1] * sg < 0) & (X[1:] * sg >= 0))[0]
    if len(cr):
        c = cr[0]; w = -X[c] / (X[c + 1] - X[c]); s['net_h'] = float(Z[c] + w * (Z[c + 1] - Z[c])); s['net_t'] = float(tt[c] + w * (tt[c + 1] - tt[c]))
    tg = np.arange(0, tt[-1] + 1e-6, 0.1)
    if len(tg) >= 2:
        Sg = np.interp(tg, tt, S); Zg = np.interp(tg, tt, Z); s['vser'] = (np.hypot(np.diff(Sg), np.diff(Zg)) / 0.1).round(1).tolist()
    else: s['vser'] = []
    m = ball[f, 3] > 30
    s['rgb'] = ball[f][m][:, 6:9].mean(0).round(0).tolist() if m.sum() >= 3 else [np.nan] * 3
    s['g'] = s['k'] = s['rms'] = s['g24'] = s['rms24'] = np.nan
    if len(f) >= 12 and not s['trunc'] and s['plane'] != 'none':
        t2 = tt - tt[0]; p, e = fit_model(t2, S - S[0], Z - Z[0])
        if p: s['g'], s['k'], s['rms'] = p[2], p[3], e
        p, e = fit_model(t2, S - S[0], Z - Z[0], kfix=0.24)
        if p: s['g24'], s['rms24'] = p[2], e
# ---------- 击球人位置、起跳、能量、按键 ----------
sgn = 1
if ptk is not None:
    aa, bb = [], []
    for s in shots:
        if s.get('valid') and s['plane'] == 'shadow' and s['hit'] < len(ptk):
            c = ptk[s['hit']]; aa.append(c[1] if s['side'] == 'L' else c[3]); bb.append(s['hy'])
    aa, bb = np.array(aa), np.array(bb); m = np.isfinite(aa) & np.isfinite(bb)
    cc = np.corrcoef(aa[m], bb[m])[0, 1]; sgn = 1 if cc >= 0 else -1; print('corr B2 z vs my Y', round(float(cc), 3), 'n', int(m.sum()), 'median |diff|', round(float(np.median(np.abs(sgn * aa[m] - bb[m]))), 2))
def col(c):
    r, g, b = c
    if not np.isfinite(r): return ''
    if r > 190 and g > 190 and b < 190: return '黄'
    if r > 190 and g < 150 and b < 150: return '红'
    if r > 140 and b > 170 and g < 150: return '紫'
    if b > 180 and r < 170: return '蓝'
    return '其他'
for s in shots:
    if not s.get('valid'): continue
    s['px'] = s['py'] = np.nan
    if ptk is not None and s['hit'] < len(ptk):
        c = ptk[s['hit']]; s['px'], s['py'] = (float(c[0]), float(sgn * c[1])) if s['side'] == 'L' else (float(c[2]), float(sgn * c[3]))
    s['jump'] = 0; s['jump_h'] = 0.0
    for j in JP:
        if j['side'] == s['side'] and int(j['f_start']) - 2 <= s['hit'] <= int(j['f_end']) + 2 and float(j['peak_h_m']) > 0.25:
            s['jump'] = 1; s['jump_h'] = float(j['peak_h_m'])
    s['color'] = col(s['rgb']); s['key'] = ''; s['energy'] = np.nan
    if s['side'] == 'L':
        tm = t_main(s['hit'] / FPS)
        if aen is not None:
            i = int(round((tm - 0.08) * 60))
            if 0 <= i < len(aen): s['energy'] = float(aen[i])
        ts = s['hit'] / FPS; best = None
        for r in AH:
            dt = float(r['t_s']) - ts          # 主视角按键时刻 − 侧视角击球时刻，实测峰值约 −0.3 s（前段）/ −0.6 s（后段）
            if -0.95 < dt < 0.05 and (best is None or abs(dt + 0.4) < abs(best[0] + 0.4)): best = (dt, r)
        if best: s['key'] = best[1]['key']; s['a_dt'] = best[0]; s['energyA'] = fnum(best[1]['energy_before'])
# ---------- 球种分类 ----------
def zone(x): x = abs(x); return '前' if x < 2.3 else ('中' if x < 4.5 else '后')
def hband(s): return '起跳' if s['jump'] else ('低手' if s['hz'] < 1.0 else ('腰' if s['hz'] < 1.8 else '头顶'))
for i, s in enumerate(shots):
    if not s.get('valid'): continue
    hzone, ezone = zone(s['hx']), zone(s['ex'])
    ap, hz = s['apex'], s['hz']; down = s['ang0'] < -6
    if s['idx'] == 1: t = '发球'
    elif hz > 1.9 and down and s['v0'] > 14 and hzone != '前': t = '杀'
    elif hz > 1.7 and down and hzone == '前': t = '扑'
    elif hzone != '前' and hz > 1.7 and ezone == '前' and ap < hz + 0.6: t = '吊'
    elif ap > 4.2 and ezone == '后': t = '高远' if hz >= 1.5 else '挑'
    elif ap > 3.2 and ezone != '前': t = '平高' if hz >= 1.5 else '挑'
    elif hzone == '前' and ezone == '前': t = '放网/搓'
    elif ezone == '前': t = '挡/放'
    elif hzone == '前': t = '推'
    else: t = '平抽'
    s['type'] = t; s['hzone'] = hzone; s['ezone'] = ezone; s['hband'] = hband(s)
for i, s in enumerate(shots):
    same = i > 0 and shots[i - 1]['rally'] == s['rally']
    s['prev'] = shots[i - 1].get('type', '') if same else ''
    s['gap'] = (s['hit'] - shots[i - 1]['hit']) / FPS if same else np.nan
pickle.dump(shots, open(CACHE + '/shots.pkl', 'wb'))
def F(v, n=2):
    if v is None: return ''
    if isinstance(v, (float, np.floating)): return '' if not np.isfinite(v) else f'{v:.{n}f}'
    return str(v)
hdr = ['shot', 'rally', 'idx', 'hit_frame', 't_s', 'side', 'type', 'key_A', 'trail', 'trail_r', 'trail_g', 'trail_b', 'hit_x', 'hit_y', 'hit_h', 'dist_net', 'hit_zone', 'hit_band', 'jump', 'jump_h', 'player_x', 'player_y',
       'end_kind', 'end_frame', 'end_x', 'end_y', 'end_h', 'T', 'dist', 'v0', 'ang0', 'net_h', 'net_t', 'apex', 'apex_prog', 'apex_t', 'trunc_top', 'v_end', 'ang_end', 'vh_mean', 'v_series_0.1s',
       'energy_L', 'energyA_before', 'prev_type', 'gap_prev', 'fit_g', 'fit_k', 'fit_rms', 'fit_g_k024', 'fit_rms_k024', 'plane', 'plane_a', 'plane_b', 'plane_n', 'n_pts', 'cover', 'first_pt_delay_f', 'flash']
with open(DATA + '/B_shots.csv', 'w', newline='', encoding='utf-8-sig') as fo:
    w = csv.writer(fo); w.writerow(hdr)
    for i, s in enumerate(shots):
        if not s.get('valid'):
            w.writerow([i + 1, s['rally'], s['idx'], s['hit'], F(s['hit'] / FPS), s['side'], '无轨迹']); continue
        w.writerow([i + 1, s['rally'], s['idx'], s['hit'], F(s['hit'] / FPS), s['side'], s['type'], s['key'], s['color'], *[F(float(c), 0) for c in s['rgb']], F(s['hx']), F(s['hy']), F(s['hz']), F(abs(s['hx'])), s['hzone'], s['hband'], s['jump'], F(s['jump_h']), F(s['px']), F(s['py']),
                    '对方击球' if s['returned'] else '落地/轨迹终止', s['end'], F(s['ex']), F(s['ey']), F(s['ez']), F(s['T']), F(s['dist']), F(s['v0'], 1), F(s['ang0'], 1), F(s['net_h']), F(s['net_t']), F(s['apex']), F(s['apex_prog']), F(s['apex_t']), int(s['trunc']), F(s['v1'], 1), F(s['ang1'], 1), F(s['vh'], 1),
                    ' '.join(str(v) for v in s['vser']), F(s['energy']), F(s.get('energyA', np.nan), 0), s['prev'], F(s['gap']), F(s['g'], 1), F(s['k'], 3), F(s['rms'], 3), F(s['g24'], 1), F(s['rms24'], 3), s['plane'], F(s['a']), F(s['b'], 3), s['npl'], s['n'], F(s['cover']), s['late'], F(float(s['flash']), 0)])
with open(DATA + '/B_shot_samples.csv', 'w', newline='', encoding='utf-8-sig') as fo:
    w = csv.writer(fo); w.writerow(['shot', 'frame', 't_since_hit', 's_m', 'h_m', 'X_m', 'Y_m']); w.writerows(samples)
with open(DATA + '/B_ball_track.csv', 'w', newline='', encoding='utf-8-sig') as fo:
    w = csv.writer(fo); w.writerow(['frame', 't_s', 'px_x', 'px_y', 'conf', 'still', 'used', 'shot', 'X_m', 'Y_m', 'Z_m'])
    for k in range(NF):
        if np.isfinite(ball[k, 0]):
            w.writerow([k, f'{k / FPS:.2f}', f'{ball[k, 0]:.1f}', f'{ball[k, 1]:.1f}', f'{ball[k, 13]:.2f}', int(still[k]), int(ok[k]), F(float(track3[k, 3]), 0), F(float(track3[k, 0])), F(float(track3[k, 1])), F(float(track3[k, 2]))])
        else: w.writerow([k, f'{k / FPS:.2f}', '', '', '0', '', 0, '', '', '', ''])
V = [s for s in shots if s.get('valid')]
print('shots', len(shots), 'valid', len(V), 'rallies', shots[-1]['rally'], Counter(s['type'] for s in V), Counter(s['plane'] for s in V))
print('cover>=0.8:', sum(s['cover'] >= 0.8 for s in V), ' 0.5-0.8:', sum(0.5 <= s['cover'] < 0.8 for s in V), ' <0.5:', sum(s['cover'] < 0.5 for s in V), 'trunc', sum(s['trunc'] for s in V))
same = [(shots[i]['hit'], shots[i]['side']) for i in range(1, len(shots)) if shots[i]['rally'] == shots[i - 1]['rally'] and shots[i]['side'] == shots[i - 1]['side']]
print('same-side consecutive', same); print('a_dt', np.round(np.percentile([x['a_dt'] for x in V if 'a_dt' in x], [5, 25, 50, 75, 95]), 2)); g = np.array([x['gap'] for x in shots if np.isfinite(x['gap'])]); print('gap pct', np.round(np.percentile(g, [5, 25, 50, 75, 95, 100]), 2))
print('rally sizes', sorted(Counter(s['rally'] for s in shots).items()))
print('rally starts', [s['hit'] for s in shots if s['idx'] == 1])
print('key vs color', Counter((s['key'], s['color']) for s in V if s['side'] == 'L'))
print('color all', Counter(s['color'] for s in V))
