---
name: video-creator
description: 用代码创建视频（Remotion）— 动画、字幕、3D、音频、过渡等 30+ 规则按需加载
---

处理 Remotion 视频项目代码时，按需加载对应规则文件获取详细说明和代码示例。  
首次使用时加载 [SETUP.md](SETUP.md) 检查环境依赖。

## 项目与渲染

- [project-setup.md](rules/project-setup.md) - 项目初始化、文件结构、registerRoot、package.json 配置
- [rendering.md](rules/rendering.md) - 渲染/预览/调试命令大全（render、still、studio）

## 核心概念

- [compositions.md](rules/compositions.md) - 合成定义、静态帧、文件夹、默认属性、动态元数据
- [calculate-metadata.md](rules/calculate-metadata.md) - 动态设置合成的时长、尺寸和属性
- [parameters.md](rules/parameters.md) - 使用 Zod schema 使视频可参数化
- [sequencing.md](rules/sequencing.md) - 序列模式：延迟、裁剪、限制元素时长

## 动画与过渡

- [animations.md](rules/animations.md) - 基础动画技巧
- [timing.md](rules/timing.md) - 插值曲线：线性、缓动、弹簧动画
- [transitions.md](rules/transitions.md) - 场景过渡模式
- [trimming.md](rules/trimming.md) - 裁剪模式：剪掉动画的开头或结尾

## 文字与字幕

- [text-animations.md](rules/text-animations.md) - 文字排版和文字动画模式
- [measuring-text.md](rules/measuring-text.md) - 文本尺寸测量、自适应容器、溢出检测
- [fonts.md](rules/fonts.md) - 加载 Google Fonts 和本地字体
- [subtitles.md](rules/subtitles.md) - 字幕处理总览
- [display-captions.md](rules/display-captions.md) - 显示字幕
- [import-srt-captions.md](rules/import-srt-captions.md) - 导入 SRT 字幕文件
- [transcribe-captions.md](rules/transcribe-captions.md) - 语音转字幕

## 媒体素材

- [assets.md](rules/assets.md) - 导入图片、视频、音频和字体
- [images.md](rules/images.md) - 使用 Img 组件嵌入图片
- [videos.md](rules/videos.md) - 嵌入视频：裁剪、音量、速度、循环、音高
- [gifs.md](rules/gifs.md) - 显示与时间线同步的 GIF
- [lottie.md](rules/lottie.md) - 嵌入 Lottie 动画
- [transparent-videos.md](rules/transparent-videos.md) - 渲染带透明度的视频

## 音频

- [audio.md](rules/audio.md) - 音频导入、裁剪、音量、速度、音高
- [audio-visualization.md](rules/audio-visualization.md) - 音频可视化：频谱柱状图、波形图、低音响应
- [sfx.md](rules/sfx.md) - 音效
- [voiceover.md](rules/voiceover.md) - 使用 ElevenLabs TTS 添加 AI 配音

## 媒体信息提取

- [get-audio-duration.md](rules/get-audio-duration.md) - 获取音频时长（Mediabunny）
- [get-video-duration.md](rules/get-video-duration.md) - 获取视频时长（Mediabunny）
- [get-video-dimensions.md](rules/get-video-dimensions.md) - 获取视频宽高（Mediabunny）
- [extract-frames.md](rules/extract-frames.md) - 在指定时间戳提取视频帧（Mediabunny）
- [can-decode.md](rules/can-decode.md) - 检查浏览器是否能解码视频（Mediabunny）

## 数据可视化与 3D

- [charts.md](rules/charts.md) - 图表模式：柱状图、饼图、折线图、股票图
- [3d.md](rules/3d.md) - 使用 Three.js / React Three Fiber 创建 3D 内容
- [maps.md](rules/maps.md) - 使用 Mapbox 添加地图并制作动画

## 工具与样式

- [tailwind.md](rules/tailwind.md) - 在 Remotion 中使用 TailwindCSS
- [ffmpeg.md](rules/ffmpeg.md) - FFmpeg 操作：裁剪视频、检测静音等
- [measuring-dom-nodes.md](rules/measuring-dom-nodes.md) - 测量 DOM 元素尺寸
- [light-leaks.md](rules/light-leaks.md) - @remotion/light-leaks 光泄漏叠加效果
