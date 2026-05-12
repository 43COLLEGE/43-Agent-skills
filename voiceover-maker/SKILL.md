---
name: voiceover-maker
description: 把任意文本变成 MP3 口播 / 旁白 / 配音 / 朗读 / voiceover / narration 文件。多 provider 自动路由：中文走 MiniMax（speech-2.8-hd），英文走 ElevenLabs。支持长稿自动分段、dry-run 估价、情绪/语速/音调/音量调节、网络重试、双 key 自动 fallback、本地缓存与用量统计。
---

# voiceover-maker — 多 provider TTS 配音生成器

> 作者：43 COLLEGE 凯寓 (KAIYU) 出品
> 版本：v1.0

把任意文本扔进来 → MP3 口播音频文件。**自动按语种路由**：
- 中文 → MiniMax（中文质量更好）
- 英文 → ElevenLabs

## 触发场景

- "用 TTS 把这段话生成口播 / 旁白 / 配音 / 朗读"
- "把这段文字变成语音 / 念出来 / 录成音频"
- "做一段视频旁白 MP3"
- "voice this / narrate this / read this aloud"
- "把这篇公众号文章录成音频"

**不触发**：用户只是问"TTS 是什么意思"——这是科普问题。Skill 仅用于**生成 MP3 文件**。

## 首次使用

需要先配置至少一个 provider 的 API key（推荐两个都配，自动按语种路由）。详见 `SETUP.md`。

## 跨平台兼容

| 项目 | macOS / Linux | Windows |
|------|--------------|---------|
| Python | `python3` | `python` |
| 路径分隔符 | `/` | `\` |
| 脚本路径 | `${CLAUDE_SKILL_DIR}/scripts/tts.py` | `${CLAUDE_SKILL_DIR}\scripts\tts.py` |

下面所有示例用 `python3` 写法（Mac/Linux）。Windows 用户把 `python3` 换成 `python`、把 `/` 换成 `\` 即可。

> **关于 `${CLAUDE_SKILL_DIR}`**：这是文档占位符，代表本 skill 的安装目录（通常是 `~/.claude/skills/voiceover-maker/`）。Claude 在 bash 里执行命令时会自动替换成实际路径，**用户不要直接复制这串到终端**——直接复制粘贴会因变量未定义而失败。要么把命令交给 AI 执行，要么自行替换成具体目录。

## 主脚本

`scripts/tts.py`，零依赖（仅 Python 3 标准库）。

### 预检（首次使用推荐）

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --check
```

不调真实合成 API，只检查：config.json 是否存在且能解析、ElevenLabs / MiniMax key 是否填写、静默 asset 是否就位、两个 endpoint 网络可达性。配完 key 先跑一遍预检，确认没问题再正式合成。

### 基本用法

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "你好世界，这是一段中文测试。"   # auto → MiniMax
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "Hello world, this is a test."   # auto → ElevenLabs
```

输出默认 `~/Desktop`，文件名 `tts-{provider}-{voice}-{timestamp}.mp3`。

### 指定音色（大小写不敏感）

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "中文" --voice lyrical          # MiniMax 抒情男声
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "中文" --voice news_anchor      # MiniMax 新闻女声
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "English" --voice rachel        # ElevenLabs Rachel
```

`--voice` 既接受预设名，也接受原始 voice_id 透传。

### 强制 provider

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "文本" --provider minimax
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "文本" --provider elevenlabs
```

### MiniMax 情绪 / 语速 / 音调 / 音量

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "好消息！" --emotion happy --speed 1.1
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "深夜独白" --voice radio_host --emotion sad --speed 0.9
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "正式播报" --voice executive --pitch -2 --vol 1.2
```

- `--emotion`：`neutral` / `happy` / `sad` / `angry` / `fearful` / `disgusted` / `surprised`
- `--speed`：0.5–2.0
- `--pitch`：-12–12
- `--vol`：0.5–2.0

ElevenLabs 不支持这些参数，传了会被忽略并打 warning。

