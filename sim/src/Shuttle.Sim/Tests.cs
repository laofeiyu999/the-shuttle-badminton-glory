using System;
using System.Collections.Generic;
using Shuttle.Core;
namespace Shuttle.Sim
{
    /// <summary>设计文档测试锚点。失败返回非零。</summary>
    public static class Tests
    {
        static int _fail, _pass;
        static void Eq(string name, int want, int got) { if (want == got) _pass++; else { _fail++; Console.WriteLine("FAIL " + name + "：期望 " + want + "，得到 " + got); } }
        static void True(string name, bool v) { if (v) _pass++; else { _fail++; Console.WriteLine("FAIL " + name); } }

        static ShotResult Shot(CoreConfig c, string act, int tier, Quality q, int h0, int dist, int lane = 0, int uQ = 65536, int rQ = 0)
        {
            return Trajectory.Generate(c, new ShotRequest { Action = c.Actions[act], Tier = tier, Quality = q, BadUQ = uQ, Lane = lane,
                P0X = 0, P0Z = -dist, H0 = h0, OffsetRQ = rQ, RandX = 128, RandZ = 128 });
        }

        public static int Run(CoreConfig c)
        {
            // T6.1：完美白档时长 = 基础 tick
            foreach (var a in c.Actions.Values) Eq("T6.1 " + a.Id + " 白档完美时长", a.BaseTicks, Shot(c, a.Id, 0, Quality.Perfect, 230, 350).N);
            // T6.1：红档时长 = round(基础 × 0.74)
            Eq("T6.1 高远红档", (int)Math.Round(117 * 0.74, MidpointRounding.AwayFromZero), Shot(c, "T03", 3, Quality.Perfect, 230, 600).N);
            // T5.7-7：放网/挑高 糟糕 u=1，R = 0 / 0.225 / 0.45
            int[] rs = { 0, (int)Math.Round(0.225 * 65536), (int)Math.Round(0.45 * 65536) };
            int[] wantDrop = { 81, 75, 69 }, wantLift = { 167, 154, 142 };
            for (int i = 0; i < 3; i++)
            {
                Eq("T5.7-7 放网 R" + i, wantDrop[i], Shot(c, "Q04", 0, Quality.Bad, 40, 120, 0, 65536, rs[i]).N);
                Eq("T5.7-7 挑高 R" + i, wantLift[i], Shot(c, "T01", 0, Quality.Bad, 40, 120, 0, 65536, rs[i]).N);
            }
            // T6.6-1：前场下坠黄档 触点 1.20 撞网、1.21 过网
            True("T6.6-1 下坠黄档 120 撞网", Shot(c, "Q04", 1, Quality.Perfect, 120, 120).NetHit);
            True("T6.6-1 下坠黄档 121 过网", !Shot(c, "Q04", 1, Quality.Perfect, 121, 120).NetHit);
            // T6.6-2：平弧红档 触点 1.50 撞网、1.51 过网
            True("T6.6-2 平弧红档 150 撞网", Shot(c, "Z09", 3, Quality.Perfect, 150, 350).NetHit);
            True("T6.6-2 平弧红档 151 过网", !Shot(c, "Z09", 3, Quality.Perfect, 151, 350).NetHit);
            // 白档永不撞网
            foreach (var a in c.Actions.Values) True("白档不撞网 " + a.Id, !Shot(c, a.Id, 0, Quality.Perfect, 40, 120).NetHit);
            // 确定性：同输入两次结果逐 tick 一致
            var r1 = Shot(c, "Z10", 3, Quality.Stride, 290, 600, 1); var r2 = Shot(c, "Z10", 3, Quality.Stride, 290, 600, 1);
            bool same = r1.Ys.Length == r2.Ys.Length; for (int i = 0; same && i < r1.Ys.Length; i++) same = r1.Xs[i] == r2.Xs[i] && r1.Ys[i] == r2.Ys[i] && r1.Zs[i] == r2.Zs[i];
            True("确定性 逐 tick 一致", same);
            // 落点终点 = 目标落点
            var e = Shot(c, "T03", 2, Quality.Perfect, 230, 600, -1);
            Eq("终点 Z = 落点", e.LandZ, e.Zs[e.Zs.Length - 1]); Eq("终点 Y = 0", 0, e.Ys[e.Ys.Length - 1]);
            Console.WriteLine("测试：通过 " + _pass + "，失败 " + _fail);
            return _fail == 0 ? 0 : 1;
        }
    }
}
