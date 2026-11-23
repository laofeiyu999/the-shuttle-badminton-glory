using System.Collections.Generic;
namespace Shuttle.Core
{
    public sealed class ShotRequest
    {
        public ActionDef Action; public int Tier; public Quality Quality; public int BadUQ;
        public int Lane;        // -1 左, 0 中, +1 右（相对击球方面向对方场地）
        public int P0X, P0Z, H0; // 击球点 cm；击球方在 Z<0 半场
        public int OffsetRQ;    // 快球蓄力抵消 R（Q16），只作用于糟糕
        public int RandX, RandZ; // fRand 8 位索引
        public int ConsecutiveBad = 1;
    }

    public sealed class ShotResult
    {
        public int N; public int Gather; public int QualityTermQ; public int ApexTarget; public int ApexActual;
        public int NetPlaneAnalytic; public int NetPlaneInterp; public bool NetHit; public int NetTick = -1;
        public int LandX, LandZ; public bool Clamped; public bool DownPress; public int BQ;
        public int[] Xs, Ys, Zs; // 逐 tick，0..N（撞网时截至过网 tick）
        public List<string> Notes = new List<string>();
    }

    /// <summary>六参数弹道生成（设计文档第 6.3–6.6 节）。纯整数、确定性。</summary>
    public static class Trajectory
    {
        public static ShotResult Generate(CoreConfig c, ShotRequest q)
        {
            var a = q.Action; var tier = c.Tiers[q.Tier]; var res = new ShotResult();
            // ---- 质量项与抵消（5.5、5.7） ----
            int qTerm, apexDelta = 0, gather = tier.Gather;
            if (q.Quality == Quality.Perfect) qTerm = c.PerfectQ;
            else if (q.Quality == Quality.Stride) { qTerm = c.StrideQ; gather = System.Math.Max(0, gather - c.StrideGatherDrop); }
            else
            {
                qTerm = c.BadBaseQ + Fx.Mul(c.BadSpanQ, q.BadUQ);
                apexDelta = c.BadApexBase + Fx.Mul(c.BadApexSpan, q.BadUQ);
                int decay = Fx.One; for (int i = 1; i < q.ConsecutiveBad && decay > Fx.One / 4; i++) decay >>= 1;
                if (decay < Fx.One / 4) decay = Fx.One / 4;
                apexDelta = Fx.Mul(apexDelta, decay);
                gather = 0;
                int keep = Fx.One - q.OffsetRQ;
                qTerm = System.Math.Max(Fx.One, Fx.One + Fx.Mul(qTerm - Fx.One, keep));
                apexDelta = Fx.Mul(apexDelta, keep);
            }
            res.QualityTermQ = qTerm; res.Gather = gather;
            // ---- 时长（6.3.4）：基础 × durationMul × q'，最后一步四舍五入 ----
            long num = (long)a.BaseTicks * tier.DurationMulQ * qTerm;
            int n = (int)((num + (1L << 31)) >> 32);
            if (n < c.MinDurationTicks) n = c.MinDurationTicks;
            res.N = n;
            // ---- 落点（6.5） ----
            int[] dg = c.DepthGroups[a.DepthGroup];
            int lz = DropAxis(c, dg[0], dg[1], gather, q.RandZ);
            int lx;
            if (q.Lane == 0)
            {
                int bad = (q.RandX >= 128 ? 1 : -1) * c.MidLaneBad;
                lx = DropAxis(c, bad, 0, gather, q.RandX);
            }
            else lx = DropAxis(c, 0, q.Lane * c.SinglesHalfWidth, gather, q.RandX);
            if (q.Quality == Quality.Bad)
            {
                int lim = c.BadLateral;
                if (q.OffsetRQ > 0)
                {   // 有抵消：在糟糕落点与同族同档跨步落点之间按 R 插值
                    int sg = System.Math.Max(0, tier.Gather - c.StrideGatherDrop);
                    int sz = DropAxis(c, dg[0], dg[1], sg, q.RandZ);
                    int sx = q.Lane == 0 ? DropAxis(c, (q.RandX >= 128 ? 1 : -1) * c.MidLaneBad, 0, sg, q.RandX)
                                         : DropAxis(c, 0, q.Lane * c.SinglesHalfWidth, sg, q.RandX);
                    lx = Fx.Clamp(lx, -lim, lim);
                    lx = Fx.Lerp(lx, sx, q.OffsetRQ); lz = Fx.Lerp(lz, sz, q.OffsetRQ);
                }
                else lx = Fx.Clamp(lx, -lim, lim);
            }
            int cx = Fx.Clamp(lx, -c.SinglesHalfWidth, c.SinglesHalfWidth), cz = Fx.Clamp(lz, 1, c.HalfLength);
            res.Clamped = cx != lx || cz != lz; res.LandX = cx; res.LandZ = cz;
            // ---- 网平面参数 tn（6.3.2） ----
            long dz = (long)cz - q.P0Z;
            int fQ = Fx.Div(-q.P0Z, dz);
            int tn = Tables.InvEase(c, fQ);
            int minClear = c.NetHeight + c.WhiteClearMargin;
            int lift = a.Family == Family.Drop ? c.NetLiftDrop[q.Tier] : (a.Family == Family.Flat ? c.NetLiftFlat[q.Tier] : 0);
            bool geometric = q.Tier > 0 && a.Family != Family.High;
            bool guarantee = q.Tier == 0 || a.Family == Family.High;
            int h0 = q.H0;
            res.Xs = new int[n + 1]; res.Ys = new int[n + 1]; res.Zs = new int[n + 1];
            for (int i = 0; i <= n; i++)
            {
                int s = Tables.Ease(c, Fx.Div(i, n));
                res.Xs[i] = q.P0X + Fx.Mul(cx - q.P0X, s);
                res.Zs[i] = q.P0Z + (int)(((long)(cz - q.P0Z) * s + 32768) >> 16);
            }
            int yn;
            if (a.Kill && h0 >= c.NetHeight)
            {   // ---- 下压型：y = h0(1 − b t − (1 − b) t²) ----
                res.DownPress = true;
                int hn = c.NetHeight + Fx.Mul(a.HnWhite - c.NetHeight, tier.ApexMulQ) + apexDelta;
                if (guarantee && hn < minClear) hn = minClear;
                if (geometric && hn > h0 + lift) hn = h0 + lift;
                int tn2 = Fx.Mul(tn, tn);
                long numer = Fx.One - Fx.Div(hn, h0) - tn2;
                long den = tn - tn2;
                int b = den == 0 ? 0 : (int)(numer * Fx.One / den);
                if (b > c.BMaxQ) { b = c.BMaxQ; res.Notes.Add("b 触上限 2.0"); }
                res.BQ = b; res.ApexTarget = h0;
                for (int i = 0; i <= n; i++) res.Ys[i] = YDown(h0, b, Fx.Div(i, n));
                yn = YDown(h0, b, tn);
            }
            else
            {   // ---- 上升型：分段二次（前段 round(N×ρ) tick） ----
                int rho = a.Family == Family.Drop ? c.RhoDropQ : (a.Family == Family.High ? c.RhoHighQ : c.RhoFlatQ);
                int nf = Fx.Round((long)n * rho); if (nf < 1) nf = 1; if (nf >= n) nf = n - 1;
                int H = h0 + Fx.Mul(a.ApexWhite - h0, tier.ApexMulQ) + apexDelta;
                if (H < h0 && h0 < c.NetHeight) H = h0; // 低点回球：必须上扬
                long tnTicksQ = (long)tn * n;           // Q16 tick
                // 网平面高度对 H 线性：yn = k0 + k1·H
                int k0, k1;
                if (tnTicksQ <= (long)nf << 16)
                {
                    int u = (int)(tnTicksQ / nf);       // Q16
                    int w = Fx.One - u; int aQ = Fx.One - Fx.Mul(w, w);
                    k1 = aQ; k0 = Fx.Mul(h0, Fx.One - aQ);
                }
                else
                {
                    int u = (int)((tnTicksQ - ((long)nf << 16)) / (n - nf));
                    k1 = Fx.One - Fx.Mul(u, u); k0 = 0;
                }
                int ynH = k0 + Fx.Mul(H, k1);
                if (guarantee && ynH < minClear && k1 > 0) { H = (int)(((long)(minClear - k0) * Fx.One + k1 - 1) / k1); res.Notes.Add("白档/高弧过网保证抬高顶点"); }
                bool capped = false;
                if (geometric && ynH > h0 + lift && k1 > 0) { H = (int)(((long)(h0 + lift - k0) * Fx.One + k1 / 2) / k1); capped = true; res.Notes.Add("蓄力档网平面高度压到 触点+netLift"); }
                res.ApexTarget = H;
                for (int i = 0; i <= n; i++)
                {
                    long y;
                    if (i <= nf) { int u = Fx.Div(i, nf); int w = Fx.One - u; y = h0 + Fx.Mul(H - h0, Fx.One - Fx.Mul(w, w)); }
                    else { int u = Fx.Div(i - nf, n - nf); y = Fx.Mul(H, Fx.One - Fx.Mul(u, u)); }
                    res.Ys[i] = (int)y;
                }
                yn = capped ? h0 + lift : k0 + Fx.Mul(H, k1);
            }
            res.NetPlaneAnalytic = yn;
            // ---- 网平面插值高度与撞网（6.6） ----
            for (int i = 1; i <= n; i++)
            {
                if (res.Zs[i - 1] < 0 && res.Zs[i] >= 0)
                {
                    long dzz = res.Zs[i] - res.Zs[i - 1];
                    int f = dzz == 0 ? 0 : Fx.Div(-res.Zs[i - 1], dzz);
                    res.NetPlaneInterp = res.Ys[i - 1] + Fx.Mul(res.Ys[i] - res.Ys[i - 1], f);
                    res.NetTick = i; break;
                }
            }
            res.NetHit = geometric && yn <= c.NetHeight;
            if (res.NetHit)
            {
                int m = res.NetTick < 0 ? n : res.NetTick;
                System.Array.Resize(ref res.Xs, m + 1); System.Array.Resize(ref res.Ys, m + 1); System.Array.Resize(ref res.Zs, m + 1);
            }
            int mx = 0; foreach (var y in res.Ys) if (y > mx) mx = y; res.ApexActual = mx;
            return res;
        }

        static int YDown(int h0, int bQ, int tQ)
        {
            int t2 = Fx.Mul(tQ, tQ);
            int f = Fx.One - Fx.Mul(bQ, tQ) - Fx.Mul(Fx.One - bQ, t2);
            return Fx.Mul(h0, f);
        }

        /// <summary>落点单轴：fBad + (fGood − fBad) × fRand^((100−Gather)/100)。</summary>
        public static int DropAxis(CoreConfig c, int fBad, int fGood, int gather, int r8)
        {
            return fBad + Fx.Mul(fGood - fBad, Tables.Pow(c, gather, r8));
        }

        /// <summary>接球方理论最大可蓄 tick（6.1 表口径：N − 地面命中帧偏移，上限 72）。</summary>
        public static int ReceiverMaxCharge(CoreConfig c, int n) { int v = n - c.HitFrameOffsetGround; return v < 0 ? 0 : (v > c.MaxChargeTicks ? c.MaxChargeTicks : v); }
    }
}
