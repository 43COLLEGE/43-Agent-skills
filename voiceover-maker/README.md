# voiceover-maker

把任意文本变成 MP3 配音文件。多 provider 自动路由：中文走 MiniMax，英文走 ElevenLabs。

---

## 能力

| 能力 | 说明 |
|------|------|
| 多 provider 路由 | 按语种自动选 provider（中文 MiniMax，英文 ElevenLabs），也可手动指定 |
| 长稿分段 | 超长文本自动按段落 / 句末标点 / 硬切分段，多段拼接为单个 MP3 |
| 情绪/语速调节 | MiniMax 支持 7 种情绪、0.5–2.0 倍速、±12 音调、0.5–2.0 倍音量 |
| Dry-run 估价 | 调 API 前先估字符数和费用，长稿避免烧爆 |
| 音色试听 | 5 秒样本快速对比音色，挑出最合适的再正式合成 |
| 本地缓存 | 相同输入命中缓存复用，不重复调 API |
| 用量统计 | 本地 JSONL 日志，按天/月/key 拆分查看消耗 |
| 双 key fallback | MiniMax 主 key 鉴权失败/配额耗尽时自动切 fallback key |
| 远端音色发现 | 拉取 MiniMax 全量约 300 个系统音色，按关键词筛选 |
| 零依赖 | 仅 Python 3 标准库，跨平台 Mac/Windows/Linux |

## 安装

**方式一：让 Claude 自动安装**

```
帮我安装这个 skill：https://github.com/43COLLEGE/43-Agent-skills（voiceover-maker 目录）
```

**方式二：手动**

```bash
git clone https://github.com/43COLLEGE/43-Agent-skills /tmp/43-skills
cp -r /tmp/43-skills/voiceover-maker ~/.claude/skills/voiceover-maker
rm -rf /tmp/43-skills
```

## 前置条件

- **Python 3**（macOS/Linux 通常自带；Windows 从 https://python.org 下载安装时**务必勾选 "Add Python to PATH"**，否则命令会找不到）
- **ElevenLabs API Key**（英文配音，注册有免费额度，具体限额见官网）
- **MiniMax API Key**（中文配音，注册有免费额度，具体限额见官网）

只配一个 provider 也能跑，详细配置步骤见 [SETUP.md](./SETUP.md)。

## 使用

安装并配置完后直接用自然语言：

- "把这段文字录成音频：今天天气不错，适合出门散步"
- "用 lyrical 这个音色把桌面上的旁白稿.txt 录成 MP3"
- "做一段视频旁白，要沉稳的播报员声音，速度稍慢一点"
- "把这篇文章录成音频，先估一下要花多少钱"
- "试听一下 radio_host 这个音色"
- "看看我这个月用了多少 TTS 字符"

## 输出

每次合成生成一个 `tts-{provider}-{voice}-{时间戳}.mp3` 到桌面（可在 `config.json` 改 `default_output_dir`）。

试听样本生成 `preview-{provider}-{voice}.mp3`，会自动覆盖同名文件。

## 音色

### MiniMax（中文，10 个内置预设）

`lyrical`（默认）/ `gentleman` / `radio_host` / `executive` / `announcer` / `sincere` / `news_anchor` / `sweet_lady` / `warm_bestie` / `wise_women`

MiniMax 系统总共约 300 个音色，可用 `--list-remote-voices` 查全量，挑出来加进 `config.json`。

### ElevenLabs（英文，6 个内置预设）

`rachel`（默认）/ `adam` / `bella` / `antoni` / `domi` / `josh`

ElevenLabs Voice Library 还有更多，复制 voice_id 到 `config.json` 即可使用。

## 计费速查

| Provider | 计费规则 | 中文 1000 字大约 |
|---|---|---|
| MiniMax `speech-2.8-hd` | 按 UTF-8 字节，1 汉字 ≈ 2 字符 | 约 ¥0.4（按量付费） |
| ElevenLabs `eleven_multilingual_v2` | 按字符数 | 约 $0.30 ≈ ¥2.1 |

具体价格以 provider 官网为准。长稿前用 dry-run 估算更稳。

## 测试

```bash
cd ~/.claude/skills/voiceover-maker
python3 -m unittest tests.test_logic -v
```

26 个单元测试覆盖核心逻辑（语种检测/分段/计费/缓存/估价），不调网络。

## 设计要点

- **零依赖**：纯 Python 3 标准库，不用装包
- **缓存层**：内容哈希索引，相同输入直接复用
- **网络重试**：5xx + URLError 自动指数退避重试，4xx 不重试
- **fallback 严格白名单**：HTTP 401/402/403/429 + MiniMax 业务码 1004/1008/1029/1039/2013/2049 触发切 key，避免误判浪费配额
- **MP3 帧拼接**：长稿多段直接 byte 拼接，同 codec/bitrate 不需要 ffmpeg
- **段间静默**：内置 300ms 静默 asset，避免长稿段间接得太赶

## License

CC BY-NC-SA 4.0 — 详见仓库根目录 [LICENSE](https://github.com/43COLLEGE/43-Agent-skills/blob/main/LICENSE)。

43 COLLEGE 凯寓 (KAIYU) 出品
