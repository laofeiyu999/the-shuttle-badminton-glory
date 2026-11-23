# sim/ 弹道仿真（M1）

技术路线（U45）：C# 写确定性核心（与 Unity 正式版共用），Three.js 只做画面呈现，后续人物 GLB 模型也接在 Three.js 查看器里。

## 目录
- config/core.json、actions.json —— 游戏同款外置配置（设计文档第 16 章）；scenarios.json —— 仿真专用代表站位。
- src/Shuttle.Core —— netstandard2.1 纯整数核心：Fx（Q16）、Pcg32、Config、Tables、Trajectory（第 6.3–6.6 节六参数弹道、质量项、抵消、落点、撞网）。
- src/Shuttle.Sim —— 命令行：配置加载与查表生成、批量组合、自动检查、测试锚点。
- out/ —— trajectories.csv（324 地面 + 90 起跳）、trajectories.json（查看器数据）、checks.txt。
- viewer/ —— Three.js 查看器（M1.5 美化版）：按手绘界面图排布的实战 HUD（计分板+状态提示、时间/网络/设置、摇杆、三击球键＋四档蓄力环、觉醒键＋剩余时间环、体力/意志条）、羽毛球外形球、火柴人、脚下旋转光圈、质量拖尾（杀类三光带+火花）、时机泡泡两阶段、落点标记三圈与落地水波、球出屏指示器、灰色网格空间背景；视角 实战 / 360° 自由 / 侧视 / 俯视 / 接球方。
- src/Shuttle.Core/CameraRig.cs —— 实战视角机位（10.7.2），按片区插值，参数在 core.json camera，按飞羽四张片区截图投影拟合；Movement.cs —— 椭圆合成移速。
- src/Shuttle.Sim/Scene.cs —— 每条弹道展开成逐 tick 场景时间轴（来球示意段、蓄力、出球、落地后），机位每 tick 由 CameraRig 计算。

## 用法
```
cd sim
dotnet run --project src/Shuttle.Sim -c Release -- test    # 测试锚点
dotnet run --project src/Shuttle.Sim -c Release -- batch   # 生成 out/
cd viewer && npm install && npm start                      # http://127.0.0.1:5180
# URL 参数：?zone=中场&tier=红&qual=完美&group=起跳&i=0&t=90&view=free&panel=0&awake=1
```

## 现状
- 测试 50 项全过（T6.1 时长、T5.7-7 抵消、T6.6-1/2 撞网阈值、白档不撞网、确定性、终点=落点）；批量 414 条自动检查 0 问题。
- 实战视角机位已由 C# CameraRig 逐 tick 输出，查看器只读。来球段与对手跑位仍是示意（对手不回球），M2 接入完整回合。
- actions.json 中 placeholder=true 的动作（拨腰、挡网、推球、平抽、推挑）白档顶点为占位值，待拍板。
