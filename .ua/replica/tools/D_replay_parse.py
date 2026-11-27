# -*- coding: utf-8 -*-
"""任务D：解析飞羽客户端 .replay（Common_pb2.ReplayDataMsg），把服务器下发的战斗消息解码成 JSONL。
用法: python D_replay_parse.py <replay路径> <输出jsonl> [只保留的消息号,逗号分隔]
只读 References；输出放 .ua/replica/data/ 。
"""
import os, sys, json, struct
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
ROOT = r"D:\GameDev\the-shuttle-badminton-glory\References\fyqc\fyqc-client\python_src"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "base", "protobufdata"))
from google.protobuf import json_format
import importlib

def _imp(name):
    for mod in ("base.protobufdata." + name, name):
        try:
            return importlib.import_module(mod)
        except Exception as e:
            err = e
    raise err

Common_pb2 = _imp("Common_pb2")
BattleCmd_pb2 = _imp("BattleCmd_pb2")

# 消息号 -> 类名（来自 prediction/nethandler.py:456-494 与 battlelogic 各 AddDelta 调用点）
MSG_CLS = {
    2: "BattleHitMsg", 3: "BattleHitResMsg", 4: "BattleJoystickDirMsg", 6: "BattlePosMsg",
    7: "BattleGameStateMsg", 8: "BattleScoreBoardMsg", 9: "BattleServePlayerMsg",
    10: "BattleWalkToMsg", 12: "BattlePosIndexMsg", 13: "BattleAddObjectMsg",
    14: "BattleRemoveObjectMsg", 15: "BattleMoveTypeMsg", 16: "BattleWinkMoveMsg",
    22: "BattleBadmintonLandedMsg", 26: "BadmintonStarMarkMsg", 27: "BattleHitBadmintonMsg",
    31: "BattleFacingMsg", 34: "BadmintonBodyShotMsg", 41: "BattlePropChangeMsg",
    44: "BadmintonNetShotMsg", 45: "BattleAddStateMsg", 46: "BattleRemoveStateMsg",
    47: "BattleBadmintonHitHintMsg", 48: "BattleNotifyMsg", 54: "BattleObjBulletTimeMsg",
    55: "BattleSceneBulletTimeMsg", 57: "BattleUpdateCounterMsg", 62: "BattleHitDirMsg",
    63: "BattleBadmintonCurveMsg", 64: "BattleBadmintonCurveEndMsg",
    65: "BattleBadmintonCouldBeHitMsg", 66: "BattleCurPointServePlayerIDMsg",
    74: "BattleMoveDirMsg", 81: "BattleHitKeyCDMsg", 88: "BattleBadmintonPrejudgeCurveMsg",
    89: "BattleHitNumMsg", 90: "BattleFakebadmintonCurveMsg", 91: "BattleBadmintonLockedMsg",
    100: "BattleAddCounterRecMsg", 107: "BattleBehaviorMsg", 108: "BattleHitEndMsg",
    116: "BattleObjDoSetBulletTimeMsg", 118: "BattleServerSmoothPosMsg",
}
ID2NAME = {}
for k, v in vars(BattleCmd_pb2).items():
    if k.startswith("BATTLE_") and k.endswith("_MSG") and isinstance(v, int):
        ID2NAME[v] = k


def decode(msgid, body):
    cls = getattr(BattleCmd_pb2, MSG_CLS.get(msgid, ""), None)
    if cls is None:
        return None
    m = cls()
    try:
        m.ParseFromString(body)
    except Exception as e:
        return {"_err": str(e), "_hex": body.hex()}
    return json_format.MessageToDict(m, preserving_proto_field_name=True,
                                     always_print_fields_with_no_presence=False)


def main():
    path, out = sys.argv[1], sys.argv[2]
    keep = set(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else None
    data = open(path, "rb").read()
    rp = Common_pb2.ReplayDataMsg()
    rp.ParseFromString(data)
    stat = {}
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps({"_meta": {"file": os.path.basename(path), "frames": len(rp.FrameData),
                                      "readyServe": list(rp.ReadyServeFrameNum),
                                      "createLen": len(rp.CreateGameMsgBuffer),
                                      "resLen": len(rp.NormalGameResMsgBuffer)}}, ensure_ascii=False) + "\n")
        for fr in rp.FrameData:
            for b in fr.BinData:
                if len(b) < 6:
                    continue
                msgid = b[1]
                pid = struct.unpack("<i", b[2:6])[0]
                body = b[6:]
                stat[msgid] = stat.get(msgid, 0) + 1
                if keep is not None and msgid not in keep:
                    continue
                d = decode(msgid, body)
                rec = {"f": fr.FrameNum, "id": msgid, "n": ID2NAME.get(msgid, "?"), "pid": pid}
                if d is None:
                    rec["hex"] = body.hex()
                else:
                    rec["d"] = d
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(os.path.basename(path), "frames", len(rp.FrameData), "lastFrame",
          rp.FrameData[-1].FrameNum if rp.FrameData else None)
    for k in sorted(stat):
        print("  %3d %-45s %6d %s" % (k, ID2NAME.get(k, "?"), stat[k], MSG_CLS.get(k, "(raw)")))


if __name__ == "__main__":
    main()
