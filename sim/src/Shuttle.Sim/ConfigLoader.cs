using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Shuttle.Core;
namespace Shuttle.Sim
{
    /// <summary>离线加载器：读 JSON、把小数转 Q16、生成 ease 表与幂表。浮点只出现在这里（相当于游戏的配置导出步骤）。</summary>
    public static class ConfigLoader
    {
        static int Q(double v) { return (int)Math.Round(v * 65536.0); }
        public static CoreConfig Load(string dir)
        {
            var core = JsonDocument.Parse(File.ReadAllText(Path.Combine(dir, "core.json"))).RootElement;
            var c = new CoreConfig();
            var court = core.GetProperty("court");
            c.SinglesHalfWidth = court.GetProperty("singlesHalfWidth").GetInt32();
            c.HalfLength = court.GetProperty("halfLength").GetInt32();
            var net = core.GetProperty("net");
            c.NetHeight = net.GetProperty("height").GetInt32(); c.WhiteClearMargin = net.GetProperty("whiteClearMargin").GetInt32();
            var tiers = new List<TierDef>();
            foreach (var e in core.GetProperty("chargeTier").EnumerateArray())
                tiers.Add(new TierDef { Name = e.GetProperty("name").GetString(), FromTick = e.GetProperty("fromTick").GetInt32(),
                    DurationMulQ = Q(e.GetProperty("durationMul").GetDouble()), Gather = e.GetProperty("gather").GetInt32(),
                    ApexMulQ = Q(e.GetProperty("apexMul").GetDouble()), RecoveryExtra = e.GetProperty("recoveryExtra").GetInt32() });
            c.Tiers = tiers.ToArray();
            var sw = core.GetProperty("swing");
            c.HitFrameOffsetGround = sw.GetProperty("hitFrameOffsetGround").GetInt32();
            c.HitFrameOffsetJump = sw.GetProperty("hitFrameOffsetJump").GetInt32();
            c.MaxChargeTicks = sw.GetProperty("maxChargeTicks").GetInt32();
            var tr = core.GetProperty("trajectory");
            c.RhoDropQ = Q(tr.GetProperty("rhoDrop").GetDouble()); c.RhoHighQ = Q(tr.GetProperty("rhoHigh").GetDouble());
            c.RhoFlatQ = Q(tr.GetProperty("rhoFlat").GetDouble()); c.BMaxQ = Q(tr.GetProperty("downPressBMax").GetDouble());
            c.MinDurationTicks = tr.GetProperty("minDurationTicks").GetInt32();
            double k = tr.GetProperty("easeK").GetDouble();
            c.EaseQ16 = new int[1025];
            for (int i = 0; i <= 1024; i++) c.EaseQ16[i] = Q(1 - Math.Pow(1 - i / 1024.0, k));
            c.PowQ16 = new int[101][];
            for (int g = 0; g <= 100; g++)
            {
                c.PowQ16[g] = new int[256];
                double ex = (100 - g) / 100.0;
                for (int r = 0; r < 256; r++) c.PowQ16[g][r] = Q(Math.Pow((r + 0.5) / 256.0, ex));
            }
            var qu = core.GetProperty("quality");
            c.PerfectQ = Q(qu.GetProperty("perfect").GetDouble()); c.StrideQ = Q(qu.GetProperty("stride").GetDouble());
            c.StrideGatherDrop = qu.GetProperty("strideGatherDrop").GetInt32();
            c.BadBaseQ = Q(qu.GetProperty("badBase").GetDouble()); c.BadSpanQ = Q(qu.GetProperty("badSpan").GetDouble());
            c.BadApexBase = qu.GetProperty("badApexBase").GetInt32(); c.BadApexSpan = qu.GetProperty("badApexSpan").GetInt32();
            c.BadLateral = qu.GetProperty("badLateral").GetInt32();
            var nl = core.GetProperty("netLift");
            c.NetLiftDrop = Ints(nl.GetProperty("drop")); c.NetLiftFlat = Ints(nl.GetProperty("flat"));
            c.MidLaneBad = core.GetProperty("lane").GetProperty("midBad").GetInt32();
            c.DepthGroups = new Dictionary<string, int[]>();
            foreach (var p in core.GetProperty("depthGroups").EnumerateObject()) c.DepthGroups[p.Name] = Ints(p.Value);
            var off = core.GetProperty("offset");
            c.OffsetKQ = Q(off.GetProperty("K").GetDouble()); c.OffsetKmQ = Q(off.GetProperty("Km").GetDouble());
            c.Actions = new Dictionary<string, ActionDef>();
            var acts = JsonDocument.Parse(File.ReadAllText(Path.Combine(dir, "actions.json"))).RootElement;
            foreach (var e in acts.GetProperty("actions").EnumerateArray())
            {
                var a = new ActionDef { Id = e.GetProperty("id").GetString(), Name = e.GetProperty("name").GetString(),
                    Family = (Family)Enum.Parse(typeof(Family), e.GetProperty("family").GetString()),
                    BaseTicks = e.GetProperty("baseTicks").GetInt32(), ApexWhite = e.GetProperty("apexWhite").GetInt32(),
                    HnWhite = e.GetProperty("hnWhite").GetInt32(), Kill = e.GetProperty("kill").GetBoolean(),
                    DepthGroup = e.GetProperty("depthGroup").GetString(), Placeholder = e.GetProperty("placeholder").GetBoolean() };
                c.Actions[a.Id] = a;
            }
            return c;
        }
        static int[] Ints(JsonElement e) { var l = new List<int>(); foreach (var x in e.EnumerateArray()) l.Add(x.GetInt32()); return l.ToArray(); }
    }
}
