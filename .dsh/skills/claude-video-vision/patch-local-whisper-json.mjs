#!/usr/bin/env node
/**
 * 修复 claude-video-vision 的本地 whisper 音频链路（幂等，可重复运行）。
 *
 * 问题：dist/backends/local.js 的 transcribeWithWhisperPython 只解析 CLI 的
 * stdout；而 openai-whisper 的 Python CLI 默认 verbose，把逐段进度打到 stdout
 * （非 JSON、中文按系统编码输出成乱码），真正的 JSON 写在
 * <output_dir>/<basename>.json 里。结果 MCP 返回的 transcription 只有一整段乱码。
 *
 * 修复：优先读那个 JSON 文件再交给 parseWhisperOutput，读完照旧删除临时文件。
 *
 * 用法：node patch-local-whisper-json.mjs [claude-video-vision 包目录]
 *   默认包目录：C:/Users/OVO/.dsh/mcp/claude-video-vision/node_modules/claude-video-vision
 * npm 升级覆盖 dist/ 后需要重跑一次。
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const pkgDir = process.argv[2] || "C:/Users/OVO/.dsh/mcp/claude-video-vision/node_modules/claude-video-vision";
const file = join(pkgDir, "dist/backends/local.js");

if (!existsSync(file)) {
  console.error("找不到 " + file + "，请先 npm install claude-video-vision");
  process.exit(1);
}

let s = readFileSync(file, "utf8");
if (s.includes("LOCALPATCH:read-json")) {
  console.log("已打过补丁，跳过。");
  process.exit(0);
}

const oldBlock = `    // Best-effort cleanup of the on-disk JSON; we already have what we
    // need on stdout via parseWhisperOutput. The CLI derives the output
    // filename from the input wav, so derive it the same way.
    try {
        const jsonName = basename(wavPath, ".wav") + ".json";
        rmSync(join(outputDir, jsonName), { force: true });
    }
    catch { /* ignore */ }
    return parseWhisperOutput(stdout);`;

const newBlock = `    // LOCALPATCH:read-json — openai-whisper prints human-readable segments to
    // stdout (verbose default True) and writes the real JSON to
    // <outputDir>/<basename>.json, so stdout is not parseable. Prefer the file.
    const jsonPath = join(outputDir, basename(wavPath, ".wav") + ".json");
    let payload = stdout;
    try {
        if (existsSync(jsonPath)) {
            payload = readFileSync(jsonPath, "utf8");
        }
    }
    catch { /* fall back to stdout */ }
    // Best-effort cleanup of the on-disk JSON.
    try {
        rmSync(jsonPath, { force: true });
    }
    catch { /* ignore */ }
    return parseWhisperOutput(payload);`;

if (!s.includes(oldBlock)) {
  console.error("未找到待替换代码块，上游可能已改动，请人工核对 " + file);
  process.exit(2);
}

s = s.replace(oldBlock, newBlock);
writeFileSync(file, s, "utf8");
console.log("已打补丁：" + file);
