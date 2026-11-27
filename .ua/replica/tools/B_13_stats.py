# 由 shots.pkl 生成分组统计表（Markdown 片段）-> data/B_stats.md
import sys, numpy as np, pickle, csv
sys.path.insert(0, r'D:/GameDev/the-shuttle-badminton-glory/.ua/replica/tools')
from B_common import *
from collections import defaultdict, Counter
S = pickle.load(open(CACHE + '/shots.pkl', 'rb'))
SM = defaultdict(list)
for r in csv.DictReader(open(DATA + '/B_shot_samples.csv', encoding='utf-8-sig')):
    SM[int(r['shot'])].append((float(r['t_since_hit']), float(r['s_m']), float(r['h_m'])))
for i, s in enumerate(S):
    s['no'] = i + 1
    s['miss'] = i > 0 and S[i - 1]['rally'] == s['rally'] and S[i - 1]['side'] == s['side']
    s['good'] = s['plane'] != 'none' and s['cover'] >= 0.6 and not s['trunc'] and -0.3 < s['hz'] < 4.5 and s['v0'] < 70 and s['T'] >= 0.3
out = []
def P(*a): out.append(' '.join(str(x) for x in a))
def st(v, n=2):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v): return '—'
    return f'{np.median(v):.{n}f} ({v.min():.{n}f}–{v.max():.{n}f})'
def col(g, key, n=2, f=None):
    return st([(f(x[key]) if f else x[key]) for x in g], n)
def table(groups, title):
    P('\n' + title + '\n')
    P('| 组 | n | 时长 s | 击球高 m | 初速 m/s | 仰角 ° | 顶点高 m | 顶点进度 | 过网高 m | 水平距离 m | 终点距网 m | 平均水平速 m/s | 末速 m/s | 末角 ° |')
    P('|' + '---|' * 14)
    for k in sorted(groups, key=lambda k: -len(groups[k])):
        g = groups[k]
        cells = [k, len(g), col(g, 'T'), col(g, 'hz'), col(g, 'v0', 1), col(g, 'ang0', 0), col(g, 'apex'), col(g, 'apex_prog'),
                 col(g, 'net_h'), col(g, 'dist', 1), col(g, 'ex', 1, abs), col(g, 'vh', 1), col(g, 'v1', 1), col(g, 'ang1', 0)]
        P('| ' + ' | '.join(str(c) for c in cells) + ' |')
G = [s for s in S if s['good']]
P(f'总拍数 {len(S)}，其中可用于定量（有平面、覆盖率≥0.6、未出画、击球高在 −0.3 至 4.5 m、时长≥0.3 s）{len(G)} 拍；表中数值为 中位数 (最小–最大)。')
g = defaultdict(list)
for s in G: g[s['type']].append(s)
table(g, '### 5.1 按球种')
g2 = defaultdict(list)
for s in G: g2[(s['color'] or '无') + '/' + s['hzone'] + '场/' + s['hband']].append(s)
table({k: v for k, v in g2.items() if len(v) >= 2}, '### 5.2 按 拖尾颜色 × 击球区 × 击球高度（n≥2 的组）')
g3 = defaultdict(list)
for s in G:
    if s['side'] == 'L' and s['key']: g3[s['key'] + '键/' + s['hzone'] + '场/' + s['hband']].append(s)
table({k: v for k, v in g3.items() if len(v) >= 2}, '### 5.3 左方（主视角玩家）按 A_hits 按键 × 击球区 × 击球高度（n≥2）')
P('\n### 5.4 代表拍采样点 (t s, s m, h m)，每 0.1 s\n')
for k, v in g.items():
    for s in sorted(v, key=lambda x: -x['cover'])[:2]:
        a = np.array(SM[s['no']]); tg = np.arange(0, a[-1, 0] + 1e-6, 0.1)
        if a[0, 0] > 0.08: tg = tg[tg >= a[0, 0]]
        pts = ' '.join('({:.1f},{:.2f},{:.2f})'.format(t, np.interp(t, a[:, 0], a[:, 1]), np.interp(t, a[:, 0], a[:, 2])) for t in tg)
        P('- {} 拍#{} 帧{} {} 拖尾{}：{}'.format(k, s['no'], s['hit'], s['side'], s['color'], pts))
P('\n### 6.1 重力+二次阻力拟合（每拍自由拟合 g、k；以及固定 k=0.24 /m 只拟合 g）\n')
P('| 球种 | n | 自由 g m/s² | 自由 k 1/m | 自由 rms m | k=0.24 时 g m/s² | k=0.24 rms m |'); P('|---|---|---|---|---|---|---|')
for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
    v = [x for x in v if np.isfinite(x['g'])]
    if v: P('| ' + ' | '.join([k, str(len(v)), col(v, 'g', 1), col(v, 'k', 3), col(v, 'rms', 3), col(v, 'g24', 1), col(v, 'rms24', 3)]) + ' |')
