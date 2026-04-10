---
name: media-transcriber
description: 使用 OpenAI Whisper 将视频/音频文件转为逐字稿（带时间戳）。当用户提供视频路径并要求转录、生成逐字稿、提取字幕时使用此技能。
---

# media-transcriber — 音视频逐字稿转录

> 作者：43 COLLEGE 凯寓 (KAIYU) 出品
> 版本：v1.0

使用 OpenAI Whisper 将视频/音频文件转为带时间戳的逐字稿。支持说话人识别和 Claude 标点恢复。

**第一次运行时会自动创建虚拟环境、安装依赖并下载 Whisper 模型（turbo 约 1.5GB），全程自动，无需手动配置。**

> **重要：首次转录前必须提前告知用户**——模型下载 + 依赖安装可能需要 5-15 分钟（取决于网速），期间终端可能长时间没有新输出，这不是卡死。务必在执行转录命令前向用户说明这一点，避免用户中途强制中断导致环境损坏。

如果运行报错缺少 ffmpeg 或需要配置说话人识别，读 `SETUP.md` 完成首次配置。

## 跨平台兼容

| 项目 | macOS / Linux | Windows |
|------|--------------|---------|
| Python | `python3` | `python` |
| 路径分隔符 | `/` | `\` |
| 脚本路径 | `${CLAUDE_SKILL_DIR}/scripts/transcribe.py` | `${CLAUDE_SKILL_DIR}\scripts\transcribe.py` |

## 调用方式

### 质量模式（默认推荐）

带说话人识别 + Claude 标点恢复，适合正式内容沉淀。速度约为实时的 1/2（turbo 模型，CPU）。

```bash
# 预检环境和权限（推荐首次运行）
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py --check

# 质量模式：说话人识别 + 标点恢复
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py "video.mp4" --language zh --diarize --punctuate

# 指定说话人数量（不指定则自动检测）
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py "video.mp4" --language zh --diarize --punctuate --speakers 2

# 整个文件夹批量转录（质量模式）
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py "/path/to/folder" --language zh --diarize --punctuate

# 强制覆盖已有逐字稿
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py "video.mp4" --language zh --diarize --punctuate --overwrite
```

Python 内联调用：
```python
import sys; sys.path.insert(0, f"{CLAUDE_SKILL_DIR}/scripts")
from transcribe import transcribe_file

transcribe_file("video.mp4", language="zh", diarize=True, punctuate=True)
```

### 快速模式

无说话人识别、无标点恢复，速度快 3-5 倍，适合快速预览内容。

```bash
# 快速模式：仅转录，无说话人，无标点
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py "video.mp4" --language zh

# Windows 快速模式
python ${CLAUDE_SKILL_DIR}\scripts\transcribe.py "C:\path\to\video.mp4" --language zh
```

## 环境信息

- **虚拟环境**: 首次运行自动创建在 skill 目录的 `venv/`
- **模型存储**: `models/`（本地化，不依赖系统缓存）
- **自动安装**: openai-whisper, numpy<2.4, numba, anthropic
- **按需安装**: pyannote-audio（仅 `--diarize` 时安装）
- **GPU**: 无 CUDA 时自动回退 CPU

## 模型选择

| 模型 | 大小 | CPU 速度 | 中文质量 | 场景 |
|------|------|----------|----------|------|
| `turbo` | 1.5GB | ~2x 实时 | 优秀 | **默认推荐** |
| `medium` | 1.4GB | ~3x 实时 | 良好 | turbo 备选 |
| `small` | 461MB | ~1x 实时 | 一般 | 追求速度 |
| `base` | 139MB | ~0.3x 实时 | 较差 | 快速预览 |

> "Nx 实时" = 1 分钟音频需 N 分钟处理（CPU）

## 输出格式

每个文件生成 `<原文件名>_逐字稿.txt`：

**无说话人识别**（默认）：
```
# 文件名

[00:00 - 00:05] 文本内容
[00:05 - 00:12] 文本内容

---

# 完整文本

完整的文本内容。
```

**有说话人识别**（`--diarize`）：
```
# 文件名

**[说话人A]**
[00:00 - 00:05] 文本内容

**[说话人B]**
[00:05 - 00:12] 文本内容

---

# 完整文本

[说话人A] 第一段话内容。
[说话人B] 第二段话内容。
```

支持格式：`.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.mp3` `.wav` `.flac` `.aac` `.ogg` `.m4a` `.wma`

## 关键设计

- **自动 bootstrap**: 首次运行自动创建 venv 并安装依赖，之后直接用 `python3` 调用即可，无需 activate
- **防幻觉**: `condition_on_previous_text=False` 阻止错误传播 + ffprobe 时长过滤超时段落
- **标点引导**: 指定 `--language zh` 时自动注入 `initial_prompt` 引导标点输出
- **Claude 标点恢复**: `--punctuate` 调用 Claude Haiku 对全文做整体标点恢复
- **说话人匹配**: 按时间重叠量将 Whisper 片段匹配到 pyannote 说话人段落
- **按需安装**: pyannote-audio 体积大，仅在使用 `--diarize` 时自动安装
- **模型本地化**: Whisper 模型存放在 `models/` 目录，通过 `download_root` 加载

## 已知限制

1. **NumPy 版本**: numba 需要 numpy<2.4，已在自动安装时固定版本
2. **长视频内存**: 超 2 小时视频 turbo 模型约需 4-6GB RAM
3. **背景音乐**: 末尾纯音乐段可能残留少量误识别
4. **说话人识别精度**: 多人同时说话时准确率下降
5. **标点恢复速度**: Claude API 调用约 3-10 秒延迟