### 长文本（从文件读 + 自动分段）

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --file 旁白稿.txt
```

- MiniMax 单次上限 9500 字符（保留 buffer，原始 10000）
- ElevenLabs 单次上限 4500 字符
- 超长按 段落 → 句末标点 → 硬切 顺序自动分段，多段 MP3 帧直接拼接

### Dry-run（估字数和价钱，不调 API）

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --file 长稿.txt --dry-run
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "测试文本" --provider minimax --dry-run
```

打印：文本字符数 / 估算计费字符 / 估算费用（CNY/USD）/ 分段数 + 各段字符数。

> **长稿先 dry-run**——MiniMax 中文按 CJK ×2 计费，中文长稿计费字符约是字符数的 2 倍。

### 音色试听（5 秒样本）

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --preview lyrical
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --preview rachel
```

用一句固定示例文本快速生成 5s 样本到 `~/Desktop/preview-{provider}-{voice}.mp3`，方便横向对比选音色。会自动覆盖同名文件。

### 长稿段间静默

多段合成时默认在段与段之间插 **300ms 静默**（避免接得太赶），asset 来自 `assets/silence-300ms-32k-128k-mono.mp3`（与 MiniMax 默认 audio_setting 对齐）。

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --file 长稿.txt --gap-ms 600
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --file 长稿.txt --gap-ms 0
```

`--gap-ms` 按 300ms 单位四舍五入（asset 是 300ms 一个，整数倍重复）。

### 输出控制

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "文本" -o ~/Desktop/旁白.mp3
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "文本" -o -          # stdout（管道）
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "文本" --force       # 覆盖已存在文件
```

默认不覆盖已有文件（保护意外）。

### 列出本地预设

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --list-voices
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --list-voices minimax
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --list-voices elevenlabs
```

### 列出 MiniMax 远端系统音色（约 300 个）

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --list-remote-voices
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --list-remote-voices --filter Lyrical
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --list-remote-voices --filter Female
```

调 `/v1/get_voice` 拿全量 system_voice 列表。挑出来想用的，把 voice_id 加进 `config.json` 的 `providers.minimax.voices` 起个短名。

### 本地缓存

相同的 (provider + voice_id + model + text + voice_settings + audio_setting) 组合命中缓存直接复用，不再调 API。命中时打印 `✓ cache hit [hash]`。

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py "文本" --no-cache    # 跳过缓存
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --clear-cache        # 清空缓存
```

缓存位置：`cache/{16位哈希}.mp3` + `cache/{16位哈希}.json`（meta）。

