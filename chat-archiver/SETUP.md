# 首次初始化指南

chat-archiver 需要知道"把内容存到哪里、怎么分类"。首次使用时按本指南完成初始化，之后不再需要。

---

## 第 1 步：确认知识库位置

先告知用户当前工作目录，确认这是不是知识库：

```
当前工作目录：[路径]
这是你的知识库目录吗？如果不是，请告诉我正确路径。
```

确定 `knowledge_base` 路径后继续。

---

## 第 2 步：检测环境

### 识别已知工具

扫描 knowledge_base 根目录是否存在以下标志：

| 标志文件 | 工具 | 自动适配 |
|----------|------|---------|
| `.obsidian/` | Obsidian | `index_file` → `README.md` |
| `.logseq/` | Logseq | `index_file` → `""`（不使用索引） |
| `mkdocs.yml` | MkDocs | `index_file` → `index.md` |

检测到时告知：`"检测到这是 Obsidian vault，索引文件已适配为 README.md。"`

未检测到时默认 `index_file` = `_INDEX.md`。

### 判断目录状态

**有内容（有子目录和文件）**：

扫描目录结构，读索引文件了解各目录用途，向用户展示发现的结构：

```
你的知识库结构：
- knowledge/ai/    — AI 领域知识（12 个文件）
- knowledge/dev/   — 开发技术（8 个文件）
- projects/        — 项目记录（5 个文件）
- insights/        — 个人洞察（3 个文件）

我会按这个结构分类归档。需要调整吗？
```

**有子文件夹但都是空的**：

```
你的知识库有以下目录，但都是空的：
- projects/
- notes/
- insights/

请简要说明每个目录的用途，我来按此分类。
或者直接告诉我："放 notes/ 就行"。
```

**完全空目录**：

提供预设模板快速选择：

```
当前目录是空的，选一个起步结构？

A. 极简 — 一个文件夹装所有
   notes/

B. 三分法 — 大多数人够用
   tech/        ← 技术知识
   projects/    ← 项目相关
   thoughts/    ← 想法洞察

C. 知识管理 — 重度用户
   knowledge/ai/     ← AI 领域
   knowledge/dev/    ← 开发技术
   projects/         ← 项目记录
   insights/         ← 个人洞察
   workflows/        ← 工作流

D. 我自己定义（告诉我你想要的分类）

E. 不分类，全部放当前目录
```

用户选择后，创建对应目录。

---

## 第 3 步：生成并保存配置

根据前两步的结果，自动生成 `${CLAUDE_SKILL_DIR}/config.json`：

```bash
# Mac / Linux
cp ${CLAUDE_SKILL_DIR}/config.json.template ${CLAUDE_SKILL_DIR}/config.json
```

```cmd
# Windows
copy ${CLAUDE_SKILL_DIR}\config.json.template ${CLAUDE_SKILL_DIR}\config.json
```

然后用 Python 或 Edit 工具写入实际配置。示例：

```json
{
  "knowledge_base": "/Users/xxx/my-notes",
  "index_file": "README.md",
  "file_prefix": "chat-",
  "categories": {
    "技术知识": "tech/",
    "项目相关": "projects/",
    "想法洞察": "thoughts/"
  },
  "default_category": "thoughts/"
}
```

### 配置字段说明

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `knowledge_base` | 否 | 当前工作目录 | 知识库根目录绝对路径 |
| `index_file` | 否 | `_INDEX.md` | 索引文件名，留空跳过索引更新 |
| `file_prefix` | 否 | `chat-` | 生成文件名前缀 |
| `categories` | 否 | 无（自动发现） | 分类名 → 目录路径映射 |
| `default_category` | 否 | 无 | 兜底分类目录 |

**不填 `categories`** → 每次自动发现模式，AI 动态判断。
**填了 `categories`** → 映射模式，按固定分类写入。

---

## 第 4 步：验证

告知用户：

```
配置已保存。现在可以开始入库了——说"入库"即可。
```

返回 SKILL.md 第 1 步继续执行。

---

## 后续修改

随时可以修改 `${CLAUDE_SKILL_DIR}/config.json`：
- 增减分类 → 编辑 `categories`
- 换知识库目录 → 修改 `knowledge_base`
- 换索引文件名 → 修改 `index_file`
- 换文件前缀 → 修改 `file_prefix`

也可以删除 config.json 重新走一遍初始化。

---

## 常见问题

**Q：知识库不在当前目录怎么办？**
config.json 里设置 `knowledge_base` 为绝对路径。

**Q：用 Obsidian / Logseq，索引文件不叫 `_INDEX.md`？**
初始化时会自动检测并适配。也可以手动设置 `index_file`。

**Q：不想要 `chat-` 前缀？**
config.json 里设置 `"file_prefix": "note-"` 或 `""`。

**Q：两种模式可以混用吗？**
可以。`categories` 有值用映射模式，没值用自动发现。其他字段两种模式通用。
