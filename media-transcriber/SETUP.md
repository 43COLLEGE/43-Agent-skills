# 首次配置指南

这份指南写给完全不懂技术的人。按步骤操作，配置一次，之后每次转录直接告诉 AI 视频路径就行。

---

## 你能用这个工具做什么

- 把视频或音频里的话，自动变成文字稿
- 区分谁在说话（说话人A、说话人B……）
- 自动加标点符号，而不是一大段没有逗号句号的原始文字

---

## 第一步：安装 ffmpeg（处理视频的基础工具）

**Mac 用户：**

1. 打开"终端"（在应用程序 → 实用工具里，或者用 Spotlight 搜"终端"）
2. 粘贴这行命令，回车：
   ```
   brew install ffmpeg
   ```
3. 等它安装完（可能要几分钟）

> 如果提示 brew 不存在，先去 https://brew.sh 按照首页那行命令装 Homebrew，再回来装 ffmpeg。

**Windows 用户：**

1. 按 Win+R，输入 `cmd`，回车，打开命令行
2. 粘贴这行命令，回车：
   ```
   winget install ffmpeg
   ```

---

## 第二步：配置说话人识别（可选，想区分谁在说话才需要）

说话人识别依赖一个叫 HuggingFace 的 AI 平台。需要注册账号、申请三个模型的访问权限、获取一个密钥。听起来麻烦，但实际上每步就是点几下鼠标。

### 2-1. 注册 HuggingFace 账号

打开 https://huggingface.co/join ，填邮箱和密码注册。注册完验证一下邮箱。

### 2-2. 申请三个模型的访问权限

说话人识别需要用到三个 AI 模型，每个都要单独申请。一次性全部搞定，之后永久有效。

**按顺序打开这三个链接，每个都登录后点"Agree and access repository"：**

1. https://huggingface.co/pyannote/speaker-diarization-3.1
2. https://huggingface.co/pyannote/segmentation-3.0
3. https://huggingface.co/pyannote/speaker-diarization-community-1

每个页面都会让你填 Company/university 和 Website，随便填就行（比如填你的名字和 https://github.com/你的用户名）。

### 2-3. 生成访问密钥（Token）

1. 登录状态下，打开 https://huggingface.co/settings/tokens
2. 点右上角"New token"
3. 名字随便填（比如"whisper"）
4. 权限选"Read"就够
5. 点"Create token"
6. 复制显示的那串以 `hf_` 开头的字符（这就是你的 Token，**只显示一次，先存到备忘录**）

### 2-4. 把密钥告诉 AI，让它帮你保存

把 Token 告诉 AI（也就是 Claude），AI 会自动运行以下命令保存：

**Mac / Linux：**
```
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py --hf-token 你的token --save-token
```

**Windows：**
```
python ${CLAUDE_SKILL_DIR}\scripts\transcribe.py --hf-token 你的token --save-token
```

保存之后，以后用说话人识别时就不用再粘贴 Token 了。

---

## 第三步：验证配置是否正确

让 AI 运行这个预检命令：

**Mac / Linux：**
```
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py --check
```

**Windows：**
```
python ${CLAUDE_SKILL_DIR}\scripts\transcribe.py --check
```

正常的话会看到类似这样的输出：

```
✓ ffmpeg 已安装
✓ openai-whisper 已安装
✓ ANTHROPIC_API_KEY 已设置
✓ HuggingFace token 已配置
  ✓ pyannote/speaker-diarization-3.1
  ✓ pyannote/segmentation-3.0
  ✓ pyannote/speaker-diarization-community-1
  所有模型授权正常，说话人识别可用。
```

如果某项显示 ✗，按照提示操作就行。

---

## 配置完成后，日常怎么用

直接告诉 AI：

> "帮我把桌面上的会议录音.mp4 转成逐字稿，要区分说话人，并加上标点"

AI 会自动调用这个工具，你不需要知道任何命令行的事情。

---

## 常见问题

**首次运行很慢？**

首次转录时需要下载 Whisper 模型（默认 turbo，约 1.5GB），取决于网速可能需要几分钟。模型下载后保存在本地，以后不会重复下载。

**转录需要多长时间？**

大约是视频时长的 1/4 到 1/2。一个 10 分钟的视频，转录大约需要 2-3 分钟。说话人识别会额外多花 2-5 分钟。

**我的 Token 泄露了怎么办？**

去 https://huggingface.co/settings/tokens 把那个 Token 删掉，重新生成一个，再告诉 AI 更新一下配置（重新运行 `--hf-token 新token --save-token`）。

**说话人识别准确吗？**

对于清晰的对话录音，准确率通常在 80-90%。背景噪音大、多人同时说话时会下降。说话人标签是自动分配的（说话人A、B、C……），不会自动识别出"这是张三"。

**Token 只需要配置一次吗？**

是的。保存之后存在本地，不会过期，除非你主动删除。
