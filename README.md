# 43 Agent Skills

实用的 Claude Code 技能合集，让 AI 帮你完成更多事。

> 43 COLLEGE 凯寓 (KAIYU) 出品

## 技能列表

| 技能 | 功能 | 配置门槛 |
|------|------|----------|
| [feishu-assistant](./feishu-assistant/) | 飞书助手 — 消息、文档、知识库、日历、多维表格、邮箱 | 需要飞书企业账号 |
| [social-media-scout](./social-media-scout/) | 跨平台社交媒体数据查询 — 抖音/小红书/B站/TikTok 等 10+ 平台 | 注册 API Key 即可 |
| [web-browser](./web-browser/) | 联网策略 + CDP 浏览器操作 + 站点经验积累 | 需要 Node.js 22+ 和 Chrome |
| [media-transcriber](./media-transcriber/) | 音视频逐字稿转录 — Whisper + 说话人识别 + 标点恢复 | 安装 ffmpeg 即可 |
| [email-invoice-processor](./email-invoice-processor/) | 邮箱发票自动提取 + 字段识别 + Excel 汇总 | 开启邮箱 IMAP 即可 |
| [chat-archiver](./chat-archiver/) | 对话入库器 — 提取对话精华，分类存入知识库 | 零配置可用，可选自定义 |

## 安装方法

### 第 1 步：下载技能

**方式 A：Git 克隆（推荐）**

```bash
# 如果 skills 目录不存在，先创建
mkdir -p ~/.claude/skills

# 克隆整个仓库
cd ~/.claude/skills
git clone https://github.com/43COLLEGE/43-Agent-skills.git

# 把你需要的技能移到 skills 根目录（Claude Code 要求技能在 ~/.claude/skills/ 下）
mv 43-Agent-skills/feishu-assistant ~/.claude/skills/
mv 43-Agent-skills/social-media-scout ~/.claude/skills/
mv 43-Agent-skills/web-browser ~/.claude/skills/
mv 43-Agent-skills/media-transcriber ~/.claude/skills/
mv 43-Agent-skills/email-invoice-processor ~/.claude/skills/
mv 43-Agent-skills/chat-archiver ~/.claude/skills/
```

**方式 B：手动下载**

1. 打开 https://github.com/43COLLEGE/43-Agent-skills
2. 点击绿色 **Code** 按钮 → **Download ZIP**
3. 解压后，将需要的技能文件夹复制到 `~/.claude/skills/` 目录下

### 第 2 步：配置技能

每个技能首次使用时，AI 会自动检测并引导你完成配置。你也可以提前查看各技能的配置说明：

- [feishu-assistant 配置指南](./feishu-assistant/README.md)
- [social-media-scout 配置指南](./social-media-scout/README.md)
- [web-browser 配置指南](./web-browser/README.md)
- [media-transcriber 配置指南](./media-transcriber/README.md)
- [email-invoice-processor 配置指南](./email-invoice-processor/README.md)
- [chat-archiver 配置指南](./chat-archiver/README.md)

### 第 3 步：在 Claude Code 中使用

配置完成后，直接用自然语言告诉 Claude 你想做什么：

```
你：给张三发条飞书消息，说下午三点开会
你：搜索抖音用户"李佳琦"，看看他最近发了什么
你：去小红书搜一下这个品牌的口碑
你：帮我把桌面上的会议录音转成逐字稿，要区分说话人
你：帮我处理上个月邮箱里的发票，生成 Excel
你：入库（把当前对话的精华存到知识库）
```

Claude 会自动识别你的需求，调用对应的技能。

## 常见问题

**Q：`~/.claude/skills/` 目录在哪里？**

- macOS / Linux：打开终端，输入 `open ~/.claude/skills` 或 `cd ~/.claude/skills`
- Windows：路径是 `C:\Users\你的用户名\.claude\skills\`
- 如果目录不存在，运行 `mkdir -p ~/.claude/skills` 创建

**Q：我不会用终端命令行怎么办？**

你只需要完成一次安装配置。之后所有操作都在 Claude Code 里用自然语言完成，不需要再碰命令行。

**Q：这些技能是免费的吗？**

技能本身免费开源。但部分技能依赖第三方服务：
- **飞书助手**：需要飞书企业账号（飞书本身免费）
- **Social Media Scout**：需要 TikHub API Key（注册有少量免费额度可测试，正式使用需充值）
- **media-transcriber**：转录免费，说话人识别需注册 HuggingFace（免费），标点恢复需要 Claude API
- **email-invoice-processor**：完全免费，只需开通邮箱 IMAP 服务
- **chat-archiver**：完全免费，零配置即可使用

## 许可证

[CC BY-NC-SA 4.0](./LICENSE) — 可自由使用、修改、分享，但**不可商用**，修改后需以相同协议分享。

## 反馈与贡献

- 提 Bug / 建议：[GitHub Issues](https://github.com/43COLLEGE/43-Agent-skills/issues)
- 作者：43 COLLEGE 凯寓 (KAIYU) 出品
