namespace Shuttle.Core
{
    /// <summary>查表：水平缓动 s(t) 与落点幂表。表本身是配置数据（离线生成），运行时不算浮点。</summary>
    public static class Tables
    {
        public static int Ease(CoreConfig c, int tQ)
        {
            if (tQ <= 0) return 0;
            if (tQ >= Fx.One) return Fx.One;
            int n = c.EaseQ16.Length - 1;               // 1024
            long pos = (long)tQ * n;                    // Q16 * n
            int idx = (int)(pos >> 16);
            int frac = (int)(pos & 0xFFFF);
            int a = c.EaseQ16[idx], b = c.EaseQ16[idx + 1];
            return a + Fx.Mul(b - a, frac);
        }
        /// <summary>逆缓动：求最小 t 使 s(t) ≥ f（二分，整数）。</summary>
        public static int InvEase(CoreConfig c, int fQ)
        {
            if (fQ <= 0) return 0;
            if (fQ >= Fx.One) return Fx.One;
            int lo = 0, hi = Fx.One;
            while (lo < hi) { int mid = (lo + hi) >> 1; if (Ease(c, mid) >= fQ) hi = mid; else lo = mid + 1; }
            return lo;
        }
        public static int Pow(CoreConfig c, int gather, int r8) { return c.PowQ16[Fx.Clamp(gather, 0, 100)][r8 & 255]; }
    }
}
