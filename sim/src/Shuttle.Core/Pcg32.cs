namespace Shuttle.Core
{
    /// <summary>PCG32（XSH RR）。ball / ai / fx 三路独立流，显式种子。</summary>
    public sealed class Pcg32
    {
        ulong _state, _inc;
        public Pcg32(ulong seed, ulong stream)
        {
            _state = 0; _inc = (stream << 1) | 1UL;
            Next(); _state += seed; Next();
        }
        public uint Next()
        {
            ulong old = _state;
            _state = unchecked(old * 6364136223846793005UL + _inc);
            uint xs = (uint)(((old >> 18) ^ old) >> 27);
            int rot = (int)(old >> 59);
            return (xs >> rot) | (xs << ((-rot) & 31));
        }
        /// <summary>取 8 位，得到 fRand 的 256 档索引。</summary>
        public int Next8() { return (int)(Next() >> 24); }
    }
}
