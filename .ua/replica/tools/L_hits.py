# -*- coding: utf-8 -*-
# Lead：把 A3 的按键事件和 A 的能量变化事件合并成本方击球清单 data/A_hits.csv
import csv, statistics as st
P=list(csv.DictReader(open('data/A3_press.csv',encoding='utf-8')))
E=list(csv.DictReader(open('data/A_energy_events.csv',encoding='utf-8')))
score=[30.0,47.0,65.0,85.0,111.0,139.0,161.5,176.5,210.5,231.5]
ev=[(float(e['t_start_s']),int(e['from_pct']),int(e['to_pct'])) for e in E]
def energy_at(t):
    v=0
    for ts,a,b in ev:
        if ts<=t: v=b
    return v
rows=[];used=set()
for p in P:
    t=float(p['t_s']); m=None
    for i,(ts,a,b) in enumerate(ev):
        if i in used: continue
        if -0.05<=ts-t<=0.70 and (m is None or ts-t<m[1]): m=(i,ts-t,a,b)
    r=dict(frame=p['frame'],t_s=p['t_s'],key=p['key'],energy_before=energy_at(t-0.01),lag_s='',delta='',energy_after='')
    if m:
        used.add(m[0]); r.update(lag_s='%.3f'%m[1],delta=m[3]-m[2],energy_after=m[3],energy_before=m[2])
    r['rally']=sum(1 for s in score if s<t)+1
    rows.append(r)
w=csv.DictWriter(open('data/A_hits.csv','w',encoding='utf-8',newline=''),fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
out=[]
out.append('presses %d  energy events %d  matched %d'%(len(P),len(ev),len(used)))
from collections import Counter
out.append('delta by matched press: %s'%Counter(r['delta'] for r in rows))
out.append('key counts: %s'%Counter(r['key'] for r in rows))
out.append('key x delta: %s'%Counter((r['key'],r['delta']) for r in rows))
lags=[float(r['lag_s']) for r in rows if r['lag_s']]
out.append('lag press->energy change: median %.3f min %.3f max %.3f'%(st.median(lags),min(lags),max(lags)))
out.append('unmatched energy events: %s'%[(round(ev[i][0],2),ev[i][1],ev[i][2]) for i in range(len(ev)) if i not in used])
iv=[]
for a,b in zip(rows,rows[1:]):
    if a['rally']==b['rally']: iv.append(float(b['t_s'])-float(a['t_s']))
iv.sort()
out.append('own-press intervals within rally n=%d median %.2f p10 %.2f p90 %.2f min %.2f max %.2f'%(len(iv),st.median(iv),iv[len(iv)//10],iv[len(iv)*9//10],iv[0],iv[-1]))
out.append('per rally presses: %s'%Counter(r['rally'] for r in rows))
out.append('energy_before tier x count: %s'%Counter(('low' if int(r['energy_before'])<40 else 'mid' if int(r['energy_before'])<100 else 'full') for r in rows))
open('data/L_hits_stats.md','w',encoding='utf-8').write('\n'.join(out))
