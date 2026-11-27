# claude-video-vision（video-perception 技能）

来源：jordanrendric/claude-video-vision。这里只放技能正文 `SKILL.md` 与本项目自行维护的补丁脚本，
MCP 服务本体装在本机用户目录，不进仓库（87 MB 的 node_modules）。

## 依赖（用户级，换机器要重装）

- MCP 服务：`C:\Users\OVO\.dsh\mcp\claude-video-vision`（`npm install claude-video-vision@latest`）
- 插件配置行：`C:\Users\OVO\.dsh\profiles\desktop\cordis.patch.yml` 的 insert 段 `mcp-claude-video-vision`
- 运行时配置：`C:\Users\OVO\.claude-video-vision\config.json`
  （当前 `backend=local`、`whisper_engine=python`、`whisper_model=small`、`frame_resolution=512`、`max_frames=60`）
- 音频转录：openai-whisper 的 Python CLI（`D:\TmpProject\miniconda3\Scripts\whisper.exe`），
  模型缓存在 `C:\Users\OVO\.cache\whisper\small.pt`（340 MB）。
- 视频抽帧：ffmpeg / ffprobe 在 PATH 上。

## 补丁

`node patch-local-whisper-json.mjs` —— 让 Python whisper 后端读取 CLI 落盘的 JSON
而不是被逐段日志污染的 stdout。幂等；`npm install` 覆盖 `dist/` 后需重跑一次。
判断是否已打过：在包内搜 `LOCALPATCH:read-json`。
