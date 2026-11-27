# -*- coding: utf-8 -*-
"""模型 A（设计文档现行弹道，sim/out/trajectories.json）对 模型 B（飞羽源码模型，D_fy_curve.build）
同一击球点、同一落点下的对比。在仓库根目录运行：
  python .ua/replica/tools/L_modelA_vs_B.py
输出 .ua/replica/data/L_modelA_vs_B.csv 与 .ua/replica/data/L_modelA_vs_B.md
只取 线路=中、质量=完美 的组合。蓄力档与飞羽能量档的对应按 U46e：白=低档 黄=中档 红=满档，橙档取中档与满档两条的平均。
"""
import io, json, math, sys, csv, os
import numpy as np
sys.path.insert(0, os.path.join('.ua', 'replica', 'tools'))
import D_fy_curve as D

SIM = json.load(io.open('sim/out/trajectories.json', encoding='utf-8'))
TICK = float(SIM['tickHz'])
FAMB = {'Q': ('近球', (1000, 1001, 1002)), 'Z': ('远球', (1013, 1014, 1015)), 'T': ('高球', (1003, 1004, 1005))}
KILL = {'Z03', 'Z07', 'Z08', 'Z09', 'Z10'}
SMASH_V = (10.0, 11.5, 13.0)          # 飞羽跳扣三档匀速 m/s（D 报告）
TIERS = ['白', '黄', '橙', '红']


def t_down(t, sdist, y, s_net, h=100.0):
    """过网以后球下降到 h cm 的时刻；过网后一直低于 h 则返回过网时刻；到落地都没降到 h（不会发生）返回末时刻。"""
    t = np.asarray(t); sdist = np.asarray(sdist); y = np.asarray(y)
    idx = np.where((sdist >= s_net) & (y <= h))[0]
    if len(idx) == 0: return float(t[-1])
    i = int(idx[0])
    if i == 0 or sdist[i - 1] < s_net or y[i - 1] <= h: return float(t[i])
    f = (y[i - 1] - h) / (y[i - 1] - y[i])
    return float(t[i - 1] + (t[i] - t[i - 1]) * f)


def model_b(fam_ids, tier, y0, dist, nf):
    """返回 (摘要 dict, 曲线号文字, 用来画图的那条 build)。橙档 = 中档与满档两条的平均。"""
    def one(cid):
        b = D.build(cid, y0, dist, nf)
        i = int(np.argmax(b['y']))
        return dict(T=b['T'], apex=b['apex'], net=b['net_h'], tnet=b['t_net'], ap=float(b['s'][i]) / (dist / 100.0), ang=float(b['angle']),
                    t100=t_down(b['rt'], b['s'] * 100, b['y'] * 100, nf * dist)), b
    if tier != 2:
        cid = fam_ids[{0: 0, 1: 1, 3: 2}[tier]]
        m, b = one(cid); return m, str(cid), b
    m1, b1 = one(fam_ids[1]); m2, b2 = one(fam_ids[2])
    return {k: 0.5 * (m1[k] + m2[k]) for k in m1}, '%d与%d平均' % (fam_ids[1], fam_ids[2]), b1


