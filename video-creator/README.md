# video-creator

告诉 AI 你想做什么视频，它帮你用代码生成。不用学 After Effects，不用剪辑软件，说一句话就能出片。

基于 [Remotion](https://remotion.dev)（用 React 写视频的框架），内置 30+ 规则文件，AI 写代码时自动加载对应知识，少踩坑、少走弯路。

> 43 COLLEGE 凯寓 (KAIYU) 出品

## 能干什么

- **做动画** — 文字入场、数据可视化、产品展示，不用一帧一帧调
- **加字幕** — 丢音频进去自动生成字幕，逐词高亮，支持多语言
- **做 3D** — Three.js 3D 场景直接渲染成视频，地球、产品模型、粒子效果
- **配音** — 接 ElevenLabs 等 TTS 服务，输入文案自动生成 AI 旁白
- **加音乐和音效** — 背景音乐、音效、音量渐入渐出、多轨混音
- **数据图表动画** — 柱状图、折线图、饼图，数据驱动的动态图表
- **场景过渡** — 淡入淡出、滑动、擦除等转场效果

## 安装

打开 Claude Code，把下面这句话发给 AI：

```
帮我安装 43-Agent-skills 的 video-creator：
git clone https://github.com/43COLLEGE/43-Agent-skills.git /tmp/43-Agent-skills && cp -r /tmp/43-Agent-skills/video-creator ~/.claude/skills/ && rm -rf /tmp/43-Agent-skills
```

## 使用

装好之后，直接跟 AI 说你要做什么视频就行：

- *「帮我做一个 30 秒的产品介绍视频，要有文字动画和背景音乐」*
- *「把这段文案生成 AI 配音，配上字幕做成视频」*
- *「做一个数据可视化动画，展示上季度的销售趋势」*
- *「用 3D 做一个地球旋转的效果，配上旁白」*

AI 会自动创建 Remotion 项目、写代码、渲染输出视频文件。

## 环境要求

- Node.js >= 18
- ffmpeg（音视频处理需要）
- 可选：ElevenLabs API Key（AI 配音功能）

首次使用时 AI 会自动检查环境并引导配置。

## 许可证

[CC BY-NC-SA 4.0](../LICENSE)
