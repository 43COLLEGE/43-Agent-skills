# media-transcriber

使用 OpenAI Whisper 将视频/音频文件转为带时间戳的逐字稿。

---

## 能力

| 能力 | 说明 |
|------|------|
| 语音转文字 | 支持 14 种音视频格式，中/英/日多语言 |
| 说话人识别 | 基于 pyannote，自动区分谁在说话 |
| 标点恢复 | 调用 Claude Haiku 为原始转录补充准确标点 |
| 批量处理 | 整个文件夹一次性转录，模型只加载一次 |
| 自动环境管理 | 首次运行自动创建 venv、安装依赖、下载模型 |

## 安装

**方式一：让 Claude 自动安装**

```
帮我安装这个 skill：https://github.com/43COLLEGE/43-Agent-skills（media-transcriber 目录）
```

**方式二：手动**

```bash
git clone https://github.com/43COLLEGE/43-Agent-skills /tmp/43-skills
cp -r /tmp/43-skills/media-transcriber ~/.claude/skills/media-transcriber
rm -rf /tmp/43-skills
```

## 前置条件

- **ffmpeg**：处理音视频的基础工具（必须）
- **HuggingFace Token**：说话人识别功能需要（可选）
- **ANTHROPIC_API_KEY**：标点恢复功能需要（Claude Code 用户通常已有）

详细配置步骤见 [SETUP.md](./SETUP.md)。

## 使用

安装后直接用自然语言：

- "帮我把这个视频转成逐字稿：/path/to/video.mp4"
- "转录桌面上的会议录音，要区分说话人，加标点"
- "把这个文件夹里所有视频批量转录"
- "快速转录一下这个音频，不需要说话人识别"

## 输出

每个文件生成 `<原文件名>_逐字稿.txt`，包含：

1. **带时间戳的逐行文本**（可选带说话人标签）
2. **完整文本**（适合直接阅读或二次加工）

## 模型

| 模型 | 大小 | 中文质量 | 场景 |
|------|------|----------|------|
| turbo（默认） | 1.5GB | 优秀 | 正式内容 |
| medium | 1.4GB | 良好 | 备选 |
| small | 461MB | 一般 | 追求速度 |
| base | 139MB | 较差 | 快速预览 |

首次运行自动下载模型到 skill 目录的 `models/` 下。

## 支持格式

视频：`.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm`
音频：`.mp3` `.wav` `.flac` `.aac` `.ogg` `.m4a` `.wma`

## License

[CC BY-NC-SA 4.0](../LICENSE) · 43 COLLEGE 凯寓 (KAIYU) 出品