v = [x for x in G if np.isfinite(x['g']) and x['T'] > 0.6]
def q(key, p): return np.percentile([x[key] for x in v], p)
P('\n全部时长>0.6 s 的 {} 拍：自由 g 中位 {:.2f}（四分位 {:.2f}–{:.2f}），k 中位 {:.3f}（{:.3f}–{:.3f}），rms 中位 {:.3f} m；固定 k=0.24：g 中位 {:.2f}（{:.2f}–{:.2f}），rms 中位 {:.3f} m。'.format(
    len(v), q('g', 50), q('g', 25), q('g', 75), q('k', 50), q('k', 25), q('k', 75), q('rms', 50), q('g24', 50), q('g24', 25), q('g24', 75), q('rms24', 50)))
P('\n### 6.2 沿程速度序列（每 0.1 s 的三维速度 m/s，各球种覆盖最好的 3 拍）\n')
for k, v in g.items():
    for s in sorted(v, key=lambda x: -x['cover'])[:3]: P('- {} 拍#{}：{}'.format(k, s['no'], ' '.join(str(x) for x in s['vser'])))
P('\n速度序列首尾比（末 0.1 s 速度 ÷ 首 0.1 s 速度）：')
for k in ('杀', '扑', '吊', '平抽', '推', '高远', '挑', '放网/搓'):
    r = [s['vser'][-1] / s['vser'][0] for s in g.get(k, []) if len(s['vser']) >= 2 and s['vser'][0] > 0]
    P('- {}：n={}，{}'.format(k, len(r), st(r)))
P('\n### 7.1 能量档（左方，A_hits 的 energy_before）\n')
def tier(e): return '' if not np.isfinite(e) else ('<40' if e < 40 else ('40–99' if e < 100 else '100'))
def hasE(s): return s['side'] == 'L' and s['key'] and np.isfinite(s.get('energyA', np.nan))
P('| 按键/球种 | 能量档 | n | 时长 s | 水平距离 m | 平均水平速 m/s | 初速 m/s | 顶点高 m | 击球高 m |'); P('|---|---|---|---|---|---|---|---|---|')
ge = defaultdict(list)
for s in G:
    if hasE(s): ge[(s['key'], s['type'], tier(s['energyA']))].append(s)
for k in sorted(ge):
    v = ge[k]
    P('| ' + ' | '.join([k[0] + '/' + k[1], k[2], str(len(v)), col(v, 'T'), col(v, 'dist', 1), col(v, 'vh', 1), col(v, 'v0', 1), col(v, 'apex'), col(v, 'hz')]) + ' |')
P('\n按键合并（不分球种，不含发球）：\n'); P('| 按键 | 能量档 | n | 时长 s | 水平距离 m | 平均水平速 m/s | 初速 m/s | 顶点高 m |'); P('|---|---|---|---|---|---|---|---|')
ge = defaultdict(list)
for s in G:
    if hasE(s) and s['idx'] > 1: ge[(s['key'], tier(s['energyA']))].append(s)
for k in sorted(ge):
    v = ge[k]
    P('| ' + ' | '.join([k[0], k[1], str(len(v)), col(v, 'T'), col(v, 'dist', 1), col(v, 'vh', 1), col(v, 'v0', 1), col(v, 'apex')]) + ' |')
P('\n能量（A_hits energy_before，0–100）与指标的相关系数（左方，不含发球）：')
for key in sorted(set(s['key'] for s in G if s['key'])):
    v = [s for s in G if s['key'] == key and hasE(s) and s['idx'] > 1]
    if len(v) >= 5:
        e = np.array([s['energyA'] for s in v])
        if np.ptp(e) > 0:
            cc = lambda kk: np.corrcoef(e, [s[kk] for s in v])[0, 1]
            P('- {}：n={}，r(能量, 平均水平速)={:.2f}，r(能量, 顶点高)={:.2f}，r(能量, 时长)={:.2f}'.format(key, len(v), cc('vh'), cc('apex'), cc('T')))
P('\n### 8.1 来球 → 回球 转移表（格内：次数 (拍间隔中位数 s)；剔除疑似漏拍的相邻同侧对）\n')
tr = defaultdict(list)
for s in S:
    if s['prev'] and not s['miss'] and np.isfinite(s['gap']): tr[(s['prev'], s['type'])].append(s)
types = [k for k, _ in Counter(s['type'] for s in S).most_common()]
P('| 来球＼回球 | ' + ' | '.join(types) + ' |'); P('|' + '---|' * (len(types) + 1))
for a in types:
    row = []
    for b in types:
        v = tr.get((a, b), [])
        row.append('{} ({:.2f})'.format(len(v), np.median([x['gap'] for x in v])) if v else '')
    if any(row): P('| ' + a + ' | ' + ' | '.join(row) + ' |')
