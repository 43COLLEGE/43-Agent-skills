# 飞书助手 (feishu-assistant)

> 作者：**凯寓 (KAIYU)** · v2.0

让 AI 帮你操作飞书：发消息、读知识库、写文档、查日历、操作多维表格、收发邮件，一句话搞定。

## 前提条件

- **Python 3.8+**（检查：终端输入 `python3 --version`，能看到版本号就行）
- **Claude Code**（你正在用的工具）
- **飞书企业账号**（个人版飞书也可以，需要能创建应用）

> Node.js 是可选的。安装引导会自动检测，有就用，没有会切换到手动流程，最终效果一样。

## 安装步骤

### 第 1 步：下载到正确位置

```bash
# 如果 skills 目录不存在，先创建
mkdir -p ~/.claude/skills

# 将 feishu-assistant 文件夹放到 skills 目录下
# （如果你是从 GitHub 下载的 ZIP，解压后把 feishu-assistant 文件夹复制过去）
```

最终目录结构应该是：
```
~/.claude/skills/
  └── feishu-assistant/
        ├── SKILL.md
        ├── README.md
        └── scripts/
              ├── setup.py
              └── ...
```

### 第 2 步：运行安装引导

```bash
cd ~/.claude/skills/feishu-assistant
python3 scripts/setup.py
```

安装引导会自动帮你完成所有配置：

1. 检测环境（Python 包、Node.js 等），缺什么自动装
2. 引导你在飞书开放平台创建应用（会打开一个链接，点一下就好）
3. 授权所有需要的权限（也是点一个链接）
4. 拉取你的团队通讯录（自动完成）

全程大约 3-5 分钟，只需要点 2 个链接。

> **如果 setup.py 中途报错？** 别慌，重新运行 `python3 scripts/setup.py` 即可。它会从断点继续，不会重复已完成的步骤。

### 第 3 步：开始使用

回到 Claude Code，直接用自然语言说你想做什么：

```
你：给张三发消息，说下午三点开会
你：帮我创建一个项目讨论群，把张三和李四拉进来
你：查一下我明天有什么日程
你：在多维表格里新增一条记录
你：帮我看看知识库里关于报销流程的文档
```

Claude 会自动调用飞书助手完成操作。**你不需要记任何命令。**

## 功能一览

| 功能 | 能做什么 |
|------|---------|
| 消息 | 发送/读取私聊和群聊消息 |
| 群聊 | 创建群、拉人/踢人、改群信息 |
| 文档 | 创建和更新飞书文档 |
| 知识库 | 浏览和阅读知识库文章 |
| 日历 | 查看/创建/修改/删除日程，查忙闲、推荐开会时间 |
| 任务 | 创建/查看/完成任务 |
| 电子表格 | 读写表格数据 |
| 多维表格 | 读写记录、管理字段和数据表 |
| 邮箱 | 收发邮件、搜索邮件 |
| 通讯录 | 查看团队成员信息 |

## 文件说明

```
feishu-assistant/
├── SKILL.md                    # AI 读取的技能定义（不用管）
├── README.md                   # 你正在看的文件
├── .gitignore                  # Git 忽略规则
└── scripts/
    ├── setup.py                # 安装引导（只需运行一次）
    ├── feishu_client.py        # 核心代码（不用手动运行）
    ├── oauth_server.py         # OAuth 授权（备用）
    ├── replace_doc.py          # 文档工具（高级）
    ├── scopes.json             # 权限清单（手动配置时参考）
    ├── config.json.template    # 配置模板（参考用）
    ├── config.json             # 运行时配置（自动生成，别删）
    └── cache/                  # 缓存目录（自动生成）
```

## 安全提醒

- `config.json` 和 `cache/` 已在 `.gitignore` 中排除，不会被提交到 Git
- **不要把 `config.json` 或 `cache/user_token.json` 分享给任何人**，里面有你的认证信息

## 故障排查

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| setup.py 报错 "npm not found" | 没有 Node.js，但没关系 | setup.py 会自动切换到手动配置流程，按提示操作即可 |
| "Bot has NO availability" | 飞书应用的可用范围太窄 | 去[飞书开放平台](https://open.feishu.cn/app)，把应用可用范围设为「所有员工」，重新发布 |
| 发消息报权限不足 | 缺少对应权限 | 运行 `lark-cli auth login --domain all` 重新授权 |
| 通讯录是空的 | 缓存未生成 | 在 Claude Code 里说"刷新通讯录" |
| lark-cli token 过期 | 长时间未使用 | 运行 `lark-cli auth login --domain all` |
| config.json 被误删 | — | 重新运行 `python3 scripts/setup.py` |

**其他问题？** 提 Issue：[GitHub Issues](https://github.com/43COLLEGE/43-Agent-skills/issues)

## 许可证

[CC BY-NC-SA 4.0](../LICENSE) · 43 COLLEGE 凯寓 (KAIYU) 出品
