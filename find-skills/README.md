# find-skills — 技能发现与安装

让 AI 帮你从 skills.sh 生态中找到需要的技能，一句话搜索、验证质量、自动安装。不用自己翻 GitHub。

## 安装

```bash
git clone https://github.com/43COLLEGE/43-Agent-skills.git /tmp/43-Agent-skills
cp -r /tmp/43-Agent-skills/find-skills ~/.claude/skills/
rm -rf /tmp/43-Agent-skills
```

## 使用

对 AI 说：

> *「有没有做 React 测试的技能？」*
> *「找一个能帮我写 changelog 的技能」*
> *「我想给 PR review 找个自动化工具」*

AI 会搜索 skills.sh 生态，验证质量（安装量、来源信誉），推荐后帮你一键安装。

## 依赖

需要 Node.js（提供 `npx` 命令）。未安装时 AI 会提示。

## 许可证

CC BY-NC-SA 4.0 — 详见 [LICENSE](../LICENSE)

43 COLLEGE 凯寓 (KAIYU) 出品