### 用量统计

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/tts.py --usage
```

打印：今天 / 本月 / 累计的请求数 + 计费字符数；按 key 拆分；缓存大小。
数据来自 `usage.jsonl`（每次真实调 API 时 append 一行 JSON，缓存命中不计）。

### 单元测试（纯逻辑，不调网络）

```bash
cd ${CLAUDE_SKILL_DIR}
python3 -m unittest tests.test_logic -v
```

26 个测试覆盖语种检测、文本分段、计费字符、缓存 key、价格估算。改完核心函数前后跑一下避免回归。

## 路由规则

`config.json` 的 `language_routing`：
```json
{ "zh": "minimax", "en": "elevenlabs" }
```

语种检测：汉字占比 ≥ 15% 视为中文，否则英文。中英混杂且占比 ∈ [10%, 90%] 时打**混合警告**，提示可以用 `--provider` 强制切换。

**优先级**（高到低）：
1. `--provider` 显式指定
2. `--voice` 是某 provider 的预设名 → 反推（同名冲突即报错，要求 `--provider` 明确）
3. auto + 语种检测

## 内置音色预设 + 场景建议

### MiniMax（中文，默认 model `speech-2.8-hd`）

| 预设 | 描述 | 适合场景 |
|---|---|---|
| **lyrical**（默认） | 抒情男声，青年磁性、流畅富表现力 | 理性叙述、感性段落 |
| gentleman | 温润男声，青年磁性、标准普通话 | 产品介绍、客户视频开场 |
| radio_host | 电台男主播，青年富诗意、深夜电台质感 | 文艺向旁白、品牌情绪片 |
| executive | 沉稳高管，中年男性、商务深度 | 商务 PPT 旁白、投资人路演 |
| announcer | 播报男声，中年磁性、清晰权威 | 正式发布、年报数据 |
| sincere | 真诚青年男声，鼓励性、亲和力强 | 用户致谢、社区公告 |
| news_anchor | 新闻女声，中年专业播音腔 | 新闻报道、严肃科普 |
| sweet_lady | 甜美女声，青年温柔 | 轻量教程、消费品 |
| warm_bestie | 温暖闺蜜女声，青年清脆友好 | 生活向 vlog、对话场景 |
| wise_women | 阅历姐姐女声，中年抒情 | 长文章节选、回忆型旁白 |

MiniMax 系统音色总共约 300 个，要新增其他音色：用 `--list-remote-voices` 查 voice_id，加进 `config.json` 的 `providers.minimax.voices`。

### ElevenLabs（英文，默认 model `eleven_multilingual_v2`）

| 预设 | 描述 |
|---|---|
| **rachel**（默认） | 英文女声沉稳，科普旁白 |
| adam | 英文男声深沉 |
| bella | 英文女声年轻活泼 |
| antoni | 英文男声温和 |
| domi | 英文女声有力 |
| josh | 英文男声年轻 |

## 配置 / 凭证

`config.json`（**不要 commit**，含 API key）由 `config.json.template` 复制而来，结构：
```
{
  "default_output_dir": "~/Desktop",
  "default_provider": "auto",
  "language_routing": { "zh": "minimax", "en": "elevenlabs" },
  "providers": {
    "elevenlabs": { api_key, endpoint, default_voice, default_model, voices, voice_settings },
    "minimax":    { api_key, fallback_keys, endpoint, default_voice, default_model, voices, voice_settings, audio_setting }
  }
}
```

只配一个 provider 也能跑——只填了 ElevenLabs 的话，中文文本也会路由到 ElevenLabs（质量略差，但能用）。建议两个都配。

### 环境变量覆盖

优先级：环境变量 > config.json。换机器或 CI 时用：

| 变量 | 作用 |
|---|---|
| `ELEVENLABS_API_KEY` | 覆盖 ElevenLabs key |
| `MINIMAX_API_KEY` | 覆盖 MiniMax 主 key |
| `MINIMAX_FALLBACK_API_KEY` | 追加为最优先的 fallback key |

## 容错机制

### 网络层（同 key 重试）
- HTTP 5xx → 指数退避（2s → 4s）重试 2 次
- URLError（DNS、超时、连接拒绝）→ 同上
- 4xx → 不重试，交业务层判断

### MiniMax 双 key fallback（切 key 重试）

触发条件（**严格白名单**，不再 substring 关键词匹配以避免误判）：
- HTTP 状态码：401 / 402 / 403 / 429
- 业务状态码：1004 / 1008 / 1029 / 1039 / 2013 / 2049

满足任一 → 切到 `fallback_keys` 重试。其它错误（如 2039 文本审核）直接 fail，不浪费 fallback 配额。

`api_key` 优先用（推荐放更便宜的 key，比如 Token Plan key），`fallback_keys` 兜底（按量付费 key）。两者不通用，必须配两个才能用 fallback。只配一个也能跑。

## 注意事项

- ElevenLabs 按字符计费，长文本前先 `--dry-run`
- MiniMax 单次请求文本上限 10000 字符（脚本内取 9500 留 buffer，自动分段）
- MiniMax 计费按 UTF-8 字节，1 个汉字 ≈ 2 字符
- 跨平台：Mac/Windows/Linux 都能跑，零第三方依赖
- 默认输出 `~/Desktop`，可在 `config.json` 改 `default_output_dir`
- 已存在的输出文件默认不覆盖，需 `--force`

## 来源参考

- ElevenLabs 文档：https://elevenlabs.io/docs/api-reference/text-to-speech
- MiniMax 文档：https://platform.minimaxi.com/docs/api-reference/speech-t2a-http.md
- MiniMax voice 列表：https://platform.minimaxi.com/docs/faq/system-voice-id.md
