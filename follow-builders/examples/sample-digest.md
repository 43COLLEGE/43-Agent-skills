# 示例日报

以下是一份 AI 构建者日报的示例输出。

---

# AI 构建者日报 — 2026-03-14

---

## X / Twitter

### Andrej Karpathy — 前 Tesla AI 总监、Eureka Labs 创始人

发了一个长帖讨论「Software 3.0」：自然语言编程会在五年内让传统写代码变成小众技能。核心论点是编译目标正在从机器码变成 LLM prompt。引发大量争议。同时发布了一个 Eureka Labs 新教程，从零搭建一个代码解释器。

https://x.com/karpathy/status/example1
https://x.com/karpathy/status/example2

### Guillermo Rauch — Vercel CEO

宣布 Vercel 新产品「v0 Teams」：多人协作 AI 原型设计，多个人可以同时对同一个 UI 出 prompt、迭代。他自己的原话：「Google Docs for vibe coding」。下周上线。

https://x.com/rauchg/status/example3

### Amanda Askell — Anthropic 研究员

发了一条关于 AI 安全评测的深度思考：「我们在测好测的东西，不是测该测的东西。能力评测告诉你模型能做什么，对齐评测应该告诉你模型会主动做什么。」附了一篇 Anthropic 行为评估的新论文。

https://x.com/AmandaAskell/status/example4

---

## 播客

### Latent Space —「为什么 Agent 总是失败（以及怎么修）」

**一句话要点**：大部分 agent 失败不是智力问题，是工具调用问题。模型推理没问题，就是不能在对的时间调对的 API。

当可用工具超过 15 个时，工具选择准确率从 95% 暴跌到 60%。解法不是更聪明的模型，而是按任务做工具筛选。「Eval 驱动开发」正在取代氛围驱动的 prompt 调优。如果你不测量，你就是在猜。主持人预测 2026 年 agent 框架会从 50 多个收敛到 3-4 个赢家，他们押注 OpenAI Agents SDK、Claude Code 和 LangGraph。

https://youtube.com/watch?v=example123

### No Priors —「Scaling Laws 已死，Scaling Laws 万岁」(Ilya Sutskever)

**一句话要点**：预训练 scaling law 已到拐点，但后训练和推理时 compute scaling 才刚开始。

Ilya 认为下一个 10 倍提升来自让模型在推理时「想更久」，而不是更大的预训练。合成数据质量比数量重要得多：「一本完美的教科书抵得上一百万条 Reddit 评论。」他对开源出人意料地乐观：「差距会缩小到以月计，而不是以年计。」

https://youtube.com/watch?v=example456

---

> 回复可随时调整投递设置、关注列表或摘要风格。
