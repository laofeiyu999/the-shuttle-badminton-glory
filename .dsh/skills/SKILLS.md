# The Shuttle - Badminton Glory（荣耀羽毛球竞技）项目技能清单（project skills）

本目录是项目级技能根（DSH 发现顺序 rank 100，高于用户级 `~/.dsh/skills` 的 rank 400）。
技能来源均为公开仓库，逐个核对过 `SKILL.md` 正文，不是只看名字。

## 已随仓库提交的技能

| 技能 | 来源 | 本项目用途 |
|---|---|---|
| `threejs-game-ui-designer` | majidmanzarpour/threejs-game-skills | 仿真系统的 Three.js 场景、HUD、播控与响应式 |
| `game-engine` | github/awesome-copilot | WebGL 游戏循环、相机、输入、渲染组织 |
| `game-ui-ux` | gamedev-skills/awesome-gamedev-agent-skills | 控制台信息层级、输入与状态流、HUD 更新方式 |
| `game-ui-design` | omer-metin/skills-for-antigravity | 界面视觉语言与可读性 |
| `game-feel` | gamedev-skills/awesome-gamedev-agent-skills | 拖尾、落点提示、命中与死球反馈 |
| `game-design-theory` | pluginagentmarketplace/custom-plugin-game-developer | 数值与循环设计的推演（体力/意志/觉醒/难度曲线） |
| `game-studio` | openai/plugins | 浏览器游戏打法路由（three-webgl-game / game-ui-frontend） |
| `brainstorming` | obra/superpowers | 新系统开工前的需求收敛 |
| `planning-with-files` | OthmanAdi/planning-with-files | 多步交付落盘 task_plan / findings / progress |
| `karpathy-guidelines` | multica-ai/andrej-karpathy-skills | 防过度设计，界定可验证的成功标准 |
| `diagram-design` | cathrynlavery/diagram-design | 架构图、回放时序、状态机图 |
| `unity-skills` | Besty0728/Unity-Skills | Unity 编辑器自动化（84 模块：animator/ui/profiler/urp/test…），正式开发阶段用 |
| `gamedev-agent-skills` | gamedev-skills/awesome-gamedev-agent-skills | 引擎无关手法 + skills/unity/ 专章（需 Unity 工程后启用） |
| `game-developer` | jeffallan/claude-skills | Unity/引擎实现模式速查 |
| `blender-skills` | arjun988/blender-skills | 3D 资产与动画管线（附录 A 相关），自制资产时用 |
| `higgsfield-game-generation` | higgsfield-ai/skills | 浏览器游戏与素材生成（需 Higgsfield CLI） |
| `understand-anything` | Donchitos/understand-anything-plugin | 代码库知识图谱与可浏览看板；后续 Unity/C# 工程与 sim 代码的架构梳理 |
| `watch`（目录 `claude-video-watch`） | bradautomates/claude-video | 看参考视频：yt-dlp 下载 + ffmpeg 抽帧 + 字幕/本地转录，读帧后回答画面问题 |
| `video-perception`（目录 `claude-video-vision`） | jordanrendric/claude-video-vision | 结构化看片：video_info → video_analyze（场景/静音/运动）→ video_watch 抽帧 → video_detail 钻取；需配套 MCP 服务 |

## 未复制、但全局可用的内置技能

`test-driven-development`、`webapp-testing`、`agent-browser`、`office-docx`、`office-xlsx`、`writing-plans`、`executing-plans`、`screenshot`、`ffmpeg-skills` 等属于 DSH 内置技能（rank 600），已随运行环境提供，不需要也不应该复制进仓库。

## 已知前置条件

- `unity-skills`：需要 Unity 2022.3+/6000.x 且项目安装 UnitySkills 包（本地 REST 服务 localhost:8090–8100）、Python 3。当前仓库无 Unity 工程，暂为“已装待用”。
- `gamedev-agent-skills`：`skills/unity/` 章节按 Unity 语义编写，无工程时只作知识参考。
- `blender-skills`：咨询型技能包（references/*.md），不驱动 Blender 进程。
- `higgsfield-game-generation`：需要 Higgsfield CLI 与账号授权。
- `understand-anything`：已排除 `node_modules/`（496 MB，可重建），首次使用需在该目录执行 `pnpm install && pnpm --filter @understand-anything/core build`。
- `watch`：需要 `ffmpeg`/`ffprobe`/`yt-dlp` 在 PATH 上（本项目本机已装 ffmpeg 8.1.2 与 yt-dlp 2026.11.23），配置写在 `C:\Users\OVO\.config\watch\.env`；当前为 `engine=local`、`backend=none`（不转录）、`detail=balanced`。调用 `scripts/watch.py` 时必须传**绝对路径**，相对路径会被解析到技能目录下而报找不到文件。要开转录就把 backend 换成 whisperx/groq/openai。
- `video-perception`：依赖用户级 MCP 服务 `claude-video-vision`（`@deepseek-ai/dsh-mcp-client` 插件，配置在 `C:\Users\OVO\.dsh\profiles\desktop\cordis.patch.yml` 的 insert 段，命令 `D:\nodejs\node.exe` 跑 `C:\Users\OVO\.dsh\mcp\claude-video-vision\node_modules\claude-video-vision\dist\index.js`，超时 600000 ms）。该服务是**用户级**安装，不在本仓库里；换机器需重新 `npm install claude-video-vision@latest` 并加配置行。配置持久化在 `C:\Users\OVO\.claude-video-vision\config.json`，当前 `backend=local`、`whisper_engine=python`、`whisper_model=small`、`frame_mode=images`、`frame_resolution=512`、`max_frames=60`。
- `video-perception` 的音频链路：走 openai-whisper 的 Python CLI（`D:\TmpProject\miniconda3\Scripts\whisper.exe`，模型缓存在 `C:\Users\OVO\.cache\whisper\small.pt`，340 MB）。whisper.cpp 的 `whisper-cli` 官方无 Windows 预编译包，不要走 cpp 引擎。另有一处**本地补丁**：`dist/backends/local.js` 里 `transcribeWithWhisperPython` 原本只读 stdout，而 openai-whisper 把逐段结果打到 stdout、把真正的 JSON 写到 `<outputDir>/<basename>.json`，导致转录文本带乱码进不了分段；已改为优先读该 JSON 文件（代码里搜 `LOCALPATCH:read-json`）。升级该 npm 包会覆盖掉，升级后需重打。

## 明确排除

- `multiplayer-game`：正文要求先读 `BASE_SKILL.md`，且明确只适用于 **RivetKit** 平台，与本项目自研服务端冲突，不安装。
- `ponytail`：2026-11-05 已删除（项目级与用户级 `~/.dsh/skills` 两处都删）。该技能主张“最小改动优先、能省就省”，会压缩输出与推演长度，与本项目“设计文档要写全、数值要推演到位、口径要逐条对齐”的要求相反，容易导致理解偏差和遗漏。删除后无功能依赖，摘除不影响任何既有流程。

维护说明：升级技能时替换对应目录并同步更新本表；项目专属约定写在 `the-shuttle-project` 技能里，不直接改第三方 `SKILL.md`。
