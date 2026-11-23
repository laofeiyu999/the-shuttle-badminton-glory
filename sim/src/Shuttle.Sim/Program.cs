using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using Shuttle.Core;
namespace Shuttle.Sim
{
    /// <summary>
    /// 仿真命令行：
    ///   batch  —— 生成 324 条地面 + 起跳组合 CSV 与查看器用 JSON，并跑自动检查（设计文档 6.2.3）
    ///   test   —— 跑测试锚点（T6.1 / T6.6 / T5.7-7 / 确定性）
    /// </summary>
    public static class Program
    {
        static readonly string[] Lanes = { "左", "中", "右" };
        static readonly string[] Quals = { "完美", "跨步", "糟糕" };

        public static int Main(string[] args)
        {
            string root = FindRoot();
            string cfgDir = Path.Combine(root, "config");
            var c = ConfigLoader.Load(cfgDir);
            string cmd = args.Length > 0 ? args[0] : "batch";
            if (cmd == "test") return Tests.Run(c);
            return Batch(c, cfgDir, Path.Combine(root, "out"));
        }

        static string FindRoot()
        {
            var d = new DirectoryInfo(AppContext.BaseDirectory);
            while (d != null && !File.Exists(Path.Combine(d.FullName, "config", "core.json"))) d = d.Parent;
            if (d == null) throw new Exception("找不到 sim/config/core.json");
            return d.FullName;
        }

        sealed class Row { public string Group, Zone, Label, Act, Tier, Lane, Qual; public ShotRequest Req; public ShotResult Res; }

