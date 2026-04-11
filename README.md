# 43 Agent Skills

实用的 Claude Code 技能合集，让 AI 帮你完成更多事。

> 43 COLLEGE 凯寓 (KAIYU) 出品

## 安装

打开 Claude Code，把下面这句话发给 AI：

```
帮我安装 43-Agent-skills：
git clone https://github.com/43COLLEGE/43-Agent-skills.git /tmp/43-Agent-skills && cp -r /tmp/43-Agent-skills/feishu-assistant /tmp/43-Agent-skills/social-media-scout /tmp/43-Agent-skills/web-browser /tmp/43-Agent-skills/media-transcriber /tmp/43-Agent-skills/email-invoice-processor /tmp/43-Agent-skills/chat-archiver ~/.claude/skills/ && rm -rf /tmp/43-Agent-skills
```

只要某几个？把不需要的技能名从命令里删掉就行。AI 会自动执行安装，首次使用时还会引导你完成配置。

---

## 速查表

| 技能 | 能帮你干什么 | 配置门槛 |
|------|------------|----------|
| [feishu-assistant](./feishu-assistant/) | 用自然语言操作飞书——发消息、写文档、查日历、建任务、管知识库、操作多维表格、收发邮箱，不用再在飞书里切来切去 | 需要飞书企业账号 |
| [social-media-scout](./social-media-scout/) | 抖音、小红书、B站、TikTok、快手、微博、Instagram、YouTube、Twitter、微信公众号的数据一句话查到——粉丝画像、视频数据、评论分析、趋势追踪，做竞品分析和选题研究不用手动翻 | 注册 API Key 即可 |
| [web-browser](./web-browser/) | 让 AI 操控真实 Chrome 浏览器——登录需要账号密码的后台抓数据、搞定小红书/微信公众号等反爬平台、截图取证、填表提交 | 需要 Node.js + Chrome |
| [media-transcriber](./media-transcriber/) | 丢个音视频文件进来，出带时间戳的逐字稿，能分清谁说了什么（说话人识别），还能自动加标点断句。开完会、听完播客不用手动整理 | 安装 ffmpeg 即可 |
| [email-invoice-processor](./email-invoice-processor/) | 自动从 QQ/163/Gmail/Outlook 邮箱里按日期范围捞发票，识别金额、税号、开票日期等字段，按购买方分类生成 Excel 汇总表。报销季不用一封封翻邮件 | 开启邮箱 IMAP 即可 |
| [chat-archiver](./chat-archiver/) | 和 AI 聊出了好东西？一句"入库"自动提炼精华、分类存进你的知识库。支持 Obsidian/Logseq 等主流工具，也支持自定义目录结构 | 零配置可用 |

---

## 技能详情

### 🔗 [feishu-assistant](./feishu-assistant/) — 飞书全家桶

用自然语言操作飞书——发消息、写文档、查日历、建任务、管知识库、操作多维表格、收发邮箱，不用再在飞书里切来切去。

> **配置**：需要飞书企业账号
>
> *「给张三发条飞书消息，说下午三点开会」*
> *「把这份周报发到飞书文档，同时同步到知识库」*
> *「查一下明天日历上有几个会，帮我把冲突的重新排一下」*

### 🔍 [social-media-scout](./social-media-scout/) — 跨平台数据挖掘

抖音、小红书、B站、TikTok、快手、微博、Instagram、YouTube、Twitter、微信公众号的数据一句话查到——粉丝画像、视频数据、评论分析、趋势追踪，做竞品分析和选题研究不用手动翻。

> **配置**：注册 TikHub API Key 即可
>
> *「查一下这个抖音号最近 30 天的数据趋势，粉丝增长、播放量、互动率」*
> *「小红书上搜"露营装备"，看看哪些笔记互动最高，总结爆款选题规律」*
> *「对比这三个 B站 UP主的粉丝画像和内容风格差异」*

### 🌐 [web-browser](./web-browser/) — 真实浏览器操控

让 AI 操控真实 Chrome 浏览器——登录需要账号密码的后台抓数据、搞定小红书/微信公众号等反爬平台、截图取证、填表提交。

> **配置**：需要 Node.js + Chrome
>
> *「登录我的后台，截个图看看今天的订单数据」*
> *「打开这个需要登录的网页，帮我把表格数据抓下来」*
> *「小红书搜索这个关键词，把前 10 条笔记的标题和点赞数整理出来」*

### 🎙️ [media-transcriber](./media-transcriber/) — 音视频转文字

丢个音视频文件进来，出带时间戳的逐字稿，能分清谁说了什么（说话人识别），还能自动加标点断句。开完会、听完播客不用手动整理。

> **配置**：安装 ffmpeg 即可
>
> *「把桌面上的会议录音转成逐字稿，标注每个人说了什么」*
> *「这个播客有两个嘉宾，帮我分别提取每个人的核心观点」*
> *「把这段采访视频转成文字，按时间线整理成会议纪要格式」*

### 📧 [email-invoice-processor](./email-invoice-processor/) — 邮箱发票自动处理

自动从 QQ/163/Gmail/Outlook 邮箱里按日期范围捞发票，识别金额、税号、开票日期等字段，按购买方分类生成 Excel 汇总表。报销季不用一封封翻邮件。

> **配置**：开启邮箱 IMAP 即可
>
> *「把上个月邮箱里的发票全部提取出来，生成 Excel 汇总表」*
> *「只处理 3 月 15 号到 3 月 31 号的发票，按购买方分类」*
> *「扫一下最近的邮件，看看有没有漏报的发票」*

### 📝 [chat-archiver](./chat-archiver/) — 对话精华入库

和 AI 聊出了好东西？一句"入库"自动提炼精华、分类存进你的知识库。支持 Obsidian/Logseq 等主流工具，也支持自定义目录结构。

> **配置**：零配置可用
>
> *「入库」*
> *「把今天讨论的架构决策存到知识库」*
> *「归档这次对话，技术方案部分单独存一份」*

---

## 常见问题

**Q：我不会用命令行怎么办？**
把安装那段话直接发给 Claude Code，AI 帮你执行。之后所有操作都是自然语言，不需要碰命令行。

**Q：Windows 能用吗？**
能。所有技能都做了跨平台兼容。Windows 用户的 skills 目录在 `C:\Users\你的用户名\.claude\skills\`。

**Q：这些技能免费吗？**
技能本身免费开源。部分技能依赖第三方服务：
- **飞书助手**：需要飞书企业账号（飞书本身免费）
- **Social Media Scout**：需要 TikHub API Key（注册有免费额度可测试）
- **media-transcriber**：转录免费，说话人识别需注册 HuggingFace（免费）
- **email-invoice-processor / chat-archiver**：完全免费

## 许可证

[CC BY-NC-SA 4.0](./LICENSE) — 可自由使用、修改、分享，但**不可商用**，修改后需以相同协议分享。

---

问题反馈：[GitHub Issues](https://github.com/43COLLEGE/43-Agent-skills/issues) | 43 COLLEGE 凯寓 (KAIYU) 出品
