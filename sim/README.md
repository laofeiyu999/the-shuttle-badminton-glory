# sim/ 弹道仿真（M1）

技术路线（U45）：C# 写确定性核心（与 Unity 正式版共用），Three.js 只做画面呈现，后续人物 GLB 模型也接在 Three.js 查看器里。

## 目录
- config/core.json、actions.json —— 游戏同款外置配置（设计文档第 16 章）；scenarios.json —— 仿真专用代表站位。
- src/Shuttle.Core —— netstandard2.1 纯整数核心：Fx（Q16）、Pcg32、Config、Tables、Trajectory（第 6.3–6.6 节六参数弹道、质量项、抵消、落点、撞网）。
- src/Shuttle.Sim —— 命令行：配置加载与查表生成、批量组合、自动检查、测试锚点。
- out/ —— trajectories.csv（324 地面 + 90 起跳）、trajectories.json（查看器数据）、checks.txt。
- viewer/ —— Three.js 查看器：实战 / 自由 360° / 侧视 / 俯视 / 接球方，逐 tick 播放。

## 用法
```
cd sim
dotnet run --project src/Shuttle.Sim -c Release -- test    # 测试锚点
dotnet run --project src/Shuttle.Sim -c Release -- batch   # 生成 out/
cd viewer && npm install && npm start                      # http://127.0.0.1:5180
```

## 现状
- 测试 50 项全过（T6.1 时长、T5.7-7 抵消、T6.6-1/2 撞网阈值、白档不撞网、确定性、终点=落点）；批量 414 条自动检查 0 问题。
- 实战视角暂用 10.7.2 主机位初值的 JS 占位，下一步改为 C# Camera.rigParams 输出、查看器只读。
- actions.json 中 placeholder=true 的动作（拨腰、挡网、推球、平抽、推挑）白档顶点为占位值，待拍板。
