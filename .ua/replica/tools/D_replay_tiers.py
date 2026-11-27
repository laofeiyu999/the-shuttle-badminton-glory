# -*- coding: utf-8 -*-
"""任务D：跨全部回放统计 能量(COUNTER_TYPE_CONTINUOUS) 与 球路ID / 速度倍率属性 / 击球动作 的关系。
输入 .ua/replica/data/D_tmp/r*.jsonl （D_replay_parse.py 输出）。
输出 .ua/replica/data/D_replay_hits.csv （每次击球一行）并打印汇总。
"""
import json, glob, base64, struct, csv, collections, os, sys

D = r"D:\GameDev\the-shuttle-badminton-glory\.ua\replica\data"

def v3(s):
    if not s:
        return (0.0, 0.0, 0.0)
    return struct.unpack("<3f", base64.b64decode(s)[:12])

rows = []
cnt_delta = collections.Counter()      # (type, delta) 次数
prop_seen = collections.defaultdict(collections.Counter)
for p in sorted(glob.glob(os.path.join(D, "D_tmp", "r?.jsonl"))):
    rid = os.path.basename(p)[:2]
    recs = [json.loads(l) for l in open(p, encoding="utf-8")][1:]
    counters = collections.defaultdict(dict)
    props = collections.defaultdict(dict)
    lastact = {}
    # 帧内顺序：先收集同帧的计数器旧值
    pre_energy = {}
    curframe = None
    for r in recs:
        d = r.get("d") or {}
        i = r["id"]
        if r["f"] != curframe:
            curframe = r["f"]
            pre_energy = {pid: c.get("CONTINUOUS") for pid, c in counters.items()}
        if i == 57:
            t = d.get("CounterType", "NONE").replace("COUNTER_TYPE_", "")
            old = counters[r["pid"]].get(t)
            new = d.get("Value", 0)
            if old is not None and not d.get("IsServeState"):
                cnt_delta[(t, new - old)] += 1
            counters[r["pid"]][t] = new
        elif i == 41:
            k = d.get("PropType", "").replace("BATTLE_PROP_TYPE_", "")
            props[r["pid"]][k] = d.get("Value", 0)
            if "SPEED_MUL" in k or "DROPPOS" in k or k.startswith("SPEED_") or "RADIUS" in k:
                prop_seen[k][d.get("Value", 0)] += 1
        elif i == 3:
            lastact[r["pid"]] = (r["f"], d.get("ActionID", 0), d.get("HitType", ""))
        elif i == 63:
            o = d.get("OwnerID", 0)
            sp = v3(d.get("StartPos")); dp = v3(d.get("DropPos"))
            key = d.get("HitKey", "").replace("HIT_KEY_KEY_", "")
            la = lastact.get(o, (0, 0, ""))
            pk = {"P": "P_BADMINTON_SPEED_MUL", "D": "D_BADMINTON_SPEED_MUL", "GY": "GY_BADMINTON_SPEED_MUL"}.get(key)
            rows.append(dict(rep=rid, frame=r["f"], startFrame=d.get("StartFrame", 0), owner=o, key=key,
                             serve=int(bool(d.get("IsServe"))), curve=d.get("CurveID", 0),
                             avgMulMsg=d.get("AverageSpeedMul", 0),
                             keyMulProp=props[o].get(pk, "") if pk else "",
                             energyPre=pre_energy.get(o, "") if pre_energy.get(o) is not None else "",
                             energyPost=counters[o].get("CONTINUOUS", ""),
                             starCnt=counters[o].get("STARMARK", ""),
                             action=la[1], hitType=la[2].replace("HIT_TYPE_", ""),
                             sx=round(sp[0], 1), sy=round(sp[1], 1), sz=round(sp[2], 1),
                             dx=round(dp[0], 1), dz=round(dp[2], 1),
                             outDir=d.get("OutDir", "").replace("BADMINTON_OUT_DIR_", "")))

with open(os.path.join(D, "D_replay_hits.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("hits", len(rows), "with energy", sum(1 for r in rows if r["energyPre"] != ""))
print("--- 计数器增量分布 (type, delta): 次数")
for (t, dlt), n in sorted(cnt_delta.items(), key=lambda x: (x[0][0], -x[1])):
    if n >= 2 or t == "CONTINUOUS":
        print("  %-18s %+5d  x%d" % (t, dlt, n))
print("--- 属性取值分布")
for k in sorted(prop_seen):
    if "RADIUS" in k and not k.endswith("DIR1"):
        continue
    print("  %-34s %s" % (k, dict(sorted(prop_seen[k].items()))))
print("--- 有能量记录的击球：曲线ID × 能量(击球前) 分布")
tab = collections.defaultdict(list)
for r in rows:
    if r["energyPre"] != "" and not r["serve"]:
        tab[r["curve"]].append(r["energyPre"])
for c in sorted(tab):
    v = sorted(tab[c])
    print("  curve %d n=%d min=%s max=%s  %s" % (c, len(v), v[0], v[-1], v if len(v) <= 40 else v[:40]))
print("--- 全部击球：曲线ID 次数 / 动作ID集合")
cc = collections.Counter(r["curve"] for r in rows)
ca = collections.defaultdict(collections.Counter)
for r in rows:
    ca[r["curve"]][r["action"]] += 1
for c in sorted(cc):
    print("  %d x%d actions=%s" % (c, cc[c], dict(sorted(ca[c].items()))))