        static int Batch(CoreConfig c, string cfgDir, string outDir)
        {
            Directory.CreateDirectory(outDir);
            var sc = JsonDocument.Parse(File.ReadAllText(Path.Combine(cfgDir, "scenarios.json"))).RootElement;
            int badU = (int)Math.Round(sc.GetProperty("badU").GetDouble() * 65536);
            var rows = new List<Row>();
            var rng = new Pcg32(20261123UL, 1UL); // ball 流，固定种子
            foreach (var grp in new[] { "ground", "jump" })
            foreach (var s in sc.GetProperty(grp).EnumerateArray())
            {
                int dist = s.GetProperty("distance").GetInt32(), h0 = s.GetProperty("h0").GetInt32();
                var acts = s.GetProperty("actions");
                var tiers = new List<int>();
                if (s.TryGetProperty("tiers", out var tt)) foreach (var x in tt.EnumerateArray()) tiers.Add(x.GetInt32()); else tiers.AddRange(new[] { 0, 1, 2, 3 });
                string label = s.TryGetProperty("label", out var lb) ? lb.GetString() : "地面";
                bool jumpGrp = grp == "jump";
                foreach (int tier in tiers)
                for (int lane = -1; lane <= 1; lane++)
                foreach (var qual in jumpGrp ? new[] { Quality.Perfect } : new[] { Quality.Perfect, Quality.Stride, Quality.Bad })
                {
                    // 起跳组合表（6.2）按完美质量列 90 条；跨步/糟糕在地面表覆盖
                    var a = c.Actions[acts[tier].GetString()];
                    var req = new ShotRequest { Action = a, Tier = tier, Quality = qual, BadUQ = badU, Lane = lane,
                        P0X = 0, P0Z = -dist, H0 = h0, RandX = rng.Next8(), RandZ = rng.Next8() };
                    rows.Add(new Row { Group = grp, Zone = s.GetProperty("zone").GetString(), Label = label, Act = a.Id + " " + a.Name,
                        Tier = c.Tiers[tier].Name, Lane = Lanes[lane + 1], Qual = Quals[(int)qual], Req = req, Res = Trajectory.Generate(c, req) });
                }
            }
            // ---- CSV ----
            var sb = new StringBuilder();
            sb.AppendLine("编号,组,场区,类型,动作,蓄力档,线路,质量,触点cm,时长tick,时长s,集中度,质量项,顶点cm,网平面cm,撞网,落点X,落点Z(距网),落点钳制,接球方最多可蓄tick,接球方可达档,占位参数,备注");
            int idx = 0; var issues = new List<string>();
            foreach (var r in rows)
            {
                idx++;
                var x = r.Res; int rc = Trajectory.ReceiverMaxCharge(c, x.N);
                string rt = c.Tiers[0].Name; for (int i = c.Tiers.Length - 1; i >= 0; i--) if (rc >= c.Tiers[i].FromTick) { rt = c.Tiers[i].Name; break; }
                sb.AppendLine(string.Join(",", new object[] { idx, r.Group == "ground" ? "地面" : "起跳", r.Zone, r.Label, r.Act, r.Tier, r.Lane, r.Qual, r.Req.H0, x.N,
                    (x.N / 60.0).ToString("0.000", CultureInfo.InvariantCulture), x.Gather, (x.QualityTermQ / 65536.0).ToString("0.000", CultureInfo.InvariantCulture),
                    x.ApexActual, x.NetPlaneInterp, x.NetHit ? "是" : "否", x.LandX, x.LandZ, x.Clamped ? "是" : "否", rc, rt, r.Req.Action.Placeholder ? "是" : "",
                    string.Join(" / ", x.Notes) }));
                // ---- 自动检查（6.2.3） ----
                string id = "#" + idx + " " + r.Act + " " + r.Tier + r.Lane + r.Qual + "（" + r.Zone + r.Label + "）";
                if (x.N < c.MinDurationTicks) issues.Add(id + "：时长低于下限");
                if (!x.NetHit && x.NetPlaneInterp <= c.NetHeight) issues.Add(id + "：未判撞网但网平面高度 " + x.NetPlaneInterp + " ≤ 网高");
                if ((r.Req.Tier == 0 || r.Req.Action.Family == Family.High) && x.NetPlaneInterp < c.NetHeight + c.WhiteClearMargin)
                    issues.Add(id + "：白档/高弧过网余量不足（" + x.NetPlaneInterp + "）");
                if (x.Clamped) issues.Add(id + "：落点被场地钳制");
                if (!x.NetHit && Math.Abs(x.NetPlaneInterp - x.NetPlaneAnalytic) > 4) issues.Add(id + "：逐 tick 网平面与解析值相差 " + (x.NetPlaneInterp - x.NetPlaneAnalytic) + " cm");
                foreach (var y in x.Ys) if (y < 0) { issues.Add(id + "：轨迹低于地面"); break; }
            }
            File.WriteAllText(Path.Combine(outDir, "trajectories.csv"), "\uFEFF" + sb.ToString(), new UTF8Encoding(false));
            // ---- 查看器 JSON ----
            using (var fs = File.Create(Path.Combine(outDir, "trajectories.json")))
            using (var w = new Utf8JsonWriter(fs, new JsonWriterOptions { Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping }))
            {
                w.WriteStartObject();
                w.WriteNumber("tickHz", 60); w.WriteNumber("netHeight", c.NetHeight); w.WriteNumber("halfWidth", c.SinglesHalfWidth); w.WriteNumber("halfLength", c.HalfLength);
                w.WriteStartArray("shots"); idx = 0;
                foreach (var r in rows)
                {
                    idx++; w.WriteStartObject();
                    w.WriteNumber("id", idx); w.WriteString("group", r.Group == "ground" ? "地面" : "起跳"); w.WriteString("zone", r.Zone); w.WriteString("label", r.Label);
                    w.WriteString("action", r.Act); w.WriteString("tier", r.Tier); w.WriteString("lane", r.Lane); w.WriteString("quality", r.Qual);
                    w.WriteNumber("n", r.Res.N); w.WriteBoolean("netHit", r.Res.NetHit); w.WriteNumber("apex", r.Res.ApexActual); w.WriteNumber("netY", r.Res.NetPlaneInterp);
                    w.WriteNumber("receiverCharge", Trajectory.ReceiverMaxCharge(c, r.Res.N)); w.WriteBoolean("placeholder", r.Req.Action.Placeholder);
                    w.WriteStartArray("p"); for (int i = 0; i < r.Res.Ys.Length; i++) { w.WriteNumberValue(r.Res.Xs[i]); w.WriteNumberValue(r.Res.Ys[i]); w.WriteNumberValue(r.Res.Zs[i]); } w.WriteEndArray();
                    w.WriteEndObject();
                }
                w.WriteEndArray(); w.WriteEndObject();
            }
            File.WriteAllText(Path.Combine(outDir, "checks.txt"), "自动检查：" + rows.Count + " 条，问题 " + issues.Count + " 条\n" + string.Join("\n", issues), new UTF8Encoding(false));
            int g = 0; foreach (var r in rows) if (r.Group == "ground") g++;
            Console.WriteLine("地面 " + g + " 条，起跳 " + (rows.Count - g) + " 条；自动检查问题 " + issues.Count + " 条 → out/checks.txt");
            for (int i = 0; i < Math.Min(issues.Count, 40); i++) Console.WriteLine("  " + issues[i]);
            return 0;
        }
    }
}
