namespace Shuttle.Core
{
    public sealed class CamZone { public int D, Height, Back, LookAhead, Fov; }
    public sealed class CameraConfig
    {
        public CamZone[] Zones; public int DampQ, LateralQ, GroupQ, JumpFollowQ;
        public int WOwn = 4, WLand = 3, WOpp = 2, WBall = 1;
    }
    /// <summary>机位状态：位置、注视点（cm），垂直视场角（度）。</summary>
    public struct CamState { public int Px, Py, Pz, Lx, Ly, Lz, Fov; }

    /// <summary>
    /// 实战视角机位（设计文档 10.7.2）。只读确定性状态（人物位置、球、落点预判、tick），整数运算，
    /// 仿真查看器与 Unity 正式版调用同一段代码。本方在 Z&lt;0 半场、面向 +Z。
    /// </summary>
    public static class CameraRig
    {
        public static CamState Target(CameraConfig cc, int ownX, int ownZ, int ownLift,
            bool ballLive, int ballZ, bool landLive, int landZ, int oppZ)
        {
            int d = ownZ < 0 ? -ownZ : 0;
            var zs = cc.Zones; CamZone a = zs[0], b = zs[0]; int tQ = 0;
            if (d <= zs[0].D) { a = b = zs[0]; }
            else if (d >= zs[zs.Length - 1].D) { a = b = zs[zs.Length - 1]; }
            else for (int i = 0; i < zs.Length - 1; i++)
                if (d >= zs[i].D && d < zs[i + 1].D) { a = zs[i]; b = zs[i + 1]; tQ = Fx.Div(d - a.D, b.D - a.D); break; }
            int height = Fx.Lerp(a.Height, b.Height, tQ), back = Fx.Lerp(a.Back, b.Back, tQ);
            int ahead = Fx.Lerp(a.LookAhead, b.LookAhead, tQ), fov = Fx.Lerp(a.Fov, b.Fov, tQ);
            // 目标组加权中心（纵向）
            long sw = cc.WOwn + cc.WOpp, sz = (long)cc.WOwn * ownZ + (long)cc.WOpp * oppZ;
            if (landLive) { sw += cc.WLand; sz += (long)cc.WLand * landZ; }
            if (ballLive) { sw += cc.WBall; sz += (long)cc.WBall * ballZ; }
            int gz = (int)(sz / sw);
            int baseLook = ownZ + ahead;
            var s = new CamState();
            s.Lz = baseLook + Fx.Mul(cc.GroupQ, gz - baseLook);
            s.Lx = Fx.Mul(cc.LateralQ, ownX);
            s.Ly = Fx.Mul(cc.JumpFollowQ, ownLift);
            s.Px = s.Lx; s.Py = height + s.Ly; s.Pz = s.Lz - back; s.Fov = fov;
            return s;
        }

        /// <summary>每 tick 阻尼跟随。</summary>
        public static void Step(CameraConfig cc, ref CamState c, CamState t)
        {
            int k = cc.DampQ;
            c.Px += Fx.Mul(t.Px - c.Px, k); c.Py += Fx.Mul(t.Py - c.Py, k); c.Pz += Fx.Mul(t.Pz - c.Pz, k);
            c.Lx += Fx.Mul(t.Lx - c.Lx, k); c.Ly += Fx.Mul(t.Ly - c.Ly, k); c.Lz += Fx.Mul(t.Lz - c.Lz, k);
            c.Fov += Fx.Mul(t.Fov - c.Fov, k);
        }
    }
}