rows = []
curves = {}
for s in SIM['shots']:
    if s['lane'] != '中' or s['quality'] != '完美':
        continue
    p = np.array(s['p'], dtype=float).reshape(-1, 3)
    x0, y0, z0 = p[0]; x1, y1, z1 = p[-1]
    dist = math.hypot(x1 - x0, z1 - z0)
    if z1 <= 0 or dist < 50:
        continue
    nf = (0 - z0) / (z1 - z0)
    aid = s['action'].split(' ')[0]
    tier = TIERS.index(s['tier'])
    hs = np.hypot(p[:, 0] - x0, p[:, 2] - z0)
    ia = int(np.argmax(p[:, 1]))
    a = dict(T=(len(p) - 1) / TICK, apex=float(p[:, 1].max()), net=float(s['netY']), t_net=float(np.interp(nf * dist, hs, np.arange(len(p)) / TICK)),
             apex_prog=float(hs[ia] / dist), t100=t_down(np.arange(len(p)) / TICK, hs, p[:, 1], nf * dist))
    r = dict(id=s['id'], group=s['group'], zone=s['zone'], label=s['label'], action=s['action'], tier=s['tier'], h0=int(round(y0)),
             dist_to_net=int(round(-z0)), land_past_net=int(round(z1)), dist=int(round(dist)), net_hit=s['netHit'], placeholder=s['placeholder'],
             A_T=round(a['T'], 3), A_apex=round(a['apex']), A_net=round(a['net']), A_tnet=round(a['t_net'], 3), A_apex_prog=round(a['apex_prog'], 2), A_t100=round(a['t100'], 3))
    if aid in KILL:
        if s['group'] != '起跳':
            r.update(B_kind='无对应（飞羽没有地面杀球）'); rows.append(r); continue
        path = math.hypot(dist, y0) / 100.0
        lo, mid, hi = (path / v for v in SMASH_V)
        tb = [lo, mid, 0.5 * (mid + hi), hi][tier]
        r.update(B_kind='跳扣匀速', B_curve='4006–4008', B_T=round(tb, 3), T_ratio=round(a['T'] / tb, 2))
        rows.append(r); continue
    famname, ids = FAMB[aid[0]]
    try:
        m, cname, b = model_b(ids, tier, y0, dist, nf)
    except Exception as e:  # 模型解不出来（距离够不到）
        r.update(B_kind=famname, B_curve='解不出：%s' % e); rows.append(r); continue
    r.update(B_kind=famname, B_curve=cname, B_angle=round(m['ang'], 1), B_T=round(m['T'], 3), B_apex=round(m['apex']), B_net=round(m['net']), B_tnet=round(m['tnet'], 3),
             B_apex_prog=round(m['ap'], 2), B_t100=round(m['t100'], 3), T_ratio=round(a['T'] / m['T'], 2), apex_diff=round(a['apex'] - m['apex']),
             net_diff=round(a['net'] - m['net']), tnet_ratio=round(a['t_net'] / m['tnet'], 2) if m['tnet'] else '',
             t100_ratio=round(a['t100'] / m['t100'], 2) if m['t100'] else '', t100_diff=round(a['t100'] - m['t100'], 2))
    rows.append(r)
    curves[s['id']] = dict(a_s=hs.tolist(), a_y=p[:, 1].tolist(), a_t=(np.arange(len(p)) / TICK).tolist(),
                           b_s=(b['s'] * 100).tolist(), b_y=(b['y'] * 100).tolist(), b_t=b['rt'].tolist(), nf=nf, dist=dist, title='%s %s %s' % (s['zone'], s['action'], s['tier']))

cols = ['id', 'group', 'zone', 'label', 'action', 'tier', 'h0', 'dist_to_net', 'land_past_net', 'dist', 'net_hit', 'placeholder',
        'A_T', 'A_t100', 'A_apex', 'A_net', 'A_tnet', 'A_apex_prog', 'B_kind', 'B_curve', 'B_angle', 'B_T', 'B_apex', 'B_net', 'B_tnet', 'B_apex_prog', 'B_t100',
        'T_ratio', 't100_ratio', 't100_diff', 'apex_diff', 'net_diff', 'tnet_ratio']
