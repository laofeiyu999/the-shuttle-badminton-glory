namespace Shuttle.Core
{
    /// <summary>Q16 定点工具。One = 65536 表示 1.0。只用整数运算。</summary>
    public static class Fx
    {
        public const int One = 65536;
        public static int Mul(int a, int b) { return (int)(((long)a * b + 32768) >> 16); }
        public static int Div(long num, long den)
        {
            long q = num * One;
            if ((q >= 0) == (den > 0)) return (int)((q + den / 2) / den);
            return (int)((q - den / 2) / den);
        }
        /// <summary>Q16 值四舍五入到整数（半数向上）。</summary>
        public static int Round(long q16) { return (int)((q16 + 32768) >> 16); }
        public static int Clamp(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }
        public static int Lerp(int a, int b, int tQ) { return a + Mul(b - a, tQ); }
    }
}
