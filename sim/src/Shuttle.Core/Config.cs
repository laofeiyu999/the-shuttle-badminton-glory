using System.Collections.Generic;
namespace Shuttle.Core
{
    public enum Family { Drop = 0, Flat = 1, High = 2 }
    public enum Quality { Perfect = 0, Stride = 1, Bad = 2 }

    public sealed class TierDef
    {
        public string Name; public int FromTick; public int DurationMulQ; public int Gather; public int ApexMulQ; public int RecoveryExtra;
    }

    public sealed class ActionDef
    {
        public string Id, Name; public Family Family; public int BaseTicks;
        public int ApexWhite;   // 上升型白档顶点 cm
        public int HnWhite;     // 下压型（杀类）白档网平面高度 cm
        public bool Kill; public string DepthGroup; public bool Placeholder;
    }

    /// <summary>核心配置（第 16 章）。全部为整数：cm、tick、Q16。由外部加载器填充，核心不解析文件。</summary>
    public sealed class CoreConfig
    {
        public int SinglesHalfWidth = 260, HalfLength = 670;
        public int NetHeight = 150, WhiteClearMargin = 8;
        public TierDef[] Tiers;
        public int HitFrameOffsetGround = 6, HitFrameOffsetJump = 12, MaxChargeTicks = 72;
        public int RhoDropQ, RhoHighQ, RhoFlatQ, BMaxQ, MinDurationTicks = 21;
        public int PerfectQ, StrideQ, StrideGatherDrop, BadBaseQ, BadSpanQ, BadApexBase, BadApexSpan, BadLateral;
        public int[] NetLiftDrop, NetLiftFlat;
        public int MidLaneBad = 80;
        public Dictionary<string, int[]> DepthGroups; // [fBad, fGood] 距网 cm
        public int OffsetKQ, OffsetKmQ;
        public int[] EaseQ16;     // 1025 项 s(t)
        public int[][] PowQ16;    // [gather 0..100][fRand 0..255]
        public Dictionary<string, ActionDef> Actions;
    }
}
