# -*- coding: utf-8 -*-
# Lead：汇总 A2_trk 的全片相机位姿（每 6 帧一个），与本方按键时刻、得分时刻对照，输出 data/L_cam_stats.md
import glob, csv, numpy as np
rows=[]
for f in sorted(glob.glob('data/A2_trk/seg_*.csv')):
    for r in csv.DictReader(open(f)):
        rows.append([float(r[k]) for k in ('f','t','cx','cy','cz','pitch','yaw','fov','rms','inl','ok')])
a=np.array(rows); a=a[np.argsort(a[:,0])]
ok=a[:,10]==1
out=[]
out.append('采样 %d 个（每 6 帧），求解成功 %d 个（%.0f%%），覆盖 %.1f–%.1f s'%(len(a),ok.sum(),100*ok.mean(),a[:,1].min(),a[:,1].max()))
g=a[ok]
names=['cx 横向(m)','cy 高度(m)','cz 距网(m)','pitch 俯角(度)','yaw 偏航(度)','vFOV(度)']
out.append('| 量 | 1% | 10% | 50% | 90% | 99% |\n|---|---|---|---|---|---|')
for i,n in enumerate(names):
    p=np.percentile(g[:,2+i],[1,10,50,90,99]); out.append('| %s | %s |'%(n,' | '.join('%.2f'%v for v in p)))
# 相关：高度与距网、fov
def corr(x,y): return float(np.corrcoef(x,y)[0,1])
out.append('相关系数：cy~cz %.2f，cy~fov %.2f，cz~fov %.2f，pitch~cy %.2f，cx~yaw %.2f'%(corr(g[:,3],g[:,4]),corr(g[:,3],g[:,7]),corr(g[:,4],g[:,7]),corr(g[:,5],g[:,3]),corr(g[:,2],g[:,6])))
k=np.polyfit(g[:,4],g[:,3],1); out.append('线性拟合 cy = %.3f*cz + %.3f（残差标准差 %.2f m）'%(k[0],k[1],np.std(g[:,3]-np.polyval(k,g[:,4]))))
# 注视点：光轴与地面交点
pit=np.radians(g[:,5]); yaw=np.radians(g[:,6])
d=g[:,3]/np.tan(pit); lz=g[:,4]-d*np.cos(yaw); lx=g[:,2]+d*np.sin(yaw)
out.append('光轴落地点 z（距网，正=本方半场）分位 1/10/50/90/99：%s；x：%s'%(np.percentile(lz,[1,10,50,90,99]).round(2),np.percentile(lx,[1,10,50,90,99]).round(2)))
# 速度
dt=np.diff(g[:,1]); m=dt<0.15
v=np.sqrt(np.diff(g[:,2])**2+np.diff(g[:,3])**2+np.diff(g[:,4])**2)[m]/dt[m]
out.append('相机移动速度 m/s 分位 50/90/99/最大：%s'%np.percentile(v,[50,90,99,100]).round(2))
dz=(np.diff(g[:,4])[m]/dt[m]); out.append('cz 变化率 m/s 分位 1/50/99：%s'%np.percentile(dz,[1,50,99]).round(2))
# 发球机位：每分 HUD 恢复后的等待发球阶段。得分时刻 + 5.5 s 到 + 6.5 s
score=[0.0,30.0,47.0,65.0,85.0,111.0,139.0,161.5,176.5,210.5]
out.append('\n发球等待阶段（每分开始，取得分时刻后 5.6–6.4 s；第一分取 0.3–1.2 s）：')
out.append('| 分 | 时间窗 s | n | cx | cy | cz | pitch | yaw | vFOV |\n|---|---|---|---|---|---|---|---|---|')
for i,s in enumerate(score):
    w=(g[:,1]>= (0.3 if i==0 else s+5.6))&(g[:,1]<=(1.2 if i==0 else s+6.4))
    if w.sum()==0: out.append('| %d | - | 0 | | | | | | |'%(i+1)); continue
    md=np.median(g[w][:,2:8],axis=0); out.append('| %d | %.1f–%.1f | %d | %s |'%(i+1,g[w][:,1].min(),g[w][:,1].max(),w.sum(),' | '.join('%.2f'%v for v in md)))
# 发球后过渡：用本方/对方第一次按键近似发球时刻不可靠，改为逐分列出发球窗后 4 s 的 cy/cz/fov 序列（0.5 s 步）
out.append('\n每分开始后的相机序列（t 相对得分时刻；cy/cz/fov）：')
for i,s in enumerate(score[1:6],start=2):
    seq=[]
    for tt in np.arange(5.5,11.01,0.5):
        w=np.abs(g[:,1]-(s+tt))<0.12
        seq.append('%.1f:%s'%(tt,'%.1f/%.1f/%.0f'%tuple(np.median(g[w][:,[3,4,7]],axis=0)) if w.sum() else '-'))
    out.append('第 %d 分 '%i+' '.join(seq))
# 典型状态聚类：按 cz 三分位
out.append('\n按相机距网 cz 分三档的中位位姿：')
out.append('| 档 | n | cx | cy | cz | pitch | yaw | vFOV | 光轴落地点 z |\n|---|---|---|---|---|---|---|---|---|')
q=np.percentile(g[:,4],[33,67])
for nm,w in (('近（前推）',g[:,4]<q[0]),('中',(g[:,4]>=q[0])&(g[:,4]<q[1])),('远（拉远）',g[:,4]>=q[1])):
    md=np.median(g[w][:,2:8],axis=0); out.append('| %s | %d | %s | %.2f |'%(nm,w.sum(),' | '.join('%.2f'%v for v in md),np.median(lz[w])))
np.savetxt('data/A2_cam_track.csv',a,delimiter=',',fmt='%.4f',header='f,t,cx,cy,cz,pitch,yaw,fov,rms,inl,ok',comments='')
open('data/L_cam_stats.md','w',encoding='utf-8').write('\n'.join(out))
