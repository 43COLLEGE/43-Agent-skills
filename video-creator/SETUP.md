---
name: video-creator-setup
description: Remotion 视频项目的首次环境检查与配置
---

# 首次使用检查清单

在开始 Remotion 项目前，按顺序检查以下环境依赖。

## 1. 基础环境

```bash
# Node.js >= 18
node -v

# npm（随 Node.js 安装）
npm -v

# ffmpeg（音视频处理必需）
ffmpeg -version
```

如果缺少 ffmpeg：
- macOS: `brew install ffmpeg`
- Windows: `choco install ffmpeg` 或 `winget install ffmpeg`
- Linux: `sudo apt install ffmpeg`

## 2. 创建项目

```bash
npx create-video@latest my-video
cd my-video
```

创建后确认以下文件存在且正确：
- `src/index.ts` — 必须包含 `registerRoot(RemotionRoot)`
- `src/Root.tsx` — 导出 `RemotionRoot` 组件，包含 `<Composition>`
- `package.json` — `"type"` 字段应为 `"module"`（ES Module 项目）

## 3. 3D 渲染（使用 Three.js 时）

3D 内容在 headless Chrome 中渲染，需要 GPU 加速：

```bash
# 渲染时必须加 --gl=angle
npx remotion render --gl=angle src/index.ts MyComp out/video.mp4

# 预览不需要，正常启动即可
npx remotion studio
```

如不加 `--gl=angle`，3D 场景会白屏或报 WebGL context 错误。

## 4. 可选：外部服务凭证

某些功能需要第三方 API，在使用前引导用户配置：

| 功能 | 环境变量 | 用途 |
|------|---------|------|
| AI 配音 | `ELEVENLABS_API_KEY` | ElevenLabs TTS 语音合成 |
| 地图 | `MAPBOX_ACCESS_TOKEN` | Mapbox 地图渲染 |

配置方式（任选其一）：
```bash
# 方式一：写入 .env 文件（推荐，记得加入 .gitignore）
echo "ELEVENLABS_API_KEY=your-key-here" >> .env

# 方式二：运行时传入
ELEVENLABS_API_KEY=your-key node --strip-types generate-voiceover.ts
```

**重要**：如果用户未提供 API key，不要猜测或硬编码。明确告知需要哪个 key、去哪里申请、怎么配置。

## 5. 验证环境

```bash
# 启动预览，确认项目能正常运行
npx remotion studio

# 渲染一帧测试
npx remotion still src/index.ts MyComp test.png
```
