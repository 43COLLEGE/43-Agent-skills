---
name: rendering
description: Remotion 渲染、预览、调试命令大全
metadata:
  tags: render, still, studio, preview, debug, cli, gl, codec
---

# 渲染与预览

## 三个核心命令

### 预览（开发调试）

```bash
npx remotion studio
```

启动本地预览服务器，浏览器中实时调试动画和布局。

### 渲染静帧（快速验证）

```bash
npx remotion still src/index.ts MyComp output.png --frame=30
```

渲染单帧图片，适合快速验证布局、字幕位置、颜色等视觉效果。比渲染完整视频快 100 倍。

**调试技巧**：渲染多个关键帧快速检查全片效果：

```bash
# 开头、中间、结尾各一帧
npx remotion still src/index.ts MyComp frame-start.png --frame=0
npx remotion still src/index.ts MyComp frame-mid.png --frame=150
npx remotion still src/index.ts MyComp frame-end.png --frame=299
```

### 渲染视频（最终输出）

```bash
npx remotion render src/index.ts MyComp out/video.mp4
```

## 常用参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--gl=angle` | GPU 渲染后端，**3D 场景必须加** | `--gl=angle` |
| `--codec` | 编码格式 | `--codec=h264`（默认）、`--codec=vp8` |
| `--crf` | 画质（越低越清晰，默认 18） | `--crf=10` |
| `--scale` | 缩放倍数 | `--scale=0.5`（半尺寸，加速调试） |
| `--frames` | 只渲染指定帧范围 | `--frames=0-60`（只渲第一秒） |
| `--concurrency` | 并行渲染线程数 | `--concurrency=4` |
| `--log` | 日志级别 | `--log=verbose` |
| `--props` | 传入 JSON 属性 | `--props='{"title":"Hi"}'` |

## 3D 渲染注意事项

使用 Three.js / React Three Fiber 时，渲染和静帧命令都必须加 `--gl=angle`：

```bash
npx remotion render --gl=angle src/index.ts MyComp out/video.mp4
npx remotion still --gl=angle src/index.ts MyComp test.png
```

不加会报 WebGL context 创建失败，输出白屏或黑屏。

## 输出格式

| 格式 | 编码 | 适用场景 |
|------|------|---------|
| `.mp4` | H.264 | 通用，兼容性最好 |
| `.webm` | VP8/VP9 | 网页嵌入，支持透明视频 |
| `.gif` | GIF | 简短循环动画 |
| `.png` 序列 | PNG | 后期合成 |

```bash
# 透明背景视频
npx remotion render src/index.ts MyComp out/transparent.webm --codec=vp8

# GIF
npx remotion render src/index.ts MyComp out/animation.gif
```
