---
name: feishu-assistant
description: 飞书助手：消息、文档、知识库、通讯录、日历、群聊、任务、多维表格（Base）、邮箱。当用户提到飞书相关操作（发消息、写文档、查知识库、看群聊、管理任务、操作多维表格、查邮件、发邮件、收件箱）时使用此技能。
---

# 飞书助手

> 作者：43 COLLEGE 凯寓 (KAIYU) 出品
> 版本：v2.0

通过飞书 Open API 实现消息、文档、知识库、日历、群聊、多维表格、邮箱等操作。
支持两种运行模式：有 lark-cli 时自动代理（零配置），有 app_secret 时直连 API（更快）。

## 首次配置

如果命令报错找不到 config.json 或 `app_id` 为空，读取本目录下的 `SETUP.md` 并按其中的流程引导用户完成配置。

## 快速开始

### 给同事发消息

1. 读取 `scripts/config.json` 中的 `team_members` 字段（姓名 → open_id 映射）
2. 找到目标同事的 open_id
3. 执行 send-message 命令

```bash
python3 scripts/feishu_client.py send-message --type text --content "消息内容" --receive_id "ou_xxx" --receive_id_type open_id
```

### 给群里发消息

1. 读取 `scripts/config.json` 中的 `default_chat_id`
2. `receive_id_type` 改为 `chat_id`

```bash
python3 scripts/feishu_client.py send-message --type text --content "消息内容" --receive_id "oc_xxx" --receive_id_type chat_id
```

**重要**：发消息前，先从 `config.json` 的 `team_members` 查找目标同事的 open_id。

## 平台说明（跨平台兼容）

**Python 命令**：macOS/Linux 用 `python3`，Windows 用 `python`。调用前先检测哪个可用。

**路径格式**：
- macOS/Linux：`~/.claude/skills/feishu-assistant/`
- Windows：`%USERPROFILE%\.claude\skills\feishu-assistant\`

所有命令通过 `python3 scripts/feishu_client.py <command>`（macOS/Linux）或 `python scripts\feishu_client.py <command>`（Windows）调用。
执行前必须先 cd 到本 skill 的根目录。

## 核心命令

### 消息

```bash
# 发送文本消息（支持 text/post/interactive/image）
python3 scripts/feishu_client.py send-message --type text --content "内容" --receive_id "ou_xxx" --receive_id_type open_id

# 向群组发消息
python3 scripts/feishu_client.py send-message --type text --content "内容" --receive_id "oc_xxx" --receive_id_type chat_id

# 读取群消息
python3 scripts/feishu_client.py get-chat-messages --chat_id "oc_xxx" --page_size 20
```

### 群聊管理

```bash
# 创建群聊并拉入成员（members 为逗号分隔的 open_id）
python3 scripts/feishu_client.py create-chat --name "项目群" --members "ou_xxx,ou_yyy" --description "项目讨论群"

# 向已有群添加成员
python3 scripts/feishu_client.py add-chat-members --chat_id "oc_xxx" --members "ou_xxx,ou_yyy"

# 从群中移除成员
python3 scripts/feishu_client.py remove-chat-members --chat_id "oc_xxx" --members "ou_xxx"

# 获取群聊信息
python3 scripts/feishu_client.py get-chat-info --chat_id "oc_xxx"

# 修改群聊信息
python3 scripts/feishu_client.py update-chat --chat_id "oc_xxx" --name "新群名" --description "新描述"

# 列出群聊成员
python3 scripts/feishu_client.py list-chat-members --chat_id "oc_xxx"

# 解散群聊（不可恢复）
python3 scripts/feishu_client.py dissolve-chat --chat_id "oc_xxx"
```

### 文档

```bash
# 创建文档
python3 scripts/feishu_client.py create-doc --title "标题" --content "内容"

# 更新文档
python3 scripts/feishu_client.py update-doc --doc_token "doxcxxx" --content "新内容"
```

### 知识库

```bash
# 列出所有知识库空间
python3 scripts/feishu_client.py list-wiki-spaces

# 列出空间下的文章
python3 scripts/feishu_client.py list-wiki-nodes --space_id "xxx" --page_size 50

# 读取文章纯文本内容
python3 scripts/feishu_client.py read-wiki-node --node_token "xxx"
```

### 通讯录与组织

```bash
# 显示团队通讯录（从缓存读取）
python3 scripts/feishu_client.py show-contacts

# 刷新通讯录缓存
python3 scripts/feishu_client.py refresh-contacts

# 显示知识库列表
python3 scripts/feishu_client.py show-spaces

# 刷新知识库缓存
python3 scripts/feishu_client.py refresh-spaces

