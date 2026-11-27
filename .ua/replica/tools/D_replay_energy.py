# -*- coding: utf-8 -*-
"""任务D：从回放 JSONL（D_replay_parse.py 的输出）里抽取 能量计数器 / 属性变化 / 球路 的对应关系。
用法: python D_replay_energy.py <jsonl> [输出csv]
"""
import sys, json, base64, struct, csv, collections

def v3(s):
    if not s:
        return (0.0, 0.0, 0.0)
    b = base64.b64decode(s)
    return struct.unpack("<3f", b[:12])

def load(p):
    recs = [json.loads(l) for l in open(p, encoding="utf-8")]
    return recs[0]["_meta"], recs[1:]

def main():
    meta, recs = load(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    counters = collections.defaultdict(dict)   # pid -> type -> value
    props = collections.defaultdict(dict)      # pid -> prop -> value
    lastact = {}                               # pid -> (frame, actionID, hittype)
    rows = []
    cnt_log = []
    for r in recs:
        d = r.get("d") or {}
        i = r["id"]
        if i == 57:
            t = d.get("CounterType", "NONE").replace("COUNTER_TYPE_", "")
            old = counters[r["pid"]].get(t, 0)
            new = d.get("Value", 0)
            counters[r["pid"]][t] = new
            cnt_log.append((r["f"], r["pid"], t, old, new, d.get("IsServeState", False)))
        elif i == 41:
            props[r["pid"]][d.get("PropType", "").replace("BATTLE_PROP_TYPE_", "")] = d.get("Value", 0)
        elif i == 3:
            lastact[r["pid"]] = (r["f"], d.get("ActionID", 0), d.get("HitType", ""), d.get("IsDirect", False))
        elif i == 63:
            o = d.get("OwnerID", 0)
            sp = v3(d.get("StartPos")); dp = v3(d.get("DropPos"))
            key = d.get("HitKey", "").replace("HIT_KEY_KEY_", "")
            la = lastact.get(o, (0, 0, "", False))
            pk = {"P": "P_BADMINTON_SPEED_MUL", "D": "D_BADMINTON_SPEED_MUL", "GY": "GY_BADMINTON_SPEED_MUL"}.get(key)
            rows.append(dict(frame=r["f"], startFrame=d.get("StartFrame", 0), owner=o, key=key,
                             serve=int(bool(d.get("IsServe"))), curve=d.get("CurveID", 0),
                             avgMul=d.get("AverageSpeedMul", 0),
                             keyMulProp=props[o].get(pk, "") if pk else "",
                             avgMulProp=props[o].get("HIT_BADMINTON_AVERAGE_SPEED_MUL", ""),
                             energy=counters[o].get("CONTINUOUS", ""),
                             starCnt=counters[o].get("STARMARK", ""),
                             action=la[1], hitType=la[2].replace("HIT_TYPE_", ""),
                             sx=round(sp[0], 1), sy=round(sp[1], 1), sz=round(sp[2], 1),
                             dx=round(dp[0], 1), dz=round(dp[2], 1),
                             outDir=d.get("OutDir", "").replace("BADMINTON_OUT_DIR_", "")))
    # 飞行时长：到下一条球路或落地/回合结束
    ends = sorted([r["f"] for r in recs if r["id"] in (63, 64, 22)])
    import bisect
    for row in rows:
        k = bisect.bisect_right(ends, row["frame"])
        row["nextEvtFrames"] = ends[k] - row["frame"] if k < len(ends) else ""
    print(meta)
    print("counter pids:", {p: dict(v) for p, v in counters.items()})
    print("--- 计数器变化(前120条) frame pid type old->new")
    for c in cnt_log[:120]:
        print("  %6d %8d %-18s %4d -> %4d %s" % (c[0], c[1], c[2], c[3], c[4], "serve" if c[5] else ""))
    print("--- 球路 %d 条" % len(rows))
    for row in rows[:60]:
        print(row)
    if out:
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        with open(out.replace(".csv", "_counters.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["frame", "pid", "type", "old", "new", "serveState"]); w.writerows(cnt_log)

if __name__ == "__main__":
    main()