with io.open('.ua/replica/data/L_modelA_vs_B.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, cols); w.writeheader()
    for r in rows: w.writerow({k: r.get(k, '') for k in cols})
json.dump(curves, io.open('.ua/replica/data/L_modelA_vs_B_curves.json', 'w', encoding='utf-8'), ensure_ascii=False)


def med(v):
    v = [x for x in v if isinstance(x, (int, float))]
    return (float(np.median(v)), float(np.min(v)), float(np.max(v)), len(v)) if v else None


NL = chr(10)
L = []
L.append('# 模型 A（设计文档现行弹道）对 模型 B（飞羽源码模型）同条件对比')
L.append('')
L.append('由 `.ua/replica/tools/L_modelA_vs_B.py` 生成。模型 A 取 `sim/out/trajectories.json` 里线路为中、质量为完美的组合（`sim/` 还是 2026-11-23 的口径，没有同步 V65–V75）；模型 B 用 `.ua/replica/tools/D_fy_curve.py` 的 `build()`，击球高度、击球点、落点都与模型 A 的那一条相同。两边都是算出来的，不是视频实测。')
L.append('')
L.append('对应关系：下坠键对飞羽近球（内圈曲线 1000–1002），平弧键对远球（1013–1015），高弧键对高球（1003–1005）；白档对低档，黄档对中档，红档对满档，橙档取中档与满档两条的平均（U46e）。起跳杀球对飞羽跳扣的匀速值 10.0 / 11.5 / 13.0 m/s，路程按击球点到落点的直线算，橙档取 11.5 与 13.0 两个时长的平均。')
L.append('')
L.append('三个时间量：全程时长 = 击球到落地；到网时刻 = 击球到球过网平面；可接时刻 = 过网以后球降到 1.00 m 高的时刻（接球方腰部高度，过网时已低于 1.00 m 的取过网时刻）。比值都是 模型 A ÷ 模型 B，小于 1 表示现行设计比飞羽快。顶点差、过网高差 = 模型 A − 模型 B，单位 cm。顶点进度 = 顶点所在位置占水平全程的比例。')
L.append('')
L.append('## 1. 按动作汇总')
L.append('')
L.append('只统计模型 A 不撞网、参数不是占位的组合。')
L.append('')
L.append('| 本作动作 | 对应飞羽 | 档 | 条数 | 全程时长比 中位（最小–最大） | 可接时刻比 中位 | 到网时刻比 中位 | 顶点差 中位（最小–最大）cm | 过网高差 中位 cm | 顶点进度 A / B |')
L.append('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
seen = []
for r in rows:
    key = (r['action'], r['tier'])
    if key in seen or 'T_ratio' not in r or r['net_hit'] or r['placeholder']: continue
    seen.append(key)
    rr = [x for x in rows if (x['action'], x['tier']) == key and 'T_ratio' in x and not x['net_hit'] and not x['placeholder']]
    tr = med([x['T_ratio'] for x in rr]); t1 = med([x.get('t100_ratio') for x in rr]); tn = med([x.get('tnet_ratio') for x in rr])
    ad = med([x.get('apex_diff') for x in rr]); nd = med([x.get('net_diff') for x in rr])
    pa = med([x['A_apex_prog'] for x in rr]); pb = med([x.get('B_apex_prog') for x in rr])
    L.append('| %s | %s | %s | %d | %.2f（%.2f–%.2f） | %s | %s | %s | %s | %s |' % (
        r['action'], r['B_kind'], r['tier'], tr[3], tr[0], tr[1], tr[2], ('%.2f' % t1[0]) if t1 else '—', ('%.2f' % tn[0]) if tn else '—',
        ('%+.0f（%+.0f–%+.0f）' % ad[:3]) if ad else '—', ('%+.0f' % nd[0]) if nd else '—', ('%.2f / %.2f' % (pa[0], pb[0])) if pb else '—'))
L.append('')
L.append('## 2. 逐条明细')
L.append('')
L.append('| 编号 | 组 | 场区 | 动作 | 档 | 击球高 cm | 距网 cm | 落点过网 cm | A 全程 s | B 全程 s | 全程比 | A 可接 s | B 可接 s | 可接比 | A 到网 s | B 到网 s | A 顶点 | B 顶点 | A 过网 | B 过网 | A 顶点进度 | B 顶点进度 | B 曲线 | B 出球角 | 备注 |')
L.append('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
for r in rows:
    note = []
    if r['net_hit']: note.append('A 撞网')
    if r['placeholder']: note.append('A 为占位参数')
    if 'T_ratio' not in r: note.append(str(r.get('B_kind', '')) + ' ' + str(r.get('B_curve', '')))
    g = lambda k: ('%s' % r[k]) if k in r and r[k] != '' else '—'
    L.append('| %d | %s | %s | %s | %s | %d | %d | %d | %.2f | %s | %s | %.2f | %s | %s | %.2f | %s | %d | %s | %d | %s | %.2f | %s | %s | %s | %s |' % (
        r['id'], r['group'], r['zone'] + ('' if r['label'] == '地面' else ' ' + r['label']), r['action'], r['tier'], r['h0'], r['dist_to_net'], r['land_past_net'],
        r['A_T'], g('B_T'), g('T_ratio'), r['A_t100'], g('B_t100'), g('t100_ratio'), r['A_tnet'], g('B_tnet'), r['A_apex'], g('B_apex'), r['A_net'], g('B_net'),
        r['A_apex_prog'], g('B_apex_prog'), g('B_curve') if 'T_ratio' in r else '—', g('B_angle'), '；'.join(note)))
L.append('')
io.open('.ua/replica/data/L_modelA_vs_B_tables.md', 'w', encoding='utf-8').write(NL.join(L))
print('rows', len(rows), 'curves', len(curves))