# 显示组织信息
python3 scripts/feishu_client.py show-org

# 通过邮箱查用户
python3 scripts/feishu_client.py get-user --email "user@example.com"
```

### 文件上传

```bash
python3 scripts/feishu_client.py upload-file --file_path "path/to/file.pdf" --parent_node "fldxxx"
```

### 日历

```bash
# 查看我的日历列表
python3 scripts/feishu_client.py list-calendars

# 查看指定时间范围内的日程
python3 scripts/feishu_client.py list-events --calendar_id primary --start_time "2026-03-02 00:00" --end_time "2026-03-08 23:59"

# 创建日程
python3 scripts/feishu_client.py create-event --summary "周会" --start_time "2026-03-05 14:00" --end_time "2026-03-05 15:00" --description "每周例会" --attendees "ou_xxx,ou_yyy"

# 查看日程详情
python3 scripts/feishu_client.py get-event --calendar_id primary --event_id "xxx"

# 修改日程
python3 scripts/feishu_client.py update-event --calendar_id primary --event_id "xxx" --summary "新标题"

# 删除日程
python3 scripts/feishu_client.py delete-event --calendar_id primary --event_id "xxx"

# 查询忙闲信息（查自己）
python3 scripts/feishu_client.py query-freebusy --start_time "2026-03-29" --end_time "2026-03-30"

# 查询指定同事的忙闲信息
python3 scripts/feishu_client.py query-freebusy --start_time "2026-03-29 09:00" --end_time "2026-03-29 18:00" --user_id "ou_xxx"

# 推荐多人共同空闲时段（自动查询所有参会人的忙闲，计算交集）
python3 scripts/feishu_client.py suggest-meeting-time --start_time "2026-03-31 09:00" --end_time "2026-03-31 18:00" --attendees "ou_xxx,ou_yyy" --duration 30
```

**忙闲查询 vs 空闲推荐**：
- `query-freebusy`：查一个人的忙碌时段列表（含 RSVP 状态），只返回时间不返回日程详情
- `suggest-meeting-time`：查多人，自动计算共同空闲，返回最多 5 个推荐时段

### 任务管理

```bash
# 创建任务
python3 scripts/feishu_client.py create-task --summary "完成周报" --due "2026-03-31 18:00" --description "整理本周工作内容"

# 创建无截止时间的简单任务
python3 scripts/feishu_client.py create-task --summary "回复客户邮件"

# 查看我的任务列表
python3 scripts/feishu_client.py list-tasks --page_size 20

# 获取任务详情
python3 scripts/feishu_client.py get-task --task_id "xxx"

# 更新任务标题或描述
python3 scripts/feishu_client.py update-task --task_id "xxx" --summary "新标题" --description "新描述"

# 标记任务为已完成
python3 scripts/feishu_client.py complete-task --task_id "xxx"

# 或通过 update-task 标记完成
python3 scripts/feishu_client.py update-task --task_id "xxx" --completed
```

**说明**：任务管理使用飞书 Task v2 API，需要用户授权（user_token）。`complete-task` 是 `update-task --completed` 的快捷方式。

### 电子表格（Sheets）

```bash
# 创建电子表格
python3 scripts/feishu_client.py create-sheet --title "销售数据"

# 读取表格数据（token 从表格 URL 提取）
python3 scripts/feishu_client.py read-sheet --token "shtcnXXX" --range "Sheet1!A1:C10"

# 写入数据（二维数组 JSON）
python3 scripts/feishu_client.py write-sheet --token "shtcnXXX" --range "Sheet1!A1" --values '[["姓名","分数"],["张三","95"]]'

# 追加数据到表格末尾
python3 scripts/feishu_client.py append-sheet --token "shtcnXXX" --range "Sheet1" --values '[["李四","88"]]'
```

**token 获取方式**：从电子表格 URL 中提取，格式为 `https://xxx.feishu.cn/sheets/{token}`

**与多维表格的区别**：电子表格（Sheets）是传统行列表格，适合简单数据录入和计算；多维表格（Base）是结构化数据库，支持字段类型、视图、关联等高级功能。

### 多维表格（Base）

