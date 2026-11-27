# -*- coding: utf-8 -*-
"""任务D：打印每个回放的建局信息（模式、玩家、技能、是否 AI）与帧号断档。"""
import os, sys, json, glob, re
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
R = r"D:\GameDev\the-shuttle-badminton-glory\References\fyqc\fyqc-client"
sys.path.insert(0, os.path.join(R, "python_src", "base", "protobufdata"))
import Common_pb2, BattleCtrl_pb2, NormalCmd_pb2
from google.protobuf import json_format

full = len(sys.argv) > 1
for i, p in enumerate(sorted(glob.glob(R + r"\replays\*.replay")), 1):
    rp = Common_pb2.ReplayDataMsg(); rp.ParseFromString(open(p, "rb").read())
    fs = [f.FrameNum for f in rp.FrameData]
    gaps = [(a, b) for a, b in zip(fs, fs[1:]) if b - a > 50]
    out = None
    for cls in (BattleCtrl_pb2.BattleCtrlCreateGameMsg, Common_pb2.PreCreateGameData):
        m = cls()
        try:
            m.ParseFromString(rp.CreateGameMsgBuffer)
            out = json_format.MessageToDict(m, preserving_proto_field_name=True)
            break
        except Exception as e:
            out = {"ERR": str(e)}
    s = json.dumps(out, ensure_ascii=False)
    print("r%d" % i, os.path.basename(p)[:24], "frames", len(fs), fs[0], fs[-1], "gaps", gaps[:5],
          "readyServe", len(rp.ReadyServeFrameNum))
    if full:
        print(s[:6000])
    else:
        print("  ", re.findall(r'"(GameMode|BattleMode|IsGameAI|GameAIDifficulty|BTConfID|SceneIndex)": ?("[^"]*"|[^,}\]]*)', s)[:20])
    res = Common_pb2.GameRes()
    try:
        res.ParseFromString(rp.NormalGameResMsgBuffer)
        d = json_format.MessageToDict(res, preserving_proto_field_name=True)
        print("   res:", d.get("GameMode"), d.get("BattleMode"), "score", d.get("HostScore"), d.get("GuestScore"),
              "dur", d.get("GameDuration"))
        for pb in d.get("PlayerBattleDatas", []):
            sc = pb.get("PlayerScoreData", {})
            print("     ", pb.get("ID"), pb.get("MemberType", "")[17:], "skill", pb.get("EquipSkill"),
                  {k: sc.get(k) for k in ("HitTimes", "PHitTimes", "DHitTimes", "GYHitTimes", "JumpTimes", "StarTimes",
                                          "AVGContinuousTimes", "HighContinuousTimes", "MiddleContinuousTimes",
                                          "LowContinuousTimes", "InsideHitTimes", "MiddleHitTimes", "OutsideHitTimes",
                                          "NormalHitTimes")})
    except Exception as e:
        print("   res ERR", e)
