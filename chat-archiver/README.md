# chat-archiver — 对话入库器

回顾 AI 对话，提取有价值的洞察和知识，分类后存入你的知识库。

## 功能

- 自动回顾当前对话，提取知识、决策、方法、技术方案
- 过滤操作性内容和试错过程，只保留有价值的结论
- 两种分类模式：**Config 映射**（固定分类）和**自动发现**（AI 智能判断）
- 自动去重：主题重叠时追加而非新建
- 写入前必须用户确认，不会自动操作

## 安装

```bash
# 克隆到 Claude Code skills 目录
git clone https://github.com/43COLLEGE/43-Agent-skills.git /tmp/43-Agent-skills
cp -r /tmp/43-Agent-skills/chat-archiver ~/.claude/skills/chat-archiver
```

## 使用

在你的知识库目录下，对 AI 说：

- "入库"
- "归档对话"
- "把这次对话存下来"
- `/chat-archiver`

### 零配置使用

不需要任何配置。AI 会自动扫描当前目录结构，读取索引文件，智能判断分类。

### 自定义分类

创建 `config.json`（从模板复制），定义你的知识库结构：

```json
{
  "knowledge_base": "~/my-notes",
  "categories": {
    "技术笔记": "notes/tech/",
    "项目记录": "projects/",
    "个人想法": "thoughts/"
  }
}
```

详见 `SETUP.md`。

## 配置项

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `knowledge_base` | 当前工作目录 | 知识库根目录 |
| `index_file` | `_INDEX.md` | 索引文件名（留空跳过） |
| `file_prefix` | `chat-` | 生成文件名前缀 |
| `categories` | 无 | 分类映射（无则自动发现） |
| `default_category` | 无 | 兜底分类目录 |

## 许可证

CC BY-NC-SA 4.0 — 详见 [LICENSE](../LICENSE)

43 COLLEGE 凯寓 (KAIYU) 出品
