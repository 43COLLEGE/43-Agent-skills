---
name: project-setup
description: Remotion 项目初始化的完整步骤和文件结构
metadata:
  tags: setup, init, create, project, structure, registerRoot, package
---

# 项目初始化

## 创建新项目

```bash
npx create-video@latest my-video
cd my-video
npm start  # 启动预览
```

## 关键文件结构

```
my-video/
├── src/
│   ├── index.ts          # 入口：必须调用 registerRoot
│   ├── Root.tsx           # 合成注册：所有 <Composition> 定义
│   └── MyComposition.tsx  # 视频组件
├── public/                # 静态资源（图片、音频、字体）
├── package.json
└── tsconfig.json
```

## 入口文件 `src/index.ts`

**必须**包含 `registerRoot` 调用，否则渲染会报错找不到合成：

```ts
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);
```

## `package.json` 注意事项

```json
{
  "type": "module"
}
```

- `"type": "module"` — 使用 ES Module（`import/export`），推荐
- `"type": "commonjs"` — 使用 CommonJS（`require/module.exports`）

如果项目中有独立的 Node.js 脚本（如生成配音、转录字幕），`"type"` 的值决定了这些脚本能否直接运行。使用 `"module"` 时，脚本文件可以用 `.ts` 后缀配合 `node --strip-types` 运行。

## 添加 Remotion 包

使用 `remotion add` 而不是直接 `npm install`，确保版本一致：

```bash
npx remotion add @remotion/media          # 音视频
npx remotion add @remotion/three          # 3D
npx remotion add @remotion/captions       # 字幕
npx remotion add @remotion/transitions    # 过渡动画
npx remotion add @remotion/install-whisper-cpp  # 语音转文字
```

## 静态资源

放在 `public/` 目录下，通过 `staticFile()` 引用：

```tsx
import { staticFile } from "remotion";

// public/logo.png → staticFile("logo.png")
// public/audio/bgm.mp3 → staticFile("audio/bgm.mp3")
```

不要用相对路径引用 `public/` 下的文件，Remotion 渲染时工作目录不固定。
