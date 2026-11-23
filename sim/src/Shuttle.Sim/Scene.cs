
using System;
using System.Text.Json;
using Shuttle.Core;
namespace Shuttle.Sim
{
    /// <summary>
    /// 把一拍球展开成逐 tick 的场景时间轴，供 Three.js 查看器直接播放（查看器不算任何逻辑）。
    /// 时间轴：蓄力前段（示意来球 + 本方按档蓄力）→ 出球（Shuttle.Core.Trajectory）→ 落地后余段。
    /// 机位每 tick 由 Shuttle.Core.CameraRig 计算，与游戏同源。
    /// 注：来球段与接球方跑位是示意（接球方只跑位、不回球），M2 接入完整回合后替换。
    /// </summary>
    public static class Scene
    {
        public static void Write(Utf8JsonWriter w, CoreConfig c, CameraConfig cc, MoveConfig mc, ShotRequest q, ShotResult r, bool jump)
        {
            int charge = c.Tiers[q.Tier].FromTick;
            int pre = Math.Max(34, charge + 16), post = 50, n = r.Ys.Length - 1;
            int fall = r.NetHit ? 18 : 0;
            int T = pre + n + 1 + fall + post;
            var bx = new int[T]; var by = new int[T]; var bz = new int[T];
            var hx = new int[T]; var hz = new int[T]; var hl = new int[T]; var rx = new int[T]; var rz = new int[T];
            var bub = new int[T]; var chg = new int[T]; var cam = new int[T * 7];
            // ---- 球 ----
            int sx = 0, sz = q.P0Z > -200 ? 300 : 420, sy = 220;           // 示意来球起点（对手击球点）
            for (int i = 0; i < pre; i++)
            {
                int u = Fx.Div(i, pre);
                bx[i] = sx + Fx.Mul(q.P0X - sx, u); bz[i] = sz + Fx.Mul(q.P0Z - sz, u);
                int apex = Math.Max(q.H0, sy) + 160;
                int lin = sy + Fx.Mul(q.H0 - sy, u);
                by[i] = lin + Fx.Mul(apex - Math.Max(q.H0, sy), Fx.Mul(4 * Fx.One, Fx.Mul(u, Fx.One - u)));
            }
            for (int i = 0; i <= n; i++) { bx[pre + i] = r.Xs[i]; by[pre + i] = r.Ys[i]; bz[pre + i] = r.Zs[i]; }
            int land = pre + n;
            for (int i = 1; i <= fall; i++) { int k = land + i; bx[k] = r.Xs[n]; bz[k] = -6 - i; by[k] = Math.Max(0, r.Ys[n] - (r.Ys[n] * i * i) / (fall * fall)); }
            land += fall;
            for (int k = land + 1; k < T; k++) { bx[k] = bx[land]; by[k] = 0; bz[k] = bz[land]; }
            // ---- 本方（击球方）：站在击球点左后侧（右手正手），出球后回中 ----
            int px = q.P0X - 35, pz = q.P0Z - 30;
            int ox = 0, oz = sz;                                            // 对手起点
            int lift = jump ? Math.Max(0, q.H0 - 230) : 0;
            int toward = r.NetHit ? r.Xs[n] : r.LandX, towardZ = r.NetHit ? 300 : r.LandZ;
            for (int k = 0; k < T; k++)
            {
                int t = k - pre;
                if (t > 20) Movement.StepToward(mc, ref px, ref pz, 0, -300, 1, Fx.One);
                hx[k] = px; hz[k] = pz;
                hl[k] = (jump && t > -18 && t < 18) ? lift - lift * t * t / 324 : 0;
                // 松键在命中前 hitFrameOffset(6) tick；蓄力段结束于 t = −7
                chg[k] = charge > 0 ? ((t <= -7 && t >= -charge - 7) ? charge + t + 7 : -1) : ((t <= -7 && t >= -12) ? 0 : -1);
                if (t > mc.ReactionTicks && k <= land) Movement.StepToward(mc, ref ox, ref oz, toward, towardZ + 40, -1, Fx.One);
                rx[k] = ox; rz[k] = oz;
                // 时机泡泡：出球后到落地；进入起跳击球高度段（255–320 cm）且在接球方半场为紫色快闪，其余浅蓝慢闪
                if (t >= 0 && k <= land && !r.NetHit) bub[k] = (bz[k] > 0 && by[k] >= 255 && by[k] <= 320) ? 2 : 1;
                if (t < 0 && k >= 4) bub[k] = (bz[k] < 0 && by[k] >= 255 && by[k] <= 320) ? 2 : 1; // 来球段：本方泡泡
            }
            // ---- 机位 ----
            CamState cs = default(CamState);
            for (int k = 0; k < T; k++)
            {
                int t = k - pre;
                bool live = k <= land; bool landLive = t >= 6 && k <= land && !r.NetHit;
                var tg = CameraRig.Target(cc, hx[k], hz[k], hl[k], live, bz[k], landLive, r.LandZ, rz[k]);
                if (k == 0) cs = tg; else CameraRig.Step(cc, ref cs, tg);
                cam[k * 7] = cs.Px; cam[k * 7 + 1] = cs.Py; cam[k * 7 + 2] = cs.Pz; cam[k * 7 + 3] = cs.Lx; cam[k * 7 + 4] = cs.Ly; cam[k * 7 + 5] = cs.Lz; cam[k * 7 + 6] = cs.Fov;
            }
            long ddx = rx[land] - r.LandX, ddz = rz[land] - r.LandZ;
            w.WriteStartObject("scene");
            w.WriteNumber("pre", pre); w.WriteNumber("land", land); w.WriteNumber("ticks", T); w.WriteNumber("chargeTicks", charge);
            w.WriteNumber("landX", r.LandX); w.WriteNumber("landZ", r.LandZ); w.WriteBoolean("jump", jump); w.WriteBoolean("kill", q.Action.Kill);
            w.WriteNumber("recvDist", r.NetHit ? -1 : (int)Movement.ISqrt(ddx * ddx + ddz * ddz));
            Arr(w, "ball", T, k => new[] { bx[k], by[k], bz[k] });
            Arr(w, "own", T, k => new[] { hx[k], hz[k], hl[k] });
            Arr(w, "opp", T, k => new[] { rx[k], rz[k] });
            Arr(w, "bubble", T, k => new[] { bub[k] });
            Arr(w, "charge", T, k => new[] { chg[k] });
            Arr(w, "cam", T, k => new[] { cam[k * 7], cam[k * 7 + 1], cam[k * 7 + 2], cam[k * 7 + 3], cam[k * 7 + 4], cam[k * 7 + 5], cam[k * 7 + 6] });
            w.WriteEndObject();
        }
        static void Arr(Utf8JsonWriter w, string name, int T, Func<int, int[]> f)
        {
            w.WriteStartArray(name); for (int k = 0; k < T; k++) foreach (var v in f(k)) w.WriteNumberValue(v); w.WriteEndArray();
        }
    }
}