```bash
# 列出数据表
python3 scripts/feishu_client.py list-base-tables --app_token "bascnXXX"

# 列出字段
python3 scripts/feishu_client.py list-base-fields --app_token "bascnXXX" --table_id "tblXXX"

# 列出记录
python3 scripts/feishu_client.py list-base-records --app_token "bascnXXX" --table_id "tblXXX" --page_size 50

# 获取单条记录
python3 scripts/feishu_client.py get-base-record --app_token "bascnXXX" --table_id "tblXXX" --record_id "recXXX"

# 创建记录（fields 为 JSON）
python3 scripts/feishu_client.py create-base-record --app_token "bascnXXX" --table_id "tblXXX" --fields '{"名称":"测试","状态":"进行中"}'

# 批量创建记录
python3 scripts/feishu_client.py batch-create-base-records --app_token "bascnXXX" --table_id "tblXXX" --records '[{"名称":"A"},{"名称":"B"}]'

# 更新记录
python3 scripts/feishu_client.py update-base-record --app_token "bascnXXX" --table_id "tblXXX" --record_id "recXXX" --fields '{"状态":"已完成"}'

# 删除记录
python3 scripts/feishu_client.py delete-base-record --app_token "bascnXXX" --table_id "tblXXX" --record_id "recXXX"

# 创建数据表
python3 scripts/feishu_client.py create-base-table --app_token "bascnXXX" --name "新表"

# 创建字段（field_type: 1=文本, 2=数字, 3=单选, 4=多选, 5=日期, 7=复选框, 11=人员, 15=超链接, 17=附件）
python3 scripts/feishu_client.py create-base-field --app_token "bascnXXX" --table_id "tblXXX" --field_name "优先级" --field_type 3
```

**app_token 获取方式**：从多维表格 URL 中提取，格式为 `https://xxx.feishu.cn/base/{app_token}`

### 邮箱（Mail）

```bash
# 获取当前用户邮箱地址
python3 scripts/feishu_client.py mail-profile

# 查看收件箱
python3 scripts/feishu_client.py list-mail --folder INBOX --page_size 20

# 查看已发送
python3 scripts/feishu_client.py list-mail --folder SENT

# 读取邮件
python3 scripts/feishu_client.py read-mail --message_id "xxx"

# 搜索邮件
python3 scripts/feishu_client.py search-mail --query "关键词"

# 发送邮件（默认 HTML 格式）
python3 scripts/feishu_client.py send-mail --to "alice@example.com" --subject "标题" --body "<p>正文</p>"

# 发送纯文本 / 多收件人 / 带抄送
python3 scripts/feishu_client.py send-mail --to "a@x.com,b@x.com" --cc "c@x.com" --subject "标题" --body "正文" --plain_text

# 创建草稿（不发送）
python3 scripts/feishu_client.py draft-mail --to "alice@example.com" --subject "标题" --body "正文"
```

**重要**：发送邮件前必须确认收件人和内容。

## 初始化

详见「首次配置」章节和 `SETUP.md`。

## 缓存说明

- **通讯录**：`scripts/cache/contacts.json`，格式 `[{"name": "张三", "open_id": "ou_xxx", ...}]`
- **知识库列表**：`scripts/cache/wiki_spaces.json`，格式 `[{"name": "空间名", "space_id": "xxx", ...}]`
- **默认群聊 ID**：`scripts/config.json` 的 `default_chat_id`
- **team_members**：`scripts/config.json` 的 `team_members`（姓名 → open_id 映射）

如果缓存不存在，运行 `refresh-contacts` 或 `refresh-spaces` 生成。

## 双模式架构

feishu_client.py 支持两种运行模式，自动选择：

| 模式 | 条件 | 特点 |
|------|------|------|
| **直连模式** | config.json 中有 app_secret + cache/user_token.json | 直接调飞书 API，最快 |
| **lark-cli 代理模式** | 无 app_secret 或无 user_token，但有 lark-cli | 通过 `lark-cli api` 代理请求，零配置 |

已有配置（app_secret + OAuth token）的老用户继续走直连模式，无任何影响。
新用户通过 lark-cli 配置后，所有请求自动走 lark-cli 代理，无需手动管理 token。

## 故障排除

| 错误 | 原因 | 修复 |
|------|------|------|
| config.json 不存在 | 未运行安装引导 | 运行 `python3 scripts/setup.py` |
| lark-cli 未安装 | 无 lark-cli 且无 app_secret | `npm install -g @larksuite/cli && lark-cli config init --new && lark-cli auth login --domain all` |
| lark-cli 调用失败 | token 过期 | `lark-cli auth login --domain all` 重新授权 |
| 通讯录/知识库缓存为空 | 未刷新缓存 | 运行 `refresh-contacts` 或 `refresh-spaces` |
| Bot has NO availability | 机器人可用范围不含目标用户 | 在飞书开放平台将应用可用范围设为「所有员工」并重新发布 |
| 权限不足 | 缺少所需 scope | `lark-cli auth login --domain all` 补充授权 |

飞书开放平台后台：https://open.feishu.cn/app