P('\n主要对碰组合的回球数据（n≥3）：\n'); P('| 来球→回球 | n | 拍间隔 s | 回球击球高 m | 回球初速 m/s | 回球仰角 ° | 回球顶点 m | 回球时长 s |'); P('|---|---|---|---|---|---|---|---|')
for k, v in sorted(tr.items(), key=lambda kv: -len(kv[1])):
    if len(v) >= 3: P('| ' + ' | '.join([k[0] + '→' + k[1], str(len(v)), col(v, 'gap'), col(v, 'hz'), col(v, 'v0', 1), col(v, 'ang0', 0), col(v, 'apex'), col(v, 'T')]) + ' |')
P('\n### 8.2 节奏\n')
gp = np.array([s['gap'] for s in S if s['prev'] and not s['miss'] and np.isfinite(s['gap'])])
pc = lambda p: np.percentile(gp, p)
P('拍间隔（击球到对方击球，n={}）：中位 {:.2f} s，P10 {:.2f}，P25 {:.2f}，P75 {:.2f}，P90 {:.2f}，最小 {:.2f}，最大 {:.2f}。'.format(len(gp), pc(50), pc(10), pc(25), pc(75), pc(90), gp.min(), gp.max()))
P('\n按来球球种的拍间隔（即该球从击出到被回击的时间）：\n'); P('| 来球 | n | 间隔 s |'); P('|---|---|---|')
gg = defaultdict(list)
for s in S:
    if s['prev'] and not s['miss'] and np.isfinite(s['gap']): gg[s['prev']].append(s['gap'])
for k, v in sorted(gg.items(), key=lambda kv: -len(kv[1])): P('| {} | {} | {} |'.format(k, len(v), st(v)))
rl = defaultdict(list)
for s in S: rl[s['rally']].append(s)
P('\n| 回合 | 起始帧 | 时刻 s | 发球方 | 检出拍数 | 时长 s | 疑似漏拍数 |'); P('|---|---|---|---|---|---|---|')
for r, v in rl.items():
    P('| {} | {} | {:.1f} | {} | {} | {:.1f} | {} |'.format(r, v[0]['hit'], v[0]['hit'] / FPS, v[0]['side'], len(v), (v[-1]['end'] - v[0]['hit']) / FPS, sum(x['miss'] for x in v)))
n = np.array([len(v) for v in rl.values()]); d = np.array([(v[-1]['end'] - v[0]['hit']) / FPS for v in rl.values()])
P('\n每回合检出拍数中位 {:.0f}（{}–{}），回合时长中位 {:.1f} s（{:.1f}–{:.1f}）。'.format(np.median(n), n.min(), n.max(), np.median(d), d.min(), d.max()))
sv = [v[1]['gap'] for v in rl.values() if len(v) > 1 and not v[1]['miss']]
P('发球到接发的时间：n={}，{} s。'.format(len(sv), st(sv)))
P('\n### 9 发球\n'); P('| 拍# | 帧 | 方 | 拖尾 | 击球点 x m | 击球高 m | 初速 m/s | 仰角 ° | 顶点 m | 过网高 m | 终点 x m | 时长 s | 终止 | 定量可用 |'); P('|' + '---|' * 14)
def F(v, n=2): return '—' if not np.isfinite(v) else '{:.{}f}'.format(v, n)
for s in S:
    if s['idx'] == 1:
        P('| ' + ' | '.join([str(s['no']), str(s['hit']), s['side'], s['color'], F(s['hx']), F(s['hz']), F(s['v0'], 1), F(s['ang0'], 0), F(s['apex']), F(s['net_h']), F(s['ex']), F(s['T']),
                             '被回击' if s['returned'] else '落地/终止', '是' if s['good'] else '否']) + ' |')
P('\n### 附：质量统计\n')
P('平面来源：{}；覆盖率≥0.8 的 {} 拍，0.5–0.8 的 {} 拍，<0.5 的 {} 拍；顶部出画 {} 拍；疑似前面漏拍 {} 处。'.format(
    dict(Counter(s['plane'] for s in S)), sum(s['cover'] >= 0.8 for s in S), sum(0.5 <= s['cover'] < 0.8 for s in S), sum(s['cover'] < 0.5 for s in S), sum(s['trunc'] for s in S), sum(s['miss'] for s in S)))
P('影子平面残差（地面 Y 方向标准差）中位 {:.3f} m；拖尾颜色与 A 按键对照：{}'.format(
    np.nanmedian([s['sdp'] for s in S if s['plane'] == 'shadow']), dict(Counter((s['key'], s['color']) for s in S if s['side'] == 'L' and s['key']))))
P('击球点高度（good 拍）：L 中位 {:.2f} m，R 中位 {:.2f} m；起跳击球 {} 拍；击球方 {}。'.format(
    np.median([s['hz'] for s in G if s['side'] == 'L']), np.median([s['hz'] for s in G if s['side'] == 'R']), sum(s['jump'] for s in S), dict(Counter(s['side'] for s in S))))
P('拖尾颜色 × 球种：{}'.format(dict(Counter((s['color'], s['type']) for s in S))))
open(DATA + '/B_stats.md', 'w', encoding='utf-8').write('\n'.join(out))
print(len(out), 'lines')
