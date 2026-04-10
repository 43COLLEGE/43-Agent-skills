# Social Media Scout

> 作者：**凯寓 (KAIYU)** · v1.0

跨平台社交媒体数据查询工具。支持抖音、TikTok、小红书、B站、微博、快手、Instagram、YouTube、Twitter、微信公众号等 10+ 平台，926+ 个 API 接口。

## 前提条件

- **Python 3.8+**（检查：终端输入 `python3 --version`，能看到版本号就行）
- **Claude Code**（你正在用的工具）
- **TikHub API Key**（免费注册，下面有详细步骤）

> 核心功能只使用 Python 内置库，无需额外安装。下载 B站视频需要 `yt-dlp`（使用时 AI 会引导安装）。

## 安装步骤

### 第 1 步：下载到正确位置

```bash
# 如果 skills 目录不存在，先创建
mkdir -p ~/.claude/skills

# 将 social-media-scout 文件夹放到 skills 目录下
# （如果你是从 GitHub 下载的 ZIP，解压后把 social-media-scout 文件夹复制过去）
```

最终目录结构应该是：
```
~/.claude/skills/
  └── social-media-scout/
        ├── SKILL.md
        ├── README.md
        └── scripts/
              ├── tikhub_client.py
              └── config.json.template
```

### 第 2 步：获取 TikHub API Key

1. 打开 https://user.tikhub.io ，用邮箱注册账号并登录
2. 点击左侧菜单 **「API 设置」→「API 密钥」**
3. 点击右上角红色按钮 **「+ 创建 API 密钥」**
4. 给密钥起个名字（比如"Claude Code"），确认创建
5. 在密钥列表里，点击 Key 列旁边的 **复制图标**，复制密钥
6. 保存好这个密钥，下一步要用

> TikHub 注册后有少量免费额度可供测试，正式使用需要充值。每次成功查询消耗少量额度，失败的请求不计费。

### 第 3 步：填入 API Key

```bash
cd ~/.claude/skills/social-media-scout/scripts

# 复制配置模板
cp config.json.template config.json
```

用任意文本编辑器打开 `config.json`，把 `your_tikhub_api_key_here` 替换成你刚才复制的 API Key：

```json
{
  "api_key": "把你的API Key粘贴到这里",
  "base_url": "https://mcp.tikhub.io",
  "mcp_proxy_exe": "",
  "mcp_proxy_zip": ""
}
```

> **只需要改第一行的 `api_key`**，其他三行保持不动。

保存文件，配置完成！

### 第 4 步：开始使用

回到 Claude Code，直接用自然语言说你想查什么：

```
你：搜索抖音用户"李佳琦"，看看他最近发了什么视频
你：帮我查一下这个小红书博主的粉丝数和最新笔记
你：解析这个分享链接：https://v.douyin.com/xxx
你：看看B站今天的热搜是什么
你：提取这篇微信公众号文章的内容：https://mp.weixin.qq.com/s/xxx
```

Claude 会自动调用 Social Media Scout 完成查询。**你不需要记任何命令或接口名。**

## 支持的平台

| 平台 | 状态 | 能做什么 |
|------|------|---------|
| 抖音 | ✅ 稳定 | 搜索用户/视频、用户资料、作品列表、评论、热搜、下载视频 |
| TikTok | ✅ 稳定 | 搜索视频、用户资料、作品列表、评论 |
| 小红书 | ✅ 稳定 | 搜索笔记/用户、用户笔记列表、评论 |
| B站 | ⚠️ 部分接口不稳定 | 搜索用户/视频、用户动态、评论、弹幕、热搜（部分接口偶尔 500） |
| 快手 | ✅ 稳定 | 搜索、用户资料、作品列表 |
| 微博 | ✅ 稳定 | 搜索、用户资料 |
| Instagram | ✅ 稳定 | 用户资料、作品列表 |
| YouTube | ✅ 稳定 | 搜索、视频详情 |
| Twitter/X | ✅ 稳定 | 搜索、用户资料 |
| 微信公众号 | 🔧 有限支持 | 文章列表、文章内容提取（需要文章链接，不支持按名称搜索） |

## 文件说明

```
social-media-scout/
├── SKILL.md                      # AI 读取的技能定义（含完整 API 速查表和踩坑记录，不用管）
├── README.md                     # 你正在看的文件
├── .gitignore                    # Git 忽略规则
└── scripts/
    ├── tikhub_client.py          # 核心代码（不用手动运行）
    ├── config.json.template      # 配置模板（参考用）
    └── config.json               # 运行时配置（自动排除，不提交到 Git）
```

## 安全提醒

- `config.json` 已在 `.gitignore` 中排除，不会被提交到 Git
- **不要把 `config.json` 分享给任何人**，里面有你的 API Key

## 故障排查

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| `FileNotFoundError: config.json` | 没创建配置文件 | 回到第 3 步，运行 `cp config.json.template config.json` 并填入 API Key |
| API 返回 401 Unauthorized | API Key 不对 | 打开 `config.json`，检查 `api_key` 是否和 TikHub 网站上一致，注意别多空格 |
| API 返回 500 | 平台接口不稳定（尤其 B站） | 正常现象，稍后重试，或让 Claude 换个接口试试 |
| MCP 代理连不上 | 正常，代理是可选的 | 无需处理，客户端会自动降级为 REST 直调模式 |
| 网络连接失败 | 网络问题 | 检查网络，部分平台可能需要科学上网 |

**其他问题？** 提 Issue：[GitHub Issues](https://github.com/43COLLEGE/43-Agent-skills/issues)

## 许可证

[CC BY-NC-SA 4.0](../LICENSE) · 43 COLLEGE 凯寓 (KAIYU) 出品
