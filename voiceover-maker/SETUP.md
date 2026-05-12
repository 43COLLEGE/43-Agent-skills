# 首次配置指南

这份指南写给完全不懂技术的人。配置一次，之后告诉 AI"把这段文字录成音频"就行。

---

## 你能用这个工具做什么

- 把任意一段文字（中文/英文）变成 MP3 音频文件
- 中文用 MiniMax 的声音（中文质量好），英文用 ElevenLabs 的声音
- 自动分段处理长文章、估算费用、试听音色、缓存复用

---

## 第一步：复制配置模板

在 skill 目录里找到 `config.json.template`，复制一份改名为 `config.json`：

**Mac / Linux：**
```bash
cd ~/.claude/skills/voiceover-maker
cp config.json.template config.json
```

**Windows：**
```cmd
cd %USERPROFILE%\.claude\skills\voiceover-maker
copy config.json.template config.json
```

或者直接告诉 AI："帮我把 voiceover-maker 的 config.json.template 复制成 config.json"。

---

## 第二步：拿 ElevenLabs API Key（用于英文配音）

如果只做中文，可以跳过这一步。

### 2-1. 注册 ElevenLabs 账号

打开 https://elevenlabs.io 点右上角 `Sign Up`，邮箱注册即可。免费额度每月 10,000 字符，够测试。

### 2-2. 获取 API Key

1. 登录后右上角头像 → `My Account` → 左侧 `API Keys`
2. 点 `Create API Key`
3. 名字随便填（比如"voiceover"），权限默认即可
4. 复制显示的那串以 `sk_` 开头的字符（**只显示一次，先存到备忘录**）

### 2-3. 填进 config.json

打开刚才复制的 `config.json`，找到这一段：

```json
"elevenlabs": {
  "api_key": "",
```

把空字符串换成你的 key：

```json
"elevenlabs": {
  "api_key": "sk_你刚才复制的key",
```

---

## 第三步：拿 MiniMax API Key（用于中文配音）

如果只做英文，可以跳过这一步。

### 3-1. 注册 MiniMax 账号

打开 https://platform.minimaxi.com 注册（手机号或邮箱都行，国内访问无障碍）。新用户有免费额度。

### 3-2. 获取 API Key

1. 登录后顶部菜单 → `账户管理` → `接口密钥`
2. 点 `创建新密钥`
3. 名字随便填（比如"voiceover"）
4. 复制显示的 key（以 `sk-` 开头）

### 3-3. 填进 config.json

找到这一段：

```json
"minimax": {
  "api_key": "",
  "fallback_keys": [],
```

把 key 填进去：

```json
"minimax": {
  "api_key": "sk-你刚才复制的key",
  "fallback_keys": [],
```

> **可选：双 key fallback**
> 如果你同时买了 MiniMax Token Plan 套餐 + 按量付费 key，可以把 Token Plan key 放 `api_key`（更便宜），把按量付费 key 放 `fallback_keys`（兜底）：
> ```json
> "api_key": "sk-tokenplan-key-xxx",
> "fallback_keys": ["sk-payg-key-xxx"]
> ```
> 主 key 鉴权失败/配额耗尽时会自动切到 fallback。只用一个 key 完全可以，`fallback_keys` 留空数组就行。

---

## 第四步：验证配置

### 4-1. 跑预检命令

让 AI 跑一遍预检，不会烧 API 字符：

> "帮我跑一下 voiceover-maker 的预检"

AI 会执行 `python3 ~/.claude/skills/voiceover-maker/scripts/tts.py --check`，正常的话会看到类似输出：

```
=== voiceover-maker 环境预检 ===

  Python：3.x.x
  config.json：✓ 解析成功
  静默 asset：✓ 存在
  ElevenLabs key：✓ 已配置（sk_xxxxx...）
  MiniMax key：✓ 已配置（sk-xxxxx...）

  网络可达性：
    elevenlabs: ✓ ...
    minimax: ✓ ...

✅ 预检通过，skill 可以正常使用。
```

如果某项 ✗，按提示修复（最常见：JSON 格式被记事本改坏了——用 VS Code 等编辑器重存）。

### 4-2. 真实合成测试

预检通过后，再让 AI 实际生成一段：

> "用 voiceover-maker 把"你好世界，这是一段配音测试"转成 MP3"

正常的话会在桌面生成一个 `tts-minimax-lyrical-时间戳.mp3` 文件，打开能听到声音就成了。

如果想测英文：

> "用 voiceover-maker 把 'Hello world, this is a voiceover test' 转成 MP3"

会在桌面生成一个 `tts-elevenlabs-rachel-时间戳.mp3`。

---

## 配置完成后，日常怎么用

直接用自然语言告诉 AI：

> "把这段文字录成音频：[你的文本]"
> "用 lyrical 这个音色把桌面上的旁白稿.txt 录成 MP3"
> "做一段 30 秒的视频旁白，文本是 XXX，要用沉稳的播报员声音"
> "把这篇文章录成音频，先估一下要花多少钱"（→ AI 会先 dry-run）

AI 会自动选合适的 provider、音色、参数，不用你管命令行。

---

## 常见问题

**只配了一个 provider 能用吗？**
能。只配 ElevenLabs 的话，中文也会走 ElevenLabs（质量略差但能用）。只配 MiniMax 的话，英文也会走 MiniMax。建议两个都配。

**API Key 泄露了怎么办？**
去对应平台后台把那个 key 删掉，重新生成一个，更新 `config.json`。

**长文章会不会很贵？**
先让 AI 跑一次 dry-run（"先估一下要多少钱再做"），AI 会自动用 `--dry-run` 算字符数和费用。MiniMax 中文按 UTF-8 字节算，1 个汉字 ≈ 2 字符。

**输出文件在哪？**
默认 `~/Desktop`（桌面）。想改的话编辑 `config.json` 的 `default_output_dir`。

**MiniMax 中文质量为什么比 ElevenLabs 好？**
ElevenLabs 主要训练英文语料，中文音色少且部分音色发音不达标。MiniMax 是国产模型，中文音色多、发音地道、支持情绪/语速等参数。所以默认中文走 MiniMax。

**Windows 路径用 `\` 还是 `/`？**
都能用。Python 在 Windows 下两种分隔符都能识别。命令里写 `\` 更标准。

**为什么不直接用环境变量？**
也可以。设置 `ELEVENLABS_API_KEY` / `MINIMAX_API_KEY` 环境变量会覆盖 `config.json` 里的值。CI 或多台机器共用时方便。
