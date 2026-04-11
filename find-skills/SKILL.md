---
name: find-skills
description: 帮助用户发现和安装 Claude Code 技能。当用户问"怎么做 X"、"找一个能做 X 的技能"、"有没有技能可以……"或想扩展 AI 能力时使用此技能。通过 skills.sh 生态搜索、验证质量、协助安装。
---

# find-skills — 技能发现与安装

> 43 COLLEGE 凯寓 (KAIYU) 出品 | v1.0

从开放的 agent 技能生态中发现和安装技能。依赖 Node.js（`npx` 命令），未安装时提示用户先装 Node.js。

## 何时使用

- 用户问"怎么做 X"，而 X 可能有现成的技能
- 用户说"找一个做 X 的技能"
- 用户想扩展 agent 的能力
- 用户想搜索工具、模板或工作流

## 核心命令

```bash
npx skills find [query]     # 搜索技能
npx skills add <package>    # 安装技能（-g 全局，-y 跳过确认）
npx skills check            # 检查更新
npx skills update           # 更新所有已安装技能
```

**浏览技能**：https://skills.sh/

## 执行步骤

### 第 1 步：理解需求

识别用户需要的领域和具体任务。

### 第 2 步：先查排行榜

在运行 CLI 搜索前，先查看 [skills.sh 排行榜](https://skills.sh/) 看是否已有知名技能。排行榜按安装量排名，展示最受欢迎的选项。

热门来源：
- `vercel-labs/agent-skills` — React、Next.js、Web 设计（10万+ 安装量）
- `anthropics/skills` — 前端设计、文档处理（10万+ 安装量）

### 第 3 步：搜索技能

```bash
npx skills find react performance
npx skills find pr review
npx skills find changelog
```

### 第 4 步：验证质量再推荐

**不要仅凭搜索结果就推荐。** 验证：

1. **安装量** — 优先 1K+，低于 100 要谨慎
2. **来源信誉** — 官方来源（`vercel-labs`、`anthropics`、`microsoft`）更可信
3. **GitHub stars** — 源仓库 star 不足 100 需持怀疑态度

### 第 5 步：展示选项

向用户展示技能名称、功能、安装量、安装命令和详情链接：

```
找到一个技能："react-best-practices"
来自 Vercel 工程团队的 React 性能优化指南（18.5万安装量）

安装：npx skills add vercel-labs/agent-skills@react-best-practices -g -y
详情：https://skills.sh/vercel-labs/agent-skills/react-best-practices
```

### 第 6 步：协助安装

用户确认后执行：

```bash
npx skills add <owner/repo@skill> -g -y
```

## 搜索关键词参考

| 分类 | 关键词 |
|------|-------|
| Web 开发 | react, nextjs, typescript, css, tailwind |
| 测试 | testing, jest, playwright, e2e |
| DevOps | deploy, docker, kubernetes, ci-cd |
| 文档 | docs, readme, changelog, api-docs |
| 代码质量 | review, lint, refactor, best-practices |
| 设计 | ui, ux, design-system, accessibility |
| 效率工具 | workflow, automation, git |

## 没有找到时

1. 告知用户没有现成技能
2. 提议用自身能力直接完成任务
3. 建议创建自己的技能：`npx skills init my-skill`
