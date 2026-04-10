# web-browser

给 Claude Code 装上完整联网能力的 skill。

Claude Code 原本有 WebSearch、WebFetch，但缺少调度策略和浏览器自动化能力。这个 skill 补上的是：**联网策略 + CDP 浏览器操作 + 站点经验积累**。

---

## 能力

| 能力 | 说明 |
|------|------|
| 联网工具自动选择 | WebSearch / WebFetch / curl / Jina / CDP，按场景自主判断，可任意组合 |
| CDP Proxy 浏览器操作 | 直连用户日常 Chrome，天然携带登录态，支持动态页面、交互操作、视频截帧 |
| 三种点击方式 | `/click`（JS click）、`/clickAt`（CDP 真实鼠标事件）、`/setFiles`（文件上传） |
| 并行分治 | 多目标时分发子 Agent 并行执行，共享一个 Proxy，tab 级隔离 |
| 站点经验积累 | 按域名存储操作经验（URL 模式、平台特征、已知陷阱），跨 session 复用 |
| 媒体提取 | 从 DOM 直取图片/视频 URL，或对视频任意时间点截帧分析 |

## 安装

**方式一：让 Claude 自动安装**

```
帮我安装这个 skill：https://github.com/43COLLEGE/43-Agent-skills（web-browser 目录）
```

**方式二：手动**

```bash
git clone https://github.com/43COLLEGE/43-Agent-skills /tmp/43-skills
cp -r /tmp/43-skills/web-browser ~/.claude/skills/web-browser
rm -rf /tmp/43-skills
```

## 前置配置（CDP 模式）

CDP 模式需要 **Node.js 22+** 和 Chrome 开启远程调试。详细步骤见 [SETUP.md](./SETUP.md)。

快速检查：

```bash
bash ~/.claude/skills/web-browser/scripts/check-deps.sh
```

## 使用

安装后直接让 Agent 执行联网任务，skill 自动接管：

- "帮我搜索 xxx 最新进展"
- "读一下这个页面：[URL]"
- "去小红书搜索 xxx 的账号"
- "帮我在创作者平台发一篇图文"
- "同时调研这 5 个产品的官网，给我对比摘要"

## 设计哲学

> Skill = 哲学 + 技术事实，不是操作手册。讲清 tradeoff 让 AI 自己选，不替它推理。

详见 [SKILL.md](./SKILL.md) 中的浏览哲学部分。

## License

[CC BY-NC-SA 4.0](../LICENSE) · 43 COLLEGE 凯寓 (KAIYU) 出品
