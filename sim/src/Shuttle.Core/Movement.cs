namespace Shuttle.Core
{
    public sealed class MoveConfig { public int Forward = 380, Side = 380, Back = 310, ReactionTicks = 15, StopRadius = 25; }

    /// <summary>移动（5.8 节）：前/侧/后速度按椭圆合成，无加速度。单位 cm，结果整数。</summary>
    public static class Movement
    {
        public static long ISqrt(long v) { if (v <= 0) return 0; long r = (long)System.Math.Sqrt(v); while (r * r > v) r--; while ((r + 1) * (r + 1) <= v) r++; return r; }

        /// <summary>朝 (tx,tz) 走一 tick。facingSign：+1 表示面向 +Z（后退 = −Z），−1 表示面向 −Z。返回是否已到达。</summary>
        public static bool StepToward(MoveConfig m, ref int x, ref int z, int tx, int tz, int facingSign, int speedMulQ)
        {
            long dx = tx - x, dz = tz - z; long dist = ISqrt(dx * dx + dz * dz);
            if (dist <= m.StopRadius) return true;
            bool backward = dz * facingSign < 0;
            long a = m.Side, b = backward ? m.Back : m.Forward; // 椭圆半轴
            // v = a·b / sqrt((b·dx)² + (a·dz)²) × dist
            long den = ISqrt(b * b * dx * dx + a * a * dz * dz);
            long v = den == 0 ? a : a * b * dist / den;       // cm/s
            v = (v * speedMulQ) >> 16;
            long step = (v * 65536 / 60);                      // Q16 cm/tick
            long remain = (dist - m.StopRadius) << 16;
            if (step > remain) step = remain;
            x += (int)((dx * step / dist + 32768) >> 16);
            z += (int)((dz * step / dist + 32768) >> 16);
            return false;
        }
    }
}
